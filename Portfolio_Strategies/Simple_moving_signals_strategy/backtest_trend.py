from datetime import datetime, timedelta
from lumibot.backtesting import YahooDataBacktesting
from lumibot.brokers import Alpaca
from lumibot.strategies import Strategy
from lumibot.traders import Trader
import numpy as np
import pandas as pd
import os


from dotenv import load_dotenv
load_dotenv()
from datetime import datetime

# Populate the ALPACA_CONFIG dictionary
ALPACA_CONFIG = {
    'API_KEY': os.environ.get('APCA_API_KEY_ID'),
    'API_SECRET': os.environ.get('APCA_API_SECRET_KEY'),
    'BASE_URL': os.environ.get('BASE_URL')
}

class Trend(Strategy):

    def initialize(self):
        signal = None
        self.signal = signal
        self.start = start
        self.sleeptime = "1D"

    def on_trading_iteration(self):
        # Define the symbols and dynamically calculate the quantity based on the cash available
        cash = 100000  # $1M
        symbols = ["AAPL", "MSFT", "GOOG"]
        prices = {symbol: self.get_last_price(symbol) for symbol in symbols} #Potential warning generator
        quantities = {symbol: cash // (len(symbols) * prices[symbol]) for symbol in symbols}
        print(f"Symbols: {symbols}")
        print(f"Quantities: {quantities}")

        for symbol in symbols:
            quantity = quantities[symbol]
            # Only print the signal when the backtest is done
            bars = self.get_historical_prices(symbol, 22, "day")
            df = bars.df
            df['9-day'] = df['close'].rolling(9).mean()
            df['21-day'] = df['close'].rolling(21).mean()
            df['Signal'] = np.where(np.logical_and(df['9-day'] > df['21-day'],
                                                    df['9-day'].shift(1) < df['21-day'].shift(1)),
                                    "BUY", None)
            df['Signal'] = np.where(np.logical_and(df['9-day'] < df['21-day'],
                                                    df['9-day'].shift(1) > df['21-day'].shift(1)),
                                    "SELL", df['Signal'])
            self.signal = df.iloc[-1].Signal
            print(f"Signal for {symbol}: {self.signal}")

            if self.signal == 'BUY':
                pos = self.get_position(symbol)
                if pos is not None:
                    self.sell_all()
                    
                order = self.create_order(symbol, quantity, "buy")
                self.submit_order(order)
            elif self.signal == 'SELL':
                pos = self.get_position(symbol)
                if pos is not None:
                    self.sell_all()
                    
                order = self.create_order(symbol, quantity, "sell")
                self.submit_order(order)
    
if __name__ == "__main__":
    trade = False
    #Reactivate after code rebase
    if trade:
        broker = Alpaca(ALPACA_CONFIG)
        strategy = Trend(broker=broker)
        bot = Trader()
        bot.add_strategy(strategy)
        bot.run_all()
    else:
        # Backtesting works for the last 1 month or more to get better stats for the strategy
        start = datetime(2024, 9, 21)
        end = datetime(2024, 10, 25)
        Trend.backtest(
            YahooDataBacktesting,
            start,
            end        
        )
