from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from typing import List
from typing import Annotated
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import RemoveMessage
from langchain_core.tools import tool
from datetime import date, timedelta, datetime
import functools
import logging
import pandas as pd
import os
from dateutil.relativedelta import relativedelta
from langchain_openai import ChatOpenAI
import tradingagents.dataflows.interface as interface
from tradingagents.default_config import DEFAULT_CONFIG
from langchain_core.messages import HumanMessage


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]
        
        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]
        
        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")
        
        return {"messages": removal_operations + [placeholder]}
    
    return delete_messages


class Toolkit:
    _config = DEFAULT_CONFIG.copy()

    @classmethod
    def update_config(cls, config):
        """Update the class-level configuration."""
        cls._config.update(config)

    @property
    def config(self):
        """Access the configuration."""
        return self._config

    def __init__(self, config=None):
        if config:
            self.update_config(config)

    @staticmethod
    @tool
    def get_reddit_news(
        curr_date: Annotated[str, "Date you want to get news for in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve global news from Reddit within a specified time frame.
        Args:
            curr_date (str): Date you want to get news for in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the latest global news from Reddit in the specified time frame.
        """
        logging.info(f"Calling get_reddit_news tool for date: {curr_date}")
        global_news_result = interface.get_reddit_global_news(curr_date, 7, 5)

        return global_news_result

    @staticmethod
    @tool
    def get_finnhub_news(
        ticker: Annotated[
            str,
            "Search query of a company, e.g. 'AAPL, TSM, etc.",
        ],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news about a given stock from Finnhub within a date range
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing news about the company within the date range from start_date to end_date
        """

        end_date_str = end_date

        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        look_back_days = (end_date - start_date).days

        logging.info(f"Calling get_finnhub_news tool for {ticker} from {start_date} to {end_date}")
        finnhub_news_result = interface.get_finnhub_news(
            ticker, end_date_str, look_back_days
        )

        return finnhub_news_result

    @staticmethod
    @tool
    def get_finnhub_news_online(
        ticker: Annotated[
            str,
            "Search query of a company, e.g. 'AAPL, TSM, etc.",
        ],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
        look_back_days: Annotated[int, "how many days to look back"] = 7,
    ):
        """
        Retrieve the latest news about a given stock from Finnhub within a date range using the online API.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): Current date in yyyy-mm-dd format
            look_back_days (int): How many days to look back, default is 7
        Returns:
            str: A formatted string containing news about the company within the date range.
        """
        logging.info(f"Calling get_finnhub_news_online tool for {ticker} on {curr_date}")
        return interface.get_finnhub_news_online_interface(
            ticker, curr_date, look_back_days
        )

    @staticmethod
    @tool
    def get_reddit_stock_info_offline(
        ticker: Annotated[
            str,
            "Ticker of a company. e.g. AAPL, TSM",
        ],
        curr_date: Annotated[str, "Current date you want to get news for"],
    ) -> str:
        """
        Retrieve the latest news about a given stock from offline Reddit data, given the current date.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): current date in yyyy-mm-dd format to get news for
        Returns:
            str: A formatted dataframe containing the latest news about the company on the given date
        """

        logging.info(f"Calling get_reddit_stock_info_offline tool for {ticker} on {curr_date}")
        stock_news_results = interface.get_reddit_stock_info_offline(ticker, curr_date, 7, 5)

        return stock_news_results

    @staticmethod
    @tool
    def get_reddit_stock_info_online(
        ticker: Annotated[
            str,
            "Ticker of a company. e.g. AAPL, TSM",
        ],
        look_back_days: Annotated[int, "How many days back to search for posts."] = 7,
    ) -> str:
        """
        Retrieve recent news about a given stock from online Reddit posts.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            look_back_days (int): How many days back to search for posts.
        Returns:
            str: A formatted string containing recent posts about the company.
        """

        logging.info(f"Calling get_reddit_stock_info_online tool for {ticker}")
        stock_news_results = interface.get_reddit_stock_info_online(ticker, look_back_days)

        return stock_news_results

    @staticmethod
    @tool
    def get_daily_stock_data(
        symbol: Annotated[str, "The stock ticker symbol, e.g., 'AAPL'."],
        start_date: Annotated[str, "The start date for the data retrieval in YYYY-MM-DD format."],
        end_date: Annotated[str, "The end date for the data retrieval in YYYY-MM-DD format."],
    ) -> pd.DataFrame:
        """
        Fetches daily OHLCV (Open, High, Low, Close, Volume) stock data for a given ticker and date range.
        This tool provides the raw data necessary for all technical analysis calculations.
        """
        logging.info(f"Calling get_daily_stock_data tool for {symbol} from {start_date} to {end_date}")
        return interface.get_daily_stock_data(symbol, start_date, end_date)

    @staticmethod
    @tool
    def get_YFin_data(
        symbol: Annotated[str, "ticker symbol of the company"],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve the stock price data for a given ticker symbol from Yahoo Finance.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the stock price data for the specified ticker symbol in the specified date range.
        """

        logging.info(f"Calling get_YFin_data_online tool for {symbol} from {start_date} to {end_date}")
        result_data = interface.get_YFin_data_online(symbol, start_date, end_date)

        return result_data

    @staticmethod
    @tool
    def get_finnhub_company_insider_sentiment(
        ticker: Annotated[str, "ticker symbol for the company"],
        curr_date: Annotated[
            str,
            "current date of you are trading at, yyyy-mm-dd",
        ],
    ):
        """
        Retrieve insider sentiment information about a company (retrieved from public SEC information) for the past 30 days
        Args:
            ticker (str): ticker symbol of the company
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the sentiment in the past 30 days starting at curr_date
        """

        logging.info(f"Calling get_finnhub_company_insider_sentiment tool for {ticker} on {curr_date}")
        data_sentiment = interface.get_finnhub_company_insider_sentiment(
            ticker, curr_date, 30
        )

        return data_sentiment

    @staticmethod
    @tool
    def get_finnhub_company_insider_transactions(
        ticker: Annotated[str, "ticker symbol"],
        curr_date: Annotated[
            str,
            "current date you are trading at, yyyy-mm-dd",
        ],
    ):
        """
        Retrieve insider transaction information about a company (retrieved from public SEC information) for the past 30 days
        Args:
            ticker (str): ticker symbol of the company
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the company's insider transactions/trading information in the past 30 days
        """

        logging.info(f"Calling get_finnhub_company_insider_transactions tool for {ticker} on {curr_date}")
        data_trans = interface.get_finnhub_company_insider_transactions(
            ticker, curr_date, 30
        )

        return data_trans

    @staticmethod
    @tool
    def get_balance_sheet(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency: 'annual' or 'quarterly'",
        ],
    ):
        """
        Retrieve the most recent balance sheet of a company from online sources.
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency: 'annual' or 'quarterly'
        Returns:
            str: a report of the company's most recent balance sheet
        """

        logging.info(f"Calling get_balance_sheet_online tool for {ticker}")
        data_balance_sheet = interface.get_balance_sheet_online(ticker, freq)

        return data_balance_sheet

    @staticmethod
    @tool
    def get_cashflow(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency: 'annual' or 'quarterly'",
        ],
    ):
        """
        Retrieve the most recent cash flow statement of a company from online sources.
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency: 'annual' or 'quarterly'
        Returns:
                str: a report of the company's most recent cash flow statement
        """

        logging.info(f"Calling get_cashflow_online tool for {ticker}")
        data_cashflow = interface.get_cashflow_online(ticker, freq)

        return data_cashflow

    @staticmethod
    @tool
    def get_income_statement(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency: 'annual' or 'quarterly'",
        ],
    ):
        """
        Retrieve the most recent income statement of a company from online sources.
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency: 'annual' or 'quarterly'
        Returns:
                str: a report of the company's most recent income statement
        """

        logging.info(f"Calling get_income_statement_online tool for {ticker}")
        data_income_stmt = interface.get_income_statement_online(
            ticker, freq
        )

        return data_income_stmt

    @staticmethod
    @tool
    def get_google_news(
        query: Annotated[str, "Query to search with"],
        curr_date: Annotated[str, "Curr date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news from Google News based on a query and date range.
        Args:
            query (str): Query to search with
            curr_date (str): Current date in yyyy-mm-dd format
            look_back_days (int): How many days to look back
        Returns:
            str: A formatted string containing the latest news from Google News based on the query and date range.
        """

        logging.info(f"Calling get_google_news tool with query: {query}")
        google_news_results = interface.get_google_news(query, curr_date, 7)

        return google_news_results

    @staticmethod
    @tool
    def get_stock_news_openai(
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news about a given stock by using OpenAI's news API.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest news about the company on the given date.
        """

        logging.info(f"Calling get_stock_news_openai tool for {ticker}")
        openai_news_results = interface.get_stock_news_openai(ticker, curr_date)

        return openai_news_results

    @staticmethod
    @tool
    def get_global_news_openai(
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest macroeconomics news on a given date using OpenAI's macroeconomics news API.
        Args:
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest macroeconomic news on the given date.
        """

        logging.info(f"Calling get_global_news_openai tool for date: {curr_date}")
        openai_news_results = interface.get_global_news_openai(curr_date)

        return openai_news_results

    @staticmethod
    @tool
    def get_fundamentals_openai(
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest fundamental information about a given stock on a given date by using OpenAI's news API.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest fundamental information about the company on the given date.
        """

        logging.info(f"Calling get_fundamentals_openai tool for {ticker}")
        openai_fundamentals_results = interface.get_fundamentals_openai(
            ticker, curr_date
        )

        return openai_fundamentals_results
