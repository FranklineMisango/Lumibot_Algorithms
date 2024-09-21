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

from alpaca.trading.requests import MarketOrderRequest

from alpaca.trading.enums import AssetStatus,OrderSide, OrderType, TimeInForce, OrderClass, QueryOrderStatus

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

class BuyHold():

    def __init__(self):
        self.alpaca = tradeapi.REST(API_KEY, API_SECRET, APCA_API_BASE_URL, 'v2')
        self.initial_portfolio_value = 0
        self.end_of_day_portfolio_value = 0
        equity = self.alpaca.get_account().equity
        self.start_of_day_portfolio_value = float(equity)
        self.stock_initial_prices = {}
        self.monitoring_thread = threading.Thread(target=self.monitor_prices)
        self.monitoring_thread.daemon = True  # Ensure thread exits when main program exits

    def awaitMarketOpen(self):
        nyc = pytz.timezone('America/New_York')
        isOpen = self.alpaca.get_clock().is_open
        while not isOpen:
            clock = self.alpaca.get_clock()
            openingTime = clock.next_open.replace(tzinfo=datetime.timezone.utc).timestamp()
            currTime = clock.timestamp.replace(tzinfo=datetime.timezone.utc).timestamp()
            timeToOpen = int((openingTime - currTime) / 60)
            if timeToOpen == 30:
                self.send_email("Market Opening Soon", "Hey Trader, The market is opening in 30 minutes.")
            print(f"{timeToOpen} minutes till market open.")
            time.sleep(60)
            isOpen = self.alpaca.get_clock().is_open

        
        self.send_email("Market Opened", "The market has opened.")

    def get_positions_with_retries(self, retries=3, backoff_in_seconds=3):
        for i in range(retries):
            try:
                positions = self.alpaca.list_positions()
                return positions
            except 'HTTPError' as e:
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
                        {"symbol": "AAPL", "quantity": 2816},
                        {"symbol": "BAC", "quantity": 6495},
                        {"symbol": "AXP", "quantity": 840},
                        {"symbol": "KO", "quantity": 2794},
                        {"symbol": "CVX", "quantity": 929},
                        {"symbol": "OXY", "quantity": 2143},
                        {"symbol": "KHC", "quantity": 2100},
                        {"symbol": "MCO", "quantity": 123},
                        {"symbol": "CB", "quantity": 219},
                        {"symbol": "DVA", "quantity": 295},
                        {"symbol": "C", "quantity": 347},
                        {"symbol": "KR", "quantity": 319},
                        {"symbol": "SIRI", "quantity": 623},
                        {"symbol": "V", "quantity": 56},
                        {"symbol": "VRSN", "quantity": 72},
                        {"symbol": "MA", "quantity": 24},
                        {"symbol": "AMZN", "quantity": 64},
                        {"symbol": "NU", "quantity": 685},
                        {"symbol": "AON", "quantity": 29},
                        {"symbol": "COF", "quantity": 57},
                        {"symbol": "CHTR", "quantity": 22},
                        {"symbol": "ALLY", "quantity": 32},
                        {"symbol": "TMUS", "quantity": 29},
                        {"symbol": "FWONK", "quantity": 33},
                        {"symbol": "LPX", "quantity": 42},
                        {"symbol": "LLYVK", "quantity": 31},
                        {"symbol": "FND", "quantity": 16},
                        {"symbol": "ULTA", "quantity": 5},
                        {"symbol": "HEI.A", "quantity": 6},
                        {"symbol": "LLYVA", "quantity": 48},
                        {"symbol": "NVR", "quantity": 0},
                        {"symbol": "DEO", "quantity": 4},
                        {"symbol": "LEN.B", "quantity": 5},
                        {"symbol": "JEF", "quantity": 13},
                        {"symbol": "LILA", "quantity": 105},
                        {"symbol": "VOO", "quantity": 2},
                        {"symbol": "SPY", "quantity": 1},
                        {"symbol": "LILAK", "quantity": 76},
                        {"symbol": "BATRK", "quantity": 15},
                    ]
                    for stock_info in stocks_and_quantities:
                        symbol = stock_info["symbol"]
                        quantity = stock_info["quantity"]
                        req = MarketOrderRequest(
                            symbol=symbol,
                            qty=quantity,
                            side=OrderSide.BUY,
                            type=OrderType.MARKET,
                            time_in_force=TimeInForce.DAY,
                            client_order_id=None,
                        )
                        res = trade_client.submit_order(req)
                        print(f"Placed order for {quantity} shares of {symbol}.")
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
        # Sell the stock
        self.alpaca.submit_order(
            symbol=symbol,
            qty=qty,
            side='sell',
            type='market',
            time_in_force='gtc'
        )
        self.send_email("Stock Sold", f"Sold {qty} of {symbol} as it fell below 90% of its initial value.")
        
        # Identify the top-performing stock
        top_stock = self.get_top_performing_stock()
        if top_stock:
            # Calculate the quantity to purchase
            available_funds = float(self.alpaca.get_account().equity) + float(self.alpaca.get_account().buying_power)
            top_stock_price = float(self.alpaca.get_last_trade(top_stock).price)
            qty_to_buy = int(available_funds / top_stock_price)
            
            if qty_to_buy > 0:
                # Purchase the calculated quantity of the top-performing stock
                self.alpaca.submit_order(
                    symbol=top_stock,
                    qty=qty_to_buy,
                    side='buy',
                    type='market',
                    time_in_force='gtc'
                )
                self.send_email("Stock Bought", f"Bought {qty_to_buy} of {top_stock} as it is the top-performing stock.")


    def buy_more_stock(self, symbol, current_qty):
        cash = float(self.alpaca.get_account().equity)
        price = float(self.alpaca.get_last_trade(symbol).price)
        qty_to_buy = int(current_qty * 0.40)
        total_cost = qty_to_buy * price

        if total_cost <= cash:
            self.alpaca.submit_order(
                symbol=symbol,
                qty=qty_to_buy,
                side='buy',
                type='market',
                time_in_force='gtc'
            )
            self.send_email("Stock Bought", f"Bought {qty_to_buy} of {symbol} as it gained more than 10% of its initial value.")



    def get_top_performing_stock(self):
        positions = self.alpaca.list_positions()
        top_stock = None
        top_performance = -float('inf')
        
        for position in positions:
            initial_price = self.stock_initial_prices.get(position.symbol, float(position.current_price))
            current_price = float(position.current_price)
            performance = (current_price - initial_price) / initial_price
            
            if performance > top_performance:
                top_performance = performance
                top_stock = position.symbol
        
        return top_stock

    

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
        msg['From'] = 'Frankline & Co. LP Buy/Hold Day Trading Bot'
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
    if live:
        bs = BuyHold()
        bs.run()
    else:
        start = dt(2020, 1, 1)  # Convert start_date to datetime
        end = dt(2024, 8, 31)  # Convert end_date to datetime
        BuyHold.backtest(
            YahooDataBacktesting,
            start,
            end
        )