from datetime import datetime, timedelta
from lumibot.backtesting import YahooDataBacktesting
from lumibot.brokers import Alpaca
from lumibot.strategies import Strategy
from lumibot.traders import Trader
from dotenv import load_dotenv
import numpy as np
import pandas as pd
import os
import requests
from tenacity import retry, stop_after_attempt, wait_fixed

load_dotenv()

class Config:
    # 🆕 Added transaction cost parameters
    TRANSACTION_COST_PER_SHARE = 0.005  # $0.005 per share
    SLIPPAGE_RATE = 0.0001  # 0.01% of order value
    FMP_API_KEY = os.getenv('FMP_API_KEY')  # Financial Modeling Prep API key

class BacktestTrend(Strategy):
    def initialize(self):
        self.transaction_costs = 0.0
        self.sleeptime = "1D"
        self.sectors = self.load_sector_data()
        self.adx_window = 14
        self.min_liquidity = 1e6  # $1M daily volume
    
    def get_required_data(self):
        symbols = list(self.symbols.keys()) + ["SPY"]
        return self.get_historical_prices(symbols, 50, "day")
    
    # 🆕 Technical indicator calculations
    def calculate_ATR(self, df):
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(Config.ATR_PERIOD).mean()
    
    def is_tradable(self, symbol):
        volume = self.get_historical_prices(symbol, 1, "day").df['volume'][0]
        return volume * self.get_last_price(symbol) > self.min_liquidity
    
    def calculate_position_size(self, atr):
        risk_amount = self.portfolio_value * Config.RISK_PER_TRADE
        return int(risk_amount / atr) if atr > 0 else 0
    
    def calculate_ADX(self, df, period=14):
        df = df.copy()
        df['high_low'] = df['high'] - df['low']
        df['high_prev_close'] = abs(df['high'] - df['close'].shift(1))
        df['low_prev_close'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['high_low', 'high_prev_close', 'low_prev_close']].max(axis=1)
        
        df['plus_dm'] = np.where(
            (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
            df['high'] - df['high'].shift(1), 0)
        df['minus_dm'] = np.where(
            (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
            df['low'].shift(1) - df['low'], 0)
        
        # Smoothing
        df['tr_smooth'] = df['tr'].ewm(alpha=1/period, adjust=False).mean()
        df['plus_smooth'] = df['plus_dm'].ewm(alpha=1/period, adjust=False).mean()
        df['minus_smooth'] = df['minus_dm'].ewm(alpha=1/period, adjust=False).mean()
        
        df['plus_di'] = (df['plus_smooth'] / df['tr_smooth']) * 100
        df['minus_di'] = (df['minus_smooth'] / df['tr_smooth']) * 100
        df['dx'] = (abs(df['plus_di'] - df['minus_di']) / 
                   (df['plus_di'] + df['minus_di'])) * 100
        df['adx'] = df['dx'].ewm(alpha=1/period, adjust=False).mean()
        
        return df[['adx', 'plus_di', 'minus_di']].iloc[-1]

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))  # 🆕 Error recovery
    def fetch_sector_data(self, symbol):
        url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={Config.FMP_API_KEY}"
        try:
            response = requests.get(url, timeout=5)
            data = response.json()
            return data[0].get('sector', 'Unknown')
        except Exception as e:
            self.logger.error(f"Sector data fetch failed: {e}")
            return 'Unknown'

    def calculate_sector_exposure(self):
        sector_values = {}
        for symbol in self.symbols:
            if symbol not in self.sector_map:
                self.sector_map[symbol] = self.fetch_sector_data(symbol)
                
            sector = self.sector_map[symbol]
            position = self.get_position(symbol)
            if position:
                sector_values[sector] = sector_values.get(sector, 0) + position.market_value
                
        total_value = self.portfolio_value
        return {sector: value/total_value for sector, value in sector_values.items()}

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def submit_order(self, order):
        # Calculate transaction costs
        cost = Config.TRANSACTION_COST_PER_SHARE * order.quantity
        slippage = order.quantity * self.get_last_price(order.symbol) * Config.SLIPPAGE_RATE
        total_cost = cost + slippage
        
        self.transaction_costs += total_cost
        self.portfolio_value -= total_cost
        
        super().submit_order(order)

    def reconcile_positions(self):
        try:
            reported = self.get_positions()
            actual = self.broker.get_positions()
            
            # Compare and resolve discrepancies
            for rep_pos in reported:
                act_pos = next((p for p in actual if p.symbol == rep_pos.symbol), None)
                if not act_pos or act_pos.quantity != rep_pos.quantity:
                    self.logger.warning(f"Position mismatch detected for {rep_pos.symbol}")
                    self.sell_all(rep_pos.symbol)  # Emergency close
        except Exception as e:
            self.logger.error(f"Reconciliation failed: {e}")
            self.emergency_shutdown()

    
    def on_trading_iteration(self):
        # Batch data retrieval
        batch_data = self.get_required_data()
        spy_data = batch_data["SPY"].df
        market_trend = self.calculate_ADX(spy_data)
        
        # 🆕 Market regime filter
        if market_trend[-1] < Config.ADX_THRESHOLD:
            return  # Don't trade in range-bound markets
            
        # 🆕 Sector exposure tracking
        sector_allocation = self.calculate_sector_exposure()
        
        for symbol in self.symbols:
            # 🆕 Liquidity check
            if not self.is_tradable(symbol):
                continue
                
            # Asset-specific signals
            df = batch_data[symbol].df
            df['9_ema'] = df['close'].ewm(span=9).mean()
            df['21_ema'] = df['close'].ewm(span=21).mean()
            
            # 🆕 Crossover confirmation
            current_crossover = (df['9_ema'][-1] > df['21_ema'][-1]) 
            prev_crossover = (df['9_ema'][-2] < df['21_ema'][-2])
            signal = "BUY" if current_crossover and prev_crossover else None
            
            # 🆕 Dynamic position sizing
            atr = self.calculate_ATR(df).iloc[-1]
            position_size = self.calculate_position_size(atr)
            
            # 🆕 Sector allocation check
            if sector_allocation.get(self.sectors[symbol], 0) >= Config.SECTOR_LIMIT:
                continue
                
            # Order execution
            self.execute_trade(symbol, signal, position_size)
    
    def execute_trade(self, symbol, signal, quantity):
        position = self.get_position(symbol)
        
        if signal == "BUY":
            # 🆕 Phased order entry
            for i in range(3):
                try:
                    order = self.create_order(
                        symbol=symbol,
                        quantity=quantity//3,
                        side="buy",
                        type="trailing_stop",
                        trail_percent=Config.TRAILING_STOP_MULTIPLIER
                    )
                    self.submit_order(order)
                except Exception as e:
                    self.logger.error(f"Order failed: {e}")
                    
        elif position and not signal:
            # 🆕 Trailing stop exit
            order = self.create_order(
                symbol=symbol,
                quantity=position.quantity,
                side="sell",
                type="trailing_stop",
                trail_percent=Config.TRAILING_STOP_MULTIPLIER
            )
            self.submit_order(order)
   
    def emergency_shutdown(self):
        self.logger.critical("Initiating emergency shutdown")
        self.sell_all()
        self.stop()


if __name__ == "__main__":
    start = datetime(2024, 8, 1)
    end = datetime(2025, 1, 1)
    
    EnhancedTrend.backtest(
        YahooDataBacktesting,
        start,
        end,
        benchmark_asset="SPY",
        backtesting_parameters={
            "slippage": 0.001,  # 0.1% slippage
            "transaction_cost": 0.0005,  # $0.005 per share
            "max_iters": 1000  # Monte Carlo simulation limit
        }
    )
