 if pred_option_portfolio_strategies == "Optimal Portfolio":
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
                    # Function to download stock data and calculate annual returns
                    def annual_returns(symbols, start_date, end_date):
                        df = yf.download(symbols, start_date, end_date)['Adj Close']
                        log_rets = np.log(df / df.shift(1))
                        return np.exp(log_rets.groupby(log_rets.index.year).sum()) - 1

                    # Function to calculate portfolio variance
                    def portfolio_var(returns, weights):
                        cov_matrix = np.cov(returns.T)
                        return np.dot(weights.T, np.dot(cov_matrix, weights))

                    # Function to calculate Sharpe ratio
                    def sharpe_ratio(returns, weights, rf_rate):
                        portfolio_return = np.dot(returns.mean(), weights)
                        portfolio_volatility = np.sqrt(portfolio_var(returns, weights))
                        return (portfolio_return - rf_rate) / portfolio_volatility

                    # Function to optimize portfolio for maximum Sharpe ratio
                    def optimize_portfolio(returns, initial_weights, rf_rate):
                        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
                        bounds = tuple((0, 1) for _ in range(len(initial_weights)))
                        optimized = fmin(lambda x: -sharpe_ratio(returns, x, rf_rate), initial_weights, disp=False)
                        return optimized

                    # Main function to execute the script
                    def main():
                        st.title("Optimal Portfolio Optimization")

                        symbols = st.text_input("Enter stock symbols (comma-separated):")
                        start_date = st.date_input("Enter start date:")
                        end_date = st.date_input("Enter end date:")
                        rf_rate = st.number_input("Enter risk-free rate (in decimal):", min_value=0.0, value=0.003)

                        if not symbols or not start_date or not end_date:
                            st.warning("Please provide all required inputs.")
                            return

                        symbols = symbols.split(',')

                        # Calculate annual returns
                        returns = annual_returns(symbols, start_date, end_date)

                        # Initialize equal weights
                        initial_weights = np.ones(len(symbols)) / len(symbols)

                        # Calculate equal weighted portfolio Sharpe ratio
                        equal_weighted_sharpe = sharpe_ratio(returns, initial_weights, rf_rate)
                        
                        # Optimize portfolio
                        optimal_weights = optimize_portfolio(returns, initial_weights, rf_rate)
                        optimal_sharpe = sharpe_ratio(returns, optimal_weights, rf_rate)

                        # Display results
                        st.write(f"Equal Weighted Portfolio Sharpe Ratio: {equal_weighted_sharpe}")
                        st.write(f"Optimal Portfolio Weights: {optimal_weights}")
                        st.write(f"Optimal Portfolio Sharpe Ratio: {optimal_sharpe}")
