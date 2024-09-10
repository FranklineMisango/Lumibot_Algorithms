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
    def initialize(self):
        self.sleeptime = "1D"
        self.set_cash = 100000  # Set initial cash balance

    def on_trading_iteration(self):
        if self.first_iteration:
            stocks_and_quantities = [
                {"symbol": 'NVDA', "quantity": 100},
            ]
            for stock_info in stocks_and_quantities:
                symbol = stock_info["symbol"]
                quantity = stock_info["quantity"]
                price = self.get_last_price(symbol)
                cost = price * quantity
                if self.cash >= cost:
                    order = self.create_order(symbol, quantity, "buy")
                    self.submit_order(order)

trade = False
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
        end
    )