import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime as dt, timedelta
from pytz import timezone


# Function to read and parse tickers from file
def read_tickers_from_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    tickers = content.split()
    return tickers

# Mock data for testing
#mock_tickers = read_tickers_from_file('Tickers/all_tickers.txt')
mock_tickers = ['AAPL', 'GOOGL', 'AMZN', 'MSFT', 'TSLA', 'FB', 'NVDA', 'INTC', 'AMD', 'QCOM']
mock_minute_data = {
    ticker: pd.DataFrame({
        'timestamp': [(dt.now() - timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M') for i in range(2)],
        'ask_price': [150.0 + i for i in range(2)],
        'price': [149.0 + i for i in range(2)]
    }) for ticker in mock_tickers
}
mock_past30_data = {
    ticker: pd.DataFrame({
        'timestamp': [(dt.now() - timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M') for i in range(30)],
        'ask_price': [150.0 + i for i in range(30)],
        'price': [149.0 + i for i in range(30)]
    }) for ticker in mock_tickers
}

class TestTradingBot(unittest.TestCase):

    @patch('AlpacafetchMain.api')
    @patch('AlpacafetchMain.get_minute_data')
    @patch('AlpacafetchMain.get_past30_data')
    @patch('AlpacafetchMain.mail_alert')
    def test_simulate_trading_day(self, mock_mail_alert, mock_get_past30_data, mock_get_minute_data, mock_api):
        # Mock the Alpaca API responses
        mock_api.get_account.return_value.cash = '10000'
        mock_api.get_latest_trade.return_value.price = 150.0
        mock_api.get_clock.return_value.is_open = True
        mock_api.get_position.return_value.qty = '10'
        mock_api.get_position.return_value.unrealized_plpc = '0.02'
        mock_api.list_positions.return_value = []
        mock_api.get_activities.return_value = [{'order_status': 'filled'}]

        # Mock the data fetching functions
        mock_get_minute_data.side_effect = lambda tickers: [mock_minute_data[ticker] for ticker in tickers]
        mock_get_past30_data.side_effect = lambda tickers: [mock_past30_data[ticker] for ticker in tickers]

        # Debug prints
        print("Mocking data fetching functions")
        print(f"Mock tickers: {mock_tickers}")

        # Run the main function to simulate a trading day
        from AlpacafetchMain import main
        main()

        # Assertions to verify the behavior
        print("Verifying assertions")
        mock_get_minute_data.assert_called_with(mock_tickers)
        mock_get_past30_data.assert_called_with(mock_tickers)
        mock_api.submit_order.assert_called()
        mock_api.cancel_all_orders.assert_called()
        mock_api.close_position.assert_called()
        mock_mail_alert.assert_called()

    @patch('AlpacafetchMain.api')
    def test_buy_function(self, mock_api):
        from AlpacafetchMain import buy

        # Mock the Alpaca API responses
        mock_api.get_account.return_value.cash = '10000'
        mock_api.get_latest_trade.return_value.price = 150.0

        # Call the buy function
        mail_content = buy('AAPL')

        # Assertions to verify the behavior
        mock_api.submit_order.assert_called_with(
            symbol='AAPL',
            qty=66.66666666666667,
            side='buy',
            type='market',
            time_in_force='day'
        )
        self.assertIn('BUY Order Placed for AAPL', mail_content)

    @patch('AlpacafetchMain.api')
    def test_sell_function(self, mock_api):
        from AlpacafetchMain import sell

        # Mock the Alpaca API responses
        mock_api.get_position.return_value.qty = '10'
        mock_api.get_latest_trade.return_value.price = 150.0

        # Call the sell function
        mail_content = sell('AAPL')

        # Assertions to verify the behavior
        mock_api.cancel_all_orders.assert_called()
        mock_api.close_position.assert_called_with('AAPL')
        self.assertIn('SELL Order Placed for AAPL', mail_content)

    @patch('AlpacafetchMain.api')
    def test_check_rets_function(self, mock_api):
        from AlpacafetchMain import check_rets

        # Mock the Alpaca API responses
        mock_api.get_position.return_value.unrealized_plpc = '0.02'

        # Call the check_rets function
        mail_content = check_rets('AAPL')

        # Assertions to verify the behavior
        self.assertNotEqual(mail_content, 0)

if __name__ == '__main__':
    unittest.main()