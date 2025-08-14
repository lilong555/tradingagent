import logging
from typing import Annotated, Dict
from .reddit_utils import fetch_top_from_category, fetch_reddit_posts_online
from .yfin_utils import *
from .googlenews_utils import *
from .finnhub_utils import get_data_in_range, get_finnhub_news_online
from dateutil.relativedelta import relativedelta
from datetime import datetime
import json
import os
import pandas as pd
from tqdm import tqdm
import yfinance as yf
from openai import OpenAI
from .config import get_config, set_config, DATA_DIR
from stockstats import wrap

def get_daily_stock_data(
    symbol: Annotated[str, "The stock ticker symbol, e.g., 'AAPL'."],
    start_date: Annotated[str, "The start date for the data retrieval in YYYY-MM-DD format."],
    end_date: Annotated[str, "The end date for the data retrieval in YYYY-MM-DD format."],
) -> pd.DataFrame:
    """
    Fetches daily OHLCV (Open, High, Low, Close, Volume) stock data for a given ticker and date range.
    This tool provides the raw data necessary for all technical analysis calculations.
    """
    try:
        # yfinance download is inclusive of start but exclusive of end, so add one day to end_date
        end_date_adjusted = (pd.to_datetime(end_date) + pd.DateOffset(days=1)).strftime('%Y-%m-%d')
        data = yf.download(
            symbol,
            start=start_date,
            end=end_date_adjusted,
            progress=False,
            auto_adjust=True,
        )
        if data.empty:
            # Return an empty dataframe with expected columns if no data is found
            return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
        
        # Ensure column names are lowercase for consistency
        data.columns = [col.lower() for col in data.columns]
        return data.reset_index()

    except Exception as e:
        logging.error(f"Error fetching daily stock data for {symbol}: {e}")
        return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])

# --- Deprecated or unused functions from the original file are removed for clarity ---
# --- The following are existing functions that are kept ---

def get_finnhub_news(
    ticker: Annotated[
        str,
        "Search query of a company's, e.g. 'AAPL, TSM, etc.",
    ],
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "how many days to look back"],
):
    """
    Retrieve news about a company within a time frame

    Args
        ticker (str): ticker for the company you are interested in
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format
    Returns
        str: dataframe containing the news of the company in the time frame

    """

    start_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    result = get_data_in_range(ticker, before, curr_date, "news_data", DATA_DIR)

    if len(result) == 0:
        return ""

    combined_result = ""
    for day, data in result.items():
        if len(data) == 0:
            continue
        for entry in data:
            current_news = (
                "### " + entry["headline"] + f" ({day})" + "\n" + entry["summary"]
            )
            combined_result += current_news + "\n\n"

    return f"## {ticker} News, from {before} to {curr_date}:\n" + str(combined_result)


def get_finnhub_news_online_interface(
    ticker: Annotated[
        str,
        "Search query of a company's, e.g. 'AAPL, TSM, etc.",
    ],
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "how many days to look back"],
):
    """
    Retrieve news about a company within a time frame from Finnhub's online API.

    Args:
        ticker (str): ticker for the company you are interested in
        curr_date (str): Current date in yyyy-mm-dd format
        look_back_days (int): how many days to look back
    Returns:
        str: A formatted string containing the news of the company in the time frame.
    """
    end_date = datetime.strptime(curr_date, "%Y-%m-%d")
    start_date = end_date - relativedelta(days=look_back_days)
    
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    result = get_finnhub_news_online(ticker, start_date_str, end_date_str)

    if not result:
        return f"No online news found for {ticker} from {start_date_str} to {end_date_str}."

    combined_result = ""
    for entry in result:
        # Convert timestamp to readable date
        news_date = datetime.fromtimestamp(entry["datetime"]).strftime('%Y-%m-%d')
        current_news = (
            "### " + entry["headline"] + f" ({news_date})" + "\n" + entry["summary"]
        )
        combined_result += current_news + "\n\n"

    return f"## {ticker} Online News, from {start_date_str} to {end_date_str}:\n" + str(combined_result)


