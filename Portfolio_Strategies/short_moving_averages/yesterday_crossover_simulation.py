import backtrader as bt
import matplotlib.pyplot as plt 
from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
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

API_KEY = os.environ.get('API_KEY_ALPACA')
API_SECRET = os.environ.get('SECRET_KEY_ALPACA')
APCA_API_BASE_URL = "https://paper-api.alpaca.markets"
EMAIL_USER = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVER = os.environ.get('YOUR_EMAIL_ADDRESS')
paper = True
import yfinance as yf
import backtrader as bt
import pandas as pd
import pytz
import time
import threading

# Strategy Class for SMA Crossover

trading_api =  tradeapi.REST(API_KEY, API_SECRET, APCA_API_BASE_URL, 'v2')

# Global 

def mail_alert(mail_content, sleep_time):
    # The mail addresses and password
    sender_address = EMAIL_USER
    sender_pass = EMAIL_PASSWORD

    # Setup MIME
    message = MIMEMultipart()
    message['From'] = 'Frankline & Co. HFT {SMA Crossover strategy} Day Trading Bot'
    message['To'] = EMAIL_RECEIVER
    message['Subject'] = 'Frankline & Co. HFT Important Day Updates'
    message['Signature'] =  "Making HFT Fun and Profitable"
    
    # The body and the attachments for the mail
    message.attach(MIMEText(mail_content, 'plain'))

    # Create SMTP session for sending the mail
    session = smtplib.SMTP('smtp.gmail.com', 587)  # use gmail with port
    session.starttls()  # enable security

    # login with mail_id and password
    session.login(sender_address, sender_pass)
    text = message.as_string()
    session.sendmail(sender_address, EMAIL_RECEIVER, text)
    session.quit()
    time.sleep(sleep_time)

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

async def fetch_minute_data(ticker):
    # Set the timezone to UTC for consistency
    tz = pytz.timezone('America/New_York')
    
    # Get yesterday's date
    end = dt.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=1)

    # Fetch minute-level data
    data = yf.download(ticker, start=start, end=end + timedelta(days=1), interval='1m')
    
    # Filter to get only the trading hours (09:30 to 16:00)
    data = data.between_time('09:30', '16:00')
    
    return data

def run_cerebro_with_data(ticker, data_bt):
    # Ensure 'datetime' is in datetime format
    if not pd.api.types.is_datetime64_any_dtype(data_bt.datetime):
        data_bt['datetime'] = pd.to_datetime(data_bt['datetime'])

    # Replace the hour and minute
    data_bt['datetime'] = data_bt['datetime'].apply(lambda x: x.replace(hour=9, minute=30))

    cerebro = bt.Cerebro()
    cerebro.addstrategy(SmaCross)


    # Adjust the datetime index to simulate trades happening at 09:30 AM
    data_bt.datetime = data_bt.datetime.apply(lambda x: x.replace(hour=9, minute=30))

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

async def run_stock_strategy(ticker):
    while True:
        # Fetch yesterday's data and simulate as if it's 09:30 AM
        data = await fetch_minute_data(ticker)

        if not data.empty:
            # Run the strategy with the fetched data
            await run_cerebro_with_data(ticker, data)

        # Sleep for a specified duration before fetching data again
        await asyncio.sleep(900)  # Wait 15 minutes before the next cycle

async def run_sma_strategy_async(stock_list):
    tasks = [run_stock_strategy(ticker) for ticker in stock_list]
    await asyncio.gather(*tasks)


#testing 
stockUniverse = [
        # Technology
        'AAPL', 'MSFT', 'NVDA', 'GOOG', 'META',
        
        # Financials
        'JPM', 'BAC', 'GS', 'MS', 'C',
        
        # Healthcare
        'JNJ', 'PFE', 'UNH', 'ABT', 'MRK',
        
        # Consumer Discretionary
        'AMZN', 'TSLA', 'NKE', 'MCD', 'HD',
        
        # Consumer Staples
        'PG', 'KO', 'PEP', 'WMT', 'COST',
        
        # Energy
        'XOM', 'CVX', 'BP', 'SLB', 'EOG',
        
        # Industrials
        'BA', 'CAT', 'HON', 'GE', 'LMT',
        
        # Communication Services
        'DIS', 'CMCSA', 'NFLX', 'T', 'VZ',
        
        # Real Estate
        'AMT', 'PLD', 'SPG', 'EQIX', 'O',
        
        # Utilities
        'NEE', 'DUK', 'SO', 'D', 'EXC'
    ]

if __name__ == '__main__':
    print("Starting threaded SMA strategy with real-time data and statistics")
    asyncio.run(run_sma_strategy_async(stockUniverse))

   