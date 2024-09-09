from datetime import datetime
from lumibot.strategies import Strategy
from lumibot.backtesting import YahooDataBacktesting
from lumibot.brokers import Alpaca
from lumibot.traders import Trader
import os
import alpaca_trade_api as alpaca
import logging
import asyncio

#Environment variables 
from dotenv import load_dotenv
load_dotenv()

# Populate the ALPACA_CONFIG dictionary
ALPACA_CONFIG = {
    'API_KEY': os.environ.get('APCA_API_KEY_ID'),
    'API_SECRET': os.environ.get('APCA_API_SECRET_KEY'),
    'BASE_URL': os.environ.get('BASE_URL')
}

# Check if the API_KEY is loaded correctly
if not ALPACA_CONFIG['API_KEY']:
    raise ValueError("API_KEY not found in config")


# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Momentum(Strategy):
    def initialize(self, symbols=[
            "ALLY", "AMZN", "AXP", "AON", "AAPL", "BATRK", "BAC", "COF", "CHTR", "CVX", "C", "CB", "CBKO", "DVA", "DEO",
            "FND", "HEI.A", "JEF", "KHC", "KR", "LEN.B", "LILA", "LILAK", "LSXMA", "LSXMK", "LLYVA", "LLYVK", "FWONK",
            "LPX", "MA", "MCO", "NU", "NVR", "OXY", "SIRI", "SPY", "TMUS", "ULTA", "VOO", "VRSN", "SNOW", "VIAC"
        ]):
        self.period = 2
        self.counter = 0
        self.sleeptime = 0
        self.symbols = symbols or ["SPY", "VEU", "AGG"]
        self.asset = ""
        self.quantity = 0

    def on_trading_iteration(self):
        momentums = []
        if self.counter == self.period or self.counter == 0:
            self.counter = 0
            momentums = self.get_assets_momentums()
            momentums.sort(key=lambda x: x.get("return"))
            best_asset_data = momentums[-1]
            best_asset = best_asset_data["symbol"]
            best_asset_return = best_asset_data["return"]

            if self.asset:
                current_asset_data = [m for m in momentums if m["symbol"] == self.asset][0]
                current_asset_return = current_asset_data["return"]
                if current_asset_return >= best_asset_return:
                    best_asset = self.asset
                    best_asset_data = current_asset_data

            self.log_message("%s best symbol." % best_asset)

            if best_asset != self.asset:
                if self.asset:
                    self.log_message("Swapping %s for %s." % (self.asset, best_asset))
                    order = self.create_order(self.asset, self.quantity, "sell")
                    self.submit_order(order)

                self.asset = best_asset
                best_asset_price = best_asset_data["price"]
                self.quantity = int(self.portfolio_value // best_asset_price)
                order = self.create_order(self.asset, self.quantity, "buy")
                self.submit_order(order)
            else:
                self.log_message("Keeping %d shares of %s" % (self.quantity, self.asset))

        self.counter += 1
        self.await_market_to_close()

    def on_abrupt_closing(self):
        self.sell_all()

    def trace_stats(self, context, snapshot_before):
        row = {
            "old_best_asset": snapshot_before.get("asset"),
            "old_asset_quantity": snapshot_before.get("quantity"),
            "old_cash": snapshot_before.get("cash"),
            "new_best_asset": self.asset,
            "new_asset_quantity": self.quantity,
        }

        momentums = context.get("momentums")
        if momentums:
            for item in momentums:
                symbol = item.get("symbol")
                for key in item:
                    if key != "symbol":
                        row[f"{symbol}_{key}"] = item[key]

        return row

    def get_assets_momentums(self):
        momentums = []
        start_date = self.get_round_day(timeshift=self.period + 1)
        end_date = self.get_round_day(timeshift=1)
        data = self.get_bars(self.symbols, self.period + 2, timestep="day")
        for asset, bars_set in data.items():
            symbol = asset.symbol
            symbol_momentum = bars_set.get_momentum(start=start_date, end=end_date)
            self.log_message(
                "%s has a return value of %.2f%% over the last %d day(s)."
                % (symbol, 100 * symbol_momentum, self.period)
            )

            momentums.append(
                {
                    "symbol": symbol,
                    "price": bars_set.get_last_price(),
                    "return": symbol_momentum,
                }
            )

        return momentums


# TODO - Figure the datasource error and correct it
async def main():
    is_live = True

    if is_live:
        trader = Trader()
        broker = Alpaca(ALPACA_CONFIG)
        logger.info("Connecting to Alpaca API...")
        try:
            await asyncio.wait_for(broker.connect(), timeout=10)
            logger.info("Connected to Alpaca API.")
        except asyncio.TimeoutError:
            logger.error("Connection to Alpaca API timed out.")
    else:
        backtesting_start = datetime(2024, 8, 1)
        backtesting_end = datetime(2023, 8, 31)

        data_source = YahooDataBacktesting(datetime_start=backtesting_start, datetime_end=backtesting_end)
        results = Momentum.backtest(
            datasource_class=YahooDataBacktesting,
            backtesting_start=backtesting_start,
            backtesting_end=backtesting_end,
            initial_cash=100000,
        )
        print(results)


if __name__ == "__main__":
    asyncio.run(main())