def get_finnhub_company_insider_sentiment(
    ticker: Annotated[str, "ticker symbol for the company"],
    curr_date: Annotated[
        str,
        "current date of you are trading at, yyyy-mm-dd",
    ],
    look_back_days: Annotated[int, "number of days to look back"],
):
    """
    Retrieve insider sentiment about a company (retrieved from public SEC information) for the past 15 days
    Args:
        ticker (str): ticker symbol of the company
        curr_date (str): current date you are trading on, yyyy-mm-dd
    Returns:
        str: a report of the sentiment in the past 15 days starting at curr_date
    """

    date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
    before = date_obj - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    data = get_data_in_range(ticker, before, curr_date, "insider_senti", DATA_DIR)

    if len(data) == 0:
        return "Offline Finnhub insider sentiment data not found. This feature requires a local data cache."

    result_str = ""
    seen_dicts = []
    for date, senti_list in data.items():
        for entry in senti_list:
            if entry not in seen_dicts:
                result_str += f"### {entry['year']}-{entry['month']}:\nChange: {entry['change']}\nMonthly Share Purchase Ratio: {entry['mspr']}\n\n"
                seen_dicts.append(entry)

    return (
        f"## {ticker} Insider Sentiment Data for {before} to {curr_date}:\n"
        + result_str
        + "The change field refers to the net buying/selling from all insiders' transactions. The mspr field refers to monthly share purchase ratio."
    )


def get_finnhub_company_insider_transactions(
    ticker: Annotated[str, "ticker symbol"],
    curr_date: Annotated[
        str,
        "current date you are trading at, yyyy-mm-dd",
    ],
    look_back_days: Annotated[int, "how many days to look back"],
):
    """
    Retrieve insider transcaction information about a company (retrieved from public SEC information) for the past 15 days
    Args:
        ticker (str): ticker symbol of the company
        curr_date (str): current date you are trading at, yyyy-mm-dd
    Returns:
        str: a report of the company's insider transaction/trading informtaion in the past 15 days
    """

    date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
    before = date_obj - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    data = get_data_in_range(ticker, before, curr_date, "insider_trans", DATA_DIR)

    if len(data) == 0:
        return "Offline Finnhub insider transaction data not found. This feature requires a local data cache."

    result_str = ""

    seen_dicts = []
    for date, senti_list in data.items():
        for entry in senti_list:
            if entry not in seen_dicts:
                result_str += f"### Filing Date: {entry['filingDate']}, {entry['name']}:\nChange:{entry['change']}\nShares: {entry['share']}\nTransaction Price: {entry['transactionPrice']}\nTransaction Code: {entry['transactionCode']}\n\n"
                seen_dicts.append(entry)

    return (
        f"## {ticker} insider transactions from {before} to {curr_date}:\n"
        + result_str
        + "The change field reflects the variation in share count—here a negative number indicates a reduction in holdings—while share specifies the total number of shares involved. The transactionPrice denotes the per-share price at which the trade was executed, and transactionDate marks when the transaction occurred. The name field identifies the insider making the trade, and transactionCode (e.g., S for sale) clarifies the nature of the transaction. FilingDate records when the transaction was officially reported, and the unique id links to the specific SEC filing, as indicated by the source. Additionally, the symbol ties the transaction to a particular company, isDerivative flags whether the trade involves derivative securities, and currency notes the currency context of the transaction."
    )


def get_balance_sheet_online(
    ticker: Annotated[str, "The stock ticker symbol, e.g., 'AAPL'."],
    freq: Annotated[str, "The frequency of the report: 'annual' or 'quarterly'."],
) -> str:
    """
    Fetches the most recent balance sheet for a given ticker online using yfinance.
    Args:
        ticker: The stock ticker symbol.
        freq: The frequency ('annual' or 'quarterly').
    Returns:
        A formatted string of the balance sheet data.
    """
    try:
        stock = yf.Ticker(ticker)
        if freq.lower() == 'annual':
            data = stock.balance_sheet
        elif freq.lower() == 'quarterly':
            data = stock.quarterly_balance_sheet
        else:
            return "Error: Frequency must be 'annual' or 'quarterly'."

        if data.empty:
            return f"No online balance sheet data found for {ticker}."

        return f"## {ticker} Online {freq.capitalize()} Balance Sheet:\n\n{data.to_string()}\n"
    except Exception as e:
        return f"Error fetching online balance sheet for {ticker}: {e}"


