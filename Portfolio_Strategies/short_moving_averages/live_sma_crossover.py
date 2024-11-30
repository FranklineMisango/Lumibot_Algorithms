import backtrader as bt
import matplotlib.pyplot as plt 
from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
from alpaca_trade_api.rest import REST, TimeFrame
import datetime as dt
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
from alpaca.trading.enums import AssetStatus, OrderSide, OrderType, TimeInForce, OrderClass, QueryOrderStatus

API_KEY = os.environ.get('API_KEY_ALPACA')
API_SECRET = os.environ.get('SECRET_KEY_ALPACA')
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

trading_api = tradeapi.REST(API_KEY, API_SECRET, APCA_API_BASE_URL, 'v2')

#global ticker holding array 

tickers_sent = []
total_sell_orders = 0

def mail_alert(mail_content, sleep_time):
    # The mail addresses and password
    sender_address = EMAIL_USER
    sender_pass = EMAIL_PASSWORD

    # Setup MIME
    message = MIMEMultipart()
    message['From'] = 'Frankline & Co. HFT {SMA Crossover strategy} Day Trading Bot'
    message['To'] = EMAIL_RECEIVER
    message['Subject'] = 'Frankline & Co. HFT Important Day Updates'
    message['Signature'] = "Making HFT Fun and Profitable"
    
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

# Fetch minute-level data from Yahoo Finance
async def fetch_minute_data(ticker):
    loop = asyncio.get_event_loop()
    end = dt.datetime.now()
    start = end - dt.timedelta(days=1)
    data = await loop.run_in_executor(None, yf.download, ticker, start, end, '1m')
    return data

# Function to accumulate data for 15 minutes and run cerebro
async def accumulate_and_run_cerebro(ticker):
    accumulated_data = pd.DataFrame()
    end_time = datetime.now() + timedelta(minutes=15)
    
    while datetime.now() < end_time:
        data = await fetch_minute_data(ticker)
        if not data.empty:
            accumulated_data = pd.concat([accumulated_data, data])
        await asyncio.sleep(60)
    
    if not accumulated_data.empty:
        run_cerebro_with_data(ticker, accumulated_data)

# Function to send orders if the results from run_cerebro are profitable : gain_loss_ratio > 1 and avg_percent_gain > 0
def send_order(ticker, gain_loss_ratio, avg_percent_gain):
    if gain_loss_ratio > 1 and avg_percent_gain > 0:
        total_buy_orders = 0
        print(f"Sending order for {ticker}")
        number = 1000 # send a 1000 shares
        # preparing market order
        market_order_data = MarketOrderRequest(
                            symbol=ticker,
                            qty=number,
                            side=OrderSide.BUY,
                            time_in_force=TimeInForce.DAY
                            )

        # Market order
        sell_market_order = tradeapi.submit_order(
                        order_data=market_order_data
                    )
        tickers_sent.append(ticker)
        total_buy_orders += 1

        
# Function to sell orders if the results from run_cerebro are resulting in a loss : gain_loss_ratio < 1 and avg_percent_gain < 0
def sell_order(ticker, gain_loss_ratio, avg_percent_gain):
    if gain_loss_ratio < 1 and avg_percent_gain < 0:
        total_sell_orders = 0
        print(f"Selling order for {ticker}")
        # if the ticker is already in the list of tickers sent, sell the order completely
        if ticker in tickers_sent:
            number = 1000
            # preparing market order
            market_order_data = MarketOrderRequest(
                                symbol=ticker,
                                qty=number,
                                side=OrderSide.SELL,
                                time_in_force=TimeInForce.DAY
                                )   
            # Market order
            sell_market_order = tradeapi.submit_order(
                            order_data=market_order_data
                        )
            tickers_sent.remove(ticker)
            total_sell_orders += 1

# Run Cerebro for a stock with fetched data - 15 minutes - fails to run within the time zone
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

# Function to calculate and display strategy statistics for a data collected from the past 15 minutes
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
async def run_stock_strategy(ticker):
    while True:
        isOpen = trading_api.get_clock().is_open
        while not isOpen:
            clock = trading_api.get_clock()
            openingTime = clock.next_open.replace(tzinfo=datetime.timezone.utc).timestamp()
            currTime = clock.timestamp.replace(tzinfo=datetime.timezone.utc).timestamp()
            timeToOpen = int((openingTime - currTime) / 60)
            trading_api.initial_equity = int(float(trading_api.get_account().equity))
            initial_equity = trading_api.initial_equity
            if timeToOpen == 30:
                buying_power = int(float(trading_api.get_account().buying_power))
                initial_total_cash_for_trading = trading_api.initial_equity + buying_power
                mail_content = (
                    f'The market opens in 30 minutes. '
                    f'Your initial equity (cash) is: ${initial_equity:.2f}. '
                    f'Our Total cash available Before Trading is: ${initial_total_cash_for_trading:.2f}'
                )
                mail_alert(mail_content, 60)

            print(f"{timeToOpen} minutes til market open.")
            equity = int(float(trading_api.get_account().equity))
            buying_power = int(float(trading_api.get_account().buying_power))
            initial_total_cash_for_trading = equity + buying_power
            print(f'Your initial equity (cash) is: ${initial_equity:.2f}. ')                       
            print(f"Our Total Funding pool with Buying power is  : {initial_total_cash_for_trading}")
            await asyncio.sleep(60)
            isOpen = trading_api.get_clock().is_open

        await accumulate_and_run_cerebro(ticker)

        await asyncio.sleep(900)

async def run_sma_strategy_async(stock_list):
    tasks = [run_stock_strategy(ticker) for ticker in stock_list]
    await asyncio.gather(*tasks)


#testing 
stockUniverse = [
        # Technology
        'AAPL', 'MSFT', 'NVDA', 'GOOG', 'META',
        'JPM', 'BAC', 'GS', 'MS', 'C',
        'JNJ', 'PFE', 'UNH', 'ABT', 'MRK',
        'AMZN', 'TSLA', 'NKE', 'MCD', 'HD',
        'PG', 'KO', 'PEP', 'WMT', 'COST',
        'XOM', 'CVX', 'BP', 'SLB', 'EOG',
        'BA', 'CAT', 'HON', 'GE', 'LMT',
        'DIS', 'CMCSA', 'NFLX', 'T', 'VZ',
        'AMT', 'PLD', 'SPG', 'EQIX', 'O',
        'NEE', 'DUK', 'SO', 'D', 'EXC'
    ]

if __name__ == '__main__':
    print("Starting threaded SMA strategy with real-time data and statistics")
    asyncio.run(run_sma_strategy_async(stockUniverse))