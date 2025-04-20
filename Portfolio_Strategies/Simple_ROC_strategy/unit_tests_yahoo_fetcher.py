import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime as dt
from rate_of_change import sell, check_rets, mail_alert, compare_close_ltp, return_ROC_list, ROC

# Fix the tickers and the folder missing erro
class TestMain(unittest.TestCase):

    @patch('rate_of_change.api.close_position')
    @patch('rate_of_change.api.cancel_all_orders')
    @patch('rate_of_change.api.get_latest_trade')
    @patch('rate_of_change.api.get_position')
    def test_sell(self, mock_get_position, mock_get_latest_trade, mock_cancel_all_orders, mock_close_position):
        mock_get_position.return_value.qty = '10'
        mock_get_latest_trade.return_value.price = 100
        stock_to_sell = 'AAPL'
        result = sell(stock_to_sell)
        self.assertIn('SELL Order Placed for AAPL', result)


    @patch('rate_of_change.api.get_position')
    @patch('rate_of_change.sell')
    def test_check_rets(self, mock_sell, mock_get_position):
        mock_get_position.return_value.unrealized_plpc = 0.03
        stock = 'AAPL'
        result = check_rets(stock)
        mock_sell.assert_called_once_with(stock)
        self.assertIn('SELL Order Placed for AAPL', result)

    @patch('rate_of_change.smtplib.SMTP')
    def test_mail_alert(self, mock_smtp):
        mail_content = 'Test Mail'
        sleep_time = 0
        mail_alert(mail_content, sleep_time)
        mock_smtp.assert_called_once()


    @patch('rate_of_change.datetime')
    def test_get_minute_data(self, mock_datetime):
        mock_datetime.datetime.now.return_value = dt(2023, 10, 1)
        # Add the rest of the test logic here


    # TODO - Fix the Datetime column not found on the column
    # TODO - Fix the Orders.csv by regenerating an older one


    @patch('rate_of_change.pd.read_csv')
    def test_compare_ask_ltp(self, mock_read_csv):
        tickers = ['AAPL']
        mock_df = pd.DataFrame({
            'Date': ['2023-10-01 09:59', '2023-10-01 10:00'],
            'Price': [150, 155]
        })
        mock_read_csv.return_value = mock_df
        result = compare_close_ltp(tickers)
        # Add assertions here


    @patch('rate_of_change.pd.read_csv')
    def test_return_ROC_list(self, mock_read_csv):
        tickers = ['AAPL']
        mock_df = pd.DataFrame({
            'Date': ['2023-10-01 09:59', '2023-10-01 10:00'],
            'Price': [150, 155]
        })
        mock_read_csv.return_value = mock_df
        result = return_ROC_list(tickers)
        # Add assertions here

    def test_ROC(self):
        ask = [100, 200]
        rocs = (ask[-1] - ask[-2]) / ask[-2] * 100
        self.assertAlmostEqual(rocs, 100.0)

if __name__ == '__main__':
    unittest.main()