def get_simfin_balance_sheet_offline(
    ticker: Annotated[str, "ticker symbol"],
    freq: Annotated[
        str,
        "reporting frequency of the company's financial history: annual / quarterly",
    ],
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
):
    data_path = os.path.join(
        DATA_DIR,
        "fundamental_data",
        "simfin_data_all",
        "balance_sheet",
        "companies",
        "us",
        f"us-balance-{freq}.csv",
    )
    try:
        df = pd.read_csv(data_path, sep=";")
    except FileNotFoundError:
        return f"Error: Offline data file not found at {data_path}. Please ensure the necessary data is downloaded."

    # Convert date strings to datetime objects and remove any time components
    df["Report Date"] = pd.to_datetime(df["Report Date"], utc=True).dt.normalize()
    df["Publish Date"] = pd.to_datetime(df["Publish Date"], utc=True).dt.normalize()

    # Convert the current date to datetime and normalize
    curr_date_dt = pd.to_datetime(curr_date, utc=True).normalize()

    # Filter the DataFrame for the given ticker and for reports that were published on or before the current date
    filtered_df = df[(df["Ticker"] == ticker) & (df["Publish Date"] <= curr_date_dt)]

    # Check if there are any available reports; if not, return a notification
    if filtered_df.empty:
        print("No balance sheet available before the given current date.")
        return ""

    # Get the most recent balance sheet by selecting the row with the latest Publish Date
    latest_balance_sheet = filtered_df.loc[filtered_df["Publish Date"].idxmax()]

    # drop the SimFinID column
    latest_balance_sheet = latest_balance_sheet.drop("SimFinId")

    return (
        f"## {freq} balance sheet for {ticker} released on {str(latest_balance_sheet['Publish Date'])[0:10]}: \n"
        + str(latest_balance_sheet)
        + "\n\nThis includes metadata like reporting dates and currency, share details, and a breakdown of assets, liabilities, and equity. Assets are grouped as current (liquid items like cash and receivables) and noncurrent (long-term investments and property). Liabilities are split between short-term obligations and long-term debts, while equity reflects shareholder funds such as paid-in capital and retained earnings. Together, these components ensure that total assets equal the sum of liabilities and equity."
    )


def get_cashflow_online(
    ticker: Annotated[str, "The stock ticker symbol, e.g., 'AAPL'."],
    freq: Annotated[str, "The frequency of the report: 'annual' or 'quarterly'."],
) -> str:
    """
    Fetches the most recent cash flow statement for a given ticker online using yfinance.
    Args:
        ticker: The stock ticker symbol.
        freq: The frequency ('annual' or 'quarterly').
    Returns:
        A formatted string of the cash flow statement data.
    """
    try:
        stock = yf.Ticker(ticker)
        if freq.lower() == 'annual':
            data = stock.cashflow
        elif freq.lower() == 'quarterly':
            data = stock.quarterly_cashflow
        else:
            return "Error: Frequency must be 'annual' or 'quarterly'."

        if data.empty:
            return f"No online cash flow data found for {ticker}."

        return f"## {ticker} Online {freq.capitalize()} Cash Flow Statement:\n\n{data.to_string()}\n"
    except Exception as e:
        return f"Error fetching online cash flow for {ticker}: {e}"


def get_simfin_cashflow_offline(
    ticker: Annotated[str, "ticker symbol"],
    freq: Annotated[
        str,
        "reporting frequency of the company's financial history: annual / quarterly",
    ],
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
):
    data_path = os.path.join(
        DATA_DIR,
        "fundamental_data",
        "simfin_data_all",
        "cash_flow",
        "companies",
        "us",
        f"us-cashflow-{freq}.csv",
    )
    try:
        df = pd.read_csv(data_path, sep=";")
    except FileNotFoundError:
        return f"Error: Offline data file not found at {data_path}. Please ensure the necessary data is downloaded."

    # Convert date strings to datetime objects and remove any time components
    df["Report Date"] = pd.to_datetime(df["Report Date"], utc=True).dt.normalize()
    df["Publish Date"] = pd.to_datetime(df["Publish Date"], utc=True).dt.normalize()

    # Convert the current date to datetime and normalize
    curr_date_dt = pd.to_datetime(curr_date, utc=True).normalize()

    # Filter the DataFrame for the given ticker and for reports that were published on or before the current date
    filtered_df = df[(df["Ticker"] == ticker) & (df["Publish Date"] <= curr_date_dt)]

    # Check if there are any available reports; if not, return a notification
    if filtered_df.empty:
        print("No cash flow statement available before the given current date.")
        return ""

    # Get the most recent cash flow statement by selecting the row with the latest Publish Date
    latest_cash_flow = filtered_df.loc[filtered_df["Publish Date"].idxmax()]

    # drop the SimFinID column
    latest_cash_flow = latest_cash_flow.drop("SimFinId")

    return (
        f"## {freq} cash flow statement for {ticker} released on {str(latest_cash_flow['Publish Date'])[0:10]}: \n"
        + str(latest_cash_flow)
        + "\n\nThis includes metadata like reporting dates and currency, share details, and a breakdown of cash movements. Operating activities show cash generated from core business operations, including net income adjustments for non-cash items and working capital changes. Investing activities cover asset acquisitions/disposals and investments. Financing activities include debt transactions, equity issuances/repurchases, and dividend payments. The net change in cash represents the overall increase or decrease in the company's cash position during the reporting period."
    )


