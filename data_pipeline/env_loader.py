import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def load_env_file(env_file='.env'):
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent / env_file
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load environment variables when module is imported
load_env_file()
