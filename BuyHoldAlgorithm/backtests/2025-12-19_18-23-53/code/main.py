# region imports
from AlgorithmImports import *
# endregion

class BuyHoldAlgorithm(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2024, 8, 1)  # Set Start Date
        self.set_end_date(2024, 8, 31)  # Set End Date
        self.set_cash(100000)  # Set Strategy Cash
        
        self.symbols_weights = {
            "AAPL": 0.1, "BAC": 0.05, "AXP": 0.05, "KO": 0.05, "CVX": 0.05,
            "OXY": 0.03, "KHC": 0.03, "MCO": 0.02, "CB": 0.02, "DVA": 0.02,
            "C": 0.02, "KR": 0.02, "SIRI": 0.01, "V": 0.04, "VRSN": 0.01,
            "MA": 0.04, "AMZN": 0.1, "NU": 0.02, "AON": 0.01, "COF": 0.01,
            "CHTR": 0.02, "ALLY": 0.01, "TMUS": 0.02, "FWONK": 0.01, "LPX": 0.01,
            "LLYVK": 0.01, "FND": 0.01, "ULTA": 0.01, "HEI.A": 0.01, "LLYVA": 0.01,
            "DEO": 0.01, "LEN.B": 0.01, "JEF": 0.01, "LILA": 0.01, "LILAK": 0.01,
            "BATRK": 0.01, "VOO": 0.05, "SPY": 0.05
        }
        
        # Add equities
        for symbol in self.symbols_weights.keys():
            self.add_equity(symbol, Resolution.DAILY)
        
        self.rebalance_days = 30
        self.last_rebalance = None

    def on_data(self, data: Slice):
        current_date = self.time.date()
        
        # Initial buy or rebalance
        if self.last_rebalance is None or (current_date - self.last_rebalance).days >= self.rebalance_days:
            self.rebalance_portfolio()
            self.last_rebalance = current_date

    def rebalance_portfolio(self):
        for symbol, weight in self.symbols_weights.items():
            self.set_holdings(symbol, weight)
        self.debug("Rebalanced portfolio")