def get_income_statement_online(
    ticker: Annotated[str, "The stock ticker symbol, e.g., 'AAPL'."],
    freq: Annotated[str, "The frequency of the report: 'annual' or 'quarterly'."],
) -> str:
    """
    Fetches the most recent income statement for a given ticker online using yfinance.
    Args:
        ticker: The stock ticker symbol.
        freq: The frequency ('annual' or 'quarterly').
    Returns:
        A formatted string of the income statement data.
    """
    try:
        stock = yf.Ticker(ticker)
        if freq.lower() == 'annual':
            data = stock.income_stmt
        elif freq.lower() == 'quarterly':
            data = stock.quarterly_income_stmt
        else:
            return "Error: Frequency must be 'annual' or 'quarterly'."

        if data.empty:
            return f"No online income statement data found for {ticker}."

        return f"## {ticker} Online {freq.capitalize()} Income Statement:\n\n{data.to_string()}\n"
    except Exception as e:
        return f"Error fetching online income statement for {ticker}: {e}"


def get_simfin_income_stmt_offline(
    ticker: Annotated[str, "ticker symbol"],
    freq: Annotated[
        str,
        "reporting frequency of the company's financial history: annual / quarterly",
    ],
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
):
    data_path = os.path.join(
        DATA_DIR,
        "fundamental_data",
        "simfin_data_all",
        "income_statements",
        "companies",
        "us",
        f"us-income-{freq}.csv",
    )
    try:
        df = pd.read_csv(data_path, sep=";")
    except FileNotFoundError:
        return f"Error: Offline data file not found at {data_path}. Please ensure the necessary data is downloaded."

    # Convert date strings to datetime objects and remove any time components
    df["Report Date"] = pd.to_datetime(df["Report Date"], utc=True).dt.normalize()
    df["Publish Date"] = pd.to_datetime(df["Publish Date"], utc=True).dt.normalize()

    # Convert the current date to datetime and normalize
    curr_date_dt = pd.to_datetime(curr_date, utc=True).normalize()

    # Filter the DataFrame for the given ticker and for reports that were published on or before the current date
    filtered_df = df[(df["Ticker"] == ticker) & (df["Publish Date"] <= curr_date_dt)]

    # Check if there are any available reports; if not, return a notification
    if filtered_df.empty:
        print("No income statement available before the given current date.")
        return ""

    # Get the most recent income statement by selecting the row with the latest Publish Date
    latest_income = filtered_df.loc[filtered_df["Publish Date"].idxmax()]

    # drop the SimFinID column
    latest_income = latest_income.drop("SimFinId")

    return (
        f"## {freq} income statement for {ticker} released on {str(latest_income['Publish Date'])[0:10]}: \n"
        + str(latest_income)
        + "\n\nThis includes metadata like reporting dates and currency, share details, and a comprehensive breakdown of the company's financial performance. Starting with Revenue, it shows Cost of Revenue and resulting Gross Profit. Operating Expenses are detailed, including SG&A, R&D, and Depreciation. The statement then shows Operating Income, followed by non-operating items and Interest Expense, leading to Pretax Income. After accounting for Income Tax and any Extraordinary items, it concludes with Net Income, representing the company's bottom-line profit or loss for the period."
    )


