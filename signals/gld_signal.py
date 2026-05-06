import pandas as pd
import yfinance as yf
import numpy as np
import plotly.graph_objects as go
from yahoofinancials import YahooFinancials

def gld_signal(ticker_list, start_date, end_date):
    for ticker_input in ticker_list:
        data = yf.download(ticker_input, start_date, end_date)
        print(data)
        if 'Close' not in data.columns.get_level_values(0):
            print(f"Error: 'Close' column not found for {ticker_input}. Skipping this ticker.")
            continue
        
        gld = pd.DataFrame(data['Close'])
        gld['9-day'] = gld['Close'].rolling(9).mean()
        gld['21-day'] = gld['Close'].rolling(21).mean()
        gld['Signal'] = np.where(np.logical_and(gld['9-day'] > gld['21-day'],
                                gld['9-day'].shift(1) < gld['21-day'].shift(1)),
                                "BUY", None)
        gld['Signal'] = np.where(np.logical_and(gld['9-day'] < gld['21-day'],
                                gld['9-day'].shift(1) > gld['21-day'].shift(1)),
                                "SELL", gld['Signal'])

        def signal(df, start=start_date, end=end_date):
            df = pd.DataFrame(yf.download(ticker_input, start, end)['Close'])
            df['9-day'] = df['Close'].rolling(9).mean()
            df['21-day'] = df['Close'].rolling(21).mean()
            df['Signal'] = np.where(np.logical_and(df['9-day'] > df['21-day'],
                                    df['9-day'].shift(1) < df['21-day'].shift(1)),
                                    "BUY", None)
            df['Signal'] = np.where(np.logical_and(df['9-day'] < df['21-day'],
                                    df['9-day'].shift(1) > df['21-day'].shift(1)),
                                    "SELL", df['Signal'])
            return df, df.iloc[-1].Signal

        def plot_signals(df):
            fig = go.Figure()

            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close Price'))
            fig.add_trace(go.Scatter(x=df.index, y=df['9-day'], mode='lines', name='9-day MA'))
            fig.add_trace(go.Scatter(x=df.index, y=df['21-day'], mode='lines', name='21-day MA'))

            buy_signals = df[df['Signal'] == 'BUY']
            sell_signals = df[df['Signal'] == 'SELL']

            fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Close'], mode='markers', name='BUY Signal', marker=dict(color='green', size=10, symbol='triangle-up')))
            fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['Close'], mode='markers', name='SELL Signal', marker=dict(color='red', size=10, symbol='triangle-down')))

            fig.update_layout(title=f'{ticker_input} Trading Signals', xaxis_title='Date', yaxis_title='Price')
            fig.show()

        def backtest(df):
            initial_balance = 10000
            balance = initial_balance
            position = 0
            for i in range(1, len(df)):
                if df['Signal'].iloc[i] == 'BUY' and position == 0:
                    position = balance / df['Close'].iloc[i]
                    balance = 0
                elif df['Signal'].iloc[i] == 'SELL' and position > 0:
                    balance = position * df['Close'].iloc[i]
                    position = 0
            final_balance = balance + (position * df['Close'].iloc[-1])
            return final_balance

        print(gld)
        print("-" * 10)
        print(gld.iloc[-1].Signal)
        print(f"Saving the {ticker_input} GLD csv")
        gld.to_csv(f'{ticker_input}_GLD_.csv')
        data, sig = signal(gld)
        print(data)
        print(sig)
        plot_signals(gld)
        final_balance = backtest(gld)
        print(f"Final balance after backtesting {ticker_input}: ${final_balance:.2f}")

# List of ticker symbols to test
ticker_list = ['AIR.PA', 'AAPL', 'MSFT']
gld_signal(ticker_list, '2020-01-01', '2024-08-31')