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
        bars = self.get_historical_prices("GLD", 22, "day")
        gld = bars.df
        #gld = pd.DataFrame(yf.download("GLD", self.start)['Close'])
        gld['9-day'] = gld['close'].rolling(9).mean()
        gld['21-day'] = gld['close'].rolling(21).mean()
        gld['Signal'] = np.where(np.logical_and(gld['9-day'] > gld['21-day'],
                                                gld['9-day'].shift(1) < gld['21-day'].shift(1)),
                                 "BUY", None)
        gld['Signal'] = np.where(np.logical_and(gld['9-day'] < gld['21-day'],
                                                gld['9-day'].shift(1) > gld['21-day'].shift(1)),
                                 "SELL", gld['Signal'])
        self.signal = gld.iloc[-1].Signal
        
        '''
        For testing a single ticker
        symbol = "GLD"
        quantity = 200
        '''

        symbols = {
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

        for symbol in symbols:
            quantity = symbols[symbol]
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
        start = datetime(2024, 8, 1)
        end = datetime(2024, 8, 31)
        Trend.backtest(
            YahooDataBacktesting,
            start,
            end        
        )
