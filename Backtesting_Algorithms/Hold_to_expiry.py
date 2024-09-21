from datetime import datetime
from lumibot.entities import Asset, Order
from lumibot.strategies import Strategy
from lumibot.traders import Trader
import os
import alpaca_trade_api as alpaca

#Environment variables 
from dotenv import load_dotenv
load_dotenv()


POLYGON_API_KEY=os.environ.get('POLYGON_API_KEY')


API_KEY_ALPACA = os.environ.get("API_KEY_ALPACA")
APCA_API_KEY_ID=os.environ.get("APCA_API_KEY_ID")
SECRET_KEY_ALPACA =os.environ.get("SECRET_KEY_ALPACA")


BASE_URL = os.environ.get("BASE_URL")
ALPACA_CONFIG = alpaca.REST(APCA_API_KEY_ID, SECRET_KEY_ALPACA, base_url= BASE_URL, api_version = 'v2')
BASE_URL = os.environ.get("BASE_URL")

class OptionsHoldToExpiry(Strategy):
    parameters = {
        "buy_symbol": "SPY",
        "expiry": datetime(2023, 10, 20),
    }

    # =====Overloading lifecycle methods=============

    def initialize(self):
        # Set the initial variables or constants

        # Built in Variables
        self.sleeptime = "1D"

    def on_trading_iteration(self):
        """Buys the self.buy_symbol once, then never again"""

        buy_symbol = self.parameters["buy_symbol"]
        expiry = self.parameters["expiry"]

        # What to do each iteration
        underlying_price = self.get_last_price(buy_symbol)
        self.log_message(f"The value of {buy_symbol} is {underlying_price}")

        if self.first_iteration:
            # Calculate the strike price (round to nearest 1)
            strike = round(underlying_price)

            # Create options asset
            asset = Asset(
                symbol=buy_symbol,
                asset_type="option",
                expiration=expiry,
                strike=strike,
                right="call",
            )

            # Create order
            order = self.create_order(
                asset,
                10,
                "buy_to_open",
            )
            
            # Submit order
            self.submit_order(order)

            # Log a message
            self.log_message(f"Bought {order.quantity} of {asset}")


if __name__ == "__main__":
    is_live = False

    if is_live:

        from lumibot.brokers import InteractiveBrokers
        from lumibot.traders import Trader

        trader = Trader()

        #TODO - add all other brokers
        broker = alpaca(ALPACA_CONFIG)
        strategy = OptionsHoldToExpiry(broker=broker)

        trader.add_strategy(strategy)
        strategy_executors = trader.run_all()

    else:
        from lumibot.backtesting import PolygonDataBacktesting

        # Backtest this strategy
        backtesting_start = datetime(2023, 10, 19)
        backtesting_end = datetime(2023, 10, 24)

        results = OptionsHoldToExpiry.backtest(
            PolygonDataBacktesting,
            backtesting_start,
            backtesting_end,
            benchmark_asset="SPY",
            polygon_api_key=POLYGON_API_KEY,  # Add your polygon API key here
        )
        
