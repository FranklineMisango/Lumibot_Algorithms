import alpaca_trade_api as tradeapi
from alpaca_trade_api.stream import Stream
import datetime
import os
import pandas as pd
import numpy as np
import yfinance as yf
from dotenv import load_dotenv
load_dotenv()

#Backtesting configurations
from lumibot.entities import Asset, Order
from lumibot.strategies import Strategy
from lumibot.backtesting import CcxtBacktesting, YahooDataBacktesting

import ccxt

ALPACA_API_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")

# Utility to truncate a float value to a certain number of decimal places.
def truncate(val, decimal_places):
    return int(val * 10**decimal_places) / 10**decimal_places

# Convert MartingaleTrader to a Strategy class for backtesting
class MartingaleStrategy(Strategy):
    def initialize(self, symbol="NVDA", base_bet=10, tick_size=5):
        self.symbol = symbol
        self.tick_size = tick_size
        self.tick_index = 0
        self.base_bet = base_bet
        
        # These variables track the information about the current streak
        self.streak_count = 0
        self.streak_increasing = True
        self.streak_start = 0
        
        # The closing price of the last tick
        self.last_price = 0
        
        # For tracking position
        self.position = 0
        self.equity = 10000  # Starting equity
        self.margin_multiplier = 1

    def on_trading_iteration(self):
        # Get current price data
        current_price = self.get_last_price(self.symbol)
        
        if self.last_price == 0:
            self.last_price = current_price
            return
        
        # Process price change
        self.process_current_tick(self.last_price, current_price)
        self.last_price = current_price
    
    def process_current_tick(self, tick_open, tick_close):
        # Update streak info
        diff = truncate(tick_close, 2) - truncate(tick_open, 2)
        if diff != 0:
            # There was a meaningful change in the price
            self.streak_count += 1
            increasing = tick_open > tick_close
            if self.streak_increasing != increasing:
                # It moved in the opposite direction of the streak.
                # Therefore, the streak is over, and we should reset.

                # Empty out the position
                self.send_order(0)

                # Reset variables
                self.streak_increasing = increasing
                self.streak_start = tick_open
                self.streak_count = 0
            else:
                # Calculate the number of shares we want to be holding
                total_buying_power = self.portfolio_value * self.margin_multiplier
                target_value = (2 ** self.streak_count) * \
                               (self.base_bet / 100) * total_buying_power
                if target_value > total_buying_power:
                    # Limit the amount we can buy to a bit less than our total buying power
                    target_value = total_buying_power - tick_close
                target_qty = int(target_value / tick_close)
                if self.streak_increasing:
                    target_qty = target_qty * -1
                self.send_order(target_qty)

    def send_order(self, target_qty):
        delta = target_qty - self.position
        if delta == 0:
            return
        
        asset = Asset(symbol=self.symbol, asset_type="stock")
        
        if delta > 0:
            # Buy order
            self.log_message(f"Buying {delta} shares of {self.symbol}")
            order = self.create_order(asset, delta, "buy")
            self.submit_order(order)
        elif delta < 0:
            # Sell order
            sell_qty = abs(delta)
            self.log_message(f"Selling {sell_qty} shares of {self.symbol}")
            order = self.create_order(asset, sell_qty, "sell")
            self.submit_order(order)
            
        self.position = target_qty


# Original MartingaleTrader class for live trading
class MartingaleTrader(object):
    # ... [keeping the original class implementation as is] ...
    def __init__(self):
        self.key_id = ALPACA_API_KEY
        self.secret_key = ALPACA_SECRET_KEY
        self.base_url = 'https://paper-api.alpaca.markets'
        self.data_url = 'https://data.alpaca.markets'

        # The symbol we will be trading
        self.symbol = 'NVDA'

        # How many seconds we will wait in between updating the streak values
        self.tick_size = 5
        self.tick_index = 0

        # The percentage of our buying power that we will allocate to a new
        # position after a streak reset
        self.base_bet = 10

        # These variables track the information about the current streak
        self.streak_count = 0
        self.streak_start = 0
        self.streak_increasing = True

        # When this variable is not None, we have an order open
        self.current_order = None

        # The closing price of the last aggregate we saw
        self.last_price = 0

        # used to use tick data as second aggs data (mot every tick, but sec)
        self.last_trade_time = datetime.datetime.now(datetime.UTC)

        # The connection to the Alpaca API
        self.api = tradeapi.REST(
            self.key_id,
            self.secret_key,
            self.base_url
        )

        # ... [rest of the implementation] ...


# Function to fetch Yahoo Finance data
def fetch_yahoo_data(symbol, start_date, end_date, interval='1d'):
    """
    Fetch historical data from Yahoo Finance
    
    Parameters:
    symbol (str): Stock symbol
    start_date (datetime): Start date
    end_date (datetime): End date
    interval (str): Data interval ('1d', '1h', etc.)
    
    Returns:
    pandas.DataFrame: Historical price data
    """
    data = yf.download(symbol, start=start_date, end=end_date, interval=interval)
    return data


# Main backtesting function
def run_backtest(symbol, start_date, end_date, backtest_type="yahoo", base_bet=10, tick_size=5):
    """
    Run backtest on the Martingale strategy
    
    Parameters:
    symbol (str): Stock symbol
    start_date (datetime): Start date for the backtest
    end_date (datetime): End date for the backtest
    backtest_type (str): Type of backtest - "yahoo" or "ccxt"
    base_bet (int): Base bet percentage
    tick_size (int): Tick size
    
    Returns:
    tuple: Results and strategy object
    """
    if backtest_type.lower() == "yahoo":
        # Use Yahoo Finance data for backtesting
        backtesting = YahooDataBacktesting(
            start_date,
            end_date
        )
    elif backtest_type.lower() == "ccxt":
        # Use CCXT for backtesting
        CcxtBacktesting.MIN_TIMESTEP = "day"
        backtesting = CcxtBacktesting(
            start_date,
            end_date,
        )
    else:
        raise ValueError("backtest_type must be either 'yahoo' or 'ccxt'")
    
    # Initialize and run the strategy
    strategy = MartingaleStrategy(
        name="MartingaleStrategy",
        backtesting=backtesting,
        parameters={
            "symbol": symbol,
            "base_bet": base_bet,
            "tick_size": tick_size
        }
    )
    
    results = strategy.backtest()
    return results, strategy


# Example usage
if __name__ == "__main__":
    # Get user input
    backtest_type = input("Select backtest type (yahoo/ccxt): ").lower()
    symbol = input("Enter symbol to trade (default: AAPL): ") or "AAPL"
    
    # Set date range
    start_date = datetime.datetime(2023, 2, 11)
    end_date = datetime.datetime(2024, 2, 12)
    
    # Run backtest
    print(f"Running {backtest_type} backtest for {symbol} from {start_date.date()} to {end_date.date()}")
    results, strategy = run_backtest(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        backtest_type=backtest_type
    )
    
    # Print results
    print("\nBacktest Results:")
    print(f"Final Portfolio Value: ${results['portfolio_value']:.2f}")
    print(f"Total Return: {results['return']:.2%}")