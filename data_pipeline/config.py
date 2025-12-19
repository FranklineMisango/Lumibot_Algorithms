"""
Configuration file for data pipeline
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

"""
Configuration file for data pipeline
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

# API Configuration
ALPACA_API_KEY = os.getenv('ALPACA_API_KEY', '')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY', '')
ALPACA_BASE_URL = 'https://paper-api.alpaca.markets'  # Use paper trading URL for testing

BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')

# Polygon.io Configuration
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '')

# Databento Configuration
DATA_BENTO_API_KEY = os.getenv('DATA_BENTO_API_KEY', '')
DATA_BENTO_USER_ID = os.getenv('DATA_BENTO_USER_ID', '')
DATA_BENTO_PROD_NAME = os.getenv('DATA_BENTO_PROD_NAME', 'prod-001')

# Alpha Vantage Configuration
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', '')

# Tiingo Configuration
TIINGO_API_KEY = os.getenv('TIINGO_API_KEY', '')

# FRED (Federal Reserve Economic Data) Configuration
FRED_API_KEY = os.getenv('FRED_API_KEY', '')

# Quandl Configuration
QUANDL_API_KEY = os.getenv('QUANDL_API_KEY', '')

# Investing.com Configuration (no API key needed for basic scraping)
INVESTING_COM_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
INVESTING_BASE_URL = 'https://www.investing.com'
INVESTING_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'investing_com')

# Data Configuration
DATA_ROOT = os.path.join(os.path.dirname(__file__), '..', 'data')
EQUITY_DATA_PATH = os.path.join(DATA_ROOT, 'equity', 'usa')
CRYPTO_DATA_PATH = os.path.join(DATA_ROOT, 'crypto', 'binance')
OPTION_DATA_PATH = os.path.join(DATA_ROOT, 'option', 'usa')

# Date Range Configuration
DEFAULT_START_DATE = datetime.now() - timedelta(days=365)  # 1 year of data
DEFAULT_END_DATE = datetime.now()

# Supported resolutions
SUPPORTED_RESOLUTIONS = ['tick', 'second', 'minute', 'hour', 'daily']

# Default symbols to download
DEFAULT_EQUITY_SYMBOLS = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA', 'AMZN', 'META', 'NFLX', 'SPY', 'QQQ']
DEFAULT_CRYPTO_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'BNBUSDT', 'SOLUSDT', 'AVAXUSDT']
DEFAULT_OPTION_SYMBOLS = ['SPY', 'QQQ', 'AAPL', 'TSLA', 'MSFT']  # Popular options symbols
DEFAULT_FUTURES_SYMBOLS = ['ES', 'CL', 'ZS']  # Working futures symbols (Polygon.io free tier)
DEFAULT_DATABENTO_FUTURES_SYMBOLS = ['ES.FUT', 'NQ.FUT', 'YM.FUT', 'RTY.FUT', 'CL.FUT', 'GC.FUT', 'SI.FUT', 'ZB.FUT', 'ZN.FUT', 'NG.FUT']  # Databento futures symbols

# Alpha Vantage Default Symbols
DEFAULT_ALPHA_VANTAGE_STOCKS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
DEFAULT_ALPHA_VANTAGE_FOREX = [('EUR', 'USD'), ('GBP', 'USD'), ('USD', 'JPY'), ('USD', 'CHF'), ('AUD', 'USD')]
DEFAULT_ALPHA_VANTAGE_CRYPTO = ['BTC', 'ETH', 'LTC', 'XRP', 'ADA']

# Yahoo Finance Enhanced Symbols
DEFAULT_YAHOO_ETFS = ['SPY', 'QQQ', 'IWM', 'VTI', 'VOO', 'VEA', 'VWO', 'IEMG', 'BND', 'AGG']
DEFAULT_YAHOO_INDICES = ['^GSPC', '^DJI', '^IXIC', '^RUT', '^VIX', '^TNX', '^GSPTSE', '^FTSE', '^N225', '^HSI']
DEFAULT_YAHOO_FOREX = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'USDCHF=X', 'AUDUSD=X', 'USDCAD=X']
DEFAULT_YAHOO_CRYPTO = ['BTC-USD', 'ETH-USD', 'ADA-USD', 'DOT-USD', 'LINK-USD', 'BNB-USD', 'SOL-USD', 'AVAX-USD']

# NSE India Default Symbols
DEFAULT_NSE_STOCKS = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HDFC', 'ICICIBANK', 'KOTAKBANK', 'HINDUNILVR', 'SBIN', 'BHARTIARTL']
DEFAULT_NSE_INDICES = ['NIFTY 50', 'NIFTY BANK', 'NIFTY IT', 'NIFTY AUTO', 'NIFTY PHARMA']
DEFAULT_NSE_FUTURES = ['RELIANCE', 'TCS', 'NIFTY', 'BANKNIFTY']

# BSE India Default Symbols  
DEFAULT_BSE_STOCKS = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HDFC']

# Tiingo Default Symbols
DEFAULT_TIINGO_STOCKS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
DEFAULT_TIINGO_CRYPTO = ['btcusd', 'ethusd', 'ltcusd', 'xrpusd', 'adausd']
DEFAULT_TIINGO_FOREX = ['eurusd', 'gbpusd', 'usdjpy', 'usdchf', 'audusd']

