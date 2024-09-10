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
api_key = os.environ.get('APCA_API_KEY_ID')
secret_key = os.environ.get('APCA_API_SECRET_KEY')
paper = True

class BuyHold(Strategy):
    def initialize(self):
        self.sleeptime = "1D"
        self.set_cash = 100000  # Set initial cash balance

    def on_trading_iteration(self):
        if self.first_iteration:
            stocks_and_quantities = [
                {"symbol": "ALLY", "quantity": 290},
                {"symbol": "AMZN", "quantity": 100},
                {"symbol": "AXP", "quantity": 75},
                {"symbol": "AON", "quantity": 410},
                {"symbol": "AAPL", "quantity": 400},
                {"symbol": "BATRK", "quantity": 223},
                {"symbol": "BAC", "quantity": 90},
                {"symbol": "COF", "quantity": 70},
                {"symbol": "CHTR", "quantity": 65},
                {"symbol": "CVX", "quantity": 110},
                {"symbol": "C", "quantity": 95},
                {"symbol": "CB", "quantity": 85},
                {"symbol": "DVA", "quantity": 45},
                {"symbol": "DEO", "quantity": 100},
                {"symbol": "FND", "quantity": 40},
                {"symbol": "JEF", "quantity": 25},
                {"symbol": "KHC", "quantity": 35},
                {"symbol": "KR", "quantity": 50},
                {"symbol": "LILA", "quantity": 70},
                {"symbol": "LILAK", "quantity": 80},
                {"symbol": "LSXMA", "quantity": 90},
                {"symbol": "LSXMK", "quantity": 100},
                {"symbol": "FWONK", "quantity": 130},
                {"symbol": "LPX", "quantity": 140},
                {"symbol": "MA", "quantity": 150},
                {"symbol": "MCO", "quantity": 160},
                {"symbol": "NU", "quantity": 170},
                {"symbol": "NVR", "quantity": 180},
                {"symbol": "OXY", "quantity": 190},
                {"symbol": "SIRI", "quantity": 200},
                {"symbol": "SPY", "quantity": 210},
                {"symbol": "TMUS", "quantity": 220},
                {"symbol": "ULTA", "quantity": 230},
                {"symbol": "VOO", "quantity": 240},
                {"symbol": "VRSN", "quantity": 250},
                {"symbol": "SNOW", "quantity": 260},
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