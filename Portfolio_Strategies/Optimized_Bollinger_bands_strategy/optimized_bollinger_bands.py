if pred_option_portfolio_strategies == "Optimized Bollinger Bands":
                ticker = st.text_input("Please enter the ticker needed for investigation")
                if ticker:
                    message = (f"Ticker captured : {ticker}")
                    st.success(message)
                portfolio = st.number_input("Enter the portfolio size in USD")
                if portfolio:
                    st.write(f"The portfolio size in USD Captured is : {portfolio}")
                min_date = datetime(1980, 1, 1)
                # Date input widget with custom minimum date
                col1, col2 = st.columns([2, 2])
                with col1:
                    start_date = st.date_input("Start date:", min_value=min_date)
                with col2:
                    end_date = st.date_input("End Date:")
                years = end_date.year - start_date.year
                st.success(f"years captured : {years}")
                if st.button("Check"):
                # Function to download stock data from Yahoo Finance
                    def get_stock_data(ticker):
                        df = yf.download(ticker)
                        df = df[['Adj Close']]
                        return df

                    # Function to add Bollinger Bands to DataFrame
                    def add_bollinger_bands(df, window_size=20, num_std_dev=2):
                        df['SMA'] = df['Adj Close'].rolling(window=window_size).mean()
                        df['Upper Band'] = df['SMA'] + (df['Adj Close'].rolling(window=window_size).std() * num_std_dev)
                        df['Lower Band'] = df['SMA'] - (df['Adj Close'].rolling(window=window_size).std() * num_std_dev)
                        return df

                    # Function to plot stock prices with Bollinger Bands
                    def plot_with_bollinger_bands(df, ticker):
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=df.index, y=df['Adj Close'], mode='lines', name=f'{ticker} Adjusted Close'))
                        fig.add_trace(go.Scatter(x=df.index, y=df['SMA'], mode='lines', name='20 Day SMA'))
                        fig.add_trace(go.Scatter(x=df.index, y=df['Upper Band'], mode='lines', name='Upper Bollinger Band'))
                        fig.add_trace(go.Scatter(x=df.index, y=df['Lower Band'], mode='lines', name='Lower Bollinger Band'))
                        fig.update_layout(title=f'{ticker} Stock Price with Bollinger Bands',
                                        xaxis_title='Date',
                                        yaxis_title='Price')
                        st.plotly_chart(fig)

                    # Main function to execute the script
                    st.title("Stock Price with Bollinger Bands")

                    ticker = st.text_input("Enter stock ticker:")
                    if not ticker:
                        st.warning("Please enter a valid ticker.")
                        return

                    df = get_stock_data(ticker)
                    df = add_bollinger_bands(df)

                    plot_with_bollinger_bands(df, ticker)
