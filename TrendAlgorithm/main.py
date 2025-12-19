# region imports
from AlgorithmImports import *
# endregion

class TrendAlgorithm(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2024, 8, 1)  # Set Start Date
        self.set_end_date(2024, 12, 31)  # Set End Date
        self.set_cash(100000)  # Set Strategy Cash
        
        self.symbols = {
            "ALLY": 290, "AMZN": 100, "AXP": 75, "AON": 410, "AAPL": 400, "BATRK": 223, "BAC": 90, "COF": 70,
            "CHTR": 65, "CVX": 110, "C": 95, "CB": 85, "DVA": 45, "DEO": 100, "FND": 40, "JEF": 25, "KHC": 35,
            "KR": 50, "LILA": 70, "LILAK": 80, "FWONK": 130, "LPX": 140, "MA": 150, "MCO": 160, "NU": 170,
            "NVR": 180, "OXY": 190, "SIRI": 200, "SPY": 210, "TMUS": 220, "ULTA": 230, "VOO": 240, "VRSN": 250, "SNOW": 260
        }
        
        # Add GLD for signal
        self.add_equity("GLD", Resolution.DAILY)
        for symbol in self.symbols.keys():
            self.add_equity(symbol, Resolution.DAILY)
        
        self.signal = None

    def on_data(self, data: Slice):
        if not data.contains_key("GLD"):
            return
        
        # Get GLD historical data
        history = self.history("GLD", 22, Resolution.DAILY)
        if len(history) < 22:
            return
        
        closes = history['close'].values
        ma9 = np.mean(closes[-9:])
        ma21 = np.mean(closes[-21:])
        prev_ma9 = np.mean(closes[-10:-1]) if len(closes) >= 10 else ma9
        prev_ma21 = np.mean(closes[-22:-1]) if len(closes) >= 22 else ma21
        
        signal = None
        if ma9 > ma21 and prev_ma9 <= prev_ma21:
            signal = "BUY"
        elif ma9 < ma21 and prev_ma9 >= prev_ma21:
            signal = "SELL"
        
        if signal != self.signal:
            self.signal = signal
            if signal == "BUY":
                self.debug("BUY signal: Liquidating and buying all positions")
                self.liquidate()
                for symbol, quantity in self.symbols.items():
                    self.market_order(symbol, quantity)
            elif signal == "SELL":
                self.debug("SELL signal: Liquidating all positions")
                self.liquidate()
