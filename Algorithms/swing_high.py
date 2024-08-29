from lumibot.brokers import Alpaca
from lumibot.strategies import Strategy
from lumibot.traders import Trader


class SwingHigh(Strategy):
    data = {}  # Dictionary to store last price data for each symbol
    order_numbers = {}  # Dictionary to store order numbers for each symbol
    shares_per_ticker = {}  # Dictionary to specify the number of shares per ticker

    def initialize(self, ticker_input, quantities_input):
        self.symbols = ticker_input# Add other symbols as needed
        self.shares_per_ticker = {ticker_input: quantities_input}   # Specify the number of shares for each symbol
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
