 if pred_option_portfolio_strategies == "Long Hold Stats Analysis":
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
                    # Constants for analysis         
                    # Function to download stock data
                    def download_stock_data(symbol, start, end):
                        return yf.download(symbol, start, end)['Adj Close']

                    # Function to calculate investment statistics
                    def calculate_investment_stats(df, investment_amount, symbol):
                        # Calculate number of shares bought and investment values
                        shares = int(investment_amount / df.iloc[0])
                        begin_value = round(shares * df.iloc[0], 2)
                        current_value = round(shares * df.iloc[-1], 2)

                        # Calculate daily returns and various statistics
                        returns = df.pct_change().dropna()
                        stats = {
                            'mean': round(returns.mean() * 100, 2),
                            'std_dev': round(returns.std() * 100, 2),
                            'skew': round(returns.skew(), 2),
                            'kurt': round(returns.kurtosis(), 2),
                            'total_return': round((1 + returns).cumprod().iloc[-1], 4) * 100
                        }
                        return shares, begin_value, current_value, stats

                    # User inputs
                    symbol = ticker
                    num_of_years = years
                    investment_amount = portfolio

                    # Calculate date range
                    start = dt.datetime.now() - dt.timedelta(days=int(365.25 * num_of_years))
                    end = dt.datetime.now()

                    # Download and process stock data
                    df = download_stock_data(ticker, start_date, end_date)
                    shares, begin_value, current_value, stats = calculate_investment_stats(df, investment_amount, symbol)

                    # Print statistics
                    st.write(f'\nNumber of Shares for {symbol}: {shares}')
                    st.write(f'Beginning Value: ${begin_value}')
                    st.write(f'Current Value: ${current_value}')
                    st.write(f"\nStatistics:\nMean: {stats['mean']}%\nStd. Dev: {stats['std_dev']}%\nSkew: {stats['skew']}\nKurt: {stats['kurt']}\nTotal Return: {stats['total_return']}%")

                    # Plotting returns and other statistics
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df.index, y=df.pct_change(), mode='lines', name='Daily Returns'))
                    fig.update_layout(title=f'{symbol} Daily Returns', xaxis_title='Date', yaxis_title='Returns')
                    st.plotly_chart(fig)