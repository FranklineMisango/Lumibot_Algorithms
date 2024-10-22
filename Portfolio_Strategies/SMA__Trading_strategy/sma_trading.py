if pred_option_portfolio_strategies == "SMA Trading Strategy":
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
                    # Define the function to get historical data
                    def get_stock_data(stock, num_of_years):
                        start = dt.date.today() - dt.timedelta(days=365 * num_of_years)
                        end = dt.datetime.now()
                        return yf.download(stock, start, end, interval='1d')

                    # Define the function for SMA Trading Strategy
                    def sma_trading_strategy(df, short_sma, long_sma):
                        df[f"SMA_{short_sma}"] = df['Adj Close'].rolling(window=short_sma).mean()
                        df[f"SMA_{long_sma}"] = df['Adj Close'].rolling(window=long_sma).mean()

                        position = 0
                        percent_change = []
                        for i in df.index:
                            close = df['Adj Close'][i]
                            SMA_short = df[f"SMA_{short_sma}"][i]
                            SMA_long = df[f"SMA_{long_sma}"][i]

                            if SMA_short > SMA_long and position == 0:
                                buyP, position = close, 1
                                st.write("Buy at the price:", buyP)
                            elif SMA_short < SMA_long and position == 1:
                                sellP, position = close, 0
                                st.write("Sell at the price:", sellP)
                                percent_change.append((sellP / buyP - 1) * 100)

                        if position == 1:
                            position = 0
                            sellP = df['Adj Close'][-1]
                            st.write("Sell at the price:", sellP)
                            percent_change.append((sellP / buyP - 1) * 100)

                        return percent_change

                    # Main script
                    st.title("SMA Trading Strategy Visualization")

                    stock = st.text_input("Enter a ticker:", "NFLX")
                    num_of_years = st.number_input("Enter number of years:", min_value=1, max_value=10, step=1, value=5)
                    short_sma = st.number_input("Enter short SMA:", min_value=1, value=20)
                    long_sma = st.number_input("Enter long SMA:", min_value=1, value=50)

                    df = get_stock_data(stock, num_of_years)
                    percent_change = sma_trading_strategy(df, short_sma, long_sma)
                    current_price = round(df['Adj Close'][-1], 2)

                    # Calculate strategy statistics
                    gains = 0
                    numGains = 0
                    losses = 0
                    numLosses = 0
                    totReturn = 1
                    for i in percent_change:
                        if i > 0:
                            gains += i
                            numGains += 1
                        else:
                            losses += i
                            numLosses += 1
                        totReturn = totReturn * ((i / 100) + 1)
                    totReturn = round((totReturn - 1) * 100, 2)
                    # Plot SMA and Adj Close
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df.index, y=df[f"SMA_{short_sma}"], mode='lines', name=f"SMA_{short_sma}"))
                    fig.add_trace(go.Scatter(x=df.index, y=df[f"SMA_{long_sma}"], mode='lines', name=f"SMA_{long_sma}"))
                    fig.add_trace(go.Scatter(x=df.index, y=df['Adj Close'], mode='lines', name="Adj Close", line=dict(color='green')))
                    fig.update_layout(title=f"SMA Trading Strategy for {stock.upper()}", xaxis_title="Date", yaxis_title="Price", template='plotly_dark')
                    st.plotly_chart(fig)

                    # Display strategy statistics
                    st.write(f"Results for {stock.upper()} going back to {num_of_years} years:")
                    st.write(f"Number of Trades: {numGains + numLosses}")
                    st.write(f"Total return: {totReturn}%")