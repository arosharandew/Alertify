import os
import threading
import signal
import sys
from datetime import datetime

from config.config import Config
from data_collection import scheduler
from data_storage.csv_manager import CSVDataManager
from data_collection.scheduler import DataCollectorScheduler
from api.app import create_api_app


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n🛑 Shutting down...")
    if 'scheduler' in globals():
        scheduler.stop()
    sys.exit(0)


def print_startup_banner():
    """Print a nice startup banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     SRI LANKA SITUATIONAL AWARENESS SYSTEM                   ║
║                    v1.0                                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_api_status(config):
    """Print API configuration status"""
    print("\n🔧 API CONFIGURATION STATUS")
    print("=" * 60)

    # Weather API
    if config.OPENWEATHER_API_KEY and config.OPENWEATHER_API_KEY != '' and len(config.OPENWEATHER_API_KEY) > 10:
        print("🌤️  OpenWeatherMap API: ✓ ENABLED")
    else:
        print("🌤️  OpenWeatherMap API: ✗ DISABLED (no valid API key)")

    # Twitter API
    twitter_enabled = False
    twitter_details = []

    if config.TWITTER_BEARER_TOKEN and config.TWITTER_BEARER_TOKEN != '' and len(config.TWITTER_BEARER_TOKEN) > 10:
        twitter_enabled = True
        twitter_details.append("v2 (Bearer Token)")

    if config.TWITTER_API_KEY and config.TWITTER_API_KEY != '' and len(config.TWITTER_API_KEY) > 10:
        twitter_enabled = True
        twitter_details.append("v1.1 (OAuth)")

    if twitter_enabled:
        print(f"🐦 Twitter/X API: ✓ ENABLED ({', '.join(twitter_details)})")
        print(f"   • Free Tier: 100 posts/month")
        print(f"   • Collection: Every {config.TWITTER_INTERVAL // 3600} hours")
        print(f"   • Max per run: {config.MAX_TWEETS_PER_RUN} tweets")
    else:
        print("🐦 Twitter/X API: ✗ DISABLED (no valid API keys)")

    # Fuel scraper status
    print("⛽ Ceypetco Fuel Prices: ✓ ENABLED")
    print("   • Collection: Twice monthly (every 15 days)")
    print("   • Source: ceypetco.gov.lk/historical-prices/")

    print("=" * 60)


def print_system_info(config):
    """Print system information"""
    print("\n⚙️  SYSTEM INFORMATION")
    print("=" * 60)
    print(f"📊 News collection:     Every {config.NEWS_INTERVAL // 60} minutes")
    print(f"📊 Max news per run:    {config.MAX_NEWS_PER_RUN}")

    if config.OPENWEATHER_API_KEY and config.OPENWEATHER_API_KEY != '':
        print(f"📊 Weather collection:  Every {config.WEATHER_INTERVAL // 60} minutes")

    print(f"📊 Fuel collection:     Every 15 days")
    print(f"🏠 API Host:            {config.API_HOST}")
    print(f"🚪 API Port:            {config.API_PORT}")
    print(f"🐛 Debug Mode:          {'ON' if config.DEBUG else 'OFF'}")
    print("=" * 60)


def print_data_storage_info():
    """Print data storage information"""
    print("\n💾 DATA STORAGE")
    print("=" * 60)
    print("Storage: CSV files in 'data/' folder")
    print("Files:")
    print("  📄 news.csv         - All collected news articles")
    print("  🌤️  weather.csv      - Weather data")
    print("  🐦 tweets.csv       - Twitter data (API v2/v1.1)")
    print("  🔔 alerts.csv       - Generated alerts")
    print("  ⛽ fuel_prices.csv  - Historical fuel prices")
    print("=" * 60)


def print_api_endpoints():
    """Print available API endpoints"""
    print("\n🔗 AVAILABLE API ENDPOINTS")
    print("=" * 60)
    endpoints = [
        ("GET  /", "API documentation"),
        ("GET  /api/news", "Get news with filters"),
        ("GET  /api/weather", "Get weather data"),
        ("GET  /api/twitter/stats", "Get Twitter API usage stats"),
        ("GET  /api/tweets", "Get recent tweets"),
        ("GET  /api/alerts", "Get active alerts"),
        ("POST /api/classify", "Classify text into categories"),
        ("GET  /api/stats", "Get system statistics"),
        ("GET  /api/health", "Health check"),
        ("GET  /api/export/<type>", "Export data as CSV"),
        ("GET  /api/locations", "Get available locations"),
        ("POST /api/data/current-location", "Get data for user location"),
        ("GET  /api/data/summary", "Get summary of all data"),
        ("GET  /api/fuel/latest", "Get latest fuel prices"),
        ("GET  /api/fuel/history", "Get fuel price history"),
        ("GET  /api/fuel/stats", "Get fuel price statistics"),
        ("POST /api/fuel/scrape-now", "Manually scrape fuel prices"),
        ("GET  /api/fuel/analyze", "Analyze fuel price trends")
    ]

    for endpoint, description in endpoints:
        print(f"{endpoint:<35} - {description}")

    print("=" * 60)


def check_environment():
    """Check if required environment is set up"""
    print("🔍 Checking environment...")

    # Check if data directory exists
    if not os.path.exists("data"):
        os.makedirs("data")
        print("  ✓ Created 'data/' directory")
    else:
        print("  ✓ 'data/' directory exists")

    # Check if .env file exists
    if not os.path.exists(".env"):
        print("  ⚠️  Warning: No .env file found")
        print("     Create a .env file with your API keys")
        print("     See .env.example for template")
    else:
        print("  ✓ .env file found")

    # Check required Python packages
    try:
        import pandas
        import requests
        import flask
        import flask_cors
        import numpy
        print("  ✓ Required Python packages are installed")
    except ImportError as e:
        print(f"  ❌ Missing package: {e}")
        print("     Install required packages with:")
        print("     pip install -r requirements.txt")
        return False

    return True


def main():
    # Print startup banner
    print_startup_banner()

    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Check environment
    if not check_environment():
        print("\n❌ Environment check failed. Please fix the issues above.")
        sys.exit(1)

    # Load configuration
    print("\n📁 Loading configuration...")
    config = Config()

    # Print system status
    print_api_status(config)
    print_system_info(config)
    print_data_storage_info()

    # Initialize CSV Data Manager
    print("\n💿 Initializing CSV Data Manager...")
    csv_manager = CSVDataManager(data_dir="data")

    # Initialize data collector scheduler
    print("\n🔄 Initializing data collector...")
    scheduler = DataCollectorScheduler(csv_manager, config)

    # Start data collection in background thread
    print("\n🚀 Starting data collection...")
    scheduler_thread = threading.Thread(target=scheduler.start)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    # Create API app
    api_app = create_api_app(csv_manager, config)

    # Print API endpoints
    print_api_endpoints()

    # Show startup completion message
    print("\n" + "=" * 60)
    print("✅ SYSTEM STARTUP COMPLETE")
    print("=" * 60)
    print(f"🌐 API Server: http://{config.API_HOST}:{config.API_PORT}")
    print(f"📡 API Documentation: http://{config.API_HOST}:{config.API_PORT}/")
    print("\n📊 Data Sources:")
    print("  • 📰 News: Ada Derana (real-time scraping)")

    if config.OPENWEATHER_API_KEY and config.OPENWEATHER_API_KEY != '':
        print("  • 🌤️  Weather: OpenWeatherMap (API)")

    twitter_sources = []
    if config.TWITTER_BEARER_TOKEN and config.TWITTER_BEARER_TOKEN != '':
        twitter_sources.append("Twitter API v2")
    if config.TWITTER_API_KEY and config.TWITTER_API_KEY != '':
        twitter_sources.append("Twitter API v1.1")

    if twitter_sources:
        print(f"  • 🐦 Twitter: {', '.join(twitter_sources)}")

    print("  • ⛽ Fuel Prices: Ceypetco (historical data)")

    print("\n⚡ Quick Start:")
    print(f"  1. Open browser to: http://{config.API_HOST}:{config.API_PORT}/")
    print("  2. View system stats: /api/stats")
    print("  3. Check health: /api/health")
    print("  4. Get recent news: /api/news?limit=5")
    print("  5. Get fuel prices: /api/fuel/latest")
    print("\n📋 Monitoring:")
    print("  • Check Twitter API usage: /api/twitter/stats")
    print("  • View data summary: /api/data/summary")
    print("  • Export data: /api/export/<news|weather|tweets|alerts|fuel>")
    print("=" * 60)
    print("\n⚠️  Press Ctrl+C to stop the server")
    print("=" * 60 + "\n")

    # Run API in main thread
    try:
        api_app.run(
            host=config.API_HOST,
            port=config.API_PORT,
            debug=config.DEBUG,
            use_reloader=False
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n\n❌ Server error: {e}")
    finally:
        print("\n👋 Goodbye!")


if __name__ == "__main__":
    main()