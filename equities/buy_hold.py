from lumibot.brokers import Alpaca
from lumibot.strategies import Strategy
from lumibot.traders import Trader
import yfinance as yf
from datetime import datetime
from lumibot.backtesting import YahooDataBacktesting
import os

from dotenv import load_dotenv
load_dotenv()

DEFAULT_PORTFOLIO_WEIGHTS = {
    "AAPL": 0.1, "BAC": 0.05, "AXP": 0.05, "KO": 0.05, "CVX": 0.05,
    "OXY": 0.03, "KHC": 0.03, "MCO": 0.02, "CB": 0.02, "DVA": 0.02,
    "C": 0.02, "KR": 0.02, "SIRI": 0.01, "V": 0.04, "VRSN": 0.01,
    "MA": 0.04, "AMZN": 0.1, "NU": 0.02, "AON": 0.01, "COF": 0.01,
    "CHTR": 0.02, "ALLY": 0.01, "TMUS": 0.02, "FWONK": 0.01, "LPX": 0.01,
    "LLYVK": 0.01, "FND": 0.01, "ULTA": 0.01, "HEI.A": 0.01, "LLYVA": 0.01,
    "DEO": 0.01, "LEN.B": 0.01, "JEF": 0.01, "LILA": 0.01, "LILAK": 0.01,
    "BATRK": 0.01, "VOO": 0.05, "SPY": 0.05
}


def _build_weights(symbols_weights=None, symbol=None, cash_buffer=0.0, universe_size=None):
    if symbols_weights:
        return symbols_weights

    if symbol:
        return {symbol: max(0.0, 1.0 - cash_buffer)}

    items = list(DEFAULT_PORTFOLIO_WEIGHTS.items())
    if universe_size is not None:
        items = items[: max(1, int(universe_size))]

    gross_weight = max(0.0, 1.0 - cash_buffer)
    total_default_weight = sum(weight for _, weight in items) or 1.0
    return {
        ticker: (weight / total_default_weight) * gross_weight
        for ticker, weight in items
    }

# Populate the ALPACA_CONFIG dictionary
ALPACA_CONFIG = {
    'API_KEY': os.environ.get('APCA_API_KEY_ID'),
    'API_SECRET': os.environ.get('APCA_API_SECRET_KEY'),
    'BASE_URL': os.environ.get('BASE_URL')
}

class BuyHold(Strategy):
    def initialize(self, symbols_weights=None):
        self.sleeptime = "1D"
        params = getattr(self, "parameters", {}) or {}
        selected_symbol = params.get("symbol")
        cash_buffer = float(params.get("cashBuffer", params.get("cash_buffer", 0.0))) / 100.0
        universe_size = params.get("universeSize", params.get("universe_size"))

        self.symbols_weights = _build_weights(
            symbols_weights=symbols_weights or params.get("symbols_weights"),
            symbol=selected_symbol,
            cash_buffer=cash_buffer,
            universe_size=universe_size,
        )

        self.rebalance_days = int(params.get("rebalanceDays", params.get("rebalance_days", 30)))
        self.last_rebalance = None

    def on_trading_iteration(self):
        current_date = self.get_datetime()
        
        # Initial buy or rebalance
        if self.first_iteration or (self.last_rebalance and (current_date - self.last_rebalance).days >= self.rebalance_days):
            self.rebalance_portfolio()
            self.last_rebalance = current_date

    def rebalance_portfolio(self):
        total_value = self.portfolio_value
        positions = self.get_positions()
        
        # Sell positions not in target portfolio
        for position in positions:
            if position.symbol not in self.symbols_weights:
                self.sell_all(position.symbol)
        
        # Adjust positions to target weights
        for symbol, weight in self.symbols_weights.items():
            target_value = total_value * weight
            current_quantity = 0
            if symbol in [p.symbol for p in positions]:
                current_quantity = next(p.quantity for p in positions if p.symbol == symbol)
            current_value = current_quantity * self.get_last_price(symbol)
            
            if current_value < target_value * 0.95:  # Rebalance if off by more than 5%
                quantity_to_buy = int((target_value - current_value) / self.get_last_price(symbol))
                if quantity_to_buy > 0:
                    order = self.create_order(symbol, quantity_to_buy, "buy")
                    self.submit_order(order)
            elif current_value > target_value * 1.05:
                quantity_to_sell = int((current_value - target_value) / self.get_last_price(symbol))
                if quantity_to_sell > 0:
                    order = self.create_order(symbol, quantity_to_sell, "sell")
                    self.submit_order(order)


def run_live():
    broker = Alpaca(ALPACA_CONFIG)
    strategy = BuyHold(broker=broker)
    trader = Trader()
    trader.add_strategy(strategy)
    trader.run_all()


def run_backtest(start=None, end=None, cash=100000, parameters=None):
    start = start or datetime(2024, 8, 1)
    end = end or datetime(2024, 8, 31)
    return BuyHold.backtest(
        YahooDataBacktesting,
        start,
        end,
        cash=cash,
        parameters=parameters or {},
    )


def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Run the BuyHold Lumibot strategy")
    parser.add_argument("--mode", choices=["backtest", "live"], default="backtest")
    parser.add_argument("--start", default="2024-08-01")
    parser.add_argument("--end", default="2024-08-31")
    parser.add_argument("--cash", type=float, default=100000.0)
    parser.add_argument("--parameters-json", default="{}")
    args = parser.parse_args()

    parameters = json.loads(args.parameters_json)
    if args.mode == "live":
        run_live()
        return 0

    start = datetime.fromisoformat(args.start)
    end = datetime.fromisoformat(args.end)
    run_backtest(start=start, end=end, cash=args.cash, parameters=parameters)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())