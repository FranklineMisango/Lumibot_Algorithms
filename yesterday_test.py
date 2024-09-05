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
ALPACA_API_SECRET_KEY =  os.environ.get('ALPACASECRETKEY')

api = alpaca.REST(ALPACA_API_KEY, ALPACA_API_SECRET_KEY, base_url='https://paper-api.alpaca.markets', api_version = 'v2')

# Load all tickers from the global folder
ticker_files = glob.glob('Test_tickers/*')
tickers = []
for file in ticker_files:
    with open(file, 'r') as f:
        file_tickers = f.read().upper().split()
        print(f"Tickers from {file}: {file_tickers}")  # Debug print
        tickers.extend(file_tickers)

print(f"All tickers: {tickers}")  # Debug print


'''
Yesterday's data using alpaca api
# Verify validity of 1 min data
def get_minute_data(tickers):
    def save_min_data(ticker):
        end_time = dt.now().astimezone(timezone('America/New_York')).replace(hour=10, minute=00, second=0, microsecond=0) - timedelta(days=1)
        start_time = end_time - timedelta(minutes=30)
        
        prices = api.get_trades(str(ticker), start=start_time.isoformat(), end=end_time.isoformat(), limit=10000).df[['price']]
        prices.index = pd.to_datetime(prices.index, format='%Y-%m-%d').strftime('%Y-%m-%d %H:%M')
        prices = prices[~prices.index.duplicated(keep='first')]

        quotes = api.get_quotes(str(ticker), start=start_time.isoformat(), end=end_time.isoformat(), limit=10000).df[['ask_price']]
        quotes.index = pd.to_datetime(quotes.index, format='%Y-%m-%d').strftime('%Y-%m-%d %H:%M')
        quotes = quotes[~quotes.index.duplicated(keep='first')]

        df = pd.merge(prices, quotes, how='inner', left_index=True, right_index=True)
        df.to_csv(f'tick_data/{ticker}.csv')
        
    for ticker in tickers:
        save_min_data(ticker)
'''

# Verify validity of 1 min data
def get_minute_data(tickers):
    def save_min_data(ticker):
        end_time = dt.now().astimezone(timezone('America/New_York'))
        start_time = end_time - timedelta(minutes=2)
        
        try:
            data = yf.download(ticker, start=start_time, end=end_time, interval='1m')
            if data.empty:
                print(f"No price data found for {ticker}")
                return
            data.index = data.index.strftime('%Y-%m-%d %H:%M')
            data = data[~data.index.duplicated(keep='first')]
            data.to_csv(f'tick_data/{ticker}.csv')
        except Exception as e:
            print(f"Failed to download data for {ticker}: {e}")
        
    for ticker in tickers:
        save_min_data(ticker)

# Verify validity of 1 min data
def get_past30_data(tickers):
    def save_30_data(ticker):
        end_time = dt.now().astimezone(timezone('America/New_York'))
        start_time = end_time - timedelta(minutes=30)
        
        try:
            data = yf.download(ticker, start=start_time, end=end_time, interval='1m')
            if data.empty:
                print(f"No price data found for {ticker}")
                return
            data.index = data.index.strftime('%Y-%m-%d %H:%M')
            data = data[~data.index.duplicated(keep='first')]
            data.to_csv(f'tick_data/{ticker}.csv')
        except Exception as e:
            print(f"Failed to download data for {ticker}: {e}")
        
    for ticker in tickers:
        save_30_data(ticker)



get_past30_data(tickers)