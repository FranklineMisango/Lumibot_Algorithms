if pred_option_portfolio_strategies == "Portfolio Analysis":
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
                    # Override yfinance with Pandas Datareader's Yahoo Finance API
                    def get_historical_prices(symbols, start_date, end_date):
                        """Retrieve historical stock prices for specified symbols."""
                        return yf.download(symbols, start=start_date, end=end_date)['Adj Close']

                    def calculate_daily_returns(prices):
                        """Calculate daily returns from stock prices."""
                        return np.log(prices / prices.shift(1))

                    def calculate_monthly_returns(daily_returns):
                        """Calculate monthly returns from daily returns."""
                        return np.exp(daily_returns.groupby(lambda date: date.month).sum()) - 1

                    def calculate_annual_returns(daily_returns):
                        """Calculate annual returns from daily returns."""
                        return np.exp(daily_returns.groupby(lambda date: date.year).sum()) - 1

                    def portfolio_variance(returns, weights=None):
                        """Calculate the variance of a portfolio."""
                        if weights is None:
                            weights = np.ones(len(returns.columns)) / len(returns.columns)
                        covariance_matrix = np.cov(returns.T)
                        return np.dot(weights, np.dot(covariance_matrix, weights))

                    def sharpe_ratio(returns, weights=None, risk_free_rate=0.001):
                        """Calculate the Sharpe ratio of a portfolio."""
                        if weights is None:
                            weights = np.ones(len(returns.columns)) / len(returns.columns)
                        port_var = portfolio_variance(returns, weights)
                        port_return = np.dot(returns.mean(), weights)
                        return (port_return - risk_free_rate) / np.sqrt(port_var)

                    # Example usage
                    symbols = ['AAPL', 'MSFT', 'GOOGL']
                    start_date = dt.datetime.now() - dt.timedelta(days=365*5)
                    end_date = dt.datetime.now()

                    # Fetch historical data
                    historical_prices = get_historical_prices(symbols, start_date, end_date)

                    # Calculate returns
                    daily_returns = calculate_daily_returns(historical_prices)
                    monthly_returns = calculate_monthly_returns(daily_returns)
                    annual_returns = calculate_annual_returns(daily_returns)

                    # Calculate portfolio metrics
                    portfolio_variance = portfolio_variance(annual_returns)
                    portfolio_sharpe_ratio = sharpe_ratio(daily_returns)

                    # Display results
                    st.write(f"Portfolio Variance: {portfolio_variance}")
                    st.write(f"Portfolio Sharpe Ratio: {portfolio_sharpe_ratio}")

                    # Plot historical prices using Plotly
                    fig = go.Figure()
                    for symbol in symbols:
                        fig.add_trace(go.Scatter(x=historical_prices.index, y=historical_prices[symbol], mode='lines', name=symbol))

                    fig.update_layout(title="Historical Prices",
                                    xaxis_title="Date",
                                    yaxis_title="Adjusted Closing Price",
                                    legend_title="Symbols")
                    st.plotly_chart(fig)


            if pred_option_portfolio_strategies == "Portfolio Optimization":
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


                        # Registering converters for using matplotlib's plot_date() function.
                        register_matplotlib_converters()

                        # Setting display options for pandas
                        pd.set_option("display.max_columns", None)
                        pd.set_option("display.max_rows", None)

                        # Defining stocks to include in the portfolio
                        stocks = tickers

                        # Getting historical data from Yahoo Finance
                        start = start_date
                        end = end_date
                        df = yf.download(stocks, start=start, end=end)["Close"]

                        # Calculating daily returns of each stock
                        returns = df.pct_change()

                        # Define a function to generate random portfolios
                        def random_portfolios(num_portfolios, mean_returns, cov_matrix, risk_free_rate):
                            results = np.zeros((3, num_portfolios))
                            weights_record = []
                            for i in range(num_portfolios):
                                weights = np.random.random(n)
                                weights /= np.sum(weights)
                                weights_record.append(weights)
                                portfolio_std_dev, portfolio_return = portfolio_performance(
                                    weights, mean_returns, cov_matrix
                                )
                                results[0, i] = portfolio_std_dev
                                results[1, i] = portfolio_return
                                results[2, i] = (portfolio_return - risk_free_rate) / portfolio_std_dev
                            return results, weights_record

                        # Calculating mean returns and covariance matrix of returns
                        mean_returns = returns.mean()
                        cov_matrix = returns.cov()

                        # Setting the number of random portfolios to generate and the risk-free rate
                        num_portfolios = 50000
                        risk_free_rate = 0.021

                        # Define a function to calculate the negative Sharpe ratio
                        def neg_sharpe_ratio(weights, mean_returns, cov_matrix, risk_free_rate):
                            p_var, p_ret = portfolio_performance(weights, mean_returns, cov_matrix)
                            return -(p_ret - risk_free_rate) / p_var

                        # Define a function to find the portfolio with maximum Sharpe ratio
                        def max_sharpe_ratio(mean_returns, cov_matrix, risk_free_rate):
                            num_assets = len(mean_returns)
                            args = (mean_returns, cov_matrix, risk_free_rate)
                            constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
                            bound = (0.0, 1.0)
                            bounds = tuple(bound for asset in range(num_assets))
                            result = sco.minimize(
                                neg_sharpe_ratio,
                                num_assets
                                * [
                                    1.0 / num_assets,
                                ],
                                args=args,
                                method="SLSQP",
                                bounds=bounds,
                                constraints=constraints,
                            )
                            return result

                        # Helper function to calculate portfolio performance
                        def portfolio_performance(weights, mean_returns, cov_matrix):
                            returns = np.sum(mean_returns * weights) * 252
                            std_dev = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) * np.sqrt(252)
                            return std_dev, returns

                        # Calculate portfolio volatility
                        def portfolio_volatility(weights, mean_returns, cov_matrix):
                            return portfolio_performance(weights, mean_returns, cov_matrix)[0]

                        # Function to find portfolio with minimum variance
                        def min_variance(mean_returns, cov_matrix):
                            num_assets = len(mean_returns)
                            args = (mean_returns, cov_matrix)
                            bounds = tuple((0.0, 1.0) for asset in range(num_assets))
                            constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}

                            result = sco.minimize(portfolio_volatility, [1./num_assets]*num_assets,
                                                args=args, method='SLSQP', bounds=bounds, constraints=constraints)
                            return result

                        # Function to calculate efficient return
                        def efficient_return(mean_returns, cov_matrix, target_return):
                            num_assets = len(mean_returns)
                            args = (mean_returns, cov_matrix)
                            bounds = tuple((0.0, 1.0) for asset in range(num_assets))
                            constraints = [{'type': 'eq', 'fun': lambda x: portfolio_performance(x, mean_returns, cov_matrix)[1] - target_return},
                                        {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]

                            result = sco.minimize(portfolio_volatility, [1./num_assets]*num_assets,
                                                args=args, method='SLSQP', bounds=bounds, constraints=constraints)
                            return result

                        # Function to construct efficient frontier
                        def efficient_frontier(mean_returns, cov_matrix, returns_range):
                            efficient_portfolios = []
                            for ret in returns_range:
                                efficient_portfolios.append(efficient_return(mean_returns, cov_matrix, ret))
                            return efficient_portfolios

                        # Calculating efficient frontier
                        target_returns = np.linspace(0.0, 0.5, 100)
                        efficient_portfolios = efficient_frontier(mean_returns, cov_matrix, target_returns)

                        # Extracting volatility and return for each portfolio
                        volatility = [p['fun'] for p in efficient_portfolios]
                        returns = [portfolio_performance(p['x'], mean_returns, cov_matrix)[1] for p in efficient_portfolios]

                        # Plotting the efficient frontier
                        fig_efficient_frontier = go.Figure()
                        fig_efficient_frontier.add_trace(go.Scatter(x=volatility, y=returns, mode='lines', name='Efficient Frontier'))
                        fig_efficient_frontier.add_trace(go.Scatter(x=[p['fun'] for p in min_variance(mean_returns, cov_matrix)], y=[p['x'].mean() for p in min_variance(mean_returns, cov_matrix)], mode='markers', marker=dict(size=10, color='red'), name='Minimum Variance Portfolio'))
                        fig_efficient_frontier.update_layout(title='Efficient Frontier', xaxis_title='Volatility', yaxis_title='Return')
                        st.plotly_chart(fig_efficient_frontier)

                if pred_option_portfolio_strategies == "Portfolio VAR Simulation":
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

                        # Define the tickers and time parameters
                        tickers = ['GOOGL', 'FB', 'AAPL', 'NFLX', 'AMZN']
                        Time = 1440  # Number of trading days in minutes
                        pvalue = 1000  # Portfolio value in dollars
                        num_of_years = 3
                        start_date = dt.datetime.now() - dt.timedelta(days=365.25 * num_of_years)
                        end_date = dt.datetime.now()

                        # Fetching and preparing stock data
                        price_data = [web.DataReader(ticker, start=start_date, end=end_date, data_source='yahoo')['Adj Close'] for ticker in tickers]
                        df_stocks = pd.concat(price_data, axis=1)
                        df_stocks.columns = tickers

                        # Calculating expected returns and covariance matrix
                        mu = expected_returns.mean_historical_return(df_stocks)
                        Sigma = risk_models.sample_cov(df_stocks)

                        # Portfolio Optimization using Efficient Frontier
                        ef = EfficientFrontier(mu, Sigma, weight_bounds=(0,1))
                        sharpe_pwt = ef.max_sharpe()
                        cleaned_weights = ef.clean_weights()

                        # Plotting Cumulative Returns of All Stocks
                        cum_returns = ((df_stocks.pct_change() + 1).cumprod() - 1)
                        fig_cum_returns = go.Figure()
                        for column in cum_returns.columns:
                            fig_cum_returns.add_trace(go.Scatter(x=cum_returns.index, y=cum_returns[column], mode='lines', name=column))
                        fig_cum_returns.update_layout(title='Cumulative Returns', xaxis_title='Date', yaxis_title='Cumulative Returns')
                        st.plotly_chart(fig_cum_returns)

                        # Portfolio VaR Simulation
                        ticker_returns = cum_returns.pct_change().dropna()
                        weighted_returns = ticker_returns.dot(np.array(list(cleaned_weights.values())))
                        portfolio_return = weighted_returns.mean()
                        portfolio_vol = weighted_returns.std()

                        # Simulating daily returns for VAR calculation
                        simulated_daily_returns = [np.random.normal(portfolio_return / Time, portfolio_vol / np.sqrt(Time), Time) for _ in range(10000)]

                        # Plotting Range of Returns in a Day
                        fig_returns_range = go.Figure()
                        for i in range(10000):
                            fig_returns_range.add_trace(go.Scatter(y=simulated_daily_returns[i], mode='lines', name=f'Simulation {i+1}'))
                        fig_returns_range.add_trace(go.Scatter(y=np.percentile(simulated_daily_returns, 5), mode='lines', name='5th Percentile', line=dict(color='red', dash='dash')))
                        fig_returns_range.add_trace(go.Scatter(y=np.percentile(simulated_daily_returns, 95), mode='lines', name='95th Percentile', line=dict(color='green', dash='dash')))
                        fig_returns_range.add_trace(go.Scatter(y=np.mean(simulated_daily_returns), mode='lines', name='Mean', line=dict(color='blue')))
                        fig_returns_range.update_layout(title=f'Range of Returns in a Day of {Time} Minutes', xaxis_title='Minute', yaxis_title='Returns')
                        st.plotly_chart(fig_returns_range)

                        # Histogram of Daily Returns
                        fig_hist_returns = go.Figure()
                        fig_hist_returns.add_trace(go.Histogram(x=simulated_daily_returns.flatten(), nbinsx=15))
                        fig_hist_returns.add_trace(go.Scatter(x=[np.percentile(simulated_daily_returns, 5), np.percentile(simulated_daily_returns, 5)], y=[0, 1500], mode='lines', name='5th Percentile', line=dict(color='red', dash='dash')))
                        fig_hist_returns.add_trace(go.Scatter(x=[np.percentile(simulated_daily_returns, 95), np.percentile(simulated_daily_returns, 95)], y=[0, 1500], mode='lines', name='95th Percentile', line=dict(color='green', dash='dash')))
                        fig_hist_returns.update_layout(title='Histogram of Daily Returns', xaxis_title='Returns', yaxis_title='Frequency')
                        st.plotly_chart(fig_hist_returns)

                        # Printing VaR results
                        st.write(f"5th Percentile: {np.percentile(simulated_daily_returns, 5)}")
                        st.write(f"95th Percentile: {np.percentile(simulated_daily_returns, 95)}")
                        st.write(f"Amount required to cover minimum losses for one day: ${pvalue * -np.percentile(simulated_daily_returns, 5)}")
