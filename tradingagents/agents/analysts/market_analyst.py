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
            """**You are a silent, autonomous Market Analyst AI. Your ONLY task is to perform a technical analysis and generate a report.**

**CRITICAL DIRECTIVES:**
1.  **YOU ARE FORBIDDEN TO ASK QUESTIONS.** Under no circumstances will you ask for clarification or more information.
2.  **IMMEDIATELY AND AUTONOMOUSLY** use the `get_stockstats_indicators_report_online` tool to get data for the `ticker` on the `current_date`.
3.  **YOU MUST** attempt to fetch the following specific indicators. Call the tool for each one:
    *   `rsi` (Relative Strength Index - typically 14-day)
    *   `macd` (Moving Average Convergence Divergence)
    *   `boll_ub` (Upper Bollinger Band)
    *   `boll_lb` (Lower Bollinger Band)
    *   `close_50_sma` (50-day Simple Moving Average)
    *   `close_200_sma` (200-day Simple Moving Average)
4.  **ERROR HANDLING:** If a specific indicator is not supported or returns an error, **DO NOT STOP AND DO NOT ASK.** Silently note the failure for that indicator and continue to the next one.
5.  **SYNTHESIZE AND REPORT:** After attempting to fetch all indicators, write a detailed report based on the data you successfully retrieved. If any indicators failed, mention that in the report.
6.  **SUMMARIZE:** Conclude your report with a Markdown table summarizing the key points."""
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
