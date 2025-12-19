
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import time
import os
from typing import List, Dict, Optional, Any, Tuple
from tqdm import tqdm
import json

from config import (
    ALPHA_VANTAGE_API_KEY, EQUITY_DATA_PATH, CRYPTO_DATA_PATH, 
    LEAN_TIMEZONE_EQUITY, LEAN_TIME_FORMAT
)
from utils import (
    setup_logging, ensure_directory_exists, format_lean_date,
    create_lean_tradebar_csv, write_lean_zip_file, get_trading_days,
    DataValidator, static_tqdm
)

logger = setup_logging()

class AlphaVantageDownloader:
    """Enhanced Alpha Vantage downloader with comprehensive financial data support"""
    
    def __init__(self):
        if not ALPHA_VANTAGE_API_KEY:
            raise ValueError("Alpha Vantage API key not found. Please set ALPHA_VANTAGE_API_KEY environment variable.")
        
        self.api_key = ALPHA_VANTAGE_API_KEY
        self.base_url = "https://www.alphavantage.co/query"
        self.rate_limit_delay = 12  # Alpha Vantage: 5 requests per minute for free tier
        
        # Enhanced capabilities tracking
        self.supported_functions = {
            'TIME_SERIES_INTRADAY': 'Intraday OHLCV data',
            'TIME_SERIES_DAILY': 'Daily OHLCV data',
            'TIME_SERIES_WEEKLY': 'Weekly OHLCV data',
            'TIME_SERIES_MONTHLY': 'Monthly OHLCV data',
            'OVERVIEW': 'Company overview and fundamentals',
            'EARNINGS': 'Historical earnings data',
            'INCOME_STATEMENT': 'Annual and quarterly income statements',
            'BALANCE_SHEET': 'Annual and quarterly balance sheets',
            'CASH_FLOW': 'Annual and quarterly cash flow statements',
            'FX_INTRADAY': 'Intraday forex data',
            'FX_DAILY': 'Daily forex data',
            'DIGITAL_CURRENCY_INTRADAY': 'Intraday crypto data',
            'DIGITAL_CURRENCY_DAILY': 'Daily crypto data',
            'LISTING_STATUS': 'Stock listing status and exchanges'
        }
        
    def _make_request(self, params: Dict) -> Dict:
        """Make API request to Alpha Vantage"""
        params['apikey'] = self.api_key
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if 'Error Message' in data:
                logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return {}
            
            if 'Note' in data:
                logger.warning(f"Alpha Vantage API note: {data['Note']}")
                return {}
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return data
            
        except Exception as e:
            logger.error(f"Error making Alpha Vantage request: {str(e)}")
            return {}
    
    def get_stock_data(self, symbol: str, resolution: str = 'daily') -> List[Dict]:
        """Get stock data from Alpha Vantage"""
        function_map = {
            'minute': 'TIME_SERIES_INTRADAY',
            'daily': 'TIME_SERIES_DAILY',
            'weekly': 'TIME_SERIES_WEEKLY',
            'monthly': 'TIME_SERIES_MONTHLY'
        }
        
        params = {
            'function': function_map.get(resolution, 'TIME_SERIES_DAILY'),
            'symbol': symbol,
            'outputsize': 'full'
        }
        
        if resolution == 'minute':
            params['interval'] = '1min'
        
        data = self._make_request(params)
        
        if not data:
            return []
        
        # Find the time series key
        time_series_key = None
        for key in data.keys():
            if 'Time Series' in key:
                time_series_key = key
                break
        
        if not time_series_key:
            logger.error(f"No time series data found for {symbol}")
            return []
        
        time_series = data[time_series_key]
        
        # Convert to our format
        bars = []
        for timestamp_str, ohlcv in time_series.items():
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d')
            
            timestamp = timestamp.replace(tzinfo=pytz.timezone(LEAN_TIMEZONE_EQUITY))
            
            bars.append({
                'timestamp': timestamp,
                'open': float(ohlcv['1. open']),
                'high': float(ohlcv['2. high']),
                'low': float(ohlcv['3. low']),
                'close': float(ohlcv['4. close']),
                'volume': int(ohlcv['5. volume'])
            })
        
        return sorted(bars, key=lambda x: x['timestamp'])
    
    def get_forex_data(self, from_symbol: str, to_symbol: str, resolution: str = 'daily') -> List[Dict]:
        """Get forex data from Alpha Vantage"""
        function_map = {
            'minute': 'FX_INTRADAY',
            'daily': 'FX_DAILY'
        }
        
        params = {
            'function': function_map.get(resolution, 'FX_DAILY'),
            'from_symbol': from_symbol,
            'to_symbol': to_symbol,
            'outputsize': 'full'
        }
        
        if resolution == 'minute':
            params['interval'] = '1min'
        
        data = self._make_request(params)
        
        if not data:
            return []
        
        # Find the time series key
        time_series_key = None
        for key in data.keys():
            if 'Time Series' in key:
                time_series_key = key
                break
        
        if not time_series_key:
            logger.error(f"No forex data found for {from_symbol}/{to_symbol}")
            return []
        
        time_series = data[time_series_key]
        
        # Convert to our format
        bars = []
        for timestamp_str, ohlc in time_series.items():
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d')
            
            timestamp = timestamp.replace(tzinfo=pytz.timezone(LEAN_TIMEZONE_EQUITY))
            
            bars.append({
                'timestamp': timestamp,
                'open': float(ohlc['1. open']),
                'high': float(ohlc['2. high']),
                'low': float(ohlc['3. low']),
                'close': float(ohlc['4. close']),
                'volume': 0  # Forex doesn't have volume
            })
        
        return sorted(bars, key=lambda x: x['timestamp'])
    
    def get_crypto_data(self, symbol: str, market: str = 'USD', resolution: str = 'daily') -> List[Dict]:
        """Get crypto data from Alpha Vantage"""
        function_map = {
            'minute': 'CRYPTO_INTRADAY',
            'daily': 'DIGITAL_CURRENCY_DAILY'
        }
        
        params = {
            'function': function_map.get(resolution, 'DIGITAL_CURRENCY_DAILY'),
            'symbol': symbol,
            'market': market
        }
        
        if resolution == 'minute':
            params['interval'] = '1min'
        
        data = self._make_request(params)
        
        if not data:
            return []
        
        # Find the time series key
        time_series_key = None
        for key in data.keys():
            if 'Time Series' in key:
                time_series_key = key
                break
        
        if not time_series_key:
            logger.error(f"No crypto data found for {symbol}")
            return []
        
        time_series = data[time_series_key]
        
        # Convert to our format
        bars = []
        for timestamp_str, ohlcv in time_series.items():
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d')
            
            timestamp = timestamp.replace(tzinfo=pytz.timezone(LEAN_TIMEZONE_EQUITY))
            
            if resolution == 'daily':
                # Digital currency daily format
                bars.append({
                    'timestamp': timestamp,
                    'open': float(ohlcv[f'1a. open ({market})']),
                    'high': float(ohlcv[f'2a. high ({market})']),
                    'low': float(ohlcv[f'3a. low ({market})']),
                    'close': float(ohlcv[f'4a. close ({market})']),
                    'volume': float(ohlcv['5. volume'])
                })
            else:
                # Intraday format
                bars.append({
                    'timestamp': timestamp,
                    'open': float(ohlcv['1. open']),
                    'high': float(ohlcv['2. high']),
                    'low': float(ohlcv['3. low']),
                    'close': float(ohlcv['4. close']),
                    'volume': float(ohlcv['5. volume'])
                })
        
        return sorted(bars, key=lambda x: x['timestamp'])
    
    def get_commodity_data(self, commodity: str) -> List[Dict]:
        """Get commodity data from Alpha Vantage (limited support)"""
        # Alpha Vantage has limited commodity support
        commodity_functions = {
            'WTI': 'WTI',
            'BRENT': 'BRENT',
            'NATURAL_GAS': 'NATURAL_GAS'
        }
        
        if commodity not in commodity_functions:
            logger.error(f"Commodity {commodity} not supported")
            return []
        
        params = {
            'function': commodity_functions[commodity],
            'interval': 'daily'
        }
        
        data = self._make_request(params)
        
        if not data or 'data' not in data:
            return []
        
        # Convert to our format
        bars = []
        for item in data['data']:
            timestamp = datetime.strptime(item['date'], '%Y-%m-%d')
            timestamp = timestamp.replace(tzinfo=pytz.timezone(LEAN_TIMEZONE_EQUITY))
            
            bars.append({
                'timestamp': timestamp,
                'open': float(item['value']),
                'high': float(item['value']),
                'low': float(item['value']),
                'close': float(item['value']),
                'volume': 0
            })
        
        return sorted(bars, key=lambda x: x['timestamp'])
    
    def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive company overview and fundamentals"""
        params = {
            'function': 'OVERVIEW',
            'symbol': symbol
        }
        
        data = self._make_request(params)
        
        if not data or 'Symbol' not in data:
            logger.warning(f"No overview data found for {symbol}")
            return {}
        
        # Extract key fundamentals
        fundamentals = {
            'symbol': data.get('Symbol', symbol),
            'name': data.get('Name', ''),
            'description': data.get('Description', ''),
            'exchange': data.get('Exchange', ''),
            'currency': data.get('Currency', ''),
            'country': data.get('Country', ''),
            'sector': data.get('Sector', ''),
            'industry': data.get('Industry', ''),
            'market_cap': float(data.get('MarketCapitalization', 0)),
            'pe_ratio': float(data.get('PERatio', 0)) if data.get('PERatio') != 'None' else None,
            'peg_ratio': float(data.get('PEGRatio', 0)) if data.get('PEGRatio') != 'None' else None,
            'book_value': float(data.get('BookValue', 0)) if data.get('BookValue') != 'None' else None,
            'dividend_per_share': float(data.get('DividendPerShare', 0)) if data.get('DividendPerShare') != 'None' else None,
            'dividend_yield': float(data.get('DividendYield', 0)) if data.get('DividendYield') != 'None' else None,
            'eps': float(data.get('EPS', 0)) if data.get('EPS') != 'None' else None,
            'revenue_per_share_ttm': float(data.get('RevenuePerShareTTM', 0)) if data.get('RevenuePerShareTTM') != 'None' else None,
            'profit_margin': float(data.get('ProfitMargin', 0)) if data.get('ProfitMargin') != 'None' else None,
            'operating_margin_ttm': float(data.get('OperatingMarginTTM', 0)) if data.get('OperatingMarginTTM') != 'None' else None,
            'return_on_assets_ttm': float(data.get('ReturnOnAssetsTTM', 0)) if data.get('ReturnOnAssetsTTM') != 'None' else None,
            'return_on_equity_ttm': float(data.get('ReturnOnEquityTTM', 0)) if data.get('ReturnOnEquityTTM') != 'None' else None,
            'analyst_target_price': float(data.get('AnalystTargetPrice', 0)) if data.get('AnalystTargetPrice') != 'None' else None,
            '52_week_high': float(data.get('52WeekHigh', 0)) if data.get('52WeekHigh') != 'None' else None,
            '52_week_low': float(data.get('52WeekLow', 0)) if data.get('52WeekLow') != 'None' else None,
            '50_day_moving_average': float(data.get('50DayMovingAverage', 0)) if data.get('50DayMovingAverage') != 'None' else None,
            '200_day_moving_average': float(data.get('200DayMovingAverage', 0)) if data.get('200DayMovingAverage') != 'None' else None,
            'shares_outstanding': float(data.get('SharesOutstanding', 0)) if data.get('SharesOutstanding') != 'None' else None,
            'last_updated': datetime.now().isoformat()
        }
        
        return fundamentals
    
    def get_earnings_data(self, symbol: str) -> Dict[str, Any]:
        """Get historical earnings data"""
        params = {
            'function': 'EARNINGS',
            'symbol': symbol
        }
        
        data = self._make_request(params)
        
        if not data or 'quarterlyEarnings' not in data:
            logger.warning(f"No earnings data found for {symbol}")
            return {}
        
        # Process quarterly earnings
        quarterly_earnings = []
        for earning in data.get('quarterlyEarnings', []):
            quarterly_earnings.append({
                'fiscal_date_ending': earning.get('fiscalDateEnding'),
                'reported_date': earning.get('reportedDate'),
                'reported_eps': float(earning.get('reportedEPS', 0)) if earning.get('reportedEPS') != 'None' else None,
                'estimated_eps': float(earning.get('estimatedEPS', 0)) if earning.get('estimatedEPS') != 'None' else None,
                'surprise': float(earning.get('surprise', 0)) if earning.get('surprise') != 'None' else None,
                'surprise_percentage': float(earning.get('surprisePercentage', 0)) if earning.get('surprisePercentage') != 'None' else None
            })
        
        # Process annual earnings
        annual_earnings = []
        for earning in data.get('annualEarnings', []):
            annual_earnings.append({
                'fiscal_date_ending': earning.get('fiscalDateEnding'),
                'reported_eps': float(earning.get('reportedEPS', 0)) if earning.get('reportedEPS') != 'None' else None
            })
        
        return {
            'symbol': symbol,
            'quarterly_earnings': quarterly_earnings,
            'annual_earnings': annual_earnings,
            'last_updated': datetime.now().isoformat()
        }
    
    def get_income_statement(self, symbol: str) -> Dict[str, Any]:
        """Get income statement data"""
        params = {
            'function': 'INCOME_STATEMENT',
            'symbol': symbol
        }
        
        data = self._make_request(params)
        
        if not data or 'quarterlyReports' not in data:
            logger.warning(f"No income statement data found for {symbol}")
            return {}
        
        # Process quarterly reports
        quarterly_reports = []
        for report in data.get('quarterlyReports', []):
            quarterly_reports.append({
                'fiscal_date_ending': report.get('fiscalDateEnding'),
                'reported_currency': report.get('reportedCurrency'),
                'total_revenue': float(report.get('totalRevenue', 0)) if report.get('totalRevenue') != 'None' else None,
                'total_operating_expense': float(report.get('totalOperatingExpense', 0)) if report.get('totalOperatingExpense') != 'None' else None,
                'cost_of_revenue': float(report.get('costOfRevenue', 0)) if report.get('costOfRevenue') != 'None' else None,
                'gross_profit': float(report.get('grossProfit', 0)) if report.get('grossProfit') != 'None' else None,
                'ebit': float(report.get('ebit', 0)) if report.get('ebit') != 'None' else None,
                'net_income': float(report.get('netIncome', 0)) if report.get('netIncome') != 'None' else None,
                'eps': float(report.get('eps', 0)) if report.get('eps') != 'None' else None,
                'eps_diluted': float(report.get('epsdiluted', 0)) if report.get('epsdiluted') != 'None' else None,
                'operating_income': float(report.get('operatingIncome', 0)) if report.get('operatingIncome') != 'None' else None,
                'interest_expense': float(report.get('interestExpense', 0)) if report.get('interestExpense') != 'None' else None,
                'income_tax_expense': float(report.get('incomeTaxExpense', 0)) if report.get('incomeTaxExpense') != 'None' else None
            })
        
        # Process annual reports
        annual_reports = []
        for report in data.get('annualReports', []):
            annual_reports.append({
                'fiscal_date_ending': report.get('fiscalDateEnding'),
                'reported_currency': report.get('reportedCurrency'),
                'total_revenue': float(report.get('totalRevenue', 0)) if report.get('totalRevenue') != 'None' else None,
                'total_operating_expense': float(report.get('totalOperatingExpense', 0)) if report.get('totalOperatingExpense') != 'None' else None,
                'cost_of_revenue': float(report.get('costOfRevenue', 0)) if report.get('costOfRevenue') != 'None' else None,
                'gross_profit': float(report.get('grossProfit', 0)) if report.get('grossProfit') != 'None' else None,
                'ebit': float(report.get('ebit', 0)) if report.get('ebit') != 'None' else None,
                'net_income': float(report.get('netIncome', 0)) if report.get('netIncome') != 'None' else None,
                'eps': float(report.get('eps', 0)) if report.get('eps') != 'None' else None,
                'eps_diluted': float(report.get('epsdiluted', 0)) if report.get('epsdiluted') != 'None' else None,
                'operating_income': float(report.get('operatingIncome', 0)) if report.get('operatingIncome') != 'None' else None,
                'interest_expense': float(report.get('interestExpense', 0)) if report.get('interestExpense') != 'None' else None,
                'income_tax_expense': float(report.get('incomeTaxExpense', 0)) if report.get('incomeTaxExpense') != 'None' else None
            })
        
        return {
            'symbol': symbol,
            'quarterly_reports': quarterly_reports,
            'annual_reports': annual_reports,
            'last_updated': datetime.now().isoformat()
        }
    
    def get_balance_sheet(self, symbol: str) -> Dict[str, Any]:
        """Get balance sheet data"""
        params = {
            'function': 'BALANCE_SHEET',
            'symbol': symbol
        }
        
        data = self._make_request(params)
        
        if not data or 'quarterlyReports' not in data:
            logger.warning(f"No balance sheet data found for {symbol}")
            return {}
        
        # Process quarterly reports
        quarterly_reports = []
        for report in data.get('quarterlyReports', []):
            quarterly_reports.append({
                'fiscal_date_ending': report.get('fiscalDateEnding'),
                'reported_currency': report.get('reportedCurrency'),
                'total_assets': float(report.get('totalAssets', 0)) if report.get('totalAssets') != 'None' else None,
                'total_current_assets': float(report.get('totalCurrentAssets', 0)) if report.get('totalCurrentAssets') != 'None' else None,
                'cash_and_cash_equivalents': float(report.get('cashAndCashEquivalentsAtCarryingValue', 0)) if report.get('cashAndCashEquivalentsAtCarryingValue') != 'None' else None,
                'inventory': float(report.get('inventory', 0)) if report.get('inventory') != 'None' else None,
                'current_net_receivables': float(report.get('currentNetReceivables', 0)) if report.get('currentNetReceivables') != 'None' else None,
                'total_liabilities': float(report.get('totalLiabilities', 0)) if report.get('totalLiabilities') != 'None' else None,
                'total_current_liabilities': float(report.get('totalCurrentLiabilities', 0)) if report.get('totalCurrentLiabilities') != 'None' else None,
                'current_accounts_payable': float(report.get('currentAccountsPayable', 0)) if report.get('currentAccountsPayable') != 'None' else None,
                'total_shareholder_equity': float(report.get('totalShareholderEquity', 0)) if report.get('totalShareholderEquity') != 'None' else None,
                'retained_earnings': float(report.get('retainedEarnings', 0)) if report.get('retainedEarnings') != 'None' else None,
                'common_stock_shares_outstanding': float(report.get('commonStockSharesOutstanding', 0)) if report.get('commonStockSharesOutstanding') != 'None' else None
            })
        
        # Process annual reports
        annual_reports = []
        for report in data.get('annualReports', []):
            annual_reports.append({
                'fiscal_date_ending': report.get('fiscalDateEnding'),
                'reported_currency': report.get('reportedCurrency'),
                'total_assets': float(report.get('totalAssets', 0)) if report.get('totalAssets') != 'None' else None,
                'total_current_assets': float(report.get('totalCurrentAssets', 0)) if report.get('totalCurrentAssets') != 'None' else None,
                'cash_and_cash_equivalents': float(report.get('cashAndCashEquivalentsAtCarryingValue', 0)) if report.get('cashAndCashEquivalentsAtCarryingValue') != 'None' else None,
                'inventory': float(report.get('inventory', 0)) if report.get('inventory') != 'None' else None,
                'current_net_receivables': float(report.get('currentNetReceivables', 0)) if report.get('currentNetReceivables') != 'None' else None,
                'total_liabilities': float(report.get('totalLiabilities', 0)) if report.get('totalLiabilities') != 'None' else None,
                'total_current_liabilities': float(report.get('totalCurrentLiabilities', 0)) if report.get('totalCurrentLiabilities') != 'None' else None,
                'current_accounts_payable': float(report.get('currentAccountsPayable', 0)) if report.get('currentAccountsPayable') != 'None' else None,
                'total_shareholder_equity': float(report.get('totalShareholderEquity', 0)) if report.get('totalShareholderEquity') != 'None' else None,
                'retained_earnings': float(report.get('retainedEarnings', 0)) if report.get('retainedEarnings') != 'None' else None,
                'common_stock_shares_outstanding': float(report.get('commonStockSharesOutstanding', 0)) if report.get('commonStockSharesOutstanding') != 'None' else None
            })
        
        return {
            'symbol': symbol,
            'quarterly_reports': quarterly_reports,
            'annual_reports': annual_reports,
            'last_updated': datetime.now().isoformat()
        }
    
    def get_cash_flow(self, symbol: str) -> Dict[str, Any]:
        """Get cash flow statement data"""
        params = {
            'function': 'CASH_FLOW',
            'symbol': symbol
        }
        
        data = self._make_request(params)
        
        if not data or 'quarterlyReports' not in data:
            logger.warning(f"No cash flow data found for {symbol}")
            return {}
        
        # Process quarterly reports
        quarterly_reports = []
        for report in data.get('quarterlyReports', []):
            quarterly_reports.append({
                'fiscal_date_ending': report.get('fiscalDateEnding'),
                'reported_currency': report.get('reportedCurrency'),
                'operating_cashflow': float(report.get('operatingCashflow', 0)) if report.get('operatingCashflow') != 'None' else None,
                'payments_for_operating_activities': float(report.get('paymentsForOperatingActivities', 0)) if report.get('paymentsForOperatingActivities') != 'None' else None,
                'proceeds_from_operating_activities': float(report.get('proceedsFromOperatingActivities', 0)) if report.get('proceedsFromOperatingActivities') != 'None' else None,
                'change_in_operating_liabilities': float(report.get('changeInOperatingLiabilities', 0)) if report.get('changeInOperatingLiabilities') != 'None' else None,
                'change_in_operating_assets': float(report.get('changeInOperatingAssets', 0)) if report.get('changeInOperatingAssets') != 'None' else None,
                'depreciation_depletion_and_amortization': float(report.get('depreciationDepletionAndAmortization', 0)) if report.get('depreciationDepletionAndAmortization') != 'None' else None,
                'capital_expenditures': float(report.get('capitalExpenditures', 0)) if report.get('capitalExpenditures') != 'None' else None,
                'change_in_receivables': float(report.get('changeInReceivables', 0)) if report.get('changeInReceivables') != 'None' else None,
                'change_in_inventory': float(report.get('changeInInventory', 0)) if report.get('changeInInventory') != 'None' else None,
                'profit_loss': float(report.get('profitLoss', 0)) if report.get('profitLoss') != 'None' else None,
                'cashflow_from_investment': float(report.get('cashflowFromInvestment', 0)) if report.get('cashflowFromInvestment') != 'None' else None,
                'cashflow_from_financing': float(report.get('cashflowFromFinancing', 0)) if report.get('cashflowFromFinancing') != 'None' else None,
                'proceeds_from_repayments_of_short_term_debt': float(report.get('proceedsFromRepaymentsOfShortTermDebt', 0)) if report.get('proceedsFromRepaymentsOfShortTermDebt') != 'None' else None,
                'payments_for_repurchase_of_common_stock': float(report.get('paymentsForRepurchaseOfCommonStock', 0)) if report.get('paymentsForRepurchaseOfCommonStock') != 'None' else None,
                'payments_for_repurchase_of_equity': float(report.get('paymentsForRepurchaseOfEquity', 0)) if report.get('paymentsForRepurchaseOfEquity') != 'None' else None,
                'payments_for_repurchase_of_preferred_stock': float(report.get('paymentsForRepurchaseOfPreferredStock', 0)) if report.get('paymentsForRepurchaseOfPreferredStock') != 'None' else None,
                'dividend_payout': float(report.get('dividendPayout', 0)) if report.get('dividendPayout') != 'None' else None,
                'dividend_payout_common_stock': float(report.get('dividendPayoutCommonStock', 0)) if report.get('dividendPayoutCommonStock') != 'None' else None,
                'dividend_payout_preferred_stock': float(report.get('dividendPayoutPreferredStock', 0)) if report.get('dividendPayoutPreferredStock') != 'None' else None,
                'proceeds_from_issuance_of_common_stock': float(report.get('proceedsFromIssuanceOfCommonStock', 0)) if report.get('proceedsFromIssuanceOfCommonStock') != 'None' else None,
                'proceeds_from_issuance_of_long_term_debt_and_capital_securities_net': float(report.get('proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet', 0)) if report.get('proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet') != 'None' else None,
                'proceeds_from_issuance_of_preferred_stock': float(report.get('proceedsFromIssuanceOfPreferredStock', 0)) if report.get('proceedsFromIssuanceOfPreferredStock') != 'None' else None,
                'proceeds_from_repurchase_of_equity': float(report.get('proceedsFromRepurchaseOfEquity', 0)) if report.get('proceedsFromRepurchaseOfEquity') != 'None' else None,
                'change_in_cash_and_cash_equivalents': float(report.get('changeInCashAndCashEquivalents', 0)) if report.get('changeInCashAndCashEquivalents') != 'None' else None,
                'change_in_exchange_rate': float(report.get('changeInExchangeRate', 0)) if report.get('changeInExchangeRate') != 'None' else None,
                'net_income': float(report.get('netIncome', 0)) if report.get('netIncome') != 'None' else None
            })
        
        # Process annual reports
        annual_reports = []
        for report in data.get('annualReports', []):
            annual_reports.append({
                'fiscal_date_ending': report.get('fiscalDateEnding'),
                'reported_currency': report.get('reportedCurrency'),
                'operating_cashflow': float(report.get('operatingCashflow', 0)) if report.get('operatingCashflow') != 'None' else None,
                'payments_for_operating_activities': float(report.get('paymentsForOperatingActivities', 0)) if report.get('paymentsForOperatingActivities') != 'None' else None,
                'proceeds_from_operating_activities': float(report.get('proceedsFromOperatingActivities', 0)) if report.get('proceedsFromOperatingActivities') != 'None' else None,
                'change_in_operating_liabilities': float(report.get('changeInOperatingLiabilities', 0)) if report.get('changeInOperatingLiabilities') != 'None' else None,
                'change_in_operating_assets': float(report.get('changeInOperatingAssets', 0)) if report.get('changeInOperatingAssets') != 'None' else None,
                'depreciation_depletion_and_amortization': float(report.get('depreciationDepletionAndAmortization', 0)) if report.get('depreciationDepletionAndAmortization') != 'None' else None,
                'capital_expenditures': float(report.get('capitalExpenditures', 0)) if report.get('capitalExpenditures') != 'None' else None,
                'change_in_receivables': float(report.get('changeInReceivables', 0)) if report.get('changeInReceivables') != 'None' else None,
                'change_in_inventory': float(report.get('changeInInventory', 0)) if report.get('changeInInventory') != 'None' else None,
                'profit_loss': float(report.get('profitLoss', 0)) if report.get('profitLoss') != 'None' else None,
                'cashflow_from_investment': float(report.get('cashflowFromInvestment', 0)) if report.get('cashflowFromInvestment') != 'None' else None,
                'cashflow_from_financing': float(report.get('cashflowFromFinancing', 0)) if report.get('cashflowFromFinancing') != 'None' else None,
                'proceeds_from_repayments_of_short_term_debt': float(report.get('proceedsFromRepaymentsOfShortTermDebt', 0)) if report.get('proceedsFromRepaymentsOfShortTermDebt') != 'None' else None,
                'payments_for_repurchase_of_common_stock': float(report.get('paymentsForRepurchaseOfCommonStock', 0)) if report.get('paymentsForRepurchaseOfCommonStock') != 'None' else None,
                'payments_for_repurchase_of_equity': float(report.get('paymentsForRepurchaseOfEquity', 0)) if report.get('paymentsForRepurchaseOfEquity') != 'None' else None,
                'payments_for_repurchase_of_preferred_stock': float(report.get('paymentsForRepurchaseOfPreferredStock', 0)) if report.get('paymentsForRepurchaseOfPreferredStock') != 'None' else None,
                'dividend_payout': float(report.get('dividendPayout', 0)) if report.get('dividendPayout') != 'None' else None,
                'dividend_payout_common_stock': float(report.get('dividendPayoutCommonStock', 0)) if report.get('dividendPayoutCommonStock') != 'None' else None,
                'dividend_payout_preferred_stock': float(report.get('dividendPayoutPreferredStock', 0)) if report.get('dividendPayoutPreferredStock') != 'None' else None,
                'proceeds_from_issuance_of_common_stock': float(report.get('proceedsFromIssuanceOfCommonStock', 0)) if report.get('proceedsFromIssuanceOfCommonStock') != 'None' else None,
                'proceeds_from_issuance_of_long_term_debt_and_capital_securities_net': float(report.get('proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet', 0)) if report.get('proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet') != 'None' else None,
                'proceeds_from_issuance_of_preferred_stock': float(report.get('proceedsFromIssuanceOfPreferredStock', 0)) if report.get('proceedsFromIssuanceOfPreferredStock') != 'None' else None,
                'proceeds_from_repurchase_of_equity': float(report.get('proceedsFromRepurchaseOfEquity', 0)) if report.get('proceedsFromRepurchaseOfEquity') != 'None' else None,
                'change_in_cash_and_cash_equivalents': float(report.get('changeInCashAndCashEquivalents', 0)) if report.get('changeInCashAndCashEquivalents') != 'None' else None,
                'change_in_exchange_rate': float(report.get('changeInExchangeRate', 0)) if report.get('changeInExchangeRate') != 'None' else None,
                'net_income': float(report.get('netIncome', 0)) if report.get('netIncome') != 'None' else None
            })
        
        return {
            'symbol': symbol,
            'quarterly_reports': quarterly_reports,
            'annual_reports': annual_reports,
            'last_updated': datetime.now().isoformat()
        }
    
    def get_listing_status(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get stock listing status and exchange information"""
        params = {
            'function': 'LISTING_STATUS'
        }
        
        if symbol:
            params['symbol'] = symbol
        
        data = self._make_request(params)
        
        if not data or 'data' not in data:
            logger.warning("No listing status data found")
            return []
        
        listings = []
        for item in data.get('data', []):
            listings.append({
                'symbol': item.get('symbol'),
                'name': item.get('name'),
                'exchange': item.get('exchange'),
                'asset_type': item.get('assetType'),
                'ipo_date': item.get('ipoDate'),
                'delisting_date': item.get('delistingDate'),
                'status': item.get('status')
            })
        
        return listings
    
    def download_stock_symbols(self, symbols: List[str], resolution: str, start_date: datetime, end_date: datetime):
        """Download stock data for multiple symbols"""
        logger.info(f"Starting Alpha Vantage stock download for {len(symbols)} symbols")
        
        for symbol in static_tqdm(symbols, desc="Downloading stocks"):
            try:
                data = self.get_stock_data(symbol, resolution)
                
                if data:
                    # Filter by date range
                    filtered_data = [
                        bar for bar in data 
                        if start_date <= bar['timestamp'].replace(tzinfo=None) <= end_date
                    ]
                    
                    if filtered_data:
                        # Clean and validate data
                        cleaned_data = DataValidator.clean_ohlcv_data(filtered_data)
                        
                        if cleaned_data:
                            # Create directory structure
                            data_path = os.path.join(EQUITY_DATA_PATH, 'alphavantage', resolution)
                            ensure_directory_exists(data_path)
                            
                            # Save data
                            output_path = os.path.join(data_path, f"{symbol.lower()}.zip")
                            csv_filename = f"{symbol.lower()}_{resolution}_trade.csv"
                            
                            csv_content = create_lean_tradebar_csv(cleaned_data, symbol, cleaned_data[0]['timestamp'], resolution)
                            
                            if csv_content:
                                write_lean_zip_file(csv_content, output_path, csv_filename)
                                logger.info(f"Saved {len(csv_content)} bars for {symbol}")
                
            except Exception as e:
                logger.error(f"Error downloading {symbol}: {str(e)}")
                continue
    
    def download_forex_pairs(self, pairs: List[tuple], resolution: str, start_date: datetime, end_date: datetime):
        """Download forex data for multiple currency pairs"""
        logger.info(f"Starting Alpha Vantage forex download for {len(pairs)} pairs")
        
        for from_symbol, to_symbol in static_tqdm(pairs, desc="Downloading forex"):
            try:
                data = self.get_forex_data(from_symbol, to_symbol, resolution)
                
                if data:
                    # Filter by date range
                    filtered_data = [
                        bar for bar in data 
                        if start_date <= bar['timestamp'].replace(tzinfo=None) <= end_date
                    ]
                    
                    if filtered_data:
                        # Clean and validate data
                        cleaned_data = DataValidator.clean_ohlcv_data(filtered_data)
                        
                        if cleaned_data:
                            # Create directory structure
                            data_path = os.path.join(EQUITY_DATA_PATH, 'forex', 'alphavantage', resolution)
                            ensure_directory_exists(data_path)
                            
                            # Save data
                            pair_symbol = f"{from_symbol}{to_symbol}"
                            output_path = os.path.join(data_path, f"{pair_symbol.lower()}.zip")
                            csv_filename = f"{pair_symbol.lower()}_{resolution}_trade.csv"
                            
                            csv_content = create_lean_tradebar_csv(cleaned_data, pair_symbol, cleaned_data[0]['timestamp'], resolution)
                            
                            if csv_content:
                                write_lean_zip_file(csv_content, output_path, csv_filename)
                                logger.info(f"Saved {len(csv_content)} bars for {pair_symbol}")
                
            except Exception as e:
                logger.error(f"Error downloading {from_symbol}/{to_symbol}: {str(e)}")
                continue
    
    def download_crypto_symbols(self, symbols: List[str], start_date: datetime, end_date: datetime, resolution: str = 'daily'):
        """Download crypto data for multiple symbols (orchestrator-compatible method)"""
        logger.info(f"Starting Alpha Vantage crypto download for {len(symbols)} symbols")
        
        for symbol in static_tqdm(symbols, desc="Downloading crypto"):
            try:
                data = self.get_crypto_data(symbol, 'USD', resolution)
                
                if data:
                    # Filter by date range
                    filtered_data = [
                        bar for bar in data 
                        if start_date <= bar['timestamp'].replace(tzinfo=None) <= end_date
                    ]
                    
                    if filtered_data:
                        # Clean and validate data
                        cleaned_data = DataValidator.clean_ohlcv_data(filtered_data)
                        
                        if cleaned_data:
                            # Create directory structure
                            data_path = os.path.join(CRYPTO_DATA_PATH, 'alphavantage', resolution)
                            ensure_directory_exists(data_path)
                            
                            # Save data
                            output_path = os.path.join(data_path, f"{symbol.lower()}.zip")
                            csv_filename = f"{symbol.lower()}_{resolution}_trade.csv"
                            
                            csv_content = create_lean_tradebar_csv(cleaned_data, symbol, cleaned_data[0]['timestamp'], resolution)
                            
                            if csv_content:
                                write_lean_zip_file(csv_content, output_path, csv_filename)
                                logger.info(f"Saved {len(csv_content)} bars for {symbol}")
                
            except Exception as e:
                logger.error(f"Error downloading {symbol}: {str(e)}")
                continue

    def download_comprehensive_stock_data(self, symbols: List[str], start_date: datetime, 
                                        end_date: datetime, include_fundamentals: bool = True,
                                        include_financials: bool = True) -> Dict[str, Any]:
        """
        Download comprehensive stock data including OHLCV, fundamentals, and financial statements
        
        Args:
            symbols: List of stock symbols
            start_date: Start date for data
            end_date: End date for data
            include_fundamentals: Whether to include company fundamentals
            include_financials: Whether to include financial statements
            
        Returns:
            Dictionary with download results and quality scores
        """
        logger.info(f"Starting comprehensive Alpha Vantage download for {len(symbols)} symbols")
        
        results = {
            'ohlcv_data': {},
            'fundamentals': {},
            'earnings': {},
            'financial_statements': {},
            'summary': {'total_symbols': len(symbols), 'successful_downloads': 0}
        }
        
        for symbol in static_tqdm(symbols, desc="Downloading comprehensive data"):
            try:
                symbol_results = {'symbol': symbol, 'downloads': [], 'quality_score': None}
                
                # 1. Download OHLCV data
                ohlcv_data = self.get_stock_data(symbol, 'daily')
                if ohlcv_data:
                    # Filter by date range
                    filtered_data = [
                        bar for bar in ohlcv_data 
                        if start_date <= bar['timestamp'].replace(tzinfo=None) <= end_date
                    ]
                    
                    if filtered_data:
                        results['ohlcv_data'][symbol] = filtered_data
                        symbol_results['downloads'].append('ohlcv')
                        
                        # Save OHLCV data
                        cleaned_data = DataValidator.clean_ohlcv_data(filtered_data)
                        if cleaned_data:
                            data_path = os.path.join(EQUITY_DATA_PATH, 'alphavantage', 'daily')
                            ensure_directory_exists(data_path)
                            output_path = os.path.join(data_path, f"{symbol.lower()}.zip")
                            csv_filename = f"{symbol.lower()}_daily_trade.csv"
                            csv_content = create_lean_tradebar_csv(cleaned_data, symbol, cleaned_data[0]['timestamp'], 'daily')
                            if csv_content:
                                write_lean_zip_file(csv_content, output_path, csv_filename)
                
                # 2. Download fundamentals if requested
                if include_fundamentals:
                    fundamentals = self.get_company_overview(symbol)
                    if fundamentals:
                        results['fundamentals'][symbol] = fundamentals
                        symbol_results['downloads'].append('fundamentals')
                        
                        # Save fundamentals to JSON
                        fundamentals_path = os.path.join(EQUITY_DATA_PATH, 'alphavantage', 'fundamentals')
                        ensure_directory_exists(fundamentals_path)
                        with open(os.path.join(fundamentals_path, f"{symbol.lower()}_fundamentals.json"), 'w') as f:
                            json.dump(fundamentals, f, indent=2)
                
                # 3. Download earnings data if requested
                if include_fundamentals:
                    earnings = self.get_earnings_data(symbol)
                    if earnings:
                        results['earnings'][symbol] = earnings
                        symbol_results['downloads'].append('earnings')
                        
                        # Save earnings to JSON
                        earnings_path = os.path.join(EQUITY_DATA_PATH, 'alphavantage', 'earnings')
                        ensure_directory_exists(earnings_path)
                        with open(os.path.join(earnings_path, f"{symbol.lower()}_earnings.json"), 'w') as f:
                            json.dump(earnings, f, indent=2)
                
                # 4. Download financial statements if requested
                if include_financials:
                    financials = {
                        'income_statement': self.get_income_statement(symbol),
                        'balance_sheet': self.get_balance_sheet(symbol),
                        'cash_flow': self.get_cash_flow(symbol)
                    }
                    
                    if any(financials.values()):
                        results['financial_statements'][symbol] = financials
                        symbol_results['downloads'].append('financials')
                        
                        # Save financial statements to JSON
                        financials_path = os.path.join(EQUITY_DATA_PATH, 'alphavantage', 'financials')
                        ensure_directory_exists(financials_path)
                        with open(os.path.join(financials_path, f"{symbol.lower()}_financials.json"), 'w') as f:
                            json.dump(financials, f, indent=2)
                
                if symbol_results['downloads']:
                    results['summary']['successful_downloads'] += 1
                    logger.info(f"SUCCESS: {symbol}: Downloaded {', '.join(symbol_results['downloads'])}")
                else:
                    logger.warning(f"ERROR: {symbol}: No data downloaded")
                
            except Exception as e:
                logger.error(f"Error downloading comprehensive data for {symbol}: {str(e)}")
                continue
        
        # Generate summary report
        results['summary']['completion_rate'] = results['summary']['successful_downloads'] / results['summary']['total_symbols']
        
        logger.info(f"Comprehensive download completed: {results['summary']['successful_downloads']}/{results['summary']['total_symbols']} symbols")
        
        return results
    
    def get_supported_functions(self) -> Dict[str, str]:
        """Get list of supported Alpha Vantage functions"""
        return self.supported_functions.copy()
    
    def get_data_quality_report(self, symbol: str, asset_type: str = 'stocks') -> Optional[Dict[str, Any]]:
        """Get data quality report for a specific symbol"""
        # Try to get recent OHLCV data for quality assessment
        try:
            if asset_type == 'stocks':
                data = self.get_stock_data(symbol, 'daily')
            elif asset_type == 'crypto':
                data = self.get_crypto_data(symbol, 'USD', 'daily')
            elif asset_type == 'forex':
                data = self.get_forex_data(symbol.split('/')[0], symbol.split('/')[1], 'daily')
            else:
                return None
            
            if data:
                df_data = pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Error generating quality report for {symbol}: {str(e)}")
        
        return None

