if pred_option_portfolio_strategies == "Factor Analysis":
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

                        # Setting plot aesthetics
                        sns.set(style='darkgrid', context='talk', palette='Dark2')

                        # Defining the time frame for data collection
                        end_date = dt.datetime.now()
                        start_date = end_date - dt.timedelta(days=365 * 7)

                        # List of stock symbols for factor analysis
                        symbols = tickers

                        # Fetching adjusted close prices for the specified symbols
                        df = pd.DataFrame({symbol: yf.download(symbol, start_date, end_date)['Adj Close']
                                        for symbol in symbols})

                        # Initializing FactorAnalyzer and fitting it to our data
                        fa = FactorAnalyzer(rotation=None, n_factors=df.shape[1])
                        fa.fit(df.dropna())

                        # Extracting communalities, eigenvalues, and factor loadings
                        communalities = fa.get_communalities()
                        eigenvalues, _ = fa.get_eigenvalues()
                        loadings = fa.loadings_

                        # Plotting the Scree plot to assess the number of factors
                        # Plotting the Scree plot to assess the number of factors
                        scree_fig = go.Figure()
                        scree_fig.add_trace(go.Scatter(x=list(range(1, df.shape[1] + 1)),
                                                    y=eigenvalues,
                                                    mode='markers+lines',
                                                    name='Eigenvalues',
                                                    marker=dict(color='blue')))
                        scree_fig.update_layout(title='Scree Plot',
                                                xaxis_title='Number of Factors',
                                                yaxis_title='Eigenvalue',
                                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                        st.plotly_chart(scree_fig)

                        # Bartlett's test of sphericity
                        chi_square_value, p_value = calculate_bartlett_sphericity(df.dropna())
                        st.write('Bartlett sphericity test:\nChi-square value:', chi_square_value, '\nP-value:', p_value)

                        # Kaiser-Meyer-Olkin (KMO) test
                        kmo_all, kmo_model = calculate_kmo(df.dropna())
                        st.write('Kaiser-Meyer-Olkin (KMO) Test:\nOverall KMO:', kmo_all, '\nKMO per variable:', kmo_model)

                        # Printing results
                        st.write("\nFactor Analysis Results:")
                        st.write("\nCommunalities:\n", communalities)
                        st.write("\nFactor Loadings:\n", loadings)

                if more_input == "No":
                    st.error("The EMA crossover cannot proceed without a comparison")