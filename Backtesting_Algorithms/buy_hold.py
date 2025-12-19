from lumibot.brokers import Alpaca
from lumibot.strategies import Strategy
from lumibot.traders import Trader
import yfinance as yf
from datetime import datetime
from lumibot.backtesting import YahooDataBacktesting
import os

from dotenv import load_dotenv
load_dotenv()

# Populate the ALPACA_CONFIG dictionary
ALPACA_CONFIG = {
    'API_KEY': os.environ.get('APCA_API_KEY_ID'),
    'API_SECRET': os.environ.get('APCA_API_SECRET_KEY'),
    'BASE_URL': os.environ.get('BASE_URL')
}

class BuyHold(Strategy):
    def initialize(self, symbols_weights=None):
        self.sleeptime = "1D"
        # Default portfolio weights if not provided
        if symbols_weights is None:
            symbols_weights = {
                "AAPL": 0.1, "BAC": 0.05, "AXP": 0.05, "KO": 0.05, "CVX": 0.05,
                "OXY": 0.03, "KHC": 0.03, "MCO": 0.02, "CB": 0.02, "DVA": 0.02,
                "C": 0.02, "KR": 0.02, "SIRI": 0.01, "V": 0.04, "VRSN": 0.01,
                "MA": 0.04, "AMZN": 0.1, "NU": 0.02, "AON": 0.01, "COF": 0.01,
                "CHTR": 0.02, "ALLY": 0.01, "TMUS": 0.02, "FWONK": 0.01, "LPX": 0.01,
                "LLYVK": 0.01, "FND": 0.01, "ULTA": 0.01, "HEI.A": 0.01, "LLYVA": 0.01,
                "DEO": 0.01, "LEN.B": 0.01, "JEF": 0.01, "LILA": 0.01, "LILAK": 0.01,
                "BATRK": 0.01, "VOO": 0.05, "SPY": 0.05
            }
        self.symbols_weights = symbols_weights
        self.rebalance_days = 30  # Rebalance every 30 days
        self.last_rebalance = None

    def on_trading_iteration(self):
        current_date = self.get_datetime()
        
        # Initial buy or rebalance
        if self.first_iteration or (self.last_rebalance and (current_date - self.last_rebalance).days >= self.rebalance_days):
            self.rebalance_portfolio()
            self.last_rebalance = current_date

    def rebalance_portfolio(self):
        total_value = self.portfolio_value
        positions = self.get_positions()
        
        # Sell positions not in target portfolio
        for position in positions:
            if position.symbol not in self.symbols_weights:
                self.sell_all(position.symbol)
        
        # Adjust positions to target weights
        for symbol, weight in self.symbols_weights.items():
            target_value = total_value * weight
            current_quantity = 0
            if symbol in [p.symbol for p in positions]:
                current_quantity = next(p.quantity for p in positions if p.symbol == symbol)
            current_value = current_quantity * self.get_last_price(symbol)
            
            if current_value < target_value * 0.95:  # Rebalance if off by more than 5%
                quantity_to_buy = int((target_value - current_value) / self.get_last_price(symbol))
                if quantity_to_buy > 0:
                    order = self.create_order(symbol, quantity_to_buy, "buy")
                    self.submit_order(order)
            elif current_value > target_value * 1.05:
                quantity_to_sell = int((current_value - target_value) / self.get_last_price(symbol))
                if quantity_to_sell > 0:
                    order = self.create_order(symbol, quantity_to_sell, "sell")
                    self.submit_order(order)

trade = True
if trade:
    broker = Alpaca(ALPACA_CONFIG)
    strategy = BuyHold(broker=broker)
    trader = Trader()
    trader.add_strategy(strategy)
    trader.run_all()
else:
    start = datetime(2024, 8, 1)  # Convert start_date to datetime
    end = datetime(2024, 8, 31)  # Convert end_date to datetime
    BuyHold.backtest(
        YahooDataBacktesting,
        start,
        end,
        cash=100000  # Set initial cash for backtest
    )