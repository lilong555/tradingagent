import pandas as pd
import yfinance as yf
from stockstats import wrap
from typing import Annotated
import os
from .config import get_config


class StockstatsUtils:
    # In-memory cache for stock dataframes to avoid repeated downloads in a single run
    _stock_data_cache = {}

    @staticmethod
    def get_stock_stats(
        symbol: Annotated[str, "ticker symbol for the company"],
        indicator: Annotated[
            str, "quantitative indicators based off of the stock data for the company"
        ],
        curr_date: Annotated[
            str, "curr date for retrieving stock price data, YYYY-mm-dd"
        ],
        data_dir: Annotated[
            str,
            "directory where the stock data is stored.",
        ],
        online: Annotated[
            bool,
            "whether to use online tools to fetch data or offline tools. If True, will use online tools.",
        ] = False,
    ):
        # Normalize indicator to lower case to handle case-sensitivity issues
        indicator = indicator.lower()
        
        # Convert curr_date to datetime object at the beginning for consistent typing
        curr_date = pd.to_datetime(curr_date)
        
        df = None
        
        # Use a cache key for the current symbol
        cache_key = symbol

        if cache_key in StockstatsUtils._stock_data_cache:
            df = StockstatsUtils._stock_data_cache[cache_key]
        else:
            data = None
            if not online:
                try:
                    data = pd.read_csv(
                        os.path.join(
                            data_dir,
                            f"{symbol}-YFin-data-2015-01-01-2025-03-25.csv",
                        )
                    )
                except FileNotFoundError:
                    raise Exception("Stockstats fail: Yahoo Finance data not fetched yet!")
            else:
                # Use curr_date as the basis for the download range
                end_date = curr_date
                start_date = end_date - pd.DateOffset(years=15) # Ensure a long history for indicator calculation
                
                start_date_str = start_date.strftime("%Y-%m-%d")
                end_date_str = end_date.strftime("%Y-%m-%d")

                # Get config and ensure cache directory exists
                config = get_config()
                os.makedirs(config["data_cache_dir"], exist_ok=True)

                data_file = os.path.join(
                    config["data_cache_dir"],
                    f"{symbol}-YFin-data-{start_date_str}-{end_date_str}.csv",
                )

                if os.path.exists(data_file):
                    data = pd.read_csv(data_file)
                else:
                    data = yf.download(
                        symbol,
                        start=start_date_str,
                        end=end_date_str,
                        multi_level_index=False,
                        progress=False,
                        auto_adjust=True,
                    )
                    data = data.reset_index()
                    data.to_csv(data_file, index=False)
            
            # Ensure the 'Date' column is in datetime format
            data['Date'] = pd.to_datetime(data['Date'])
            df = wrap(data)
            # Store the processed dataframe in the cache
            StockstatsUtils._stock_data_cache[cache_key] = df

        # Now, df is guaranteed to be a wrapped dataframe with datetime 'Date' column
        df[indicator]  # trigger stockstats to calculate the indicator
        
        # Perform a direct, robust datetime comparison (ignoring time part).
        matching_rows = df[df["Date"].dt.normalize() == curr_date.normalize()]

        if not matching_rows.empty:
            indicator_value = matching_rows[indicator].values[0]
            return indicator_value
        else:
            return "N/A: Not a trading day (weekend or holiday) or data not available for this date."
