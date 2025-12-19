from flask import Flask, request, jsonify
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import re
import logging
import os
from datetime import datetime, timedelta

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/securities', methods=['GET'])
def get_securities():
    tickers = request.args.get('tickers', 'AAPL,MSFT,GOOGL').split(',')
    data = []
    for t in tickers:
        try:
            ticker = yf.Ticker(t)
            fast = ticker.fast_info
            data.append({
                'symbol': t,
                'name': t,  # fast_info does not provide name
                'exchange': fast.get('exchange', ''),
                'region': '',  # not available in fast_info
                'lastPrice': fast.get('lastPrice', None)
            })
        except Exception as e:
            data.append({'symbol': t, 'error': str(e)})
    return jsonify(data)

@app.route('/news', methods=['GET'])
def get_news():
    ticker = request.args.get('ticker', 'AAPL')
    try:
        app.logger.info(f"Fetching news for ticker: {ticker}")
        ticker_obj = yf.Ticker(ticker)
        news = ticker_obj.news
        
        if not news:
            app.logger.warning(f"No news found for ticker: {ticker}")
            return jsonify([])
        
        # Transform the news data to match our expected format
        formatted_news = []
        for item in news:
            formatted_item = {
                'Title': item.get('title', ''),
                'Publisher': item.get('publisher', ''),
                'Link': item.get('link', ''),
                'ProviderPublishTime': item.get('providerPublishTime', 0),
                'Type': item.get('type', ''),
                'Thumbnail': item.get('thumbnail', {}).get('resolutions', [{}])[0].get('url', '') if item.get('thumbnail') else '',
                'Summary': item.get('title', '')  # Use title as summary since Yahoo doesn't provide summary
            }
            formatted_news.append(formatted_item)
        
        app.logger.info(f"Successfully fetched {len(formatted_news)} news items for {ticker}")
        return jsonify(formatted_news)
        
    except Exception as e:
        app.logger.error(f"Error fetching news for {ticker}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/fundamentals', methods=['GET'])
def get_fundamentals():
    ticker = request.args.get('ticker', 'AAPL')
    try:
        app.logger.info(f"Fetching fundamentals for ticker: {ticker}")
        
        # Try multiple data sources for reliable data
        fundamentals = {}
        
        # 1. Try Alpaca API for real-time price data
        alpaca_data = get_alpaca_data(ticker)
        if alpaca_data:
            fundamentals.update(alpaca_data)
        
        # 2. Try Finviz for fundamental metrics
        finviz_data = get_finviz_data(ticker)
        if finviz_data:
            fundamentals.update(finviz_data)
        
        # 3. Use Google Search to verify and enhance data
        google_data = get_google_search_data(ticker)
        if google_data:
            fundamentals.update(google_data)
        
        # 4. Fallback to yfinance API if other sources fail
        if not fundamentals or 'currentPrice' not in fundamentals:
            app.logger.info(f"Falling back to yfinance for {ticker}")
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            
            fundamentals = {
                'symbol': ticker,
                'currentPrice': info.get('currentPrice') or info.get('regularMarketPrice'),
                'marketCap': info.get('marketCap'),
                'enterpriseValue': info.get('enterpriseValue'),
                'trailingPE': info.get('trailingPE'),
                'forwardPE': info.get('forwardPE'),
                'pegRatio': info.get('pegRatio'),
                'priceToBook': info.get('priceToBook'),
                'priceToSalesTrailing12Months': info.get('priceToSalesTrailing12Months'),
                'debtToEquity': info.get('debtToEquity'),
                'returnOnEquity': info.get('returnOnEquity'),
                'dividendYield': info.get('dividendYield'),
                'payoutRatio': info.get('payoutRatio'),
                'freeCashflow': info.get('freeCashflow'),
                'operatingCashflow': info.get('operatingCashflow'),
                'revenueGrowth': info.get('revenueGrowth'),
                'earningsGrowth': info.get('earningsGrowth'),
                'sharesOutstanding': info.get('sharesOutstanding'),
                'beta': info.get('beta'),
                'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh'),
                'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow'),
                'averageVolume': info.get('averageVolume'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'longBusinessSummary': info.get('longBusinessSummary')
            }
        
        # Ensure we have basic required fields
        if 'symbol' not in fundamentals:
            fundamentals['symbol'] = ticker
            
        app.logger.info(f"Successfully fetched fundamentals for {ticker}")
        return jsonify(fundamentals)
        
    except Exception as e:
        app.logger.error(f"Error fetching fundamentals for {ticker}: {str(e)}")
        return jsonify({'error': str(e)}), 500

