"""
Data validation and quality checks
"""

import os
import zipfile
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

from config import DATA_ROOT, EQUITY_DATA_PATH, CRYPTO_DATA_PATH
from utils import setup_logging

logger = setup_logging()

class DataValidator:
    """Validate and analyze downloaded data"""
    
    def __init__(self):
        self.equity_path = EQUITY_DATA_PATH
        self.crypto_path = CRYPTO_DATA_PATH
    
    def validate_lean_file(self, file_path: str) -> Dict:
        """Validate a single LEAN data file"""
        results = {
            'file_path': file_path,
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'bar_count': 0,
            'date_range': None,
            'price_range': None,
            'volume_stats': None
        }
        
        try:
            # Check if file exists and is a zip file
            if not os.path.exists(file_path):
                results['errors'].append("File does not exist")
                return results
            
            if not file_path.endswith('.zip'):
                results['errors'].append("File is not a zip file")
                return results
            
            # Extract and validate CSV content
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                csv_files = [f for f in zip_file.namelist() if f.endswith('.csv')]
                
                if not csv_files:
                    results['errors'].append("No CSV files found in zip")
                    return results
                
                if len(csv_files) > 1:
                    results['warnings'].append(f"Multiple CSV files found: {csv_files}")
                
                # Read the first CSV file
                csv_filename = csv_files[0]
                with zip_file.open(csv_filename) as csv_file:
                    df = pd.read_csv(csv_file, header=None)
                    
                    # Detect data type and validate CSV structure
                    if df.shape[1] == 6:
                        # TradeBar format (equity/crypto): Time, Open, High, Low, Close, Volume
                        df.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
                        data_type = 'tradebar'
                    elif df.shape[1] == 8:
                        # QuoteBar format (forex): Time, BidOpen, BidHigh, BidLow, BidClose, AskOpen, AskHigh, AskLow, AskClose
                        df.columns = ['Time', 'BidOpen', 'BidHigh', 'BidLow', 'BidClose', 'AskOpen', 'AskHigh', 'AskLow', 'AskClose']
                        data_type = 'quotebar'
                    elif df.shape[1] == 7:
                        # Options format: Time, Open, High, Low, Close, Volume, OpenInterest
                        df.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'OpenInterest']
                        data_type = 'options'
                    else:
                        results['errors'].append(f"Unsupported column count: {df.shape[1]}. Expected 6 (TradeBar), 7 (Options), or 8 (QuoteBar)")
                        return results
                    
                    # Basic validation
                    results['bar_count'] = len(df)
                    
                    if results['bar_count'] == 0:
                        results['errors'].append("No data rows found")
                        return results
                    
                    # Validate data based on type
                    if data_type == 'tradebar' or data_type == 'options':
                        # Validate OHLC logic for TradeBar and Options
                        invalid_ohlc = df[(df['Low'] > df['Open']) | 
                                         (df['Low'] > df['High']) | 
                                         (df['Low'] > df['Close']) | 
                                         (df['High'] < df['Open']) | 
                                         (df['High'] < df['Close'])]
                        
                        if len(invalid_ohlc) > 0:
                            results['errors'].append(f"Invalid OHLC data in {len(invalid_ohlc)} rows")
                        
                        # Validate volume
                        negative_volume = df[df['Volume'] < 0]
                        if len(negative_volume) > 0:
                            results['errors'].append(f"Negative volume in {len(negative_volume)} rows")
                        
                        # Calculate statistics
                        results['date_range'] = (df['Time'].min(), df['Time'].max())
                        results['price_range'] = (df['Close'].min(), df['Close'].max())
                        results['volume_stats'] = {
                            'total': df['Volume'].sum(),
                            'avg': df['Volume'].mean(),
                            'max': df['Volume'].max(),
                            'min': df['Volume'].min()
                        }
                        
                    elif data_type == 'quotebar':
                        # Validate QuoteBar (forex) data
                        # Check bid/ask spread validity
                        invalid_spread = df[df['AskOpen'] < df['BidOpen']]
                        if len(invalid_spread) > 0:
                            results['errors'].append(f"Invalid bid/ask spread in {len(invalid_spread)} rows")
                        
                        # Validate bid OHLC logic
                        invalid_bid_ohlc = df[(df['BidLow'] > df['BidOpen']) | 
                                             (df['BidLow'] > df['BidHigh']) | 
                                             (df['BidLow'] > df['BidClose']) | 
                                             (df['BidHigh'] < df['BidOpen']) | 
                                             (df['BidHigh'] < df['BidClose'])]
                        
                        if len(invalid_bid_ohlc) > 0:
                            results['errors'].append(f"Invalid bid OHLC data in {len(invalid_bid_ohlc)} rows")
                        
                        # Validate ask OHLC logic
                        invalid_ask_ohlc = df[(df['AskLow'] > df['AskOpen']) | 
                                             (df['AskLow'] > df['AskHigh']) | 
                                             (df['AskLow'] > df['AskClose']) | 
                                             (df['AskHigh'] < df['AskOpen']) | 
                                             (df['AskHigh'] < df['AskClose'])]
                        
                        if len(invalid_ask_ohlc) > 0:
                            results['errors'].append(f"Invalid ask OHLC data in {len(invalid_ask_ohlc)} rows")
                        
                        # Calculate statistics for QuoteBar
                        results['date_range'] = (df['Time'].min(), df['Time'].max())
                        results['price_range'] = (df['BidClose'].min(), df['AskClose'].max())
                        results['volume_stats'] = None  # No volume for forex
                    
                    # Time validation
                    if not df['Time'].is_monotonic_increasing:
                        results['warnings'].append("Time series is not monotonic increasing")
                    
                    # Check for gaps
                    time_diffs = df['Time'].diff().dropna()
                    if len(time_diffs.unique()) > 10:  # Too many different intervals
                        results['warnings'].append("Irregular time intervals detected")
                    
                    # If no errors, mark as valid
                    if not results['errors']:
                        results['is_valid'] = True
        
        except Exception as e:
            results['errors'].append(f"Exception during validation: {str(e)}")
        
        return results
    
    def validate_symbol_data(self, symbol: str, asset_type: str, resolution: str) -> Dict:
        """Validate all data files for a symbol"""
        base_path = self.equity_path if asset_type == 'equity' else self.crypto_path
        symbol_path = os.path.join(base_path, resolution, symbol.lower())
        
        results = {
            'symbol': symbol,
            'asset_type': asset_type,
            'resolution': resolution,
            'total_files': 0,
            'valid_files': 0,
            'invalid_files': 0,
            'total_bars': 0,
            'date_coverage': [],
            'file_results': []
        }
        
        if not os.path.exists(symbol_path):
            results['errors'] = [f"Symbol path does not exist: {symbol_path}"]
            return results
        
        # Get all zip files
        zip_files = [f for f in os.listdir(symbol_path) if f.endswith('.zip')]
        results['total_files'] = len(zip_files)
        
        for zip_file in sorted(zip_files):
            file_path = os.path.join(symbol_path, zip_file)
            file_result = self.validate_lean_file(file_path)
            
            results['file_results'].append(file_result)
            
            if file_result['is_valid']:
                results['valid_files'] += 1
                results['total_bars'] += file_result['bar_count']
                
                # Extract date from filename
                if '_' in zip_file:
                    date_str = zip_file.split('_')[0]
                    try:
                        date = datetime.strptime(date_str, '%Y%m%d')
                        results['date_coverage'].append(date)
                    except ValueError:
                        pass
            else:
                results['invalid_files'] += 1
        
        return results
    
    def generate_report(self, validation_results: List[Dict]) -> str:
        """Generate a human-readable validation report"""
        report = []
        report.append("LEAN Data Validation Report")
        report.append("=" * 50)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        total_symbols = len(validation_results)
        total_valid = sum(1 for r in validation_results if r['invalid_files'] == 0)
        total_files = sum(r['total_files'] for r in validation_results)
        total_bars = sum(r['total_bars'] for r in validation_results)
        
        report.append("Summary:")
        report.append(f"  Total symbols: {total_symbols}")
        report.append(f"  Valid symbols: {total_valid}")
        report.append(f"  Total files: {total_files}")
        report.append(f"  Total bars: {total_bars:,}")
        report.append("")
        
        for result in validation_results:
            report.append(f"Symbol: {result['symbol']} ({result['asset_type']}, {result['resolution']})")
            report.append(f"  Files: {result['valid_files']}/{result['total_files']} valid")
            report.append(f"  Bars: {result['total_bars']:,}")
            
            if result['date_coverage']:
                start_date = min(result['date_coverage'])
                end_date = max(result['date_coverage'])
                report.append(f"  Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            # Show errors
            error_files = [f for f in result['file_results'] if f['errors']]
            if error_files:
                report.append(f"  Errors in {len(error_files)} files:")
                for file_result in error_files[:5]:  # Show first 5 errors
                    report.append(f"    {os.path.basename(file_result['file_path'])}: {file_result['errors']}")
            
            report.append("")
        
        return "\n".join(report)
    
    def validate_all_data(self) -> List[Dict]:
        """Validate all downloaded data"""
        results = []
        
        # Validate equity data
        if os.path.exists(self.equity_path):
            for resolution in ['minute', 'hour', 'daily']:
                resolution_path = os.path.join(self.equity_path, resolution)
                if os.path.exists(resolution_path):
                    for symbol in os.listdir(resolution_path):
                        if os.path.isdir(os.path.join(resolution_path, symbol)):
                            result = self.validate_symbol_data(symbol.upper(), 'equity', resolution)
                            results.append(result)
        
        # Validate crypto data
        if os.path.exists(self.crypto_path):
            for resolution in ['minute', 'hour', 'daily']:
                resolution_path = os.path.join(self.crypto_path, resolution)
                if os.path.exists(resolution_path):
                    for symbol in os.listdir(resolution_path):
                        if os.path.isdir(os.path.join(resolution_path, symbol)):
                            result = self.validate_symbol_data(symbol.upper(), 'crypto', resolution)
                            results.append(result)
        
        return results

def main():
    """Main function for data validation"""
    validator = DataValidator()
    
    print("Validating LEAN data files...")
    results = validator.validate_all_data()
    
    # Generate report
    report = validator.generate_report(results)
    
    # Print to console
    print(report)
    
    # Save to file
    with open('data_validation_report.txt', 'w') as f:
        f.write(report)
    
    print(f"\nValidation report saved to data_validation_report.txt")

if __name__ == "__main__":
    main()
