import streamlit as st
import backtrader as bt
import matplotlib.pyplot as plt 
from langchain_core.tools import tool
from dotenv import load_dotenv
load_dotenv()

import os
from alpaca_trade_api.rest import REST, TimeFrame
import  datetime as dt
from requests.exceptions import HTTPError


@tool
def tool_sma_crossover(ticker : str, years : int , start_date : dt.datetime, end_date : dt.datetime, portfolio : int):
    '''This tool is used to backtest the SMA crossover strategy'''
      # Setting chart resolution
    plt.rcParams['figure.dpi'] = 140

    # API credentials
    API_KEY = os.environ.get('API_KEY_ALPACA')
    SECRET_KEY = os.environ.get('SECRET_KEY_ALPACA')

    # Initialize REST API
    rest_api = REST(API_KEY, SECRET_KEY, base_url='https://paper-api.alpaca.markets')

    def run_backtest(strategy, symbol, start, end, timeframe=TimeFrame.Day, cash=10000):
        print("starting backtest")
        cerebro = bt.Cerebro(stdstats=True)
        cerebro.broker.setcash(cash)
        cerebro.addstrategy(strategy)

        # Adding analyzers
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio')

        # Loading data
        start = start.strftime('%Y-%m-%d')
        end = end.strftime('%Y-%m-%d')
        data = rest_api.get_bars(symbol, timeframe, start, end, adjustment='all').df
        bt_data = bt.feeds.PandasData(dataname=data, name=symbol)
        cerebro.adddata(bt_data)

        # Running the backtest
        initial_value = cerebro.broker.getvalue()
        print(f'Starting Portfolio Value: {initial_value}')
        results = cerebro.run()
        final_value = cerebro.broker.getvalue()
        print(f'Final Portfolio Value: {round(final_value, 2)}')

        strategy_return = 100 * (final_value - initial_value) / initial_value
        print(f'Strategy Return: {round(strategy_return, 2)}%')

        # Display results
        strategy_statistics(results, initial_value, data)

        # Plotting the results
        cerebro.plot(iplot=False)

    def strategy_statistics(results, initial_value, data):
        # Analyzing the results
        strat = results[0]
        trade_analysis = strat.analyzers.trade_analyzer.get_analysis()

        # Sharpe Ratio
        sharpe_ratio = round(strat.analyzers.sharpe_ratio.get_analysis()['sharperatio'], 2)

        # Total number of trades
        total_trades = trade_analysis.total.closed

        # Win Rate
        win_rate = round((trade_analysis.won.total / total_trades) * 100, 2) if total_trades > 0 else 0

        # Average Percent Gain and Loss
        avg_percent_gain = round(trade_analysis.won.pnl.average / initial_value * 100, 2) if trade_analysis.won.total > 0 else 0
        avg_percent_loss = round(trade_analysis.lost.pnl.average / initial_value * 100, 2) if trade_analysis.lost.total > 0 else 0

        # Profit Factor
        profit_factor = round((avg_percent_gain * win_rate) / (avg_percent_loss * (1 - win_rate)), 2) if avg_percent_loss != 0 else float('inf')

        # Gain/Loss Ratio
        gain_loss_ratio = round(avg_percent_gain / -avg_percent_loss, 2) if avg_percent_loss != 0 else float('inf')

        # Max Return and Max Loss as Percentages
        max_return = round(trade_analysis.won.pnl.max / initial_value * 100, 2) if trade_analysis.won.total > 0 else 0
        max_loss = round(trade_analysis.lost.pnl.max / initial_value * 100, 2) if trade_analysis.lost.total > 0 else 0

        # Buy and Hold Return
        buy_and_hold_return = round((data['close'].iloc[-1] / data['close'].iloc[0] - 1) * 100, 2)

        # Displaying results
        print(f'Buy and Hold Return: {buy_and_hold_return}%')
        print('Sharpe Ratio:', sharpe_ratio)
        print('Total Trades:', total_trades)
        print('Win Rate (%):', win_rate)
        print('Average % Gain per Trade:', avg_percent_gain)
        print('Average % Loss per Trade:', avg_percent_loss)
        print('Profit Factor:', profit_factor)
        print('Gain/Loss Ratio:', gain_loss_ratio)
        print('Max % Return on a Trade:', max_return)
        print('Max % Loss on a Trade:', max_loss)

    # Class for SMA Crossover strategy
    class SmaCross(bt.Strategy):
        params = dict(pfast=13, pslow=25)

        # Define trading strategy
        def __init__(self):
            sma1 = bt.ind.SMA(period=self.p.pfast)
            sma2 = bt.ind.SMA(period=self.p.pslow)
            self.crossover = bt.ind.CrossOver(sma1, sma2)

            # Custom trade tracking
            self.trade_data = []

        # Execute trades
        def next(self):
            # Trading the entire portfolio
            size = int(self.broker.get_cash() / self.data.close[0])

            if not self.position:
                if self.crossover > 0:
                    self.buy(size=size)
                    self.entry_bar = len(self)  # Record entry bar index
            elif self.crossover < 0:
                self.close()

        # Record trade details
        def notify_trade(self, trade):
            if trade.isclosed:
                exit_bar = len(self)
                holding_period = exit_bar - self.entry_bar
                trade_record = {
                    'entry': self.entry_bar,
                    'exit': exit_bar,
                    'duration': holding_period,
                    'profit': trade.pnl
                }
                self.trade_data.append(trade_record)

        # Calculating holding periods
        def stop(self):
            # Calculate and print average holding periods
            total_holding = sum([trade['duration'] for trade in self.trade_data])
            total_trades = len(self.trade_data)
            avg_holding_period = round(total_holding / total_trades) if total_trades > 0 else 0

            # Calculating for winners and losers separately
            winners = [trade for trade in self.trade_data if trade['profit'] > 0]
            losers = [trade for trade in self.trade_data if trade['profit'] < 0]
            avg_winner_holding = round(sum(trade['duration'] for trade in winners) / len(winners)) if winners else 0
            avg_loser_holding = round(sum(trade['duration'] for trade in losers) / len(losers)) if losers else 0

            # Display average holding period statistics
            print('Average Holding Period:', avg_holding_period)
            print('Average Winner Holding Period:', avg_winner_holding)
            print('Average Loser Holding Period:', avg_loser_holding)

    # Run backtest
    run_backtest(SmaCross, ticker, start_date, end_date, TimeFrame.Day, portfolio)


