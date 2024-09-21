from datetime import datetime
from lumibot.entities import Asset, Order
from lumibot.strategies import Strategy
from lumibot.backtesting import CcxtBacktesting
from lumibot.backtesting import YahooDataBacktesting 
from lumibot.traders import Trader
from lumibot.entities import TradingFee
import alpaca_trade_api as alpaca
import os
from ccxt.base.types import TradingFees

#Environment variables 
from dotenv import load_dotenv
load_dotenv

API_KEY_ALPACA = os.environ.get("API_KEY_ALPACA")
APCA_API_KEY_ID=os.environ.get("APCA_API_KEY_ID")
SECRET_KEY_ALPACA =os.environ.get("SECRET_KEY_ALPACA")
BASE_URL = os.environ.get("BASE_URL")

ALPACA_CONFIG = alpaca.REST(APCA_API_KEY_ID, SECRET_KEY_ALPACA, base_url= BASE_URL, api_version = 'v2')
BASE_URL = os.environ.get("BASE_URL")

class DiversifiedLeverage(Strategy):
    # =====Overloading lifecycle methods=============

    parameters = {
        "portfolio": [
            {
                "symbol": "TQQQ",  # 3x Leveraged Nasdaq
                "weight": 0.20,
            },
            {
                "symbol": "UPRO",  # 3x Leveraged S&P 500
                "weight": 0.20,
            },
            {
                "symbol": "UDOW",  # 3x Leveraged Dow Jones
                "weight": 0.10,
            },
            {
                "symbol": "TMF",  # 3x Leveraged Treasury Bonds
                "weight": 0.25,
            },
            {
                "symbol": "UGL",  # 3x Leveraged Gold
                "weight": 0.10,
            },
            {
                "symbol": "DIG",  # 2x Leveraged Oil and Gas Companies (Commodities)
                "weight": 0.15,
            },
        ],
        "rebalance_period": 4,
    }

    def initialize(self):
        # Setting the waiting period (in days) and the counter
        self.counter = None

        # There is only one trading operation per day
        # no need to sleep between iterations
        self.sleeptime = "1D"

        # Initializing the portfolio variable with the assets and proportions we want to own
        self.initialized = False

        self.minutes_before_closing = 1

    def on_trading_iteration(self):
        rebalance_period = self.parameters["rebalance_period"]
        # If the target number of days (period) has passed, rebalance the portfolio
        if self.counter == rebalance_period or self.counter == None:
            self.counter = 0
            self.rebalance_portfolio()
            self.log_message(
                f"Next portfolio rebalancing will be in {rebalance_period} day(s)"
            )

        self.log_message("Sleeping until next trading day")
        self.counter += 1

    # =============Helper methods====================

    def rebalance_portfolio(self):
        """Rebalance the portfolio and create orders"""

        orders = []
        for asset in self.parameters["portfolio"]:
            # Get all of our variables from portfolio
            symbol = asset.get("symbol")
            weight = asset.get("weight")
            last_price = self.get_last_price(symbol)

            # Get how many shares we already own
            # (including orders that haven't been executed yet)
            position = self.get_position(symbol)
            quantity = 0
            if position is not None:
                quantity = float(position.quantity)

            # Calculate how many shares we need to buy or sell
            shares_value = self.portfolio_value * weight
            self.log_message(
                f"The current portfolio value is {self.portfolio_value} and the weight needed is {weight}, so we should buy {shares_value}"
            )
            new_quantity = shares_value // last_price
            quantity_difference = new_quantity - quantity
            self.log_message(
                f"Currently own {quantity} shares of {symbol} but need {new_quantity}, so the difference is {quantity_difference}"
            )

            # If quantity is positive then buy, if it's negative then sell
            side = ""
            if quantity_difference > 0:
                side = "buy"
            elif quantity_difference < 0:
                side = "sell"

            # Execute the order if necessary
            if side:
                order = self.create_order(symbol, abs(quantity_difference), side)
                orders.append(order)

        self.submit_orders(orders)


if __name__ == "__main__":
    is_live = False

    if is_live:
        ####
        # Run the strategy live
        ####

        trader = Trader()
        broker = alpaca(ALPACA_CONFIG) #Work on the alpaca config
        strategy = DiversifiedLeverage(broker=broker)
        trader.add_strategy(strategy)
        trader.run_all()

    else:
        ####
        # Backtest the strategy
        ####

        # Choose the time from and to which you want to backtest
        backtesting_start = datetime(2024, 1, 1)
        backtesting_end = datetime(2024,9, 12)

        # 0.01% trading/slippage fee
        trading_fee = TradingFee(percent_fee=0.005)

        # Initialize the backtesting object
        print("Starting Backtest...")
        result = DiversifiedLeverage.backtest(
            YahooDataBacktesting,
            backtesting_start,
            backtesting_end,
            benchmark_asset="SPY",
            parameters={},
            buy_trading_fees=[trading_fee],
            sell_trading_fees=[trading_fee],
        )

        print("Backtest result: ", result)