"""
Binance data downloader for Lean format
"""

from binance.client import Client
import pandas as pd
from datetime import datetime, timedelta
import pytz
import time
import os
from typing import List, Dict, Optional
from tqdm import tqdm

from config import (
    BINANCE_API_KEY, BINANCE_SECRET_KEY,
    CRYPTO_DATA_PATH, LEAN_TIMEZONE_CRYPTO, LEAN_TIME_FORMAT,
    BINANCE_RATE_LIMIT
)
from utils import (
    setup_logging, ensure_directory_exists, format_lean_date,
    create_lean_crypto_csv, write_lean_zip_file, DataValidator
)

logger = setup_logging()

class BinanceDataDownloader:
    """Download crypto data from Binance and convert to Lean format"""
    
    def __init__(self):
        # Initialize Binance client (API keys are optional for market data)
        self.client = Client(
            api_key=BINANCE_API_KEY if BINANCE_API_KEY else None,
            api_secret=BINANCE_SECRET_KEY if BINANCE_SECRET_KEY else None
        )
        
        self.rate_limit_delay = 60 / BINANCE_RATE_LIMIT
        
    def get_klines(self, symbol: str, interval: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get kline data from Binance"""
        try:
            # Convert interval to Binance format
            binance_interval = self._convert_interval(interval)
            
            # Get data from Binance - using timestamps to avoid date parsing issues
            start_timestamp = int(start_date.timestamp() * 1000)  # Convert to milliseconds
            end_timestamp = int(end_date.timestamp() * 1000)      # Convert to milliseconds
            
            klines = self.client.get_historical_klines(
                symbol,
                binance_interval,
                start_timestamp,
                end_timestamp
            )
            
            # Convert to our format
            data = []
            for kline in klines:
                timestamp = datetime.fromtimestamp(kline[0] / 1000.0, tz=pytz.UTC)
                
                data.append({
                    'timestamp': timestamp,
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting klines for {symbol}: {str(e)}")
            return []
    
    def _convert_interval(self, interval: str) -> str:
        """Convert resolution to Binance interval"""
        interval_map = {
            'minute': '1m',
            'hour': '1h',
            'daily': '1d'
        }
        
        return interval_map.get(interval, '1m')
    
    def download_symbol_data(self, symbol: str, resolution: str, start_date: datetime, end_date: datetime,
                           lean_format: bool = True, output_folder: str = "data"):
        """Download and save data for a single symbol"""
        logger.info(f"Downloading {symbol} data for {resolution} resolution")
        
        if resolution == 'daily' or resolution == 'hour':
            # For daily/hour, save all data in one file
            data = self.get_klines(symbol, resolution, start_date, end_date)
            
            if data:
                # Clean and validate data
                cleaned_data = DataValidator.clean_ohlcv_data(data)
                
                if cleaned_data:
                    # Determine output path based on format
                    if lean_format:
                        from config import CRYPTO_DATA_PATH
                        base_path = CRYPTO_DATA_PATH
                        csv_filename = f"{symbol.lower()}_{resolution}_trade.csv"
                    else:
                        # Raw format in data_chest folder
                        base_path = os.path.join(output_folder, "crypto")
                        ensure_directory_exists(base_path)
                        csv_filename = f"{symbol}_{resolution}_raw.csv"
                    
                    output_path = os.path.join(base_path, resolution, f"{symbol.lower()}.zip")
                    
                    # Group data by date for processing
                    daily_data = {}
                    for bar in cleaned_data:
                        date_key = bar['timestamp'].strftime(LEAN_TIME_FORMAT)
                        if date_key not in daily_data:
                            daily_data[date_key] = []
                        daily_data[date_key].append(bar)
                    
                    # Create CSV content for all dates
                    all_csv_content = []
                    for date_key in sorted(daily_data.keys()):
                        date_bars = daily_data[date_key]
                        csv_content = create_lean_crypto_csv(date_bars, symbol, date_bars[0]['timestamp'], resolution)
                        all_csv_content.extend(csv_content)
                    
                    if all_csv_content:
                        write_lean_zip_file(all_csv_content, output_path, csv_filename)
                        logger.info(f"Saved {len(all_csv_content)} bars for {symbol} {resolution}")
        
        else:
            # For minute/second, save data by date
            current_date = start_date
            
            while current_date <= end_date:
                date_start = current_date.replace(hour=0, minute=0, second=0)
                date_end = current_date.replace(hour=23, minute=59, second=59)
                
                data = self.get_klines(symbol, resolution, date_start, date_end)
                
                if data:
                    # Clean and validate data
                    cleaned_data = DataValidator.clean_ohlcv_data(data)
                    
                    if cleaned_data:
                        # Create directory structure
                        symbol_dir = os.path.join(CRYPTO_DATA_PATH, resolution, symbol.lower())
                        ensure_directory_exists(symbol_dir)
                        
                        # Create file paths
                        date_str = format_lean_date(current_date)
                        output_path = os.path.join(symbol_dir, f"{date_str}_trade.zip")
                        csv_filename = f"{date_str}_{symbol.lower()}_{resolution}_trade.csv"
                        
                        # Convert to Lean format
                        csv_content = create_lean_crypto_csv(cleaned_data, symbol, current_date, resolution)
                        
                        if csv_content:
                            write_lean_zip_file(csv_content, output_path, csv_filename)
                            logger.debug(f"Saved {len(csv_content)} bars for {symbol} on {date_str}")
                
                current_date += timedelta(days=1)
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
    
    def download_multiple_symbols(self, symbols: List[str], resolution: str, start_date: datetime, end_date: datetime):
        """Download data for multiple symbols"""
        logger.info(f"Starting download for {len(symbols)} symbols")
        
        for symbol in tqdm(symbols, desc="Downloading symbols"):
            try:
                self.download_symbol_data(symbol, resolution, start_date, end_date)
            except Exception as e:
                logger.error(f"Error downloading {symbol}: {str(e)}")
                continue
        
        logger.info("Download completed")
    
    def download_crypto_symbols(self, symbols: List[str], start_date: datetime, end_date: datetime, 
                              resolution: str = 'daily', lean_format: bool = True, output_folder: str = "data"):
        """Download crypto symbols (orchestrator-compatible method)"""
        logger.info(f"Starting crypto download for {len(symbols)} symbols from Binance")
        logger.info(f"Output: {'Lean format' if lean_format else 'Raw format'} in {output_folder}/ folder")
        downloaded_files = []
        
        for symbol in symbols:
            try:
                # Use the existing download method with custom folder
                self.download_symbol_data(symbol, resolution, start_date, end_date, 
                                        lean_format=lean_format, output_folder=output_folder)
                # Generate expected filename pattern
                folder_prefix = f"{output_folder}/crypto/{resolution}/"
                filename = f"{folder_prefix}{symbol}_{resolution}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.zip"
                downloaded_files.append(filename)
                logger.info(f"SUCCESS: Downloaded {symbol}")
            except Exception as e:
                logger.error(f"ERROR: Error downloading {symbol}: {str(e)}")
                continue
        
        logger.info(f"Crypto download completed: {len(downloaded_files)} files")
        return downloaded_files
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available USDT trading pairs"""
        try:
            exchange_info = self.client.get_exchange_info()
            usdt_symbols = []
            
            for symbol_info in exchange_info['symbols']:
                if (symbol_info['status'] == 'TRADING' and 
                    symbol_info['symbol'].endswith('USDT') and
                    symbol_info['symbol'] not in ['USDCUSDT', 'BUSDUSDT']):  # Exclude stablecoins
                    usdt_symbols.append(symbol_info['symbol'])
            
            return sorted(usdt_symbols)
            
        except Exception as e:
            logger.error(f"Error getting symbols: {str(e)}")
            return []
