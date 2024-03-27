#from config import ALPACA_CONFIG
from datetime import datetime
from lumibot.backtesting import YahooDataBacktesting
from lumibot.brokers import Alpaca
from lumibot.strategies import Strategy
from lumibot.traders import Trader


class BuyHold(Strategy):

    def initialize(self):
        self.sleeptime = "1D"

    def on_trading_iteration(self):
        if self.first_iteration:
            stocks_and_quantities = [
                {"symbol": "AAPL", "quantity": 60},
                {"symbol": "BAC", "quantity": 373},
                {"symbol": "V", "quantity": 48},
                {"symbol": "GM", "quantity": 299},
                {"symbol": "KO", "quantity": 190},
                {"symbol": "KHC", "quantity": 325},
                {"symbol": "OXY", "quantity": 195},
                {"symbol": "CVX", "quantity": 76},
                {"symbol": "HPQ", "quantity": 357},
                {"symbol": "PARA", "quantity": 733},
                {"symbol": "UPS", "quantity": 63},
                {"symbol": "MCO", "quantity":32},
                {"symbol": "AXP", "quantity": 66},
                {"symbol": "JNJ", "quantity": 74},
                {"symbol": "MA", "quantity": 29},
                {"symbol": "DVA", "quantity": 112},
                {"symbol": "AMZN", "quantity": 86},                
            ]

            for stock_info in stocks_and_quantities:
                symbol = stock_info["symbol"]
                quantity = stock_info["quantity"]
                price = self.get_last_price(symbol)
                cost = price * quantity
                self.cash = 200000
                if self.cash >= cost:
                    order = self.create_order(symbol, quantity, "buy")
                    self.submit_order(order)


if __name__ == "__main__":
    trade = False
    if trade:
        pass
        #broker = Alpaca(ALPACA_CONFIG)
        #strategy = BuyHold(broker=broker)
        #trader = Trader()
        #trader.add_strategy(strategy)
        #trader.run_all()
    else:
        start = datetime(2020, 1, 1)
        end = datetime(2023, 7, 31)
        BuyHold.backtest(
            YahooDataBacktesting,
            start,
            end
        )
