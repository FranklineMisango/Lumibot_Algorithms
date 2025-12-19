# region imports
from AlgorithmImports import *
# endregion

class MomentumAlgorithm(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2024, 8, 1)  # Set Start Date
        self.set_end_date(2024, 8, 31)  # Set End Date
        self.set_cash(100000)  # Set Strategy Cash
        
        self.symbols = [
            "ALLY", "AMZN", "AXP", "AON", "AAPL", "BATRK", "BAC", "COF", "CHTR", "CVX", "C", "CB", "DVA", "DEO",
            "FND", "JEF", "KHC", "KR", "LILA", "LILAK", "LPX", "MA", "MCO", "NU", "OXY", "SIRI", "SPY", "TMUS", "ULTA", "VOO", "VRSN"
        ]
        
        # Add equities
        for symbol in self.symbols:
            self.add_equity(symbol, Resolution.DAILY)
        
        self.period = 2  # Momentum period in days
        self.current_asset = None
        self.quantity = 0

    def on_data(self, data: Slice):
        # Calculate momentums every period days
        momentums = self.get_assets_momentums()
        if not momentums:
            return
        
        momentums.sort(key=lambda x: x["return"], reverse=True)
        best_asset = momentums[0]["symbol"]
        best_return = momentums[0]["return"]
        
        if self.current_asset:
            current_data = next((m for m in momentums if m["symbol"] == self.current_asset), None)
            if current_data and current_data["return"] >= best_return:
                best_asset = self.current_asset
        
        self.debug(f"Best symbol: {best_asset} with return {best_return:.2%}")
        
        if best_asset != self.current_asset:
            # Sell current asset
            if self.current_asset and self.quantity > 0:
                self.debug(f"Swapping {self.current_asset} for {best_asset}")
                self.liquidate(self.current_asset)
            
            # Buy new asset
            self.current_asset = best_asset
            price = self.securities[best_asset].price
            self.quantity = int(self.portfolio.cash / price)
            if self.quantity > 0:
                self.market_order(best_asset, self.quantity)
        else:
            self.debug(f"Keeping {self.quantity} shares of {self.current_asset}")

    def get_assets_momentums(self):
        momentums = []
        for symbol in self.symbols:
            history = self.history(symbol, self.period + 1, Resolution.DAILY)
            if len(history) < self.period + 1:
                continue
            
            prices = history['close'].values
            if len(prices) < 2:
                continue
            
            start_price = prices[0]
            end_price = prices[-1]
            momentum_return = (end_price - start_price) / start_price
            
            momentums.append({
                "symbol": symbol,
                "return": momentum_return,
                "price": end_price
            })
        
        return momentums
