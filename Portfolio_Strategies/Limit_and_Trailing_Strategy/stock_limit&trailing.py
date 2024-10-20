from datetime import datetime
from lumibot.strategies import Strategy
from lumibot.backtesting import YahooDataBacktesting
from lumibot.brokers import Alpaca
from lumibot.traders import Trader
import os
import alpaca_trade_api as alpaca


#Alpaca configuration and API key provision
API_KEY_ALPACA = os.environ.get("API_KEY_ALPACA")
APCA_API_KEY_ID=os.environ.get("APCA_API_KEY_ID")
SECRET_KEY_ALPACA =os.environ.get("SECRET_KEY_ALPACA")
BASE_URL = os.environ.get("BASE_URL")

ALPACA_CONFIG = alpaca.REST(APCA_API_KEY_ID, SECRET_KEY_ALPACA, base_url= BASE_URL, api_version = 'v2')

class LimitAndTrailingStop(Strategy):
    parameters = {
        "buy_symbol": "NVDA",
        "limit_buy_price": 100,
        "limit_sell_price": 150,
        "trail_percent": 0.02,
        "trail_price": 7,
    }

    def initialize(self):
        self.sleeptime = "1D"
        self.counter = 0

    def on_trading_iteration(self):
        buy_symbol = self.parameters["buy_symbol"]
        limit_buy_price = self.parameters["limit_buy_price"]
        limit_sell_price = self.parameters["limit_sell_price"]
        trail_percent = self.parameters["trail_percent"]
        trail_price = self.parameters["trail_price"]

        current_value = self.get_last_price(buy_symbol)
        self.log_message(f"The value of {buy_symbol} is {current_value}")

        if self.first_iteration:
            purchase_order = self.create_order(buy_symbol, 100, "buy", limit_price=limit_buy_price)
            self.submit_order(purchase_order)

            sell_order = self.create_order(buy_symbol, 100, "sell", limit_price=limit_sell_price)
            self.submit_order(sell_order)

            trailing_pct_stop_order = self.create_order(buy_symbol, 100, "sell", trail_percent=trail_percent)
            self.submit_order(trailing_pct_stop_order)

            trailing_price_stop_order = self.create_order(buy_symbol, 50, "sell", trail_price=trail_price)
            self.submit_order(trailing_price_stop_order)


if __name__ == "__main__":
    is_live = False

    if is_live:
        trader = Trader()
        broker = Alpaca(ALPACA_CONFIG)
        strategy = LimitAndTrailingStop(broker=broker)
        trader.add_strategy(strategy)
        strategy_executors = trader.run_all()

    else:
        backtesting_start = datetime(2024, 8, 1)
        backtesting_end = datetime(2024, 8, 31)

        results = LimitAndTrailingStop.backtest(
            YahooDataBacktesting,
            backtesting_start,
            backtesting_end,
            benchmark_asset="SPY",
        )
