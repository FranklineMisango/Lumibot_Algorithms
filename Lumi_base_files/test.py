from datetime import datetime

from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies import Strategy


class SwingHigh(Strategy):
    data = {}  # Dictionary to store last price data for each symbol
    order_numbers = {}  # Dictionary to store order numbers for each symbol
    shares_per_ticker = {}  # Dictionary to specify the number of shares per ticker

    def initialize(self):
        self.symbols = ["AAPL", "BAC", "V", "GM", "KO", "KHC", "OXY", "CVX", "HPQ", "PARA", "UPS", "MCO", "AXP", "JNJ", "MA", "DVA", "AMZN"]  # Add other symbols as needed
        self.shares_per_ticker = {"AAPL": 60, "BAC": 373, "V":48, "GM":299, "KO":190, "KHC":325, 
                                  "OXY":195, "CVX":76, "HPQ":357, "PARA":733, "UPS":63, "MCO":32, "AXP":66, 
                                  "JNJ":74, "MA" :29, "DVA" : 112, "AMZN" : 86}   # Specify the number of shares for each symbol
        self.sleeptime = "10S"
    def on_trading_iteration(self):
        for symbol in self.symbols:
            if symbol not in self.data:
                self.data[symbol] = []

            entry_price = self.get_last_price(symbol)
            self.log_message(f"Position for {symbol}: {self.get_position(symbol)}")
            self.data[symbol].append(entry_price)

            if len(self.data[symbol]) > 3:
                temp = self.data[symbol][-3:]
                if temp[-1] > temp[1] > temp[0]:
                    self.log_message(f"Last 3 prints for {symbol}: {temp}")
                    order = self.create_order(symbol, quantity=self.shares_per_ticker[symbol], side="buy")
                    self.submit_order(order)
                    if symbol not in self.order_numbers:
                        self.order_numbers[symbol] = 0
                    self.order_numbers[symbol] += 1
                    if self.order_numbers[symbol] == 1:
                        self.log_message(f"Entry price for {symbol}: {temp[-1]}")
                        entry_price = temp[-1]  # filled price
                if self.get_position(symbol) and self.data[symbol][-1] < entry_price * 0.995:
                    self.sell_all(symbol)
                    self.order_numbers[symbol] = 0
                elif self.get_position(symbol) and self.data[symbol][-1] >= entry_price * 1.015:
                    self.sell_all(symbol)
                    self.order_numbers[symbol] = 0

    def before_market_closes(self):
        for symbol in self.symbols:
            self.sell_all(symbol)
        

# Pick the dates that you want to start and end your backtest
# and the allocated budget
backtesting_start = datetime(2024, 1, 1)
backtesting_end = datetime(2024, 2, 23)

# Run the backtest
SwingHigh.backtest(
    YahooDataBacktesting,
    backtesting_start,
    backtesting_end,
)
