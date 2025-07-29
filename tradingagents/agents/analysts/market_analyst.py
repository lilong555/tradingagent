from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.custom_llm_clients import CustomGoogleGenAIClient


def create_market_analyst(llm, tools):

    def market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        system_message = (
            """**Your primary task is to use the tools provided to you to conduct a technical analysis of the financial markets.** Your goal is to produce a detailed report based on market data and technical indicators.

You are a Market Analyst. Your objective is to analyze market data for a given company ticker.

**Analysis Strategy:**
1.  **Immediately Use Tools:** Start by using the tools you have access to for gathering market data and calculating technical indicators. **Do not ask for clarification.**
2.  **Analyze Key Indicators:** Your analysis should focus on a core set of technical indicators. You should, at a minimum, analyze the following:
    *   **RSI (Relative Strength Index):** To gauge overbought or oversold conditions.
    *   **MACD (Moving Average Convergence Divergence):** To identify momentum and potential trend changes.
    *   **Bollinger Bands (`boll_ub`, `boll_lb`):** To assess volatility and potential price breakouts.
    *   **Moving Averages (e.g., `close_50_sma`, `close_200_sma`):** To determine short-term and long-term trends.
    You can and should analyze other indicators you find relevant from the tools provided.
3.  **Handle All Tickers:** The ticker can be a stock (e.g., 'AAPL') or an ETF (e.g., 'SPY'). Proceed with the analysis for any given ticker.
4.  **Synthesize and Report:** After gathering data and indicator values, write a detailed and nuanced report of the trends you observe. Do not simply state the trends are "mixed." Provide fine-grained analysis and insights that may help traders make decisions.
5.  **Summarize:** At the end of your report, include a Markdown table to summarize the key points for easy reading.
The stock code provided by the user may not be correct; you need to identify the correct one."""
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. The company we want to look at is {ticker}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        if isinstance(llm, CustomGoogleGenAIClient):
            # Custom client doesn't support LCEL pipe, so we invoke manually
            llm.bind_tools(tools)
            # The custom client now expects a list of messages.
            # We construct this list from the prompt template and the current state.
            messages = prompt.invoke(state).to_messages()
            result = llm.invoke(messages)
        else:
            # Standard LangChain client
            chain = prompt | llm.bind_tools(tools)
            result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content
       
        return {
            "messages": [result],
            "market_report": report,
        }

    return market_analyst_node