def get_reddit_stock_info_online(
    ticker: Annotated[str, "The stock ticker symbol to search for, e.g., 'AAPL'."],
    look_back_days: Annotated[int, "How many days back from the current date to search for posts."],
) -> str:
    """
    Fetches recent Reddit posts for a given ticker from popular investing subreddits online.
    Args:
        ticker: The stock ticker to search for.
        look_back_days: How many days back to search.
    Returns:
        A formatted string containing the top Reddit posts about the ticker.
    """
    posts = fetch_reddit_posts_online(ticker, look_back_days)

    if not posts:
        return f"## No recent online Reddit posts found for {ticker} in the last {look_back_days} days.\n"

    news_str = ""
    for post in posts:
        content = post.get('content', '')
        if not content or content.strip() == "[removed]" or content.strip() == "[deleted]":
            content = "No content available."
        
        news_str += f"### r/{post['subreddit']}: {post['title']} (Upvotes: {post['upvotes']})\n"
        news_str += f"**Posted on:** {post['posted_date']}\n"
        news_str += f"**Content:** {content[:1000]}...\n" # Truncate long posts
        news_str += f"**URL:** {post['url']}\n\n"

    return f"## Recent Online Reddit Posts for {ticker}:\n\n{news_str}"


def get_google_news(
    query: Annotated[str, "Query to search with"],
    curr_date: Annotated[str, "Curr date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "how many days to look back"],
) -> str:
    query = query.replace(" ", "+")

    start_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    news_results = getNewsData(query, before, curr_date)

    news_str = ""

    for news in news_results:
        news_str += (
            f"### {news['title']} (source: {news['source']}) \n\n{news['snippet']}\n\n"
        )

    if len(news_results) == 0:
        return ""

    return f"## {query} Google News, from {before} to {curr_date}:\n\n{news_str}"


def get_reddit_global_news(
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "how many days to look back"],
    max_limit_per_day: Annotated[int, "Maximum number of news per day"],
) -> str:
    """
    Retrieve the latest top reddit news
    Args:
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format
    Returns:
        str: A formatted dataframe containing the latest news articles posts on reddit and meta information in these columns: "created_utc", "id", "title", "selftext", "score", "num_comments", "url"
    """

    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    posts = []
    # iterate from start_date to end_date
    curr_date = datetime.strptime(before, "%Y-%m-%d")

    total_iterations = (start_date - curr_date).days + 1
    pbar = tqdm(desc=f"Getting Global News on {start_date}", total=total_iterations)

    while curr_date <= start_date:
        curr_date_str = curr_date.strftime("%Y-%m-%d")
        fetch_result = fetch_top_from_category(
            "global_news",
            curr_date_str,
            max_limit_per_day,
            data_path=os.path.join(DATA_DIR, "reddit_data"),
        )
        posts.extend(fetch_result)
        curr_date += relativedelta(days=1)
        pbar.update(1)

    pbar.close()

    if len(posts) == 0:
        return ""

    news_str = ""
    for post in posts:
        if post["content"] == "":
            news_str += f"### {post['title']}\n\n"
        else:
            news_str += f"### {post['title']}\n\n{post['content']}\n\n"

    return f"## Global News Reddit, from {before} to {curr_date}:\n{news_str}"


def get_reddit_stock_info_offline(
    ticker: Annotated[str, "ticker symbol of the company"],
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    look_back_days: Annotated[int, "how many days to look back"],
    max_limit_per_day: Annotated[int, "Maximum number of news per day"],
) -> str:
    """
    Retrieve the latest top reddit news
    Args:
        ticker: ticker symbol of the company
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format
    Returns:
        str: A formatted dataframe containing the latest news articles posts on reddit and meta information in these columns: "created_utc", "id", "title", "selftext", "score", "num_comments", "url"
    """

    start_date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
    before = start_date_obj - relativedelta(days=look_back_days)
    before_str = before.strftime("%Y-%m-%d")

    posts = []
    # iterate from start_date to end_date
    curr_date_obj = datetime.strptime(before_str, "%Y-%m-%d")

    total_iterations = (start_date_obj - curr_date_obj).days + 1
    pbar = tqdm(
        desc=f"Getting Offline Reddit Company News for {ticker} on {curr_date}",
        total=total_iterations,
    )

    while curr_date_obj <= start_date_obj:
        curr_date_str = curr_date_obj.strftime("%Y-%m-%d")
        fetch_result = fetch_top_from_category(
            "company_news",
            curr_date_str,
            max_limit_per_day,
            ticker,
            data_path=os.path.join(DATA_DIR, "reddit_data"),
        )
        posts.extend(fetch_result)
        curr_date_obj += relativedelta(days=1)

        pbar.update(1)

    pbar.close()

    if len(posts) == 0:
        return ""

    news_str = ""
    for post in posts:
        if post["content"] == "":
            news_str += f"### {post['title']}\n\n"
        else:
            news_str += f"### {post['title']}\n\n{post['content']}\n\n"

    return f"##{ticker} Offline Reddit News, from {before_str} to {curr_date}:\n\n{news_str}"

