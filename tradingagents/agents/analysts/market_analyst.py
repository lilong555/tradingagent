from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage
import time
import json
import pandas as pd
from stockstats import wrap
from tradingagents.agents.utils.custom_llm_clients import CustomGoogleGenAIClient
from dateutil.relativedelta import relativedelta
from datetime import datetime

def create_market_analyst(llm, tools):

    def market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        
        # Define the date range for fetching data (e.g., 1 year back for indicator calculation)
        end_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
        start_date_obj = end_date_obj - relativedelta(years=1)
        start_date = start_date_obj.strftime("%Y-%m-%d")

        system_message = (
            """**You are an autonomous Market Analyst AI.** Your goal is to perform a technical analysis.

**Your Two-Step Workflow:**

**Step 1: Get Raw Data**
- Your first and ONLY action is to call the `get_daily_stock_data` tool.
- Use the provided `ticker`, `start_date`, and `end_date` to fetch the necessary historical price data.
- **DO NOT ask for clarification. DO NOT try to calculate anything yet.** Just call the tool.

**Step 2: Analyze and Report (in a subsequent turn)**
- After you receive the raw stock data, you will analyze it to calculate technical indicators and generate a report. This will happen in your next invocation.
"""
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. The company we want to look at is {ticker}. "
                    "The required data range is from {start_date} to {end_date}.",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(
            system_message=system_message,
            tool_names=", ".join([tool.name for tool in tools]),
            current_date=current_date,
            ticker=ticker,
            start_date=start_date,
            end_date=current_date
        )
        
        # First LLM call to decide to use the tool
        if isinstance(llm, CustomGoogleGenAIClient):
            llm.bind_tools(tools)
            messages = prompt.invoke(state).to_messages()
            result = llm.invoke(messages)
        else:
            chain = prompt | llm.bind_tools(tools)
            result = chain.invoke(state["messages"])

        # Check if the LLM decided to call our data tool
        if not result.tool_calls:
            # If not, it might be hallucinating or asking a question. Return its content as a report.
            return {
                "messages": [result],
                "market_report": result.content,
            }

        # --- This is the new core logic for in-agent calculation ---
        # At this point, the LLM has correctly decided to call `get_daily_stock_data`.
        # We don't need to actually execute the tool through the graph's ToolNode.
        # We can directly call the underlying function here to get the data.
        
        # Find the correct tool function from the provided list
        data_tool = None
        for tool in tools:
            if tool.name == "get_daily_stock_data":
                data_tool = tool.func
                break
        
        if not data_tool:
            raise ValueError("The required tool 'get_daily_stock_data' was not found.")

        # Execute the tool to get the raw data
        tool_call = result.tool_calls[0]
        raw_data_df = data_tool(**tool_call['args'])

        report = ""
        if raw_data_df.empty:
            report = f"Could not retrieve historical stock data for {ticker} for the period {start_date} to {current_date}. Technical analysis cannot be performed."
        else:
            # --- Perform Calculations Internally ---
            stock_df = wrap(raw_data_df)
            indicators_to_calculate = {
                'rsi': 'rsi',
                'macd': 'macd',
                'boll_ub': 'boll_ub',
                'boll_lb': 'boll_lb',
                'close_50_sma': 'close_50_sma',
                'close_200_sma': 'close_200_sma'
            }
            
            indicator_values = {}
            for key, name in indicators_to_calculate.items():
                try:
                    # Trigger calculation and get the latest value
                    indicator_values[key] = stock_df[name].iloc[-1]
                except Exception as e:
                    indicator_values[key] = f"Error calculating: {e}"

            # --- Prepare data for the second LLM call ---
            # Create a summary of the calculated data
            data_summary = "### Technical Indicator Data for AAPL on 2025-08-14\n\n"
            data_summary += "| Indicator       | Value                               |\n"
            data_summary += "| --------------- | ----------------------------------- |\n"
            for key, value in indicator_values.items():
                val_str = f"{value:.2f}" if isinstance(value, (int, float)) else str(value)
                data_summary += f"| {key.replace('_', ' ').title():<15} | {val_str:<35} |\n"

            # --- Second LLM call to generate the report based on calculated data ---
            reporting_system_message = """
You are a Market Analyst. You have been provided with a table of calculated technical indicators for a stock.
Your task is to synthesize this data into a clear, concise, and insightful technical analysis report.
- Explain what each indicator's value means in the current context.
- Provide a summary of the overall technical outlook (e.g., bullish, bearish, neutral).
- Conclude with a summary table.
DO NOT mention your tools or the process of getting the data. Focus ONLY on the analysis of the provided numbers.
"""
            reporting_prompt = ChatPromptTemplate.from_messages([
                ("system", reporting_system_message),
                ("human", f"Here is the data to analyze:\n\n{data_summary}")
            ])
            
            reporting_chain = reporting_prompt | llm
            final_report_result = reporting_chain.invoke({})
            report = final_report_result.content

        # The final result is an AIMessage that contains the generated report
        final_message = AIMessage(content=report)
       
        return {
            "messages": [final_message],
            "market_report": report,
        }

    return market_analyst_node