def norm_sma_crossover(ticker, years, start_date, end_date, portfolio):
    
# Setting chart resolution
    plt.rcParams['figure.dpi'] = 140

    # API credentials
    API_KEY = os.environ.get('API_KEY_ALPACA')
    SECRET_KEY = os.environ.get('SECRET_KEY_ALPACA')

    # Initialize REST API
    rest_api = REST(API_KEY, SECRET_KEY, base_url='https://paper-api.alpaca.markets')

    def run_backtest(strategy, symbol, start, end, timeframe=TimeFrame.Day, cash=10000):
        print("starting backtest")
        cerebro = bt.Cerebro(stdstats=True)
        cerebro.broker.setcash(cash)
        cerebro.addstrategy(strategy)

        # Adding analyzers
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio')

        try:
            # Loading data
            start = start.strftime('%Y-%m-%d')
            end = end.strftime('%Y-%m-%d')
            data = rest_api.get_bars(symbol, timeframe, start, end, adjustment='all').df
            bt_data = bt.feeds.PandasData(dataname=data, name=symbol)
            cerebro.adddata(bt_data)

            # Running the backtest
            initial_value = cerebro.broker.getvalue()
            print(f'Starting Portfolio Value: {initial_value}')
            results = cerebro.run()
            final_value = cerebro.broker.getvalue()
            print(f'Final Portfolio Value: {round(final_value, 2)}')

            strategy_return = 100 * (final_value - initial_value) / initial_value
            print(f'Strategy Return: {round(strategy_return, 2)}%')

            # Display results
            strategy_statistics(results, initial_value, data)

            # Plotting the results
            cerebro.plot(iplot=False)

        except HTTPError as e:
            st.error(f"HTTPError: {e.response.status_code} Client Error: {e.response.reason} for url: {e.response.url}")
            print(f"HTTPError: {e.response.status_code} Client Error: {e.response.reason} for url: {e.response.url}")

    def strategy_statistics(results, initial_value, data):
        # Analyzing the results
        strat = results[0]
        trade_analysis = strat.analyzers.trade_analyzer.get_analysis()

        # Sharpe Ratio
        sharpe_ratio = round(strat.analyzers.sharpe_ratio.get_analysis()['sharperatio'], 2)

        # Total number of trades
        total_trades = trade_analysis.total.closed

        # Win Rate
        win_rate = round((trade_analysis.won.total / total_trades) * 100, 2) if total_trades > 0 else 0

        # Average Percent Gain and Loss
        avg_percent_gain = round(trade_analysis.won.pnl.average / initial_value * 100, 2) if trade_analysis.won.total > 0 else 0
        avg_percent_loss = round(trade_analysis.lost.pnl.average / initial_value * 100, 2) if trade_analysis.lost.total > 0 else 0

        # Profit Factor
        profit_factor = round((avg_percent_gain * win_rate) / (avg_percent_loss * (1 - win_rate)), 2) if avg_percent_loss != 0 else float('inf')

        # Gain/Loss Ratio
        gain_loss_ratio = round(avg_percent_gain / -avg_percent_loss, 2) if avg_percent_loss != 0 else float('inf')

        # Max Return and Max Loss as Percentages
        max_return = round(trade_analysis.won.pnl.max / initial_value * 100, 2) if trade_analysis.won.total > 0 else 0
        max_loss = round(trade_analysis.lost.pnl.max / initial_value * 100, 2) if trade_analysis.lost.total > 0 else 0

        # Buy and Hold Return
        buy_and_hold_return = round((data['close'].iloc[-1] / data['close'].iloc[0] - 1) * 100, 2)

        # Displaying results
        print(f'Buy and Hold Return: {buy_and_hold_return}%')
        print('Sharpe Ratio:', sharpe_ratio)
        print('Total Trades:', total_trades)
        print('Win Rate (%):', win_rate)
        print('Average % Gain per Trade:', avg_percent_gain)
        print('Average % Loss per Trade:', avg_percent_loss)
        print('Profit Factor:', profit_factor)
        print('Gain/Loss Ratio:', gain_loss_ratio)
        print('Max % Return on a Trade:', max_return)
        print('Max % Loss on a Trade:', max_loss)

    # Class for SMA Crossover strategy
    class SmaCross(bt.Strategy):
        params = dict(pfast=13, pslow=25)

        # Define trading strategy
        def __init__(self):
            sma1 = bt.ind.SMA(period=self.p.pfast)
            sma2 = bt.ind.SMA(period=self.p.pslow)
            self.crossover = bt.ind.CrossOver(sma1, sma2)

            # Custom trade tracking
            self.trade_data = []

        # Execute trades
        def next(self):
            # Trading the entire portfolio
            size = int(self.broker.get_cash() / self.data.close[0])

            if not self.position:
                if self.crossover > 0:
                    self.buy(size=size)
                    self.entry_bar = len(self)  # Record entry bar index
            elif self.crossover < 0:
                self.close()

        # Record trade details
        def notify_trade(self, trade):
            if trade.isclosed:
                exit_bar = len(self)
                holding_period = exit_bar - self.entry_bar
                trade_record = {
                    'entry': self.entry_bar,
                    'exit': exit_bar,
                    'duration': holding_period,
                    'profit': trade.pnl
                }
                self.trade_data.append(trade_record)

        # Calculating holding periods
        def stop(self):
            # Calculate and print average holding periods
            total_holding = sum([trade['duration'] for trade in self.trade_data])
            total_trades = len(self.trade_data)
            avg_holding_period = round(total_holding / total_trades) if total_trades > 0 else 0

            # Calculating for winners and losers separately
            winners = [trade for trade in self.trade_data if trade['profit'] > 0]
            losers = [trade for trade in self.trade_data if trade['profit'] < 0]
            avg_winner_holding = round(sum(trade['duration'] for trade in winners) / len(winners)) if winners else 0
            avg_loser_holding = round(sum(trade['duration'] for trade in losers) / len(losers)) if losers else 0

            # Display average holding period statistics
            print('Average Holding Period:', avg_holding_period)
            print('Average Winner Holding Period:', avg_winner_holding)
            print('Average Loser Holding Period:', avg_loser_holding)

    # Run backtest
    run_backtest(SmaCross, ticker, start_date, end_date, TimeFrame.Day, portfolio)


if __name__ == '__main__':
    norm_sma_crossover('AAPL', years= 5 , start_date= dt.datetime(2020, 1, 1), end_date= dt.datetime(2024, 1, 1), portfolio= 10000)