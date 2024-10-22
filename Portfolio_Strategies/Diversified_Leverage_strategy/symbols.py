import os
import sys

from dotenv import load_dotenv
load_dotenv()

KRAKEN_FUTURES_API_KEY = os.getenv('KRAKEN_FUTURES_API_KEY')

import asyncio
import ccxt.pro as ccxt  # noqa: E402


# AUTO-TRANSPILE #
async def example():
   exchange = ccxt.krakenfutures({
       'apiKey': KRAKEN_FUTURES_API_KEY,
   })
   symbols = ['BTC/USDT', 'ETH/USDT', 'DOGE/USDT']

   while True:
       trades = await exchange.fetch_ticker(symbols)
       print(trades)

   await exchange.close()


asyncio.run(example())