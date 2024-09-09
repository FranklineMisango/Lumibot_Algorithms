import pandas as pd
import datetime
from datetime import datetime as dt
from pytz import timezone
import time
from dotenv import load_dotenv

import alpaca_trade_api as alpaca
import json

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from datetime import timedelta
import os.path
import glob
import yfinance as yf

# Load API key
load_dotenv()

ALPACA_API_KEY = os.environ.get('ALPACAKEY')
ALPACA_API_SECRET_KEY = os.environ.get('ALPACASECRETKEY')

api = alpaca.REST(ALPACA_API_KEY, ALPACA_API_SECRET_KEY, base_url='https://paper-api.alpaca.markets', api_version='v2')

# Load all tickers from the global folder
ticker_files = glob.glob('Test_tickers/*')
tickers = []
for file in ticker_files:
    with open(file, 'r') as f:
        file_tickers = f.read().upper().split()
        print(f"Tickers from {file}: {file_tickers}")  # Debug print
        tickers.extend(file_tickers)

print(f"All tickers: {tickers}")  # Debug print


def get_minute_data(tickers):
    
    def save_min_data(ticker):
        end_time = dt.now().astimezone(timezone('America/New_York')).replace(hour=16, minute=0, second=0, microsecond=0) - timedelta(days=3)
        start_time = end_time - timedelta(minutes=30)
        
        trades = api.get_trades(str(ticker), start=start_time.isoformat(), end=end_time.isoformat(), limit=10000).df
        print(f"Trades columns for {ticker}: {trades.columns}")  # Debug print
        if not trades.empty:
            prices = trades[['price']] if 'price' in trades.columns else trades
            prices.index = pd.to_datetime(prices.index).tz_convert('America/New_York').strftime('%Y-%m-%d %H:%M')
            prices = prices[~prices.index.duplicated(keep='first')]
            print(prices)
        else:
            prices = pd.DataFrame()

        quotes = api.get_quotes(str(ticker), start=start_time.isoformat(), end=end_time.isoformat(), limit=10000).df
        print(f"Quotes columns for {ticker}: {quotes.columns}")  # Debug print
        if not quotes.empty:
            quotes = quotes[['ask_price']] if 'ask_price' in quotes.columns else quotes
            quotes.index = pd.to_datetime(quotes.index).tz_convert('America/New_York').strftime('%Y-%m-%d %H:%M')
            quotes = quotes[~quotes.index.duplicated(keep='first')]
        else:
            quotes = pd.DataFrame()

        if not prices.empty and not quotes.empty:
            df = pd.merge(prices, quotes, how='inner', left_index=True, right_index=True)
            df.to_csv(f'alpaca_test_ticker_data/{ticker}.csv')
        
    for ticker in tickers:
        save_min_data(ticker)
        

def get_past30_data(tickers):
    
    def save_30_data(ticker):
        end_time = dt.now().astimezone(timezone('America/New_York')).replace(hour=16, minute=0, second=0, microsecond=0) - timedelta(days=3)
        start_time = end_time - timedelta(minutes=30)
        
        # Fetch trades for the last 30 minutes
        prices_1 = api.get_trades(str(ticker), start=(end_time - timedelta(minutes=30)).isoformat(),
                                end=(end_time - timedelta(minutes=28, seconds=30)).isoformat(), 
                                limit=10000).df
        print(f"Trades columns for {ticker} (part 1): {prices_1.columns}")  # Debug print
        prices_1 = prices_1[['price']] if 'price' in prices_1.columns else prices_1
        
        prices_2 = api.get_trades(str(ticker), start=(end_time - timedelta(minutes=1, seconds=30)).isoformat(),
                                end=end_time.isoformat(), 
                                limit=10000).df
        print(f"Trades columns for {ticker} (part 2): {prices_2.columns}")  # Debug print
        prices_2 = prices_2[['price']] if 'price' in prices_2.columns else prices_2
        
        # Fetch trades for the same time period yesterday
        prices_3 = api.get_trades(str(ticker), start=(start_time - timedelta(minutes=30)).isoformat(),
                                end=(start_time - timedelta(minutes=28, seconds=30)).isoformat(), 
                                limit=10000).df
        print(f"Trades columns for {ticker} (part 3): {prices_3.columns}")  # Debug print
        prices_3 = prices_3[['price']] if 'price' in prices_3.columns else prices_3
        
        prices_4 = api.get_trades(str(ticker), start=(start_time - timedelta(minutes=1, seconds=30)).isoformat(),
                                end=start_time.isoformat(), 
                                limit=10000).df
        print(f"Trades columns for {ticker} (part 4): {prices_4.columns}")  # Debug print
        prices_4 = prices_4[['price']] if 'price' in prices_4.columns else prices_4
        
        # Combine and format prices
        prices = pd.concat([prices_1, prices_2, prices_3, prices_4])
        prices.index = pd.to_datetime(prices.index).tz_localize('UTC').tz_convert('America/New_York').strftime('%Y-%m-%d %H:%M')


        # Fetch quotes for the last 30 minutes
        quotes_1 = api.get_quotes(str(ticker), start=(end_time - timedelta(minutes=30)).isoformat(),
                                end=(end_time - timedelta(minutes=28, seconds=30)).isoformat(), 
                                limit=10000).df
        print(f"Quotes columns for {ticker} (part 1): {quotes_1.columns}")  # Debug print
        quotes_1 = quotes_1[['ask_price']] if 'ask_price' in quotes_1.columns else quotes_1
        
        quotes_2 = api.get_quotes(str(ticker), start=(end_time - timedelta(minutes=1, seconds=30)).isoformat(),
                                end=end_time.isoformat(), 
                                limit=10000).df
        print(f"Quotes columns for {ticker} (part 2): {quotes_2.columns}")  # Debug print
        quotes_2 = quotes_2[['ask_price']] if 'ask_price' in quotes_2.columns else quotes_2
        
        # Fetch quotes for the same time period yesterday
        quotes_3 = api.get_quotes(str(ticker), start=(start_time - timedelta(minutes=30)).isoformat(),
                                end=(start_time - timedelta(minutes=28, seconds=30)).isoformat(), 
                                limit=10000).df
        print(f"Quotes columns for {ticker} (part 3): {quotes_3.columns}")  # Debug print
        quotes_3 = quotes_3[['ask_price']] if 'ask_price' in quotes_3.columns else quotes_3
        
        quotes_4 = api.get_quotes(str(ticker), start=(start_time - timedelta(minutes=1, seconds=30)).isoformat(),
                                end=start_time.isoformat(), 
                                limit=10000).df
        print(f"Quotes columns for {ticker} (part 4): {quotes_4.columns}")  # Debug print
        quotes_4 = quotes_4[['ask_price']] if 'ask_price' in quotes_4.columns else quotes_4
        
        # Combine and format quotes
        quotes = pd.concat([quotes_1, quotes_2, quotes_3, quotes_4])
        quotes.index = pd.to_datetime(quotes.index).tz_convert('America/New_York').strftime('%Y-%m-%d %H:%M')
        quotes = quotes[~quotes.index.duplicated(keep='first')]
        
        # Merge prices and quotes
        df = pd.merge(prices, quotes, how='inner', left_index=True, right_index=True)
        df.to_csv('alpaca_test_ticker_data/{}.csv'.format(ticker))

    for ticker in tickers:
        save_30_data(ticker)


get_past30_data(tickers)