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
        
        # --- Direct Execution Logic ---
        # Instead of asking the LLM to call the tool, we call it directly.
        # This is more robust and avoids LLM hallucination or refusal to call tools.

        # Find the correct tool function from the provided list
        data_tool = None
        for tool in tools:
            if tool.name == "get_daily_stock_data":
                data_tool = tool.func
                break
        
        if not data_tool:
            raise ValueError("The required tool 'get_daily_stock_data' was not found in the provided toolkit.")

        # Define the date range and execute the tool to get the raw data
        end_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
        start_date_obj = end_date_obj - relativedelta(years=1)
        start_date = start_date_obj.strftime("%Y-%m-%d")
        
        raw_data_df = data_tool(symbol=ticker, start_date=start_date, end_date=current_date)

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
            # Ensure the dataframe is not empty and has enough data for calculations
            if len(raw_data_df) > 1:
                for key, name in indicators_to_calculate.items():
                    try:
                        # Trigger calculation and get the latest value
                        indicator_values[key] = stock_df[name].iloc[-1]
                    except Exception as e:
                        indicator_values[key] = f"Error calculating: {e}"
            else:
                 for key in indicators_to_calculate:
                    indicator_values[key] = "Not enough data to calculate"


            # --- Prepare data for the LLM call ---
            data_summary = f"### Technical Indicator Data for {ticker} on {current_date}\n\n"
            data_summary += "| Indicator       | Value                               |\n"
            data_summary += "| --------------- | ----------------------------------- |\n"
            for key, value in indicator_values.items():
                val_str = f"{value:.2f}" if isinstance(value, (int, float)) else str(value)
                data_summary += f"| {key.replace('_', ' ').title():<15} | {val_str:<35} |\n"

            # --- LLM call to generate the report based on calculated data ---
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
