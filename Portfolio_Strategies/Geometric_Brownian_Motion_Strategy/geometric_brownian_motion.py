if pred_option_portfolio_strategies == "Geometric Brownian Motion":
                ticker = st.text_input("Please enter the ticker needed for investigation")
                if ticker:
                    message = (f"Ticker captured : {ticker}")
                    st.success(message)
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
                    num_of_years = years  # Number of years for historical data
                    start = start_date
                    stock = ticker
                    index = '^GSPC'

                    # Fetching historical data from Yahoo Finance
                    stock_data = yf.download(stock, start_date, end_date)
                    index_data = yf.download(index, start_date, end_date)

                    # Resampling data to monthly frequency and calculating returns
                    stock_monthly = stock_data.resample('M').last()
                    index_monthly = index_data.resample('M').last()
                    combined_data = pd.DataFrame({'Stock': stock_monthly['Adj Close'], 
                                                'Index': index_monthly['Adj Close']})
                    combined_returns = combined_data.pct_change().dropna()

                    # Calculating covariance matrix for the returns
                    cov_matrix = np.cov(combined_returns['Stock'], combined_returns['Index'])

                    # Class for Geometric Brownian Motion simulation
                    class GBM:
                        def __init__(self, initial_price, drift, volatility, time_period, total_time):
                            self.initial_price = initial_price
                            self.drift = drift
                            self.volatility = volatility
                            self.time_period = time_period
                            self.total_time = total_time
                            self.simulate()

                        def simulate(self):
                            self.prices = [self.initial_price]
                            while self.total_time > 0:
                                dS = self.prices[-1] * (self.drift * self.time_period + 
                                                        self.volatility * np.random.normal(0, math.sqrt(self.time_period)))
                                self.prices.append(self.prices[-1] + dS)
                                self.total_time -= self.time_period

                    # Parameters for GBM simulation
                    num_simulations = 20
                    initial_price = stock_data['Adj Close'][-1]
                    drift = 0.24
                    volatility = math.sqrt(cov_matrix[0, 0])
                    time_period = 1 / 365
                    total_time = 1

                    # Running multiple GBM simulations
                    simulations = [GBM(initial_price, drift, volatility, time_period, total_time) for _ in range(num_simulations)]

                    # Plotting the simulations
                    fig = go.Figure()
                    for i, sim in enumerate(simulations):
                        fig.add_trace(go.Scatter(x=np.arange(len(sim.prices)), y=sim.prices, mode='lines', name=f'Simulation {i+1}'))

                    fig.add_trace(go.Scatter(x=np.arange(len(sim.prices)), y=[initial_price] * len(sim.prices),
                                            mode='lines', name='Initial Price', line=dict(color='red', dash='dash')))
                    fig.update_layout(title=f'Geometric Brownian Motion for {stock.upper()}',
                                    xaxis_title='Time Steps',
                                    yaxis_title='Price')
                    st.plotly_chart(fig)