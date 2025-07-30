# TradingAgents/graph/trading_graph.py

import os
import logging
from pathlib import Path
import json
from datetime import date
from typing import Dict, Any, Tuple, List, Optional

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from langgraph.prebuilt import ToolNode

from tradingagents.agents import *
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.agents.utils.memory import FinancialSituationMemory
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)
from tradingagents.dataflows.interface import set_config

from .conditional_logic import ConditionalLogic
from .setup import GraphSetup
from .propagation import Propagator
from .reflection import Reflector
from .signal_processing import SignalProcessor


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts=["market", "social", "news", "fundamentals"],
        debug=False,
        config: Dict[str, Any] = None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG

        # Setup logging
        self._setup_logging()

        # Update the interface's config
        set_config(self.config)

        # Create necessary directories
        os.makedirs(
            os.path.join(self.config["project_dir"], "dataflows/data_cache"),
            exist_ok=True,
        )

        # Initialize LLMs
        if self.config["llm_provider"].lower() == "openai" or self.config["llm_provider"] == "ollama" or self.config["llm_provider"] == "openrouter":
            self.deep_thinking_llm = ChatOpenAI(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatOpenAI(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif self.config["llm_provider"].lower() == "anthropic":
            self.deep_thinking_llm = ChatAnthropic(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatAnthropic(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif self.config["llm_provider"].lower() == "google":
            from tradingagents.agents.utils.custom_llm_clients import CustomGoogleGenAIClient
            google_api_key = os.getenv("GOOGLE_API_KEY")
            self.deep_thinking_llm = CustomGoogleGenAIClient(model=self.config["deep_think_llm"], api_key=google_api_key)
            self.quick_thinking_llm = CustomGoogleGenAIClient(model=self.config["quick_think_llm"], api_key=google_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config['llm_provider']}")
        
        self.toolkit = Toolkit(config=self.config)

        # Initialize memories
        self.bull_memory = FinancialSituationMemory("bull_memory", self.config)
        self.bear_memory = FinancialSituationMemory("bear_memory", self.config)
        self.trader_memory = FinancialSituationMemory("trader_memory", self.config)
        self.invest_judge_memory = FinancialSituationMemory("invest_judge_memory", self.config)
        self.risk_manager_memory = FinancialSituationMemory("risk_manager_memory", self.config)

        # Create tool nodes and store the raw tool lists
        self.analyst_tools, self.tool_nodes = self._create_tool_nodes()

        # Initialize components
        self.conditional_logic = ConditionalLogic()
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.toolkit,
            self.analyst_tools,  # Pass the raw tool lists
            self.tool_nodes,
            self.bull_memory,
            self.bear_memory,
            self.trader_memory,
            self.invest_judge_memory,
            self.risk_manager_memory,
            self.conditional_logic,
        )

        self.propagator = Propagator()
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict

        # Convert analyst enums to string values if they are not already strings
        analyst_values = [
            analyst.value if hasattr(analyst, "value") else analyst
            for analyst in selected_analysts
        ]

        # Set up the graph
        self.graph = self.graph_setup.setup_graph(analyst_values)
        
        logging.info("TradingAgentsGraph initialized successfully.")

    def _setup_logging(self):
        """Configure the logging for the application."""
        log_dir = Path(self.config.get("results_dir", "results"))
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "trading_agents.log"

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler() # Also log to console
            ]
        )

    def _create_tool_nodes(self) -> Tuple[Dict[str, list], Dict[str, ToolNode]]:
        """Create tool lists and tool nodes for different data sources, aware of the LLM provider."""
        is_google_provider = self.config.get("llm_provider", "").lower() == "google"

        # Define base tools available for all providers
        analyst_tools = {
            "market": [
                self.toolkit.get_YFin_data_online,
                self.toolkit.get_stockstats_indicators_report_online,
                self.toolkit.get_YFin_data,
                self.toolkit.get_stockstats_indicators_report,
            ],
            "social": [
                self.toolkit.get_reddit_stock_info_online,
                self.toolkit.get_reddit_stock_info_offline,
            ],
            "news": [
                self.toolkit.get_finnhub_news_online,
                self.toolkit.get_google_news,
                self.toolkit.get_finnhub_news,
                self.toolkit.get_reddit_news,
            ],
            "fundamentals": [
                self.toolkit.get_income_statement_online,
                self.toolkit.get_balance_sheet_online,
                self.toolkit.get_cashflow_online,
                self.toolkit.get_finnhub_company_insider_sentiment,
                self.toolkit.get_finnhub_company_insider_transactions,
                self.toolkit.get_simfin_balance_sheet_offline,
                self.toolkit.get_simfin_cashflow_offline,
                self.toolkit.get_simfin_income_stmt_offline,
            ],
        }

        # Add provider-specific tools
        if not is_google_provider:
            # These tools rely on OpenAI-compatible function calling for web search
            analyst_tools["social"].insert(0, self.toolkit.get_stock_news_openai)
            analyst_tools["news"].insert(1, self.toolkit.get_global_news_openai)
            analyst_tools["fundamentals"].insert(0, self.toolkit.get_fundamentals_openai)

        # Create ToolNode objects from the lists
        tool_nodes = {
            "market": ToolNode(analyst_tools["market"]),
            "social": ToolNode(analyst_tools["social"]),
            "news": ToolNode(analyst_tools["news"]),
            "fundamentals": ToolNode(analyst_tools["fundamentals"]),
        }

        return analyst_tools, tool_nodes

    def propagate(self, company_name, trade_date):
        """Run the trading agents graph for a company on a specific date."""
        logging.info(f"Starting propagation for {company_name} on {trade_date}.")
        self.ticker = company_name

        # Initialize state
        init_agent_state = self.propagator.create_initial_state(
            company_name, trade_date
        )
        args = self.propagator.get_graph_args()

        if self.debug:
            # Debug mode with tracing
            trace = []
            for chunk in self.graph.stream(init_agent_state, **args):
                if len(chunk["messages"]) == 0:
                    pass
                else:
                    chunk["messages"][-1].pretty_print()
                    trace.append(chunk)

            final_state = trace[-1]
        else:
            # Standard mode without tracing
            final_state = self.graph.invoke(init_agent_state, **args)

        # Store current state for reflection
        self.curr_state = final_state

        # Log state
        self._log_state(trade_date, final_state)

        # Return decision and processed signal
        decision = self.process_signal(final_state["final_trade_decision"])
        logging.info(f"Propagation finished for {company_name}. Final decision: {decision}")
        return final_state, decision

    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        self.log_states_dict[str(trade_date)] = {
            "company_of_interest": final_state["company_of_interest"],
            "trade_date": final_state["trade_date"],
            "market_report": final_state["market_report"],
            "sentiment_report": final_state["sentiment_report"],
            "news_report": final_state["news_report"],
            "fundamentals_report": final_state["fundamentals_report"],
            "investment_debate_state": {
                "bull_history": final_state["investment_debate_state"]["bull_history"],
                "bear_history": final_state["investment_debate_state"]["bear_history"],
                "history": final_state["investment_debate_state"]["history"],
                "current_response": final_state["investment_debate_state"][
                    "current_response"
                ],
                "judge_decision": final_state["investment_debate_state"][
                    "judge_decision"
                ],
            },
            "trader_investment_decision": final_state["trader_investment_plan"],
            "risk_debate_state": {
                "risky_history": final_state["risk_debate_state"]["risky_history"],
                "safe_history": final_state["risk_debate_state"]["safe_history"],
                "neutral_history": final_state["risk_debate_state"]["neutral_history"],
                "history": final_state["risk_debate_state"]["history"],
                "judge_decision": final_state["risk_debate_state"]["judge_decision"],
            },
            "investment_plan": final_state["investment_plan"],
            "final_trade_decision": final_state["final_trade_decision"],
        }

        # Save to file
        directory = Path(f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/")
        directory.mkdir(parents=True, exist_ok=True)

        with open(
            f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/full_states_log_{trade_date}.json",
            "w",
        ) as f:
            json.dump(self.log_states_dict, f, indent=4)

    def reflect_and_remember(self, returns_losses):
        """Reflect on decisions and update memory based on returns."""
        self.reflector.reflect_bull_researcher(
            self.curr_state, returns_losses, self.bull_memory
        )
        self.reflector.reflect_bear_researcher(
            self.curr_state, returns_losses, self.bear_memory
        )
        self.reflector.reflect_trader(
            self.curr_state, returns_losses, self.trader_memory
        )
        self.reflector.reflect_invest_judge(
            self.curr_state, returns_losses, self.invest_judge_memory
        )
        self.reflector.reflect_risk_manager(
            self.curr_state, returns_losses, self.risk_manager_memory
        )

    def process_signal(self, full_signal):
        """Process a signal to extract the core decision."""
        return self.signal_processor.process_signal(full_signal)
