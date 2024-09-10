from datetime import datetime
from lumibot.strategies import Strategy
import os
import alpaca_trade_api as alpaca


#Alpaca configuration and API key provision
API_KEY_ALPACA = os.environ.get("API_KEY_ALPACA")
APCA_API_KEY_ID=os.environ.get("APCA_API_KEY_ID")
SECRET_KEY_ALPACA =os.environ.get("SECRET_KEY_ALPACA")
BASE_URL = os.environ.get("BASE_URL")
ALPACA_CONFIG = alpaca.REST(APCA_API_KEY_ID, SECRET_KEY_ALPACA, base_url= BASE_URL, api_version = 'v2')


class StockBracket(Strategy):
        parameters = {
            "buy_symbol": "NVDA",
            "take_profit_price":800,
            "stop_loss_price": 10,
            "quantity": 100,
        }

        # =====Overloading lifecycle methods=============

        def initialize(self):
            # Set the initial variables or constants

            # Built in Variables
            self.sleeptime = "1D"

            # Our Own Variables
            self.counter = 0

        def on_trading_iteration(self):
            """Buys the self.buy_symbol once, then never again"""

            buy_symbol = self.parameters["buy_symbol"]
            take_profit_price = self.parameters["take_profit_price"]
            stop_loss_price = self.parameters["stop_loss_price"]
            quantity = self.parameters["quantity"]

            # What to do each iteration
            current_value = self.get_last_price(buy_symbol)
            self.log_message(f"The value of {buy_symbol} is {current_value}")

            if self.first_iteration:
                # Bracket order
                order = self.create_order(
                    buy_symbol,
                    quantity,
                    "buy",
                    take_profit_price=take_profit_price,
                    stop_loss_price=stop_loss_price,
                    type="bracket",
                )
                self.submit_order(order)


if __name__ == "__main__":
    is_live = False

    if is_live:

        from lumibot.brokers import Alpaca
        from lumibot.traders import Trader

        trader = Trader()

        broker = Alpaca(ALPACA_CONFIG) #Configure own alpaca

        strategy = StockBracket(broker=broker)

        trader.add_strategy(strategy)
        strategy_executors = trader.run_all()

    else:
        from lumibot.backtesting import YahooDataBacktesting

        # Backtest this strategy
        backtesting_start = datetime(2024, 1, 1)
        backtesting_end = datetime(2024, 8, 31)

        results = StockBracket.backtest(
            YahooDataBacktesting,
            backtesting_start,
            backtesting_end,
            benchmark_asset="SPY",
        )