def main():
    """Main function for testing"""
    downloader = AlphaVantageDownloader()
    
    # Test with a small set of symbols
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']
    test_start = datetime.now() - timedelta(days=30)
    test_end = datetime.now()
    
    # Test comprehensive download
    print("Testing comprehensive download...")
    results = downloader.download_comprehensive_stock_data(
        test_symbols, test_start, test_end, 
        include_fundamentals=True, include_financials=True
    )
    
    print(f"Results: {results['summary']}")
    
    # Test individual functions
    print("\nTesting individual functions...")
    
    # Test company overview
    overview = downloader.get_company_overview('AAPL')
    if overview:
        print(f"AAPL Overview: {overview.get('name', 'N/A')} - Market Cap: {overview.get('market_cap', 'N/A')}")
    
    # Test earnings
    earnings = downloader.get_earnings_data('AAPL')
    if earnings and earnings.get('quarterly_earnings'):
        latest_earnings = earnings['quarterly_earnings'][0]
        print(f"AAPL Latest EPS: {latest_earnings.get('reported_eps', 'N/A')}")
    
    # Test quality assessment
    quality_report = downloader.get_data_quality_report('AAPL', 'stocks')
    if quality_report:
        print(f"AAPL Quality Score: {quality_report.get('overall_score', 'N/A'):.1f}")

if __name__ == "__main__":
    main()