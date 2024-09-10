from datetime import datetime
import os
import alpaca_trade_api as alpaca

from dotenv import load_dotenv
load_dotenv()

# Alpaca configuration and API key provision
API_KEY = os.environ.get("APCA_API_KEY_ID")
APCA_API_SECRET_KEY = os.environ.get("APCA_API_SECRET_KEY")
BASE_URL = os.environ.get("BASE_URL")

# Check if environment variables are loaded correctly
if not API_KEY or not APCA_API_SECRET_KEY or not BASE_URL:
    raise ValueError("One or more environment variables are missing: APCA_API_KEY_ID, APCA_API_SECRET_KEY, BASE_URL")

# Initialize Alpaca configuration
ALPACA_CONFIG = {
    "API_KEY": API_KEY,
    "API_SECRET": APCA_API_SECRET_KEY,
    "BASE_URL": BASE_URL
}

# Initialize Alpaca REST API
alpaca_api = alpaca.REST(API_KEY, APCA_API_SECRET_KEY, base_url=BASE_URL, api_version='v2')

from lumibot.backtesting import YahooDataBacktesting
from lumibot.brokers import Alpaca
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader

class MyStrategy(Strategy):
    def initialize(self, symbol=""):
        # Will make on_trading_iteration() run every 180 minutes
        self.sleeptime = 180

        # Custom parameters
        self.symbol = symbol
        self.quantity = 1
        self.side = "buy"

    def on_trading_iteration(self):
        self.order = self.create_order(self.symbol, self.quantity, self.side)
        self.submit_order(self.order)


if __name__ == "__main__":
    live = False

    trader = Trader()
    broker = Alpaca(ALPACA_CONFIG)
    strategy = MyStrategy(broker, symbol="SPY")

    if not live:
        # Backtest this strategy
        backtesting_start = datetime(2020, 1, 1)
        backtesting_end = datetime(2020, 12, 31)
        strategy.backtest(
            YahooDataBacktesting,
            backtesting_start,
            backtesting_end,
            symbol="SPY",
        )
    else:
        # Run the strategy live
        trader.add_strategy(strategy)
        trader.run_all()