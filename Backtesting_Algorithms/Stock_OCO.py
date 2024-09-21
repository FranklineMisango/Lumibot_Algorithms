import streamlit as st
from datetime import datetime
from lumibot.strategies import Strategy
from lumibot.backtesting import YahooDataBacktesting
from lumibot.brokers import Alpaca
from lumibot.traders import Trader

class StockOco(Strategy):
    parameters = {
        "buy_symbol": "SPY",
        "take_profit_price": 405,
        "stop_loss_price": 395,
        "quantity": 10,
    }

    def initialize(self):
        self.sleeptime = "1D"
        self.counter = 0

    def on_trading_iteration(self):
        buy_symbol = self.parameters["buy_symbol"]
        take_profit_price = self.parameters["take_profit_price"]
        stop_loss_price = self.parameters["stop_loss_price"]
        quantity = self.parameters["quantity"]

        current_value = self.get_last_price(buy_symbol)
        self.log_message(f"The value of {buy_symbol} is {current_value}")

        if self.first_iteration:
            main_order = self.create_order(buy_symbol, quantity, "buy")
            self.submit_order(main_order)

            order = self.create_order(
                buy_symbol,
                quantity,
                "sell",
       
