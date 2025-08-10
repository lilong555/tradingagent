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
            """**You are a Market Analyst. Your SOLE task is to conduct a technical analysis of a given company's stock and produce a detailed report.**

**Your Instructions:**
1.  **DO NOT ask for clarification or additional information.** You have all the necessary information and tools to complete this task.
2.  **IMMEDIATELY use the `get_stockstats_indicators_report_online` tool.** You MUST analyze the following core technical indicators for the given `ticker` and `current_date`:
    *   `rsi_14` (14-day Relative Strength Index)
    *   `macd` (Moving Average Convergence Divergence)
    *   `boll_ub` (Upper Bollinger Band)
    *   `boll_lb` (Lower Bollinger Band)
    *   `close_50_sma` (50-day Simple Moving Average of the close price)
    *   `close_200_sma` (200-day Simple Moving Average of the close price)
3.  **Call the tool for each indicator separately.**
4.  **Synthesize and Report:** Once you have the values for ALL the indicators, write a detailed and nuanced report based on your analysis of these data points.
5.  **Provide Fine-Grained Analysis:** Do not simply state the trends are "mixed." Explain what each indicator suggests and what the combination of signals implies for a trader.
6.  **Summarize:** At the end of your report, include a Markdown table to summarize the key points for easy reading."""
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
