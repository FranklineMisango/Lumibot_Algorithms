import backtrader as bt
import matplotlib.pyplot as plt 
from langchain_core.tools import tool
from dotenv import load_dotenv
load_dotenv()
import os
from alpaca_trade_api.rest import REST, TimeFrame
import  datetime as dt
from requests.exceptions import HTTPError
from lumibot.brokers import Alpaca
from lumibot.strategies import Strategy
from lumibot.traders import Trader
import yfinance as yf
from datetime import datetime
from lumibot.backtesting import YahooDataBacktesting
import os
import alpaca_trade_api as tradeapi
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib
import csv
import time
import threading
from datetime import datetime as dt
from alpaca.trading.client import TradingClient
import schedule
import matplotlib.pyplot as plt
import datetime
import pytz
from datetime import timedelta

from alpaca.trading.requests import MarketOrderRequest

from alpaca.trading.enums import AssetStatus,OrderSide, OrderType, TimeInForce, OrderClass, QueryOrderStatus

API_KEY = os.environ.get('APCA_API_KEY_ID')
API_SECRET = os.environ.get('APCA_API_SECRET_KEY')
APCA_API_BASE_URL = "https://paper-api.alpaca.markets"
EMAIL_USER = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVER = os.environ.get('YOUR_EMAIL_ADDRESS')
paper = True

import yfinance as yf
import backtrader as bt
import datetime as dt
import pandas as pd
import pytz
import time
import threading

# Strategy Class for SMA Crossover
class SmaCross(bt.Strategy):
    params = dict(pfast=13, pslow=25)

    def __init__(self):
        sma1 = bt.ind.SMA(period=self.p.pfast)
        sma2 = bt.ind.SMA(period=self.p.pslow)
        self.crossover = bt.ind.CrossOver(sma1, sma2)

    def next(self):
        if not self.position:
            if self.crossover > 0:  # Buy signal
                self.buy(size=100)  # Example: buy 100 shares
        elif self.crossover < 0:  # Sell signal
            self.sell(size=100)  # Example: sell 100 shares

    def stop(self):
        # Strategy statistics after the strategy execution
        total_value = self.broker.getvalue()
        print(f"Final Portfolio Value: {total_value}")
        print(f"Strategy Return: {100 * (total_value - self.starting_value) / self.starting_value}%")

# Analyzer for Strategy Statistics
def add_analyzers(cerebro):
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trade_analyzer")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe_ratio")

# Fetch minute-level data from Yahoo Finance
def fetch_minute_data(ticker):
    end = dt.datetime.now()
    start = end - dt.timedelta(days=1)
    data = yf.download(ticker, start=start, end=end, interval='1m')
    return data

# Run Cerebro for a stock with fetched data
def run_cerebro_with_data(ticker, data):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(SmaCross)

    # Convert the Yahoo Finance data to Backtrader data feed
    data_bt = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_bt)

    # Set starting cash and commission
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)

    # Add analyzers for trade statistics
    add_analyzers(cerebro)

    # Run the strategy
    results = cerebro.run()

    # Print strategy statistics after each execution
    strategy_statistics(results, ticker)

# Function to calculate and display strategy statistics
def strategy_statistics(results, ticker):
    strat = results[0]
    trade_analysis = strat.analyzers.trade_analyzer.get_analysis()
    sharpe_ratio = strat.analyzers.sharpe_ratio.get_analysis().get('sharperatio', None)

    # Total number of trades
    total_trades = trade_analysis.total.closed

    # Win Rate
    win_rate = round((trade_analysis.won.total / total_trades) * 100, 2) if total_trades > 0 else 0

    # Average Percent Gain and Loss
    avg_percent_gain = round(trade_analysis.won.pnl.average, 2) if trade_analysis.won.total > 0 else 0
    avg_percent_loss = round(trade_analysis.lost.pnl.average, 2) if trade_analysis.lost.total > 0 else 0

    # Gain/Loss Ratio
    gain_loss_ratio = round(avg_percent_gain / -avg_percent_loss, 2) if avg_percent_loss != 0 else float('inf')

    # Max Return and Max Loss
    max_return = round(trade_analysis.won.pnl.max, 2) if trade_analysis.won.total > 0 else 0
    max_loss = round(trade_analysis.lost.pnl.max, 2) if trade_analysis.lost.total > 0 else 0

    # Sharpe Ratio
    sharpe_ratio = round(sharpe_ratio, 2) if sharpe_ratio else "N/A"

    print(f"\nStrategy Statistics for {ticker}:")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate}%")
    print(f"Average % Gain per Trade: {avg_percent_gain}%")
    print(f"Average % Loss per Trade: {avg_percent_loss}%")
    print(f"Gain/Loss Ratio: {gain_loss_ratio}")
    print(f"Max Return: {max_return}%")
    print(f"Max Loss: {max_loss}%")
    print(f"Sharpe Ratio: {sharpe_ratio}")
    print(f"---------------------------------------------\n")

# Threaded function to fetch data and run the strategy
def run_stock_strategy(ticker):
    while True:
        nyc_time = pytz.timezone('America/New_York')
        now = dt.datetime.now(nyc_time)
        current_time = now.time()

        market_open = dt.time(9, 30)
        market_close = dt.time(16, 0)

        if market_open <= current_time <= market_close:
            print(f"Running SMA strategy for {ticker} at {now.strftime('%Y-%m-%d %H:%M:%S')}")

            # Fetch minute-level data
            data = fetch_minute_data(ticker)

            if not data.empty:
                # Run the strategy with the fetched data
                run_cerebro_with_data(ticker, data)

            # Sleep for 15 minutes
            time.sleep(900)
        else:
            print(f"Market is closed for {ticker}. Waiting for the next session.")
            # Wait for the next market session
            next_open = dt.datetime.combine(now.date() + dt.timedelta(days=1), market_open)
            sleep_time = (next_open - now).total_seconds()
            time.sleep(sleep_time)

# Launch threads for each stock ticker
def run_sma_strategy_threaded(stock_list):
    threads = []

    for ticker in stock_list:
        thread = threading.Thread(target=run_stock_strategy, args=(ticker,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

# List of stock tickers to monitor
stock_universe = ['AAPL', 'TSLA', 'MSFT', 'NVDA', 'AMZN']  # Example tickers

if __name__ == '__main__':
    print("Starting threaded SMA strategy with real-time data and statistics")
    run_sma_strategy_threaded(stock_universe)

   