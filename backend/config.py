import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ROBINHOOD_API_KEY = os.getenv('ROBINHOOD_API_KEY')
    ROBINHOOD_PRIVATE_KEY = os.getenv('ROBINHOOD_PRIVATE_KEY')
    MAX_DRAWDOWN_PERCENT = float(os.getenv('MAX_DRAWDOWN_PERCENT', 5.0))
    PORT = int(os.getenv('PORT', 5000))
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')
    BASE_URL = "https://trading.robinhood.com"
    
    @classmethod
    def validate(clas):
        if not clas.ROBINHOOD_API_KEY or not clas.ROBINHOOD_PRIVATE_KEY:
            raise ValueError("Either ROBINHOOD_API_KEY or ROBINHOOD_PRIVATE_KEY is not set")
