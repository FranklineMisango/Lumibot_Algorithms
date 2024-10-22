import yfinance as yf
import plotly.graph_objects as go
import datetime as dt

# Universal Helper function for the Astral Signals strategy : DON'T MODIFY
def astral(data, completion, step, step_two, what, high, low, where_long, where_short):
    data['long_signal'] = 0
    data['short_signal'] = 0

    # Iterate through the DataFrame
    for i in range(len(data)):
        # Long signal logic
        if data.iloc[i][what] < data.iloc[i - step][what] and data.iloc[i][low] < data.iloc[i - step_two][low]:
            data.at[data.index[i], 'long_signal'] = -1
        elif data.iloc[i][what] >= data.iloc[i - step][what]:
            data.at[data.index[i], 'long_signal'] = 0

        # Short signal logic
        if data.iloc[i][what] > data.iloc[i - step][what] and data.iloc[i][high] > data.iloc[i - step_two][high]:
            data.at[data.index[i], 'short_signal'] = 1
        elif data.iloc[i][what] <= data.iloc[i - step][what]:
            data.at[data.index[i], 'short_signal'] = 0

    return data


def main(start_date : dt.time, end_date : dt.time, ticker:str):
    ''' This program allows you to view the Astral Signals of a ticker over time. '''
    start = start_date
    end = end_date

    # Fetch stock data
    data = yf.download(ticker, start, end)

    # Apply Astral Timing signals
    astral_data = astral(data, 8, 1, 5, 'Close', 'High', 'Low', 'long_signal', 'short_signal')

    # Display the results
    # Create candlestick chart with signals
    fig = go.Figure(data=[go.Candlestick(x=astral_data.index,
                                        open=astral_data['Open'],
                                        high=astral_data['High'],
                                        low=astral_data['Low'],
                                        close=astral_data['Close'])])

    # Add long and short signals to the plot
    fig.add_trace(go.Scatter(x=astral_data.index, y=astral_data['long_signal'],
                            mode='markers', marker=dict(color='blue'), name='Long Signal'))
    fig.add_trace(go.Scatter(x=astral_data.index, y=astral_data['short_signal'],
                            mode='markers', marker=dict(color='red'), name='Short Signal'))

    # Customize layout
    fig.update_layout(title=f"{ticker} Astral Signals : Display of the Candlestick Chart with Signals",
                    xaxis_title="Date",
                    yaxis_title="Price",
                    xaxis_rangeslider_visible=False)

    # Display the interactive plot
    fig.show()
    print(astral_data[['long_signal', 'short_signal']])


if __name__ == '__main__':
    main(dt.datetime(2024, 10, 21, 9, 30), dt.datetime(2024, 10, 21, 16, 0), 'AAPL')