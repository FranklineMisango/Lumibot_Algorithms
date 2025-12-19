"""
Main data pipeline script
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import List

from config import (
    DEFAULT_EQUITY_SYMBOLS, DEFAULT_CRYPTO_SYMBOLS, DEFAULT_OPTION_SYMBOLS, DEFAULT_FUTURES_SYMBOLS,
    DEFAULT_DATABENTO_FUTURES_SYMBOLS, DEFAULT_START_DATE, DEFAULT_END_DATE,
    SUPPORTED_RESOLUTIONS, DEFAULT_ALPHA_VANTAGE_STOCKS, DEFAULT_ALPHA_VANTAGE_FOREX,
    DEFAULT_ALPHA_VANTAGE_CRYPTO, DEFAULT_YAHOO_ETFS, DEFAULT_YAHOO_INDICES,
    DEFAULT_YAHOO_FOREX, DEFAULT_YAHOO_CRYPTO, DEFAULT_NSE_STOCKS, DEFAULT_NSE_INDICES,
    DEFAULT_BSE_STOCKS, DEFAULT_TIINGO_STOCKS, DEFAULT_TIINGO_CRYPTO, DEFAULT_TIINGO_FOREX,
    DEFAULT_FRED_SERIES, DEFAULT_QUANDL_DATASETS, DEFAULT_INVESTING_STOCKS, DEFAULT_INVESTING_FOREX,
    DEFAULT_INVESTING_COMMODITIES, DEFAULT_INVESTING_CRYPTO, DEFAULT_INVESTING_INDICES,
    DEFAULT_STOOQ_STOCKS, DEFAULT_STOOQ_FOREX, DEFAULT_STOOQ_INDICES, DEFAULT_STOOQ_COMMODITIES
)
from alpaca_downloader import AlpacaDataDownloader
from binance_downloader import BinanceDataDownloader
from polygon_futures_downloader import PolygonFuturesDownloader
from databento_downloader import DatabentoFuturesDownloader

# New downloaders
from alpha_vantage_downloader import AlphaVantageDownloader
from yahoo_finance_downloader import YahooFinanceDownloader
from nse_india_downloader import NSEIndiaDownloader
from bse_india_downloader import BSEIndiaDownloader
from tiingo_downloader import TiingoDownloader
from fred_downloader import FREDDownloader
from quandl_downloader import QuandlDownloader
from coindesk_downloader import CoinDeskDownloader
from investing_com_downloader import InvestingComDownloader
from stooq_downloader import StooqDownloader

from utils import setup_logging

logger = setup_logging()

def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime object"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")

def main():
    parser = argparse.ArgumentParser(description='Download financial data and convert to Lean format')
    
    # Data source arguments
    parser.add_argument('--source', 
                       choices=['alpaca', 'binance', 'options', 'futures', 'databento', 
                               'alpha-vantage', 'yahoo', 'nse-india', 
                               'bse-india', 'tiingo', 'fred', 'quandl', 'coindesk', 
                               'investing-com', 'stooq', 'all'], 
                       default='all',
                       help='Data source to download from')
    
    # Symbol arguments
    parser.add_argument('--equity-symbols', nargs='+', default=DEFAULT_EQUITY_SYMBOLS,
                       help='Equity symbols to download (for Alpaca)')
    parser.add_argument('--crypto-symbols', nargs='+', default=DEFAULT_CRYPTO_SYMBOLS,
                       help='Crypto symbols to download (for Binance)')
    parser.add_argument('--option-symbols', nargs='+', default=DEFAULT_OPTION_SYMBOLS,
                       help='Option symbols to download (for yfinance)')
    parser.add_argument('--futures-symbols', nargs='+', default=DEFAULT_FUTURES_SYMBOLS,
                       help='Futures symbols to download (for Polygon.io)')
    parser.add_argument('--databento-symbols', nargs='+', default=DEFAULT_DATABENTO_FUTURES_SYMBOLS,
                       help='Futures symbols to download (for Databento)')
    
    # New downloader symbols
    parser.add_argument('--av-stocks', nargs='+', default=DEFAULT_ALPHA_VANTAGE_STOCKS,
                       help='Alpha Vantage stock symbols')
    parser.add_argument('--av-forex', nargs='+', default=[f"{pair[0]}{pair[1]}" for pair in DEFAULT_ALPHA_VANTAGE_FOREX],
                       help='Alpha Vantage forex pairs')
    parser.add_argument('--av-crypto', nargs='+', default=DEFAULT_ALPHA_VANTAGE_CRYPTO,
                       help='Alpha Vantage crypto symbols')
    
    parser.add_argument('--yahoo-etfs', nargs='+', default=DEFAULT_YAHOO_ETFS,
                       help='Yahoo Finance ETF symbols')
    parser.add_argument('--yahoo-indices', nargs='+', default=DEFAULT_YAHOO_INDICES,
                       help='Yahoo Finance index symbols')
    parser.add_argument('--yahoo-forex', nargs='+', default=DEFAULT_YAHOO_FOREX,
                       help='Yahoo Finance forex pairs')
    parser.add_argument('--yahoo-crypto', nargs='+', default=DEFAULT_YAHOO_CRYPTO,
                       help='Yahoo Finance crypto symbols')
    
    parser.add_argument('--nse-stocks', nargs='+', default=DEFAULT_NSE_STOCKS,
                       help='NSE India stock symbols')
    parser.add_argument('--nse-indices', nargs='+', default=DEFAULT_NSE_INDICES,
                       help='NSE India index symbols')
    
    parser.add_argument('--bse-stocks', nargs='+', default=DEFAULT_BSE_STOCKS,
                       help='BSE India stock symbols')
    
    parser.add_argument('--tiingo-stocks', nargs='+', default=DEFAULT_TIINGO_STOCKS,
                       help='Tiingo stock symbols')
    parser.add_argument('--tiingo-crypto', nargs='+', default=DEFAULT_TIINGO_CRYPTO,
                       help='Tiingo crypto symbols')
    parser.add_argument('--tiingo-forex', nargs='+', default=DEFAULT_TIINGO_FOREX,
                       help='Tiingo forex pairs')
    
    parser.add_argument('--fred-series', nargs='+', default=DEFAULT_FRED_SERIES,
                       help='FRED economic series')
    
    parser.add_argument('--quandl-datasets', nargs='+', default=DEFAULT_QUANDL_DATASETS,
                       help='Quandl dataset codes')
    
    # Investing.com arguments
    parser.add_argument('--investing-stocks', nargs='+', default=DEFAULT_INVESTING_STOCKS,
                       help='Investing.com stock symbols')
    parser.add_argument('--investing-forex', nargs='+', default=DEFAULT_INVESTING_FOREX,
                       help='Investing.com forex pairs')
    parser.add_argument('--investing-commodities', nargs='+', default=DEFAULT_INVESTING_COMMODITIES,
                       help='Investing.com commodity symbols')
    parser.add_argument('--investing-crypto', nargs='+', default=DEFAULT_INVESTING_CRYPTO,
                       help='Investing.com crypto symbols')
    parser.add_argument('--investing-indices', nargs='+', default=DEFAULT_INVESTING_INDICES,
                       help='Investing.com index symbols')
    
    # Stooq arguments  
    parser.add_argument('--stooq-stocks', nargs='+', default=DEFAULT_STOOQ_STOCKS,
                       help='Stooq stock symbols')
    parser.add_argument('--stooq-forex', nargs='+', default=DEFAULT_STOOQ_FOREX,
                       help='Stooq forex pairs')
    parser.add_argument('--stooq-indices', nargs='+', default=DEFAULT_STOOQ_INDICES,
                       help='Stooq index symbols')
    parser.add_argument('--stooq-commodities', nargs='+', default=DEFAULT_STOOQ_COMMODITIES,
                       help='Stooq commodity symbols')
    
    # Date range arguments
    parser.add_argument('--start-date', type=parse_date, default=DEFAULT_START_DATE,
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=parse_date, default=DEFAULT_END_DATE,
                       help='End date (YYYY-MM-DD)')
    
    # Resolution arguments
    parser.add_argument('--resolution', choices=SUPPORTED_RESOLUTIONS, default='minute',
                       help='Data resolution')
    
    # Other arguments
    parser.add_argument('--test', action='store_true',
                       help='Run in test mode with limited symbols and date range')
    
    # Download type arguments
    parser.add_argument('--download-fundamentals', action='store_true',
                       help='Download fundamental data where available')
    parser.add_argument('--download-news', action='store_true',
                       help='Download news data where available')
    parser.add_argument('--download-earnings', action='store_true',
                       help='Download earnings data where available')
    
    args = parser.parse_args()
    
    # Test mode adjustments
    if args.test:
        args.equity_symbols = ['AAPL', 'GOOGL', 'MSFT'][:2]
        args.crypto_symbols = ['BTCUSDT', 'ETHUSDT'][:2]
        args.option_symbols = ['SPY', 'AAPL'][:2]
        args.futures_symbols = ['ES', 'NQ'][:2]
        args.databento_symbols = ['ES.FUT', 'NQ.FUT'][:2]
        args.av_stocks = ['AAPL', 'MSFT'][:2]
        args.yahoo_etfs = ['SPY', 'QQQ'][:2]
        args.nse_stocks = ['RELIANCE', 'TCS'][:2]
        args.bse_stocks = ['RELIANCE', 'TCS'][:2]
        args.tiingo_stocks = ['AAPL', 'MSFT'][:2]
        args.tiingo_crypto = []  # Skip crypto in test mode due to API limitations
        args.tiingo_forex = []   # Skip forex in test mode due to API limitations
        args.fred_series = ['GDP', 'UNRATE'][:2]
        args.quandl_datasets = ['WIKI/AAPL', 'FRED/GDP'][:2]
        args.start_date = datetime.now() - timedelta(days=7)
        args.end_date = datetime.now()
        logger.info("Running in test mode with limited symbols and date range")
    
    # Validate date range
    if args.start_date >= args.end_date:
        logger.error("Start date must be before end date")
        sys.exit(1)
    
    logger.info(f"Starting data download from {args.start_date.strftime('%Y-%m-%d')} to {args.end_date.strftime('%Y-%m-%d')}")
    logger.info(f"Resolution: {args.resolution}")
    
    # Download equity data from Alpaca
    if args.source in ['alpaca', 'all']:
        try:
            logger.info("Starting Alpaca data download...")
            alpaca_downloader = AlpacaDataDownloader()
            alpaca_downloader.download_multiple_symbols(
                args.equity_symbols, 
                args.resolution, 
                args.start_date, 
                args.end_date
            )
            logger.info("Alpaca download completed")
        except Exception as e:
            logger.error(f"Error with Alpaca download: {str(e)}")
            if args.source == 'alpaca':
                sys.exit(1)
    
    # Download crypto data from Binance
    if args.source in ['binance', 'all']:
        try:
            logger.info("Starting Binance data download...")
            binance_downloader = BinanceDataDownloader()
            binance_downloader.download_multiple_symbols(
                args.crypto_symbols, 
                args.resolution, 
                args.start_date, 
                args.end_date
            )
            logger.info("Binance download completed")
        except Exception as e:
            logger.error(f"Error with Binance download: {str(e)}")
            if args.source == 'binance':
                sys.exit(1)
    
    # Download options data from yfinance (free, no API key required)
    if args.source in ['options', 'all']:
        try:
            if YFinanceOptionsDownloader is not None:
                logger.info("Starting Options data download...")
                options_downloader = YFinanceOptionsDownloader()
                options_downloader.download_symbols(args.option_symbols)
                logger.info("Options download completed")
            else:
                logger.warning("YFinance options downloader not available, skipping options download")
        except Exception as e:
            logger.error(f"Error with Options download: {str(e)}")
            if args.source == 'options':
                sys.exit(1)

    # Download futures data from Polygon.io
    if args.source in ['futures', 'all']:
        try:
            logger.info("Starting Futures data download...")
            futures_downloader = PolygonFuturesDownloader()
            futures_downloader.download_symbols(
                args.futures_symbols,
                args.start_date,
                args.end_date,
                args.resolution
            )
            logger.info("Futures download completed")
        except Exception as e:
            logger.error(f"Error with Futures download: {str(e)}")
            if args.source == 'futures':
                sys.exit(1)
    
    # Download futures data from Databento
    if args.source in ['databento', 'all']:
        try:
            logger.info("Starting Databento futures data download...")
            databento_downloader = DatabentoFuturesDownloader()
            databento_downloader.download_symbols(
                args.databento_symbols,
                args.start_date,
                args.end_date,
                args.resolution
            )
            logger.info("Databento download completed")
        except Exception as e:
            logger.error(f"Error with Databento download: {str(e)}")
            if args.source == 'databento':
                sys.exit(1)
    
    # Download data from Alpha Vantage
    if args.source in ['alpha-vantage', 'all']:
        try:
            logger.info("Starting Alpha Vantage data download...")
            av_downloader = AlphaVantageDownloader()
            
            # Download stocks
            av_downloader.download_stock_symbols(args.av_stocks, args.resolution, args.start_date, args.end_date)
            
            # Download forex
            forex_pairs = [(pair[:3], pair[3:]) for pair in args.av_forex if len(pair) == 6]
            av_downloader.download_forex_pairs(forex_pairs, args.resolution, args.start_date, args.end_date)
            
            # Download crypto
            av_downloader.download_crypto_symbols(args.av_crypto, args.resolution, args.start_date, args.end_date)
            
            logger.info("Alpha Vantage download completed")
        except Exception as e:
            logger.error(f"Error with Alpha Vantage download: {str(e)}")
            if args.source == 'alpha-vantage':
                sys.exit(1)
    
    # Download data from Yahoo Finance (Enhanced)
    if args.source in ['yahoo', 'all']:
        try:
            logger.info("Starting Yahoo Finance data download...")
            yahoo_downloader = YahooFinanceDownloader()
            
            # Download stocks
            yahoo_downloader.download_stock_symbols(args.equity_symbols, args.resolution, args.start_date, args.end_date, 'equity')
            
            # Download ETFs
            yahoo_downloader.download_stock_symbols(args.yahoo_etfs, args.resolution, args.start_date, args.end_date, 'etf')
            
            # Download indices
            yahoo_downloader.download_stock_symbols(args.yahoo_indices, args.resolution, args.start_date, args.end_date, 'indices')
            
            # Download forex
            yahoo_downloader.download_forex_pairs(args.yahoo_forex, args.resolution, args.start_date, args.end_date)
            
            # Download crypto
            yahoo_downloader.download_crypto_symbols(args.yahoo_crypto, args.resolution, args.start_date, args.end_date)
            
            # Download fundamentals if requested
            if args.download_fundamentals:
                yahoo_downloader.download_fundamentals(args.equity_symbols)
            
            # Download earnings if requested
            if args.download_earnings:
                yahoo_downloader.download_earnings(args.equity_symbols)
            
            # Download news if requested
            if args.download_news:
                yahoo_downloader.download_news(args.equity_symbols, 10)
            
            logger.info("Yahoo Finance download completed")
        except Exception as e:
            logger.error(f"Error with Yahoo Finance download: {str(e)}")
            if args.source == 'yahoo':
                sys.exit(1)
    
    # Download data from NSE India
    if args.source in ['nse-india', 'all']:
        try:
            logger.info("Starting NSE India data download...")
            nse_downloader = NSEIndiaDownloader()
            
            # Download equity data
            nse_downloader.download_equity_symbols(args.nse_stocks, args.start_date, args.end_date)
            
            # Download index data
            nse_downloader.download_index_symbols(args.nse_indices, args.start_date, args.end_date)
            
            logger.info("NSE India download completed")
        except Exception as e:
            logger.error(f"Error with NSE India download: {str(e)}")
            if args.source == 'nse-india':
                sys.exit(1)
    
    # Download data from BSE India
    if args.source in ['bse-india', 'all']:
        try:
            logger.info("Starting BSE India data download...")
            bse_downloader = BSEIndiaDownloader()
            
            # Download equity data
            bse_downloader.download_equity_symbols(args.bse_stocks, args.start_date, args.end_date)
            
            logger.info("BSE India download completed")
        except Exception as e:
            logger.error(f"Error with BSE India download: {str(e)}")
            if args.source == 'bse-india':
                sys.exit(1)
    
    # Download data from Tiingo
    if args.source in ['tiingo', 'all']:
        try:
            logger.info("Starting Tiingo data download...")
            tiingo_downloader = TiingoDownloader()
            
            # Download stocks
            tiingo_downloader.download_stock_symbols(args.tiingo_stocks, args.start_date, args.end_date, args.resolution)
            
            # Download crypto
            tiingo_downloader.download_crypto_symbols(args.tiingo_crypto, args.start_date, args.end_date, args.resolution)
            
            # Download forex
            tiingo_downloader.download_forex_pairs(args.tiingo_forex, args.start_date, args.end_date, args.resolution)
            
            # Download fundamentals if requested
            if args.download_fundamentals:
                tiingo_downloader.download_fundamentals(args.tiingo_stocks)
            
            # Download news if requested
            if args.download_news:
                tiingo_downloader.download_news(args.tiingo_stocks, 10)
            
            logger.info("Tiingo download completed")
        except Exception as e:
            logger.error(f"Error with Tiingo download: {str(e)}")
            if args.source == 'tiingo':
                sys.exit(1)
    
    # Download data from FRED
    if args.source in ['fred', 'all']:
        try:
            logger.info("Starting FRED data download...")
            fred_downloader = FREDDownloader()
            
            # Download economic series
            fred_downloader.download_economic_series(args.fred_series, args.start_date, args.end_date)
            
            logger.info("FRED download completed")
        except Exception as e:
            logger.error(f"Error with FRED download: {str(e)}")
            if args.source == 'fred':
                sys.exit(1)
    
    # Download data from Quandl
    if args.source in ['quandl', 'all']:
        try:
            logger.info("Starting Quandl data download...")
            quandl_downloader = QuandlDownloader()
            
            # Download datasets
            quandl_downloader.download_datasets(args.quandl_datasets, args.start_date, args.end_date)
            
            logger.info("Quandl download completed")
        except Exception as e:
            logger.error(f"Error with Quandl download: {str(e)}")
            if args.source == 'quandl':
                sys.exit(1)
    
    # Download data from CoinDesk
    if args.source in ['coindesk', 'all']:
        try:
            logger.info("Starting CoinDesk data download...")
            coindesk_downloader = CoinDeskDownloader()
            
            # Download Bitcoin price index
            coindesk_downloader.download_bitcoin_data(args.start_date, args.end_date)
            
            # Download current prices
            coindesk_downloader.download_current_prices(['USD', 'EUR', 'GBP'])
            
            logger.info("CoinDesk download completed")
        except Exception as e:
            logger.error(f"Error with CoinDesk download: {str(e)}")
            if args.source == 'coindesk':
                sys.exit(1)
    
    logger.info("Data pipeline completed successfully!")

if __name__ == "__main__":
    main()