import argparse
import alpaca_trade_api as tradeapi
from config import ALPACA_KEY, ALPACA_SECRET_KEY, APCA_API_BASE_URL

API_KEY = ALPACA_KEY
SECRET_KEY = ALPACA_SECRET_KEY
BASE_URL = APCA_API_BASE_URL

api = tradeapi.REST(API_KEY, SECRET_KEY, base_url=BASE_URL)

class TradingBot:
    def __init__(self):
        self.running = True

    def start(self):
        print("Trading bot started. Enter commands or 'exit' to quit.")
        while self.running:
            command = input("Enter a command: ")
            if command.lower() == 'exit':
                self.running = False
            elif command.startswith('!buy'):
                self.handle_buy_command(command)
            elif command.startswith('!sell'):
                self.handle_sell_command(command)
            else:
                print("Invalid command. Available commands: !buy, !sell, exit")

    def handle_buy_command(self, command):
        _, symbol, quantity = command.split()
        try:
            response = self.buy_stock(symbol, int(quantity))
            print(response)
        except Exception as e:
            print(f'Error occurred while buying {symbol}: {str(e)}')

    def handle_sell_command(self, command):
        _, symbol, quantity = command.split()
        try:
            response = self.sell_stock(symbol, int(quantity))
            print(response)
        except Exception as e:
            print(f'Error occurred while selling {symbol}: {str(e)}')

    def buy_stock(self, symbol, quantity):
        try:
            api.submit_order(
                symbol=symbol,
                qty=quantity,
                side='buy',
                type='market',
                time_in_force='gtc'
            )
            return f'Bought {quantity} shares of {symbol}'
        except Exception as e:
            return f'Error occurred while buying {symbol}: {str(e)}'

    def sell_stock(self, symbol, quantity):
        try:
            api.submit_order(
                symbol=symbol,
                qty=quantity,
                side='sell',
                type='market',
                time_in_force='gtc'
            )
            return f'Sold {quantity} shares of {symbol}'
        except Exception as e:
            return f'Error occurred while selling {symbol}: {str(e)}'

if __name__ == '__main__':
    bot = TradingBot()
    bot.start()
