import praw
import os
import logging
import json
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Annotated
import re
import time

# Explicitly load credentials from environment variables
try:
    client_id = os.getenv("PRAW_CLIENT_ID")
    client_secret = os.getenv("PRAW_CLIENT_SECRET")
    user_agent = os.getenv("PRAW_USER_AGENT")
    username = os.getenv("PRAW_USERNAME")
    password = os.getenv("PRAW_PASSWORD")

    if not all([client_id, client_secret, user_agent, username, password]):
        raise ValueError("One or more PRAW environment variables are not set.")

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        username=username,
        password=password,
    )
    logging.info("PRAW Reddit instance created successfully from environment variables.")
except Exception as e:
    logging.error(f"Failed to create PRAW Reddit instance. Please ensure PRAW environment variables are correctly set. Error: {e}")
    reddit = None

ticker_to_company = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Google",
    "AMZN": "Amazon",
    "TSLA": "Tesla",
    "NVDA": "Nvidia",
    "TSM": "Taiwan Semiconductor Manufacturing Company OR TSMC",
    "JPM": "JPMorgan Chase OR JP Morgan",
    "JNJ": "Johnson & Johnson OR JNJ",
    "V": "Visa",
    "WMT": "Walmart",
    "META": "Meta OR Facebook",
    "AMD": "AMD",
    "INTC": "Intel",
    "QCOM": "Qualcomm",
    "BABA": "Alibaba",
    "ADBE": "Adobe",
    "NFLX": "Netflix",
    "CRM": "Salesforce",
    "PYPL": "PayPal",
    "PLTR": "Palantir",
    "MU": "Micron",
    "SQ": "Block OR Square",
    "ZM": "Zoom",
    "CSCO": "Cisco",
    "SHOP": "Shopify",
    "ORCL": "Oracle",
    "X": "Twitter OR X",
    "SPOT": "Spotify",
    "AVGO": "Broadcom",
    "ASML": "ASML ",
    "TWLO": "Twilio",
    "SNAP": "Snap Inc.",
    "TEAM": "Atlassian",
    "SQSP": "Squarespace",
    "UBER": "Uber",
    "ROKU": "Roku",
    "PINS": "Pinterest",
}


def fetch_top_from_category(
    category: Annotated[
        str, "Category to fetch top post from. Collection of subreddits."
    ],
    date: Annotated[str, "Date to fetch top posts from."],
    max_limit: Annotated[int, "Maximum number of posts to fetch."],
    query: Annotated[str, "Optional query to search for in the subreddit."] = None,
    data_path: Annotated[
        str,
        "Path to the data folder. Default is 'reddit_data'.",
    ] = "reddit_data",
):
    base_path = data_path

    all_content = []

    if max_limit < len(os.listdir(os.path.join(base_path, category))):
        raise ValueError(
            "REDDIT FETCHING ERROR: max limit is less than the number of files in the category. Will not be able to fetch any posts"
        )

    limit_per_subreddit = max_limit // len(
        os.listdir(os.path.join(base_path, category))
    )

    for data_file in os.listdir(os.path.join(base_path, category)):
        # check if data_file is a .jsonl file
        if not data_file.endswith(".jsonl"):
            continue

        all_content_curr_subreddit = []

        with open(os.path.join(base_path, category, data_file), "rb") as f:
            for i, line in enumerate(f):
                # skip empty lines
                if not line.strip():
                    continue

                parsed_line = json.loads(line)

                # select only lines that are from the date
                post_date = datetime.utcfromtimestamp(
                    parsed_line["created_utc"]
                ).strftime("%Y-%m-%d")
                if post_date != date:
                    continue

                # if is company_news, check that the title or the content has the company's name (query) mentioned
                if "company" in category and query:
                    search_terms = []
                    if "OR" in ticker_to_company[query]:
                        search_terms = ticker_to_company[query].split(" OR ")
                    else:
                        search_terms = [ticker_to_company[query]]

                    search_terms.append(query)

                    found = False
                    for term in search_terms:
                        if re.search(
                            term, parsed_line["title"], re.IGNORECASE
                        ) or re.search(term, parsed_line["selftext"], re.IGNORECASE):
                            found = True
                            break

                    if not found:
                        continue

                post = {
                    "title": parsed_line["title"],
                    "content": parsed_line["selftext"],
                    "url": parsed_line["url"],
                    "upvotes": parsed_line["ups"],
                    "posted_date": post_date,
                }

                all_content_curr_subreddit.append(post)

        # sort all_content_curr_subreddit by upvote_ratio in descending order
        all_content_curr_subreddit.sort(key=lambda x: x["upvotes"], reverse=True)

        all_content.extend(all_content_curr_subreddit[:limit_per_subreddit])

    return all_content


def fetch_reddit_posts_online(ticker: str, look_back_days: int, max_posts: int = 20):
    """
    Fetches recent Reddit posts for a given ticker from popular investing subreddits using PRAW.
    Args:
        ticker (str): The stock ticker to search for.
        look_back_days (int): How many days back to search for posts.
        max_posts (int): The maximum total number of posts to return.
    Returns:
        list: A list of dictionaries, where each dictionary represents a post.
    """
    if not reddit:
        logging.error("PRAW Reddit instance is not available. Cannot fetch posts online.")
        return []

    subreddits = ["wallstreetbets", "stocks", "investing", "StockMarket"]
    all_posts = []
    
    # Create a more flexible search query
    company_name = ticker_to_company.get(ticker, ticker)
    search_terms = [ticker, company_name]
    if " OR " in company_name:
        search_terms.extend(company_name.split(" OR "))
    
    # Remove duplicates and create the final query string
    search_query = " OR ".join(list(dict.fromkeys(search_terms)))

    for subreddit_name in subreddits:
        try:
            subreddit = reddit.subreddit(subreddit_name)
            logging.info(f"Fetching Reddit posts from r/{subreddit_name} for query: {search_query}")
            
            # PRAW's search is generally sorted by relevance by default. We can sort by new.
            for post in subreddit.search(search_query, sort='new', limit=50):
                # Post-filter by date, as search query timestamp filtering can be unreliable
                created_utc = datetime.utcfromtimestamp(post.created_utc)
                if created_utc >= (datetime.utcnow() - timedelta(days=look_back_days)):
                    all_posts.append({
                        "title": post.title,
                        "content": post.selftext,
                        "url": post.url,
                        "upvotes": post.score,
                        "posted_date": created_utc.strftime("%Y-%m-%d"),
                        "subreddit": subreddit_name
                    })

        except Exception as e:
            logging.warning(f"Could not fetch data from r/{subreddit_name} for ticker {ticker}. Error: {e}")
            continue

    # Sort all collected posts by date (most recent first) and then by upvotes
    all_posts.sort(key=lambda x: (x['posted_date'], x['upvotes']), reverse=True)

    return all_posts[:max_posts]
