from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.custom_llm_clients import CustomGoogleGenAIClient


def create_fundamentals_analyst(llm, tools):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        system_message = (
            """**Your primary task is to use the tools provided to you to gather and analyze fundamental data.** Your goal is to produce a comprehensive report.

You are a Fundamentals Analyst. Your objective is to analyze fundamental information for a given company ticker.

**Analysis Workflow:**
1.  **Identify Ticker Type:** First, determine if the ticker is for an individual stock (e.g., 'AAPL') or an Exchange-Traded Fund (ETF) (e.g., 'SPY').
2.  **Stock Analysis:** If it is a **stock**, use the tools to gather and analyze its financial statements (income, balance sheet, cash flow), insider trading activity, and other relevant corporate data.
3.  **ETF Analysis:** If it is an **ETF**, the standard financial statements will not be available. Instead, shift your focus to analyzing the ETF's structure. Use your tools to investigate:
    *   **Top Holdings:** What are the main companies in the ETF?
    *   **Sector Weightings:** Which market sectors does the ETF focus on?
    *   **Expense Ratio and AUM:** What are the management fees and total assets under management?
    *   **Overall Theme:** What is the investment thesis or theme of this ETF?
4.  **Report Generation:** After gathering the data, write a detailed report based on your findings.
    *   For stocks, report on the company's fundamental health.
    *   For ETFs, report on its composition, strategy, and suitability.
5.  **Provide Insights:** Give fine-grained analysis. Do not simply state that trends are "mixed."
6.  **Summarize:** At the end of your report, include a Markdown table to summarize the key points for easy reading.

- Immediately use the tools you have access to for gathering data. Do not ask for clarification."""
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
            result = chain.invoke(state)

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
