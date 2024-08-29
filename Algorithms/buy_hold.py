from lumibot.brokers import Alpaca
from lumibot.strategies import Strategy
from lumibot.traders import Trader
import yfinance as yf
import datetime 
from lumibot.backtesting import YahooDataBacktesting
import os


class BuyHold(Strategy):
    def initialize(self):
        self.sleeptime = "1D"

    def on_trading_iteration(self):
        if self.first_iteration:
            stocks_and_quantities = [
                {"symbol": ticker_input, "quantity": quantities_input},
            ]
            for stock_info in stocks_and_quantities:
                symbol = stock_info["symbol"]
                quantity = stock_info["quantity"]
                price = self.get_last_price(symbol)
                cost = price * quantity
                self.cash = portfolio_size
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
    start = datetime(start_date.year, start_date.month, start_date.day)  # Convert start_date to datetime
    end = datetime(end_date.year, end_date.month, end_date.day)  # Convert end_date to datetime
    BuyHold.backtest(
        YahooDataBacktesting,
        start,
        end
    )