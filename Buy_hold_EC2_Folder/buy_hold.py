from lumibot.brokers import Alpaca
from lumibot.strategies import Strategy
from lumibot.traders import Trader
import yfinance as yf
from datetime import datetime
from lumibot.backtesting import YahooDataBacktesting
import os
import alpaca_trade_api as tradeapi
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib
import csv
import time
import threading
from datetime import datetime as dt
from alpaca.trading.client import TradingClient
import schedule
import matplotlib.pyplot as plt
import datetime
import pytz
from datetime import timedelta

from dotenv import load_dotenv
load_dotenv()

API_KEY = os.environ.get('APCA_API_KEY_ID')
API_SECRET = os.environ.get('APCA_API_SECRET_KEY')
APCA_API_BASE_URL = "https://paper-api.alpaca.markets"
EMAIL_USER = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVER = os.environ.get('YOUR_EMAIL_ADDRESS')
paper = True

trade_api_url = None
trade_client = TradingClient(api_key=API_KEY, secret_key=API_SECRET, paper=paper, url_override=trade_api_url)

# Populate the ALPACA_CONFIG dictionary
ALPACA_CONFIG = {
    'API_KEY': os.environ.get('APCA_API_KEY_ID'),
    'API_SECRET': os.environ.get('APCA_API_SECRET_KEY'),
    'BASE_URL': os.environ.get('BASE_URL')
}

