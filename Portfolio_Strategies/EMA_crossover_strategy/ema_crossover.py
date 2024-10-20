def ema_crossover_strategy():
if pred_option_portfolio_strategies == "EMA Crossover Strategy":
    tickers = []
    ticker = st.text_input("Enter the ticker for investigation")
    if ticker:
        message = (f"Ticker captured : {ticker}")
        st.success(message)
        tickers.append(ticker)
    more_input = st.selectbox("Please Add one/more ticker(s) for comparison", ("","Yes", "No"))
    if more_input == "Yes":
        ticker_2 =  st.text_input("Enter another ticker to continue the investigation")
        tickers.append(ticker_2)
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
            # Define the analysis period
            num_of_years = years
            start =  start_date
            end = end_date

            # Define tickers for analysis

            # Fetch stock data using Yahoo Finance
            df = yf.download(tickers, start, end)['Close']

            # Calculate moving averages
            short_rolling = df.rolling(window=20).mean()
            long_rolling = df.rolling(window=100).mean()
            ema_short = df.ewm(span=20, adjust=False).mean()

            # Determine trading position based on EMA
            trade_positions_raw = df - ema_short
            trade_positions = trade_positions_raw.apply(np.sign) / 3  # Equal weighting
            trade_positions_final = trade_positions.shift(1)  # Shift to simulate next-day trading

            # Calculate asset and portfolio returns
            asset_log_returns = np.log(df).diff()
            portfolio_log_returns = trade_positions_final * asset_log_returns
            cumulative_portfolio_log_returns = portfolio_log_returns.cumsum()
            cumulative_portfolio_relative_returns = np.exp(cumulative_portfolio_log_returns) - 1

            # Plot cumulative returns
            cumulative_fig = go.Figure()
            for ticker in asset_log_returns:
                cumulative_fig.add_trace(go.Scatter(x=cumulative_portfolio_relative_returns.index,
                                                    y=100 * cumulative_portfolio_relative_returns[ticker],
                                                    mode='lines',
                                                    name=ticker))

            cumulative_fig.update_layout(title='Cumulative Log Returns (%)',
                                        xaxis_title='Date',
                                        yaxis_title='Cumulative Log Returns (%)',
                                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(cumulative_fig)

            # Comparing exact and approximate cumulative returns
            cumulative_return_exact = cumulative_portfolio_relative_returns.sum(axis=1)
            cumulative_log_return = cumulative_portfolio_log_returns.sum(axis=1)
            cumulative_return_approx = np.exp(cumulative_log_return) - 1

            # Plot exact vs approximate returns
            approx_fig = go.Figure()
            approx_fig.add_trace(go.Scatter(x=cumulative_return_exact.index,
                                            y=100 * cumulative_return_exact,
                                            mode='lines',
                                            name='Exact'))
            approx_fig.add_trace(go.Scatter(x=cumulative_return_approx.index,
                                            y=100 * cumulative_return_approx,
                                            mode='lines',
                                            name='Approx'))

            approx_fig.update_layout(title='Total Cumulative Relative Returns (%)',
                                    xaxis_title='Date',
                                    yaxis_title='Total Cumulative Relative Returns (%)',
                                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(approx_fig)

            # Function to print portfolio statistics
            def print_portfolio_statistics(portfolio_returns, num_of_years):
                total_return = portfolio_returns[-1]
                avg_yearly_return = (1 + total_return) ** (1 / num_of_years) - 1
                st.write(f'Total Portfolio Return: {total_return * 100:.2f}%')
                st.write(f'Average Yearly Return: {avg_yearly_return * 100:.2f}%')

            # Printing statistics for EMA crossover strategy
            print_portfolio_statistics(cumulative_return_exact, num_of_years)
    if more_input == "No":
        st.error("The EMA crossover cannot proceed without a comparison")