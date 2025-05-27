from datetime import datetime, timedelta
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies import Strategy
from lumibot.traders import Trader
from dotenv import load_dotenv
import numpy as np
import pandas as pd
import os
import requests
from tenacity import retry, stop_after_attempt, wait_fixed
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

class Config:
    TRANSACTION_COST_PER_SHARE = 0.005  # $0.005 per share
    SLIPPAGE_RATE = 0.0001  # 0.01% of order value
    FMP_API_KEY = os.environ.get('FMP_API_KEY')  # Financial Modeling Prep API key
    ATR_PERIOD = 14  # Period for ATR calculation
    RISK_PER_TRADE = 0.01  # 1% risk per trade
    ADX_THRESHOLD = 20  # Minimum ADX value for trend following
    SECTOR_LIMIT = 0.25  # Maximum sector exposure (25%)
    TRAILING_STOP_MULTIPLIER = 0.02  # 2% trailing stop

class BacktestTrend(Strategy):
    def initialize(self):
        self.transaction_costs = 0.0
        self.sleeptime = "1D"
        self.symbols = ["AAPL", "MSFT"]
        self.sector_map = {}
        self.adx_window = 14
        self.min_liquidity = 1e6  
    
    def get_required_data(self):
        """Get historical data for all required symbols with improved error handling"""
        if not hasattr(self, "symbols") or not self.symbols:
            self.symbols = ["SPY"]
            
        # Ensure SPY is in the symbol list
        all_symbols = self.symbols.copy() if isinstance(self.symbols, list) else list(self.symbols.keys())
        if "SPY" not in all_symbols:
            all_symbols.append("SPY")
            
        batch_data = {}
        for symbol in all_symbols:
            try:
                # Get the historical data for this symbol
                data = self.get_historical_prices(symbol, 50, "day")
                
                # Verify that data is valid before adding to batch_data
                if data is not None and hasattr(data, 'df') and data.df is not None and not data.df.empty:
                    batch_data[symbol] = data
                else:
                    self.logger.warning(f"Invalid or empty data for {symbol}, skipping")
            except Exception as e:
                self.logger.error(f"Failed to get data for {symbol}: {str(e)}")
                
        # If we couldn't get any data, log a clear error
        if not batch_data:
            self.logger.error("Could not get valid data for any symbols")
        
        return batch_data
    
    def calculate_ATR(self, df):
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(Config.ATR_PERIOD).mean()
    
    def is_tradable(self, symbol):
        try:
            history = self.get_historical_prices(symbol, 1, "day")
            if history is None or history.df.empty:
                return False
            volume = history.df['volume'].iloc[0]
            last_price = self.get_last_price(symbol)
            return volume * last_price > self.min_liquidity
        except Exception as e:
            self.logger.error(f"Error checking if {symbol} is tradable: {str(e)}")
            return False
    
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
            self.logger.error(f"Sector data fetch failed for {symbol}: {e}")
            return 'Unknown'

    def calculate_sector_exposure(self):
        sector_values = {}
        # Get all positions and extract symbols
        positions = self.get_positions()
        
        for position in positions:
            symbol = position.symbol
            if symbol not in self.sector_map:
                self.sector_map[symbol] = self.fetch_sector_data(symbol)
                
            sector = self.sector_map[symbol]
            
            # Calculate the market value of the position
            market_value = position.quantity * self.get_last_price(symbol)  # Replace with the correct calculation
            sector_values[sector] = sector_values.get(sector, 0) + market_value
                    
        total_value = self.portfolio_value
        return {sector: value / total_value for sector, value in sector_values.items()} if total_value > 0 else {}
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
        try:
            # Batch data retrieval
            batch_data = self.get_required_data()
            if not batch_data or "SPY" not in batch_data:
                self.logger.error("SPY data not available - skipping trading iteration")
                return
                
            spy_data = batch_data["SPY"].df
            market_trend = self.calculate_ADX(spy_data)
            
            if market_trend.adx < Config.ADX_THRESHOLD:
                self.logger.info(f"Market ADX below threshold: {market_trend.adx} - not trading")
                return  # Don't trade in range-bound markets
                
            sector_allocation = self.calculate_sector_exposure()
            
            # Fixed iteration through symbols when self.symbols is a list
            symbols_to_check = self.symbols if isinstance(self.symbols, list) else list(self.symbols.keys())
            
            for symbol in symbols_to_check:
                if symbol not in batch_data:
                    self.logger.warning(f"No data available for {symbol} - skipping")
                    continue
                    
                # Fetch sector data if not already cached
                if symbol not in self.sector_map:
                    self.sector_map[symbol] = self.fetch_sector_data(symbol)
                    
                if not self.is_tradable(symbol):
                    self.logger.info(f"{symbol} not tradable - insufficient liquidity")
                    continue
                    
                # Asset-specific signals
                df = batch_data[symbol].df
                df['9_ema'] = df['close'].ewm(span=9).mean()
                df['21_ema'] = df['close'].ewm(span=21).mean()
                
                if len(df) < 2:
                    self.logger.warning(f"Insufficient data for {symbol} - need at least 2 days")
                    continue
                
                current_crossover = (df['9_ema'].iloc[-1] > df['21_ema'].iloc[-1]) 
                prev_crossover = (df['9_ema'].iloc[-2] < df['21_ema'].iloc[-2])
                signal = "BUY" if current_crossover and prev_crossover else None
                
                atr = self.calculate_ATR(df).iloc[-1]
                position_size = self.calculate_position_size(atr)
                
                sector = self.sector_map[symbol]
                if sector_allocation.get(sector, 0) >= Config.SECTOR_LIMIT:
                    self.logger.info(f"Sector {sector} exposure limit reached - skipping {symbol}")
                    continue
                    
                self.execute_trade(symbol, signal, position_size)
        except Exception as e:
            self.logger.error(f"Error in trading iteration: {str(e)}")
            # Continue operation despite errors
    
    def execute_trade(self, symbol, signal, quantity):
        position = self.get_position(symbol)
        
        if signal == "BUY":
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
    logger.info("Starting backtesting strategy")
    
    # Check for FMP API key
    if not Config.FMP_API_KEY:
        logger.warning("No FMP_API_KEY found in environment variables. Sector data will not be available.")
    
    start = datetime(2020, 1, 1)
    end = datetime(2022, 12, 31)    
    
    try:
        # Pass initial_capital and use symbols parameter correctly
        BacktestTrend.backtest(
            YahooDataBacktesting,
            start,
            end,
            benchmark_asset="SPY",
        )
        logger.info("Backtest completed successfully")
    except Exception as e:
        logger.error(f"Backtest failed with error: {str(e)}")