# FRED Economic Indicators
DEFAULT_FRED_SERIES = [
    'GDP', 'GDPC1', 'CPIAUCSL', 'UNRATE', 'FEDFUNDS', 'DGS10', 'DGS2', 
    'DEXUSEU', 'DEXJPUS', 'HOUST', 'PAYEMS', 'INDPRO', 'UMCSENT', 'VIXCLS'
]

# Investing.com Default Symbols
DEFAULT_INVESTING_STOCKS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
DEFAULT_INVESTING_FOREX = [
    'EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'AUD/USD',
    'USD/CAD', 'NZD/USD', 'EUR/GBP', 'EUR/JPY', 'GBP/JPY'
]
DEFAULT_INVESTING_COMMODITIES = ['GOLD', 'SILVER', 'CRUDE_OIL', 'NATURAL_GAS', 'COPPER']
DEFAULT_INVESTING_CRYPTO = [
    'bitcoin', 'ethereum', 'binance-coin', 'cardano', 'dogecoin',
    'polkadot-new', 'chainlink', 'litecoin', 'bitcoin-cash', 'stellar'
]
DEFAULT_INVESTING_INDICES = ['S&P 500', 'Nasdaq 100', 'Dow Jones', 'FTSE 100', 'DAX']

# Stooq Default Symbols
DEFAULT_STOOQ_STOCKS = ['AAPL.US', 'MSFT.US', 'GOOGL.US', 'AMZN.US', 'TSLA.US']
DEFAULT_STOOQ_FOREX = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD']
DEFAULT_STOOQ_INDICES = ['^SPX', '^DJI', '^NDX', '^RUT', '^VIX']
DEFAULT_STOOQ_COMMODITIES = ['GC.F', 'CL.F', 'SI.F', 'NG.F', 'HG.F']  # Gold, Crude Oil, Silver, Natural Gas, Copper
STOOQ_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'stooq')

# Quandl Default Datasets
DEFAULT_QUANDL_DATASETS = [
    'WIKI/AAPL', 'WIKI/MSFT', 'WIKI/GOOGL', 'FRED/GDP', 'FRED/UNRATE',
    'OPEC/ORB', 'LBMA/GOLD', 'CHRIS/CME_ES1', 'CHRIS/CME_CL1'
]

# CoinDesk Default Symbols
DEFAULT_COINDESK_CRYPTO = ['BTC', 'ETH', 'LTC', 'XRP', 'ADA']
COINDESK_API_KEY = os.getenv('COIN_DESK_API_KEY', "")

# Lean format configuration
LEAN_TIME_FORMAT = "%Y%m%d"
LEAN_PRICE_MULTIPLIER = 10000  # Lean uses deci-cents for equity prices
LEAN_CRYPTO_PRICE_MULTIPLIER = 1  # Crypto uses actual prices

# Rate limiting
ALPACA_RATE_LIMIT = 200  # requests per minute
BINANCE_RATE_LIMIT = 1200  # requests per minute
ALPHA_VANTAGE_RATE_LIMIT = 5  # requests per minute (free tier)
TIINGO_RATE_LIMIT = 1000  # requests per hour
FRED_RATE_LIMIT = 120  # requests per minute

# Timezone configuration
LEAN_TIMEZONE_EQUITY = 'America/New_York'
LEAN_TIMEZONE_CRYPTO = 'UTC'
LEAN_TIMEZONE_INDIA = 'Asia/Kolkata'

# Data Configuration
DATA_ROOT = os.path.join(os.path.dirname(__file__), '..', 'data')
EQUITY_DATA_PATH = os.path.join(DATA_ROOT, 'equity', 'usa')
CRYPTO_DATA_PATH = os.path.join(DATA_ROOT, 'crypto', 'binance')
OPTION_DATA_PATH = os.path.join(DATA_ROOT, 'option', 'usa')

# Date Range Configuration
DEFAULT_START_DATE = datetime.now() - timedelta(days=365)  # 1 year of data
DEFAULT_END_DATE = datetime.now()

# Supported resolutions
SUPPORTED_RESOLUTIONS = ['tick', 'second', 'minute', 'hour', 'daily']

# Default symbols to download
DEFAULT_EQUITY_SYMBOLS = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA', 'AMZN', 'META', 'NFLX', 'SPY', 'QQQ']
DEFAULT_CRYPTO_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'BNBUSDT', 'SOLUSDT', 'AVAXUSDT']
DEFAULT_OPTION_SYMBOLS = ['SPY', 'QQQ', 'AAPL', 'TSLA', 'MSFT']  # Popular options symbols
DEFAULT_FUTURES_SYMBOLS = ['ES', 'CL', 'ZS']  # Working futures symbols (Polygon.io free tier)
DEFAULT_DATABENTO_FUTURES_SYMBOLS = ['ES.FUT', 'NQ.FUT', 'YM.FUT', 'RTY.FUT', 'CL.FUT', 'GC.FUT', 'SI.FUT', 'ZB.FUT', 'ZN.FUT', 'NG.FUT']  # Databento futures symbols

# Lean format configuration
LEAN_TIME_FORMAT = "%Y%m%d"
LEAN_PRICE_MULTIPLIER = 10000  # Lean uses deci-cents for equity prices
LEAN_CRYPTO_PRICE_MULTIPLIER = 1  # Crypto uses actual prices

# Rate limiting
ALPACA_RATE_LIMIT = 200  # requests per minute
BINANCE_RATE_LIMIT = 1200  # requests per minute

# Timezone configuration
LEAN_TIMEZONE_EQUITY = 'America/New_York'
LEAN_TIMEZONE_CRYPTO = 'UTC'