class BuyHold(Strategy):

    def __init__(self):
        self.alpaca = tradeapi.REST(API_KEY, API_SECRET, APCA_API_BASE_URL, 'v2')
        self.initial_portfolio_value = 0
        self.end_of_day_portfolio_value = 0
        self.start_of_day_portfolio_value = 0
        self.stock_initial_prices = {}
        self.monitoring_thread = threading.Thread(target=self.monitor_prices)
        self.monitoring_thread.daemon = True  # Ensure thread exits when main program exits
        self.first_iteration = True  # Define as a regular instance variable

    def awaitMarketOpen(self):
        nyc = pytz.timezone('America/New_York')
        isOpen = self.alpaca.get_clock().is_open
        while not isOpen:
            clock = self.alpaca.get_clock()
            openingTime = clock.next_open.replace(tzinfo=datetime.timezone.utc).timestamp()
            currTime = clock.timestamp.replace(tzinfo=datetime.timezone.utc).timestamp()
            timeToOpen = int((openingTime - currTime) / 60)
            print(f"{timeToOpen} minutes till market open.")
            time.sleep(60)
            isOpen = self.alpaca.get_clock().is_open
        self.send_email("Market Opened", "The market has opened.")

    def get_positions_with_retries(self, retries=3, backoff_in_seconds=3):
        for i in range(retries):
            try:
                positions = self.alpaca.list_positions()
                return positions
            except HTTPError as e:
                if i < retries - 1:
                    time.sleep(backoff_in_seconds * (2 ** i))  # Exponential backoff
                else:
                    raise e

    def monitor_prices(self):
        while True:
            try:
                positions = self.get_positions_with_retries()
                if not positions:
                    print("No positions found. Placing the first trade.")
                    stocks_and_quantities = [
                {"symbol": "AAPL", "quantity": 4224},
                {"symbol": "BAC", "quantity": 9742},
                {"symbol": "AXP", "quantity": 1261},
                {"symbol": "KO", "quantity": 4191},
                {"symbol": "CVX", "quantity": 1393},
                {"symbol": "OXY", "quantity": 3215},
                {"symbol": "KHC", "quantity": 3150},
                {"symbol": "MCO", "quantity": 185},
                {"symbol": "CB", "quantity": 328},
                {"symbol": "DVA", "quantity": 442},
                {"symbol": "C", "quantity": 521},
                {"symbol": "KR", "quantity": 479},
                {"symbol": "SIRI", "quantity": 935},
                {"symbol": "V", "quantity": 84},
                {"symbol": "VRSN", "quantity": 108},
                {"symbol": "MA", "quantity": 36},
                {"symbol": "AMZN", "quantity": 96},
                {"symbol": "NU", "quantity": 1027},
                {"symbol": "AON", "quantity": 43},
                {"symbol": "COF", "quantity": 86},
                {"symbol": "CHTR", "quantity": 33},
                {"symbol": "ALLY", "quantity": 48},
                {"symbol": "TMUS", "quantity": 44},
                {"symbol": "FWONK", "quantity": 50},
                {"symbol": "LPX", "quantity": 63},
                {"symbol": "LLYVK", "quantity": 47},
                {"symbol": "FND", "quantity": 23},
                {"symbol": "ULTA", "quantity": 8},
                {"symbol": "HEI.A", "quantity": 9},
                {"symbol": "LLYVA", "quantity": 71},
                {"symbol": "NVR", "quantity": 0},
                {"symbol": "DEO", "quantity": 6},
                {"symbol": "LEN.B", "quantity": 8},
                {"symbol": "JEF", "quantity": 20},
                {"symbol": "LILA", "quantity": 158},
                {"symbol": "VOO", "quantity": 2},
                {"symbol": "SPY", "quantity": 2},
                {"symbol": "LILAK", "quantity": 114},
                {"symbol": "BATRK", "quantity": 22},
                ]
                for stock_info in stocks_and_quantities:
                    symbol = stock_info["symbol"]
                    quantity = stock_info["quantity"]
                    price = self.get_last_price(symbol)
                    cost = price * quantity
                    if self.cash >= cost:
                        order = self.create_order(symbol, quantity, "buy")
                        self.submit_order(order)

                else:

                    for position in positions:
                        current_price = float(position.current_price)
                        initial_price = self.stock_initial_prices.get(position.symbol, current_price)
                        if current_price < 0.85 * initial_price:
                            self.sell_stock(position.symbol, position.qty)
                        elif current_price > 1.10 * initial_price:
                            self.buy_more_stock(position.symbol)
            except Exception as e:
                print(f"Error fetching positions: {e}")
            time.sleep(300)  # Check every 5 minutes

    def run(self):
        self.log_portfolio("start")
        orders = self.alpaca.list_orders(status="open")
        for order in orders:
            self.alpaca.list_orders(order.id)
        print("Waiting for market to open...")
        tAMO = threading.Thread(target=self.awaitMarketOpen)
        tAMO.start()
        tAMO.join()
        print("Market opened.")
        self.send_email("Market Opened", "The market has opened.")
        self.stock_initial_prices = self.get_initial_prices()
        
        # Start the monitoring thread
        self.monitoring_thread.start()

        while True:
            schedule.run_pending()
            time.sleep(1)

    def log_portfolio(self, time_of_day):
        positions = self.alpaca.list_positions()
        with open(f'portfolio_{time_of_day}.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Symbol", "Qty", "Side"])
            for position in positions:
                writer.writerow([position.symbol, position.qty, position.side])

    def get_portfolio_value(self):
        account = self.alpaca.get_account()
        return float(account.equity)

    def get_initial_prices(self):
        initial_prices = {}
        positions = self.alpaca.list_positions()
        for position in positions:
            initial_prices[position.symbol] = float(position.current_price)
        return initial_prices

    def sell_stock(self, symbol, qty):
        self.alpaca.submit_order(
            symbol=symbol,
            qty=qty,
            side='sell',
            type='market',
            time_in_force='gtc'
        )
        self.send_email("Stock Sold", f"Sold {qty} of {symbol} as it fell below 85% of its initial value.")

    def buy_more_stock(self, symbol):
        cash = float(self.alpaca.get_account().cash)
        price = float(self.alpaca.get_last_trade(symbol).price)
        qty = int(cash / price)
        self.alpaca.submit_order(
            symbol=symbol,
            qty=qty,
            side='buy',
            type='market',
            time_in_force='gtc'
        )
        self.send_email("Stock Bought", f"Bought {qty} of {symbol} as it gained more than 10% of its initial value.")

    def check_market_close(self):
        self.end_of_day_portfolio_value = self.get_portfolio_value()
        self.send_email("Market Closing Soon", "The market is closing in 15 minutes.")
        self.send_email("Market Closed", "The market has closed.")
        self.send_portfolio_report()

    def send_portfolio_report(self):
        times = ["Start of Day", "End of Day"]
        values = [self.start_of_day_portfolio_value, self.end_of_day_portfolio_value]
        plt.plot(times, values)
        plt.xlabel('Time of Day')
        plt.ylabel('Portfolio Value')
        plt.title('Portfolio Value Throughout the Day')
        plt.savefig('portfolio_report.png')
        self.send_email("Daily Portfolio Report", "Attached is the daily portfolio report.", 'portfolio_report.png')

    def send_email(self, subject, body, attachment=None):
        msg = MIMEMultipart()
        msg['From'] = 'Frankline & Co. LP Day Trading HFT Bot'
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        if attachment:
            with open(attachment, "rb") as file:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(file.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f"attachment; filename= {attachment}")
                msg.attach(part)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, EMAIL_RECEIVER, text)
        server.quit()

    def update_portfolio(self):
        self.log_portfolio("update")
        self.send_email("Portfolio Update", "Attached is the latest portfolio update.", f'portfolio_update.csv')

if __name__ == "__main__":
    live = True
    if live : 
        strategy = BuyHold()
        strategy.initialize()
        strategy.run()
    else:
        start = dt(2020, 1, 1)  # Convert start_date to datetime
        end = dt(2024, 8, 31)  # Convert end_date to datetime
        BuyHold.backtest(
            YahooDataBacktesting,
            start,
            end
        )