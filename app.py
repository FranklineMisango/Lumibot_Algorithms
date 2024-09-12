import streamlit as st
from streamlit_ttyd import terminal
import subprocess
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.title("Frankline & Co. HFT Trading Bot Progress Monitoring - Test Run I")
st.write("Simulating Q2 Portfolio from Warren Buffet's Berkshire Hathaway")
try:
    # Start main.py and capture its output
    process = subprocess.Popen(['python', 'long_short_strategy.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    if process:
        st.success("Strategy  started successfully")
        logger.info("Strategy started successfully")
except Exception as e:
    st.error(f"Failed to start Strategy: {e}")
    logger.error(f"Failed to start Strategy: {e}")

# Display the output of main.py in Streamlit
st.write("Output on Test Day run from our HFT bot:")
try:
    output_placeholder = st.empty()
    for line in iter(process.stdout.readline, ''):
        output_placeholder.text(line.strip())
        logger.info(line.strip())
except Exception as e:
    st.error(f"Error reading output from main.py: {e}")
    logger.error(f"Error reading output from main.py: {e}")
try:
    # start the ttyd server and display the terminal on streamlit
    ttydprocess, port = terminal(cmd="top")
    st.text(f"ttyd server is running on port : {port}")
    logger.info(f"ttyd server is running on port : {port}")

    # kill the ttyd server after a minute
    time.sleep(60)
    ttydprocess.kill()
    logger.info("ttyd server killed after 60 seconds")
except Exception as e:
    st.error(f"Failed to start or stop ttyd server: {e}")
    logger.error(f"Failed to start or stop ttyd server: {e}")

# Ensure the process is terminated
try:
    process.terminate()
    process.wait()
    logger.info("main.py process terminated")
except Exception as e:
    st.error(f"Failed to terminate main.py: {e}")
    logger.error(f"Failed to terminate main.py: {e}")

