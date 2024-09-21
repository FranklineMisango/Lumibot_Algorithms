import pandas as pd
import yfinance as yf
import numpy as np
import plotly.graph_objects as go

def gld_signal(ticker_input, start_date, end_date):
    gld = pd.DataFrame(yf.download(ticker_input, start_date)['Close'])
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

    print(gld)
    print("-" * 10)
    print(gld.iloc[-1].Signal)
    print(f"Saving the {ticker_input} GLD csv")
    gld.to_csv(f'{ticker_input}_GLD_.csv')
    data, sig = signal(gld)
    print(data)
    print(sig)
    plot_signals(gld)

gld_signal('AIR.PA', '2020-01-01', '2024-08-31')