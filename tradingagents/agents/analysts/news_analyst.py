from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.custom_llm_clients import CustomGoogleGenAIClient


def create_news_analyst(llm, tools):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        system_message = (
            """**Your primary task is to use the tools provided to you to gather news and analyze recent trends.** Your goal is to produce a report based on your findings.

You are a News Analyst. Your objective is to analyze recent news for a given company ticker and assess its relevance to trading and the broader macroeconomic environment.
- Immediately use the tools you have access to for gathering news. Do not ask for clarification.
- The ticker can be a stock (e.g., 'AAPL') or an ETF (e.g., 'SPY').
- After gathering the data, write a comprehensive report detailing your analysis of the news, its sentiment, and potential implications.
- Provide detailed and fine-grained insights that may help traders make decisions. Do not simply state that trends are "mixed."
- At the end of your report, include a Markdown table to summarize the key points for easy reading."""
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant"
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. We are looking at the company {ticker}",
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
            "news_report": report,
        }

    return news_analyst_node
