import os
import math
from datetime import datetime, timedelta
import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf  
from dotenv import load_dotenv
from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
load_dotenv()
ALPACA_API_KEY = os.environ.get('API_KEY_ALPACA')
ALPACA_SECRET_KEY = os.environ.get('SECRET_KEY_ALPACA')
ALPACA_PAPER = True  

class DiversifiedLeverageStrategy(bt.Strategy):
    """
    Strategy that invests in a diversified portfolio of leveraged ETFs and rebalances regularly.
    """
    
    params = (
        ('rebalance_period', 4),  # Rebalance every 4 days
        ('portfolio', [
            {"symbol": "TQQQ", "weight": 0.20},  # 3x Leveraged Nasdaq
            {"symbol": "UPRO", "weight": 0.20},  # 3x Leveraged S&P 500
            {"symbol": "UDOW", "weight": 0.10},  # 3x Leveraged Dow Jones
            {"symbol": "TMF", "weight": 0.25},   # 3x Leveraged Treasury Bonds
            {"symbol": "UGL", "weight": 0.10},   # 3x Leveraged Gold
            {"symbol": "DIG", "weight": 0.15},   # 2x Leveraged Oil and Gas Companies
        ]),
    )

    def __init__(self):
        self.counter = 0
        self.order_dict = {}  # Track pending orders
        self.target_weights = {asset['symbol']: asset['weight'] for asset in self.params.portfolio}
        
        # Store the data feeds in a dictionary for easy access
        self.datafeeds = {}
        for i, data in enumerate(self.datas):
            self.datafeeds[data._name] = data
        
        # Log initial portfolio value
        self.log(f'Initial Portfolio Value: ${self.broker.getvalue():.2f}')

    def log(self, txt, dt=None):
        """Logging function for strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')

    def notify_order(self, order):
        """Handle order status updates"""
        if order.status in [order.Submitted, order.Accepted]:
            return  # Wait for further notifications
            
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED - {order.data._name}, Price: {order.executed.price:.2f}, Size: {order.executed.size:.0f}')
            else:
                self.log(f'SELL EXECUTED - {order.data._name}, Price: {order.executed.price:.2f}, Size: {order.executed.size:.0f}')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order {order.data._name} Failed with Status: {order.getstatusname()}')
        
        # Remove the order from our tracking dict
        if order.data._name in self.order_dict:
            self.order_dict.pop(order.data._name)

    def next(self):
        """Main strategy logic executed on each bar"""
        # Increment counter and check if rebalancing is needed
        self.counter += 1
        
        # Only execute if we have no pending orders
        if not self.order_dict:
            # If it's time to rebalance or first execution
            if self.counter >= self.params.rebalance_period:
                self.counter = 0
                self.rebalance_portfolio()
                self.log(f'Next portfolio rebalancing will be in {self.params.rebalance_period} day(s)')

    def rebalance_portfolio(self):
        """Rebalance the portfolio according to target weights"""
        self.log("Rebalancing portfolio...")
        
        # Get current portfolio value
        portfolio_value = self.broker.getvalue()
        self.log(f'Current Portfolio Value: ${portfolio_value:.2f}')
        
        # Calculate desired position values and create orders
        for symbol, weight in self.target_weights.items():
            if symbol not in self.datafeeds:
                self.log(f"Warning: {symbol} not in datafeeds, skipping")
                continue
                
            data = self.datafeeds[symbol]
            current_price = data.close[0]
            
            # Calculate target position value and shares
            target_value = portfolio_value * weight
            target_shares = int(target_value / current_price)
            
            # Get current position
            position = self.getposition(data)
            current_shares = position.size
            
            # Calculate difference
            shares_difference = target_shares - current_shares
            
            # Skip if the difference is very small
            if abs(shares_difference) < 1:
                continue
                
            # Create the order
            if shares_difference > 0:
                self.log(f"Buying {shares_difference} shares of {symbol}")
                order = self.buy(data=data, size=shares_difference)
                self.order_dict[symbol] = order
            elif shares_difference < 0:
                self.log(f"Selling {abs(shares_difference)} shares of {symbol}")
                order = self.sell(data=data, size=abs(shares_difference))
                self.order_dict[symbol] = order

def run_backtest():
    """Run backtest configuration"""
    cerebro = bt.Cerebro()
    cerebro.addstrategy(DiversifiedLeverageStrategy)
    
    # Set cash and commission
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.005)  # 0.005% per trade
    
    # Set up data feed for each symbol using yfinance
    symbols = ["TQQQ", "UPRO", "UDOW", "TMF", "UGL", "DIG"]
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2025, 1, 1)
    
    for symbol in symbols:
        print(f"Downloading data for {symbol}...")
        # Download data using yfinance with auto_adjust=True for better data quality
        df = yf.download(symbol, start=start_date, end=end_date, auto_adjust=True)
        
        # Fix multi-level columns - convert to simple column names
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        
        # Ensure all necessary columns are present with correct names
        required_cols = {'open': 'Open', 'high': 'High', 'low': 'Low', 
                         'close': 'Close', 'volume': 'Volume'}
        
        # Rename columns to what Backtrader expects
        df_cols = {col: col.lower() for col in df.columns}
        df.rename(columns=df_cols, inplace=True)
        
        print(f"Data shape for {symbol}: {df.shape}")
        
        # Convert the data to Backtrader format
        data_feed = bt.feeds.PandasData(
            dataname=df,
            name=symbol,
            timeframe=bt.TimeFrame.Days,
            fromdate=start_date,
            todate=end_date
        )
        cerebro.adddata(data_feed, name=symbol)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    # Run the backtest
    print('Starting Portfolio Value: ${:.2f}'.format(cerebro.broker.getvalue()))
    results = cerebro.run()
    print('Final Portfolio Value: ${:.2f}'.format(cerebro.broker.getvalue()))
    
    # Print analysis
    strat = results[0]
    print('Sharpe Ratio:', strat.analyzers.sharpe.get_analysis()['sharperatio'])
    print('Drawdown:', strat.analyzers.drawdown.get_analysis()['max']['drawdown'])
    print('Return:', strat.analyzers.returns.get_analysis()['rtot'])
    
    # Plot the results
    cerebro.plot(style='candlestick')


def run_live():
    """Run live trading configuration with Alpaca"""
    cerebro = bt.Cerebro()
    cerebro.addstrategy(DiversifiedLeverageStrategy)
    
    store = alpaca_backtrader_api.AlpacaStore(
        key_id=ALPACA_API_KEY,
        secret_key=ALPACA_SECRET_KEY,
        paper=ALPACA_PAPER
    )
    
    broker = store.getbroker()
    cerebro.setbroker(broker)
    symbols = ["TQQQ", "UPRO", "UDOW", "TMF", "UGL", "DIG"]
    
    for symbol in symbols:
        data = store.getdata(
            dataname=symbol,
            timeframe=bt.TimeFrame.Days,
            fromdate=datetime.now() - timedelta(days=10),  # Need some historical data
            live=True
        )
        cerebro.adddata(data, name=symbol)
    
    print('Starting Live Trading...')
    print('Initial Portfolio Value: ${:.2f}'.format(cerebro.broker.getvalue()))
    cerebro.run()

if __name__ == "__main__":
    is_live = False 
    
    if is_live:
        print("Running in LIVE mode with Alpaca")
        run_live()
    else:
        print("Running in BACKTEST mode")
        run_backtest()