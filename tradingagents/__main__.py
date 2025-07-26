import json
import logging
import sys
import os

# This ensures that the 'tradingagents' package is in the path
# even when run as a module from the parent directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tradingagents.dataflows.reddit_utils import fetch_reddit_posts_online

# Set up basic logging to see the output from the function
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_reddit_api():
    """
    A simple test function to fetch and print Reddit posts for a specific ticker.
    """
    ticker = "AAPL"
    look_back_days = 7
    max_posts = 10

    print(f"--- Searching Reddit for '{ticker}' posts from the last {look_back_days} days (limit: {max_posts}) ---")

    # Call the function we've been working on
    posts = fetch_reddit_posts_online(
        ticker=ticker,
        look_back_days=look_back_days,
        max_posts=max_posts
    )

    if posts:
        print(f"--- Found {len(posts)} posts. ---")
        # Pretty-print the results
        print(json.dumps(posts, indent=2))
    else:
        print("--- No posts found. This could be due to no recent discussion or an API configuration issue. ---")
    
    print("--- Test complete. ---")

if __name__ == "__main__":
    test_reddit_api()
