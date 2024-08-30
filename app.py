import streamlit as st
from streamlit_ttyd import terminal
import subprocess
import time

st.title("Frankline & Co. HFT Trading Bot Progress Monitoring - Test Run I")

# Start main.py and capture its output
process = subprocess.Popen(['python', 'main.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

# Display the output of main.py in Streamlit
st.success("Output on SPY Day run from our Test HFT bot:")
for line in iter(process.stdout.readline, ''):
    st.text(line.strip())

# start the ttyd server and display the terminal on streamlit
ttydprocess, port = terminal(cmd="top")

# info on ttyd port
st.text(f"ttyd server is running on port : {port}")

# kill the ttyd server after a minute
# time.sleep(60)
#ttydprocess.kill()

# Ensure the process is terminated
#process.terminate()