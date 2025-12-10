import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///situational_data.db')

    # REAL API Keys - Update these in your .env file
    OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', '')

    # Twitter/X API Keys
    TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN', '')
    TWITTER_API_KEY = os.getenv('TWITTER_API_KEY', '')
    TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET', '')
    TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN', '')
    TWITTER_ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET', '')

    # Hugging Face API (optional for better classification)
    HUGGINGFACE_TOKEN = os.getenv('HUGGINGFACE_TOKEN', '')



    # Server settings
    API_HOST = os.getenv('API_HOST', '127.0.0.1')
    API_PORT = int(os.getenv('API_PORT', 5000))
    DEBUG = os.getenv('DEBUG', 'True').lower() in ['true', '1', 'yes']

    # Collection intervals (in seconds)
    NEWS_INTERVAL = int(os.getenv('NEWS_INTERVAL', 300))  # 5 minutes
    WEATHER_INTERVAL = int(os.getenv('WEATHER_INTERVAL', 900))  # 15 minutes
    TWITTER_INTERVAL = int(os.getenv('TWITTER_INTERVAL', 28800))  # 8 hours

    # Custom scripts interval
    CUSTOM_SCRIPTS_INTERVAL = int(os.getenv('CUSTOM_SCRIPTS_INTERVAL', '1800'))  # 30 minutes

    # Data limits
    MAX_NEWS_PER_RUN = int(os.getenv('MAX_NEWS_PER_RUN', 20))
    MAX_TWEETS_PER_RUN = int(os.getenv('MAX_TWEETS_PER_RUN', 3))  # 3 tweets per API call

    # Sri Lanka specific settings
    SRI_LANKA_DISTRICTS = [
        # Western Province (3)
        'Colombo', 'Gampaha', 'Kalutara',
        # Central Province (3)
        'Kandy', 'Matale', 'Nuwara Eliya',
        # Southern Province (2)
        'Galle', 'Matara',
        # Northern Province (1)
        'Jaffna',
        # Eastern Province (1)
        'Batticaloa'
    ]


