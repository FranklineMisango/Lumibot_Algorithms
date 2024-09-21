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
                    {"symbol": "AAPL", "quantity": 4224},
                    {"symbol": "BAC", "quantity": 9742},
                    {"symbol": "AXP", "quantity": 1261},
                    {"symbol": "KO", "quantity": 4191},
                    {"symbol": "CVX", "quantity": 1393},
                    {"symbol": "OXY", "quantity": 3215},
                    {"symbol": "KHC", "quantity": 3150},
                    {"symbol": "MCO", "quantity": 185},
                    {"symbol": "CB", "quantity": 328},
                    {"symbol": "DVA", "quantity": 442},
                    {"symbol": "C", "quantity": 521},
                    {"symbol": "KR", "quantity": 479},
                    {"symbol": "SIRI", "quantity": 935},
                    {"symbol": "V", "quantity": 84},
                    {"symbol": "VRSN", "quantity": 108},
                    {"symbol": "MA", "quantity": 36},
                    {"symbol": "AMZN", "quantity": 96},
                    {"symbol": "NU", "quantity": 1027},
                    {"symbol": "AON", "quantity": 43},
                    {"symbol": "COF", "quantity": 86},
                    {"symbol": "CHTR", "quantity": 33},
                    {"symbol": "ALLY", "quantity": 48},
                    {"symbol": "TMUS", "quantity": 44},
                    {"symbol": "FWONK", "quantity": 50},
                    {"symbol": "LPX", "quantity": 63},
                    {"symbol": "LLYVK", "quantity": 47},
                    {"symbol": "FND", "quantity": 23},
                    {"symbol": "ULTA", "quantity": 8},
                    {"symbol": "HEI.A", "quantity": 9},
                    {"symbol": "LLYVA", "quantity": 71},
                    {"symbol": "NVR", "quantity": 0},
                    {"symbol": "DEO", "quantity": 6},
                    {"symbol": "LEN.B", "quantity": 8},
                    {"symbol": "JEF", "quantity": 20},
                    {"symbol": "LILA", "quantity": 158},
                    {"symbol": "VOO", "quantity": 2},
                    {"symbol": "SPY", "quantity": 2},
                    {"symbol": "LILAK", "quantity": 114},
                    {"symbol": "BATRK", "quantity": 22},
                ]
            for stock_info in stocks_and_quantities:
                symbol = stock_info["symbol"]
                quantity = stock_info["quantity"]
                price = self.get_last_price(symbol)
                cost = price * quantity
                if self.cash >= cost:
                    order = self.create_order(symbol, quantity, "buy")
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
        end
    )