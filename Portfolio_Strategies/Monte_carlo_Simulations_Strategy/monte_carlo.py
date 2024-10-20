if pred_option_portfolio_strategies == "Monte Carlo":
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
                    # Function to download stock data
                    symbol = ticker
                    df = yf.download(symbol, start_date, end_date)

                    # Function to calculate annual volatility
                    def annual_volatility(df):
                        quote = df['Close']
                        returns = quote.pct_change()
                        return returns.std() * np.sqrt(252)

                    # Function to calculate CAGR
                    def cagr(df):
                        quote = df['Close']
                        days = (quote.index[-1] - quote.index[0]).days
                        return ((((quote[-1]) / quote[1])) ** (365.0/days)) - 1

                    # Monte Carlo Simulation Function
                    def monte_carlo_simulation(simulations, days_predicted):
                        mu = cagr(df)
                        vol = annual_volatility(df)
                        start_price = df['Close'][-1]

                        results = []
                        
                        # Run simulations
                        for _ in range(simulations):
                            prices = [start_price]
                            for _ in range(days_predicted):
                                shock = np.random.normal(mu / days_predicted, vol / math.sqrt(days_predicted))
                                prices.append(prices[-1] * (1 + shock))
                            results.append(prices[-1])

                        return pd.DataFrame({
                            "Results": results,
                            "Percentile 5%": np.percentile(results, 5),
                            "Percentile 95%": np.percentile(results, 95)
                        })
                    
                
                    symbol = ticker
                    start_date = start_date
                    end_date = end_date
                    simulations = 1000
                    days_predicted = 252

                    # Perform Monte Carlo Simulation
                    simulation_results = monte_carlo_simulation(simulations, days_predicted)

                    # Plotting
                    fig = go.Figure()
                    fig.add_trace(go.Histogram(x=simulation_results['Results'], histnorm='probability'))
                    fig.update_layout(title=f"{symbol} Monte Carlo Simulation Histogram", xaxis_title="Price", yaxis_title="Probability Density")
                    st.plotly_chart(fig)