def get_alpaca_data(ticker):
    """Get data from Alpaca API"""
    try:
        # Use Alpaca API credentials from environment/config
        import os
        
        # These should match the appsettings.json configuration
        api_key = "PK89MS3NBHE4VI1LU4C5"
        secret_key = "ehTvuMIqirTLJinOc4i6cjf68kcY1hQcResf5Jbh"
        base_url = "https://paper-api.alpaca.markets"
        
        headers = {
            'APCA-API-KEY-ID': api_key,
            'APCA-API-SECRET-KEY': secret_key,
            'Content-Type': 'application/json'
        }
        
        # Get current quote for the stock
        quote_url = f"{base_url}/v2/stocks/{ticker}/quotes/latest"
        
        response = requests.get(quote_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'quote' in data:
                quote = data['quote']
                
                # Basic quote data from Alpaca
                fundamentals = {
                    'symbol': ticker,
                    'currentPrice': float(quote.get('bp', 0)),  # bid price as current price
                    'source': 'alpaca'
                }
                
                app.logger.info(f"Alpaca data for {ticker}: {fundamentals}")
                return fundamentals
            else:
                app.logger.warning(f"No quote data in Alpaca response for {ticker}")
                return None
        else:
            app.logger.warning(f"Alpaca API returned {response.status_code} for {ticker}")
            return None
            
    except Exception as e:
        app.logger.error(f"Alpaca API error for {ticker}: {str(e)}")
        return None

def get_finviz_data(ticker):
    """Scrape Finviz for comprehensive fundamental data"""
    try:
        app.logger.info(f"Getting Finviz data for {ticker}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Finviz URL for stock fundamentals
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Finviz has a nice table structure with financial metrics
        fundamentals = {}
        
        # Find the snapshot table with financial metrics
        tables = soup.find_all('table', class_='snapshot-table2')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                
                # Finviz uses pairs of cells (label, value)
                for i in range(0, len(cells) - 1, 2):
                    if i + 1 < len(cells):
                        label = cells[i].text.strip()
                        value = cells[i + 1].text.strip()
                        
                        # Map Finviz labels to our standard keys
                        metric_mapping = {
                            'P/E': 'trailingPE',
                            'PEG': 'pegRatio',
                            'P/B': 'priceToBook',
                            'P/S': 'priceToSalesTrailing12Months',
                            'Debt/Eq': 'debtToEquity',
                            'ROE': 'returnOnEquity',
                            'Dividend %': 'dividendYield',
                            'Beta': 'beta',
                            'Market Cap': 'marketCap',
                            'Price': 'currentPrice',
                            'Volume': 'volume',
                            'Shs Outstand': 'sharesOutstanding',
                            'EPS': 'eps',
                            'Forward P/E': 'forwardPE',
                            'Insider Own': 'insiderOwnership',
                            'Inst Own': 'institutionalOwnership',
                            'Short Float': 'shortFloat',
                            'Target Price': 'targetPrice',
                            '52W High': 'fiftyTwoWeekHigh',
                            '52W Low': 'fiftyTwoWeekLow'
                        }
                        
                        if label in metric_mapping:
                            key = metric_mapping[label]
                            parsed_value = parse_finviz_value(value)
                            if parsed_value is not None:
                                fundamentals[key] = parsed_value
                                app.logger.info(f"Finviz - {label}: {parsed_value}")
        
        # Get sector and industry from the page
        try:
            # Look for sector/industry information
            sector_links = soup.find_all('a', href=re.compile(r'screener\.ashx.*sector='))
            if sector_links:
                fundamentals['sector'] = sector_links[0].text.strip()
            
            industry_links = soup.find_all('a', href=re.compile(r'screener\.ashx.*industry='))
            if industry_links:
                fundamentals['industry'] = industry_links[0].text.strip()
        except:
            pass
        
        return fundamentals if fundamentals else None
        
    except Exception as e:
        app.logger.error(f"Finviz scraping error for {ticker}: {str(e)}")
        return None

def parse_finviz_value(value_text):
    """Parse Finviz values into proper numbers"""
    try:
        # Handle different value formats from Finviz
        value_text = value_text.strip()
        
        # Skip invalid values
        if value_text in ['-', 'N/A', '', '--']:
            return None
        
        # Handle percentage values
        if '%' in value_text:
            return float(value_text.replace('%', '')) / 100
        
        # Handle market cap values (B = billions, M = millions)
        if 'B' in value_text:
            return float(value_text.replace('B', '')) * 1_000_000_000
        elif 'M' in value_text:
            return float(value_text.replace('M', '')) * 1_000_000
        elif 'K' in value_text:
            return float(value_text.replace('K', '')) * 1_000
        
        # Handle regular numbers
        return float(value_text.replace(',', ''))
        
    except:
        return None

def get_google_search_data(ticker):
    """Get financial data using Google Search API"""
    try:
        # Use Google Search API credentials from appsettings.json
        api_key = "AIzaSyDYJVpcewQUGMGkQkp96I7X8cPjAuzSRV0"
        search_engine_id = "81db24ee2e0554e76"
        
        # Search for financial data
        search_query = f"{ticker} stock financial data market cap P/E ratio"
        
        search_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': search_query,
            'num': 3  # Limit results
        }
        
        response = requests.get(search_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract financial data from search results
            fundamentals = {
                'symbol': ticker,
                'source': 'google_search'
            }
            
            # Look for financial data in search snippets
            if 'items' in data:
                for item in data['items']:
                    snippet = item.get('snippet', '').lower()
                    
                    # Try to extract market cap from snippets
                    import re
                    market_cap_pattern = r'market cap[:\s]*[\$]?([0-9.,]+[btmk]?)'
                    market_cap_match = re.search(market_cap_pattern, snippet, re.IGNORECASE)
                    if market_cap_match:
                        market_cap_text = market_cap_match.group(1)
                        market_cap = parse_finviz_value(market_cap_text)
                        if market_cap and market_cap > 1000000:  # Reasonable market cap
                            fundamentals['marketCap'] = market_cap
                            break
                            
                app.logger.info(f"Google Search data for {ticker}: {fundamentals}")
                return fundamentals
            else:
                app.logger.warning(f"No search results for {ticker}")
                return None
        else:
            app.logger.warning(f"Google Search API returned {response.status_code} for {ticker}")
            return None
            
    except Exception as e:
        app.logger.error(f"Google Search API error for {ticker}: {str(e)}")
        return None

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'yfinance-api'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
