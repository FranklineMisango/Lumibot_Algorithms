from lumibot.brokers import Alpaca
from lumibot.strategies import Strategy
from lumibot.traders import Trader
import os
from lumibot.backtesting import YahooDataBacktesting

from dotenv import load_dotenv
load_dotenv()

from datetime import datetime

# Populate the ALPACA_CONFIG dictionary
ALPACA_CONFIG = {
    'API_KEY': os.environ.get('APCA_API_KEY_ID'),
    'API_SECRET': os.environ.get('APCA_API_SECRET_KEY'),
    'BASE_URL': os.environ.get('BASE_URL')
}

class SwingHigh(Strategy):
    data = {}  # Dictionary to store last price data for each symbol
    order_numbers = {}  # Dictionary to store order numbers for each symbol
    shares_per_ticker = {}  # Dictionary to specify the number of shares per ticker

    def initialize(self):
         
        self.symbols = {
            "ALLY": 290,
            "AMZN": 100,
            "AXP": 75,
            "AON": 410,
            "AAPL": 400,
            "BATRK": 223,
            "BAC": 90,
            "COF": 70,
            "CHTR": 65,
            "CVX": 110,
            "C": 95,
            "CB": 85,
            "DVA": 45,
            "DEO": 100,
            "FND": 40,
            "JEF": 25,
            "KHC": 35,
            "KR": 50,
            "LILA": 70,
            "LILAK": 80,
            "LSXMA": 90,
            "LSXMK": 100,
            "FWONK": 130,
            "LPX": 140,
            "MA": 150,
            "MCO": 160,
            "NU": 170,
            "NVR": 180,
            "OXY": 190,
            "SIRI": 200,
            "SPY": 210,
            "TMUS": 220,
            "ULTA": 230,
            "VOO": 240,
            "VRSN": 250,
            "SNOW": 260
            }
            
        self.shares_per_ticker = self.symbols  # Directly assign the dictionary
        self.sleeptime = "10S"  # Set the sleep time to 10 seconds
    
    def on_trading_iteration(self):
        for symbol in self.symbols:
            if symbol not in self.data:
                self.data[symbol] = []

            entry_price = self.get_last_price(symbol)
            if entry_price is None:
                self.log_message(f"No price data for {symbol}, skipping.")
                continue

            self.log_message(f"Position for {symbol}: {self.get_position(symbol)}")
            self.data[symbol].append(entry_price)

            if len(self.data[symbol]) > 3:
                temp = self.data[symbol][-3:]
                if None not in temp and temp[-1] > temp[1] > temp[0]:
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

if __name__ == "__main__":
    trade = False
    # Reactivate after code rebase
    if trade:
        broker = Alpaca(ALPACA_CONFIG)
        bot = Trader()
        bot.add_strategy(SwingHigh)
        bot.run_all()
    else:
        start = datetime(2024, 8, 1)
        end = datetime(2024, 8, 5)
        SwingHigh.backtest(
            YahooDataBacktesting,
            start,
            end
        )