def get_YFin_data(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    # read in data
    data_path = os.path.join(
        DATA_DIR,
        f"market_data/price_data/{symbol}-YFin-data-2015-01-01-2025-03-25.csv",
    )
    try:
        data = pd.read_csv(data_path)
    except FileNotFoundError:
        return f"Error: Offline data file not found for ticker {symbol} at {data_path}. Please ensure the necessary data is downloaded."

    if end_date > "2025-03-25":
        raise Exception(
            f"Get_YFin_Data: {end_date} is outside of the data range of 2015-01-01 to 2025-03-25"
        )

    # Extract just the date part for comparison
    data["DateOnly"] = data["Date"].str[:10]

    # Filter data between the start and end dates (inclusive)
    filtered_data = data[
        (data["DateOnly"] >= start_date) & (data["DateOnly"] <= end_date)
    ]

    # Drop the temporary column we created
    filtered_data = filtered_data.drop("DateOnly", axis=1)

    # remove the index from the dataframe
    filtered_data = filtered_data.reset_index(drop=True)

    return filtered_data


def get_stock_news_openai(ticker, curr_date):
    config = get_config()
    provider = config.get("llm_provider", "openai").lower()
    if provider not in ["openai", "ollama", "openrouter"]:
        return f"Error: get_stock_news_openai is only supported for OpenAI-compatible providers, but the current provider is '{provider}'."

    client = OpenAI(base_url=config["backend_url"])

    response = client.responses.create(
        model=config["quick_think_llm"],
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Can you search Social Media for {ticker} from 7 days before {curr_date} to {curr_date}? Make sure you only get the data posted during that period.",
                    }
                ],
            }
        ],
        text={"format": {"type": "text"}},
        reasoning={},
        tools=[
            {
                "type": "web_search_preview",
                "user_location": {"type": "approximate"},
                "search_context_size": "low",
            }
        ],
        temperature=1,
        max_output_tokens=4096,
        top_p=1,
        store=True,
    )

    return response.output[1].content[0].text


def get_global_news_openai(curr_date):
    config = get_config()
    provider = config.get("llm_provider", "openai").lower()
    if provider not in ["openai", "ollama", "openrouter"]:
        return f"Error: get_global_news_openai is only supported for OpenAI-compatible providers, but the current provider is '{provider}'."

    client = OpenAI(base_url=config["backend_url"])

    response = client.responses.create(
        model=config["quick_think_llm"],
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Can you search global or macroeconomics news from 7 days before {curr_date} to {curr_date} that would be informative for trading purposes? Make sure you only get the data posted during that period.",
                    }
                ],
            }
        ],
        text={"format": {"type": "text"}},
        reasoning={},
        tools=[
            {
                "type": "web_search_preview",
                "user_location": {"type": "approximate"},
                "search_context_size": "low",
            }
        ],
        temperature=1,
        max_output_tokens=4096,
        top_p=1,
        store=True,
    )

    return response.output[1].content[0].text


def get_fundamentals_openai(ticker, curr_date):
    config = get_config()
    provider = config.get("llm_provider", "openai").lower()
    if provider not in ["openai", "ollama", "openrouter"]:
        return f"Error: get_fundamentals_openai is only supported for OpenAI-compatible providers, but the current provider is '{provider}'."

    client = OpenAI(base_url=config["backend_url"])

    response = client.responses.create(
        model=config["quick_think_llm"],
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Can you search Fundamental for discussions on {ticker} during of the month before {curr_date} to the month of {curr_date}. Make sure you only get the data posted during that period. List as a table, with PE/PS/Cash flow/ etc",
                    }
                ],
            }
        ],
        text={"format": {"type": "text"}},
        reasoning={},
        tools=[
            {
                "type": "web_search_preview",
                "user_location": {"type": "approximate"},
                "search_context_size": "low",
            }
        ],
        temperature=1,
        max_output_tokens=4096,
        top_p=1,
        store=True,
    )

    return response.output[1].content[0].text
