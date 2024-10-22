if pred_option_portfolio_strategies == "Pairs Trading":
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
                    def download_stock_data(symbols, start_date, end_date):
                        """Download historical stock data for given symbols from Yahoo Finance."""
                        stock_data = yf.download(symbols, start=start_date, end=end_date)['Adj Close']
                        return stock_data.dropna()

                    # Function to identify cointegrated pairs of stocks
                    def find_cointegrated_pairs(data):
                        """Identify cointegrated pairs of stocks."""
                        n = data.shape[1]
                        score_matrix, pvalue_matrix = np.zeros((n, n)), np.ones((n, n))
                        pairs = []
                        for i in range(n):
                            for j in range(i+1, n):
                                S1, S2 = data[data.columns[i]], data[data.columns[j]]
                                _, pvalue, _ = coint(S1, S2)
                                score_matrix[i, j], pvalue_matrix[i, j] = _, pvalue
                                if pvalue < 0.05:  # Using a p-value threshold of 0.05
                                    pairs.append((data.columns[i], data.columns[j]))
                        return score_matrix, pvalue_matrix, pairs

                    # Function to plot heatmap of p-values for cointegration test using Plotly
                    def plot_cointegration_heatmap(pvalues, tickers):
                        """Plot heatmap of p-values for cointegration test."""
                        fig = go.Figure(data=go.Heatmap(
                            z=pvalues,
                            x=tickers,
                            y=tickers,
                            colorscale='Viridis',
                            zmin=0,
                            zmax=0.05
                        ))
                        fig.update_layout(title="P-Values for Pairs Cointegration Test")
                        return fig

                    # Pairs Trading Section
                    def pairs_trading():
                        st.title("Pairs Trading")

                        # Inputs
                        ticker = st.text_input("Please enter the ticker needed for investigation")
                        portfolio = st.number_input("Enter the portfolio size in USD")
                        min_date = datetime.datetime(1980, 1, 1)
                        start_date = st.date_input("Start date:", min_value=min_date)
                        end_date = st.date_input("End Date:")
                        years = end_date.year - start_date.year

                        if st.button("Check"):
                            # Download and process data
                            data = download_stock_data([ticker], start_date, end_date)

                            # Find cointegrated pairs
                            _, pvalues, pairs = find_cointegrated_pairs(data)

                            # Plot heatmap of p-values
                            fig = plot_cointegration_heatmap(pvalues, [ticker])
                            st.plotly_chart(fig)

                            # Display the found pairs
                            st.write("Cointegrated Pairs:", pairs)