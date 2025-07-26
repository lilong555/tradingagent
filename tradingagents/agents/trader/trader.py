import functools
import time
import json
from langchain_core.messages import HumanMessage, SystemMessage


def create_trader(llm, memory):
    def trader_node(state, name):
        company_name = state["company_of_interest"]
        investment_plan = state["investment_plan"]
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "No past memories found."

        context = f"Based on a comprehensive analysis by a team of analysts, here is an investment plan tailored for {company_name}. This plan incorporates insights from current technical market trends, macroeconomic indicators, and social media sentiment. Use this plan as a foundation for evaluating your next trading decision.\n\nProposed Investment Plan: {investment_plan}\n\nLeverage these insights to make an informed and strategic decision."

        system_prompt = f"""You are a **Senior Trader**, a key decision-maker in this operation. Your sole responsibility is to synthesize the comprehensive analysis provided by your team of analysts and the Research Manager's proposed plan. You are not a passive assistant; you are an active, decisive trader.

**Your Task:**
1.  **Review all provided materials:** This includes the market, sentiment, news, and fundamentals reports, as well as the final investment plan from the Research Team.
2.  **Consider Past Lessons:** Reflect on the provided memories from similar past trading situations (`{past_memory_str}`) to avoid repeating mistakes.
3.  **Formulate a Concrete Trading Plan:** Based on all available information, create a detailed and actionable trading plan. This plan must include:
    *   A clear entry price.
    *   A target price for taking profits.
    *   A stop-loss price to manage risk.
4.  **Make a Definitive Decision:** Conclude your entire response with the mandatory 'FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**' tag. This is not optional. Your response is incomplete without it.

Do not state that you cannot make a decision. Your entire purpose is to make one. Analyze the data and commit to a plan."""

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
