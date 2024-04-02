import pandas as pd
import yfinance as yf
import numpy as np
from algo import ticker_input, start_date, end_date

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

'''
st.write(gld)
st.write("-" * 10)
st.write(gld.iloc[-1].Signal)
st.success("Saving the GLD csv")
gld.to_csv('gld_signal.csv')
data, sig = signal(gld)
st.write(data)
st.write(sig)
'''