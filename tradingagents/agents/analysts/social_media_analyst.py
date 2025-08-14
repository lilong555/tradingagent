from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.custom_llm_clients import CustomGoogleGenAIClient


def create_social_media_analyst(llm, tools):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        system_message = (
            """**Your primary task is to use the tools provided to you to gather social media and public sentiment data.** Your goal is to analyze this data and produce a report.

You are a Social Media Analyst. Your objective is to analyze social media posts, forums, and public sentiment data for a given company ticker.

**Data Retrieval and Reporting Strategy:**
1.  **Primary Goal:** Attempt to fetch social media data for the specified date: `{current_date}`.
2.  **Data Fallback Strategy:** If you find that no data is available for the specific historical date, **do not stop**. Instead, automatically attempt to fetch the most recent, currently available data.
3.  **Acknowledge Data Scope:** In your final report, you **must** clearly state the time period of the data you analyzed. For example: "No historical data was available for {current_date}, so this analysis is based on real-time data from today."
4.  **Handling No Data:** If the tools return a message like "No recent online Reddit posts found," **this is a valid and important finding**. Do not state that you cannot fulfill the request. Instead, explicitly report that there is a lack of social media discussion about the ticker. This low level of interest is itself a key insight. Your report should reflect this, for example: "There was no significant social media discussion found for [ticker] during the specified period, suggesting low retail investor interest."
5.  **Analyze and Report:** After gathering the data (or confirming its absence), write a comprehensive report detailing your analysis, insights, and potential implications for traders. Focus on what people are saying, the sentiment, and any emerging narratives.
6.  **Provide Insights:** Do not simply state that sentiment is "mixed." Provide detailed, fine-grained analysis.
7.  **Summarize:** At the end of your report, include a Markdown table to summarize the key points for easy reading.

- Immediately use the tools you have access to. Do not ask for clarification."""
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
                    "For your reference, the current date is {current_date}. The current company we want to analyze is {ticker}",
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
            "sentiment_report": report,
        }

    return social_media_analyst_node
