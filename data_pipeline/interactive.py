"""
Interactive Terminal App for Data Pipeline
"""

import sys
from datetime import datetime, timedelta
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

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
console = Console()

def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime object"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")

def get_user_inputs():
    """Collect user inputs interactively"""
    console.print(Panel.fit("Arithmax Research Data Chest", style="bold blue"))

    # Data source selection
    sources = ['alpaca', 'binance', 'options', 'futures', 'databento',
               'alpha-vantage', 'yahoo', 'nse-india', 'bse-india', 'tiingo',
               'fred', 'quandl', 'coindesk', 'investing-com', 'stooq', 'all']
    console.print("\n[bold]Available Data Sources:[/bold]")
    for i, source in enumerate(sources, 1):
        console.print(f"{i}. {source}")
    source_choice = Prompt.ask("Select data source (number or name)", choices=sources + [str(i) for i in range(1, len(sources)+1)])
    if source_choice.isdigit():
        source = sources[int(source_choice)-1]
    else:
        source = source_choice

    # Date range
    start_date_str = Prompt.ask("Start date (YYYY-MM-DD)", default=DEFAULT_START_DATE.strftime('%Y-%m-%d'))
    end_date_str = Prompt.ask("End date (YYYY-MM-DD)", default=DEFAULT_END_DATE.strftime('%Y-%m-%d'))
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)

    # Resolution
    resolution = Prompt.ask("Resolution", choices=SUPPORTED_RESOLUTIONS, default='minute')

    # Test mode
    test_mode = Confirm.ask("Run in test mode?", default=False)

    # Additional downloads
    download_fundamentals = Confirm.ask("Download fundamentals?", default=False)
    download_news = Confirm.ask("Download news?", default=False)
    download_earnings = Confirm.ask("Download earnings?", default=False)

    # Symbols based on source
    symbols = {}
    if source in ['alpaca', 'all']:
        equity_symbols = Prompt.ask("Equity symbols (comma-separated)", default=','.join(DEFAULT_EQUITY_SYMBOLS))
        symbols['equity_symbols'] = [s.strip() for s in equity_symbols.split(',') if s.strip()]
    if source in ['binance', 'all']:
        crypto_symbols = Prompt.ask("Crypto symbols (comma-separated)", default=','.join(DEFAULT_CRYPTO_SYMBOLS))
        symbols['crypto_symbols'] = [s.strip() for s in crypto_symbols.split(',') if s.strip()]
    if source not in ['alpaca', 'binance', 'all']:
        symbols_input = Prompt.ask("Symbols (comma-separated)", default='')
        symbols['symbols'] = [s.strip() for s in symbols_input.split(',') if s.strip()]

    return {
        'source': source,
        'start_date': start_date,
        'end_date': end_date,
        'resolution': resolution,
        'test': test_mode,
        'download_fundamentals': download_fundamentals,
        'download_news': download_news,
        'download_earnings': download_earnings,
        **symbols
    }

def run_downloads(args):
    """Run the downloads based on collected args"""
    # Validate date range
    if args['start_date'] >= args['end_date']:
        console.print("[red]Start date must be before end date[/red]")
        return

    console.print(f"Starting data download from {args['start_date'].strftime('%Y-%m-%d')} to {args['end_date'].strftime('%Y-%m-%d')}")
    console.print(f"Resolution: {args['resolution']}")

    # Adjust for test mode
    if args.get('test'):
        if 'equity_symbols' in args:
            args['equity_symbols'] = args['equity_symbols'][:2]
        if 'crypto_symbols' in args:
            args['crypto_symbols'] = args['crypto_symbols'][:2]
        # Add others...

    # Download equity data from Alpaca
    if args['source'] in ['alpaca', 'all']:
        try:
            console.print("Starting Alpaca data download...")
            alpaca_downloader = AlpacaDataDownloader()
            symbols = args.get('equity_symbols', DEFAULT_EQUITY_SYMBOLS)
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Downloading Alpaca symbols...", total=len(symbols))
                for symbol in symbols:
                    alpaca_downloader.download_multiple_symbols([symbol], args['resolution'], args['start_date'], args['end_date'])
                    progress.advance(task)
            console.print("Alpaca download completed")
        except Exception as e:
            console.print(f"[red]Error with Alpaca download: {str(e)}[/red]")
            if args['source'] == 'alpaca':
                return

    # Download crypto data from Binance
    if args['source'] in ['binance', 'all']:
        try:
            console.print("Starting Binance data download...")
            binance_downloader = BinanceDataDownloader()
            symbols = args.get('crypto_symbols', DEFAULT_CRYPTO_SYMBOLS)
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Downloading Binance symbols...", total=len(symbols))
                for symbol in symbols:
                    binance_downloader.download_multiple_symbols([symbol], args['resolution'], args['start_date'], args['end_date'])
                    progress.advance(task)
            console.print("Binance download completed")
        except Exception as e:
            console.print(f"[red]Error with Binance download: {str(e)}[/red]")
            if args['source'] == 'binance':
                return

    # Add other sources here...

    console.print("[green]Data pipeline completed successfully![/green]")

def main():
    try:
        args = get_user_inputs()
        run_downloads(args)
    except KeyboardInterrupt:
        console.print("\n[red]Operation cancelled.[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()