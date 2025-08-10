import functools
import time
import json
from langchain_core.messages import HumanMessage, SystemMessage


def create_trader(llm, memory):
    def trader_node(state, name):
        company_name = state["company_of_interest"]
        trade_date = state["trade_date"]
        investment_plan = state["investment_plan"]
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        # Consolidate all available reports into a single context string
        curr_situation = f"""
### Market Research Report
{market_research_report}

### Social Media Sentiment Report
{sentiment_report}

### News Report
{news_report}

### Fundamentals Report
{fundamentals_report}
"""
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += f"Memory {i}:\n{rec['recommendation']}\n\n"
        else:
            past_memory_str = "No past memories found."

        system_prompt = f"""You are a **Senior Trader**, a key decision-maker. Your SOLE task is to synthesize the provided analysis and create a final, actionable trading plan.

**CRITICAL INSTRUCTIONS:**
1.  **DO NOT ask for clarification or more information.** You have been given ALL necessary data.
2.  The company is **{company_name}**. The current date is **{trade_date}**.
3.  Review all provided materials: the analyst reports, the proposed investment plan, and past memories.
4.  Your output MUST be a concrete trading plan with a clear entry price, target price, and stop-loss price.
5.  You MUST conclude your entire response with the mandatory 'FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**' tag. This is not optional.

Analyze the data and commit to a decision. It is your only purpose."""

        context = f"""
**TO-DO: Create a final trading plan for {company_name} for {trade_date}.**

**1. Analyst Reports:**
{curr_situation}

**2. Research Manager's Proposed Plan:**
{investment_plan}

**3. Relevant Past Memories:**
{past_memory_str}

Based on all of the above, formulate your final, concrete trading plan.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context),
        ]

        result = llm.invoke(messages)

        return {
            "messages": [result],
            "trader_investment_plan": result.content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
