import quantstats as qs
import matplotlib as plt
from algo import portfolio_size



qs.extend_pandas()

index = {"SPY": 1.3, "AGG": -.3}
portfolio = qs.utils.make_index(index, period='3y')
portfolio.index = portfolio.index.tz_localize(None)

# Create the Matplotlib figure and axis
fig, ax = plt.subplots()
portfolio.plot_earnings(start_balance=portfolio_size)  # Use ax=ax to specify the axis

# Display the Matplotlib figure using st.pyplot() or matplotlib??
st.pyplot(fig)