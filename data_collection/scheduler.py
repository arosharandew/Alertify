import time
import threading
from datetime import datetime, timedelta
import json
from typing import List, Dict
import sys
import os
import subprocess

from data_collection.news_scraper import AdaDeranaScraper
from data_collection.weather_api import WeatherAPI
from data_collection.twitter_api import TwitterAPIClient
from data_collection.fuel_scraper import CeypetcoFuelScraper
from data_processing.classifier import NewsClassifier
from data_storage.csv_manager import CSVDataManager


class DataCollectorScheduler:
    def __init__(self, csv_manager: CSVDataManager, config):
        self.csv = csv_manager
        self.config = config
        self.running = False
        self.thread = None

        # Initialize collectors
        print(f"Initializing data collectors...")

        # Real Ada Derana scraper
        print("  → Ada Derana scraper")
        self.news_scraper = AdaDeranaScraper()

        # Real OpenWeatherMap API (only if API key is provided)
        if config.OPENWEATHER_API_KEY and config.OPENWEATHER_API_KEY != '':
            print(f"  → OpenWeatherMap API")
            self.weather_api = WeatherAPI(config.OPENWEATHER_API_KEY)
            self.has_weather_api = True
        else:
            print(f"  → OpenWeatherMap API (DISABLED - no API key)")
            self.weather_api = None
            self.has_weather_api = False

        # Twitter/X API Client (supports both v2 and v1.1)
        if (config.TWITTER_BEARER_TOKEN and config.TWITTER_BEARER_TOKEN != '') or \
                (config.TWITTER_API_KEY and config.TWITTER_API_KEY != ''):
            print(f"  → Twitter/X API Client")
            self.twitter_api = TwitterAPIClient(
                bearer_token=config.TWITTER_BEARER_TOKEN,
                api_key=config.TWITTER_API_KEY,
                api_secret=config.TWITTER_API_SECRET,
                access_token=config.TWITTER_ACCESS_TOKEN,
                access_token_secret=config.TWITTER_ACCESS_TOKEN_SECRET
            )
            self.has_twitter_api = True

            # Test Twitter API connection
            if self.twitter_api.test_connection():
                print("    ✓ Twitter API connection successful")
            else:
                print("    ✗ Twitter API connection failed")
                self.has_twitter_api = False
        else:
            print(f"  → Twitter/X API (DISABLED - no API keys)")
            self.twitter_api = None
            self.has_twitter_api = False

        # Initialize fuel scraper
        print("  → Ceypetco Fuel Price Scraper")
        self.fuel_scraper = CeypetcoFuelScraper()

        # Initialize classifier
        print(f"  → News classifier")
        self.classifier = NewsClassifier(
            use_llm=bool(config.HUGGINGFACE_TOKEN),
            llm_api_key=config.HUGGINGFACE_TOKEN
        )

        # Set up custom scripts path
        self.scripts_dir = r"C:\Users\Arosha IIT\OneDrive - Robert Gordon University\Desktop\Private\Hack\process"

        # Check if custom scripts directory exists
        if os.path.exists(self.scripts_dir):
            print(f"  → Custom scripts directory found")
            sys.path.insert(0, self.scripts_dir)
        else:
            print(f"  ⚠️ Custom scripts directory not found: {self.scripts_dir}")

        # Task schedule configuration
        self.tasks = [
            {'func': self.collect_news, 'interval': config.NEWS_INTERVAL, 'last_run': 0},
            {'func': self.generate_alerts, 'interval': 600, 'last_run': 0},  # Every 10 minutes
            {'func': self.cleanup_data, 'interval': 3600, 'last_run': 0},  # Every hour
            {'func': self.collect_fuel_prices, 'interval': 15 * 24 * 3600, 'last_run': 0},  # Every 15 days
            # Add custom scripts task - run every 30 minutes
            {'func': self.run_custom_scripts, 'interval': getattr(config, 'CUSTOM_SCRIPTS_INTERVAL', 1800),
             'last_run': 0},
        ]

        # Add weather task only if API is available
        if self.has_weather_api:
            self.tasks.append({'func': self.collect_weather, 'interval': config.WEATHER_INTERVAL, 'last_run': 0})

        # Add twitter API task only if API is available
        if self.has_twitter_api:
            self.tasks.append({'func': self.collect_tweets_api, 'interval': config.TWITTER_INTERVAL, 'last_run': 0})

        # Statistics
        self.stats = {
            'news_collected': 0,
            'tweets_collected': 0,
            'weather_updates': 0,
            'alerts_generated': 0,
            'fuel_updates': 0,
            'custom_scripts_runs': 0,
            'last_success': None,
            'twitter_usage': None
        }

    def start(self):
        """Start the scheduler"""
        self.running = True

        print("\n" + "=" * 60)
        print("DATA COLLECTOR SCHEDULER STARTED")
        print("=" * 60)

        if self.has_weather_api:
            print("✓ OpenWeatherMap API: ENABLED")
        else:
            print("✗ OpenWeatherMap API: DISABLED")

        if self.has_twitter_api:
            print("✓ Twitter/X API: ENABLED")
            usage = self.twitter_api.get_usage_stats()
            print(f"  • Free Tier: {usage['monthly_used']}/{usage['monthly_limit']} posts this month")
            print(f"  • Daily: {usage['daily_used']}/{usage['daily_limit']} posts today")
            print(f"  • Collection: Every {self.config.TWITTER_INTERVAL // 3600} hours")
            print(f"  • Max per run: {self.config.MAX_TWEETS_PER_RUN} tweets")
        else:
            print("✗ Twitter/X API: DISABLED")

        print("✓ Ceypetco Fuel Prices: ENABLED")
        print(f"  • Collection: Twice monthly (every 15 days)")
        print("✓ Custom Scripts: ENABLED")
        print(f"  • merge.py & process.py every {getattr(self.config, 'CUSTOM_SCRIPTS_INTERVAL', 1800) // 60} minutes")
        print("=" * 60)

        # Run all tasks once immediately
        print("\nRunning initial data collection...")
        for task in self.tasks:
            try:
                task['func']()
            except Exception as e:
                print(f"Error in initial run: {e}")

        # Start scheduler thread
        self.thread = threading.Thread(target=self._scheduler_loop)
        self.thread.daemon = True
        self.thread.start()

        print("\nScheduler is running. Press Ctrl+C to stop.")
        self._print_schedule_info()

    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("Data collector scheduler stopped")

    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            current_time = time.time()

            for task in self.tasks:
                time_since_last_run = current_time - task['last_run']
                if time_since_last_run >= task['interval']:
                    try:
                        task['func']()
                    except Exception as e:
                        print(f"Error running task: {e}")
                    task['last_run'] = current_time

            time.sleep(1)  # Check every second

    # ============ CUSTOM SCRIPTS METHODS ============

    def run_custom_scripts(self):
        """Run merge.py and process.py scripts"""
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⚙️ Running custom scripts...")

            success_count = 0
            script_results = []

            # Check if scripts directory exists
            if not os.path.exists(self.scripts_dir):
                print(f"  ❌ Scripts directory not found: {self.scripts_dir}")
                return False

            # Run merge.py
            merge_success = self._run_single_script("merge.py")
            if merge_success:
                success_count += 1

            # Run process.py
            process_success = self._run_single_script("process.py")
            if process_success:
                success_count += 1

            self.stats['custom_scripts_runs'] += 1

            if success_count == 2:
                print(f"  ✅ Both custom scripts completed successfully")
                self.stats['last_success'] = datetime.now().isoformat()
                return True
            else:
                print(f"  ⚠️ Only {success_count}/2 scripts completed successfully")
                return False

        except Exception as e:
            print(f"❌ Error in run_custom_scripts: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _run_single_script(self, script_name):
        """Run a single script using multiple methods"""
        script_path = os.path.join(self.scripts_dir, script_name)

        if not os.path.exists(script_path):
            print(f"  ❌ {script_name} not found at {script_path}")
            return False

        print(f"  🔄 Running {script_name}...")

        # Method 1: Try to import and run as module
        if self._run_script_as_module(script_name):
            return True

        # Method 2: Try subprocess execution
        if self._run_script_with_subprocess(script_path, script_name):
            return True

        # Method 3: Try direct execution
        if self._run_script_directly(script_path, script_name):
            return True

        print(f"  ❌ All methods failed for {script_name}")
        return False

    def _run_script_as_module(self, script_name):
        """Try to import and run script as Python module"""
        try:
            # Remove .py extension for import
            module_name = script_name.replace('.py', '')

            # Import the module
            module = __import__(module_name)

            # Check for main function
            if hasattr(module, 'main'):
                result = module.main()
                if result:
                    print(f"    ✅ {script_name} executed via module import")
                    return True
                else:
                    print(f"    ⚠️ {script_name}.main() returned False")
                    return False
            else:
                print(f"    ⚠️ {script_name} has no main() function")
                return False

        except ImportError as e:
            print(f"    ⚠️ Could not import {script_name} as module: {e}")
            return False
        except Exception as e:
            print(f"    ❌ Error running {script_name} as module: {e}")
            return False

    def _run_script_with_subprocess(self, script_path, script_name):
        """Run script using subprocess"""
        try:
            result = subprocess.run(
                ['python', script_path],
                capture_output=True,
                text=True,
                shell=True,
                cwd=self.scripts_dir  # Run from script directory
            )

            if result.returncode == 0:
                print(f"    ✅ {script_name} executed via subprocess")
                if result.stdout and result.stdout.strip():
                    output_lines = result.stdout.strip().split('\n')
                    if len(output_lines) > 0:
                        print(f"      Output: {output_lines[0][:80]}...")
                return True
            else:
                print(f"    ❌ {script_name} failed via subprocess (code: {result.returncode})")
                if result.stderr:
                    error_msg = result.stderr.strip().split('\n')[0][:100]
                    print(f"      Error: {error_msg}")
                return False

        except Exception as e:
            print(f"    ❌ Error running {script_name} via subprocess: {e}")
            return False

    def _run_script_directly(self, script_path, script_name):
        """Run script by reading and executing its code directly"""
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                script_code = f.read()

            # Create a namespace for execution
            namespace = {
                '__name__': '__main__',
                '__file__': script_path
            }

            # Execute the script
            exec(script_code, namespace)
            print(f"    ✅ {script_name} executed directly")
            return True

        except Exception as e:
            print(f"    ❌ Error running {script_name} directly: {e}")
            return False

    # ============ EXISTING COLLECTION METHODS (keep as is) ============

    def collect_news(self):
        """Collect and classify news from Ada Derana"""
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📰 Collecting news from Ada Derana...")

            # Collect from homepage
            news_items = self.news_scraper.scrape_homepage()

            # Also collect from major categories
            for category in ['hot-news', 'sports-news']:
                category_news = self.news_scraper.scrape_by_category(category)
                news_items.extend(category_news)

            # Process and store news
            stored_count = 0
            for item in news_items[:self.config.MAX_NEWS_PER_RUN]:
                try:
                    # Prepare text for classification
                    text = f"{item['title']} {item.get('summary', '')} {item.get('full_text', '')}"

                    # Classify the news
                    classification = self.classifier.classify(text)

                    # Prepare news record
                    news_record = {
                        'title': item['title'],
                        'summary': item.get('summary', ''),
                        'full_text': item.get('full_text', ''),
                        'link': item['link'],
                        'source': 'ada_derana',
                        'category': classification.category,
                        'subcategory': classification.subcategory,
                        'location': classification.location,
                        'impact': classification.impact,
                        'severity': classification.severity,
                        'keywords': [],
                        'timestamp': datetime.now().isoformat(),
                        'raw_data': json.dumps(item)
                    }

                    # Store in CSV
                    self.csv.insert_news(news_record)
                    stored_count += 1

                    # Create alert for high/medium severity
                    if classification.severity in ['high', 'medium']:
                        self._create_alert(news_record, classification)

                except Exception as e:
                    print(f"Error processing news item: {e}")
                    continue

            self.stats['news_collected'] += stored_count
            if stored_count > 0:
                print(f"  ✅ Stored {stored_count} news items")
            else:
                print(f"  ⚠️ No news items collected")
            self.stats['last_success'] = datetime.now().isoformat()

        except Exception as e:
            print(f"❌ Error collecting news: {e}")

    def collect_weather(self):
        """Collect weather data for all Sri Lankan districts"""
        if not self.has_weather_api:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Weather collection skipped - no API key")
            return

        try:
            # Get weather for all 10 districts
            weather_data = self.weather_api.get_all_districts_weather(max_districts=10, show_progress=True)

            # Store weather data
            stored_count = 0
            for district, data in weather_data.items():
                try:
                    if not data or not data.get('current'):
                        print(f"  ⚠️ Skipping {district} - no weather data")
                        continue

                    weather_record = {
                        'location': district,
                        'temperature': data['current'].get('temperature'),
                        'feels_like': data['current'].get('feels_like'),
                        'humidity': data['current'].get('humidity'),
                        'weather': data['current'].get('weather'),
                        'description': data['current'].get('description'),
                        'wind_speed': data['current'].get('wind_speed'),
                        'rain': data['current'].get('rain', 0),
                        'snow': data['current'].get('snow', 0),
                        'pressure': data['current'].get('pressure'),
                        'visibility': data['current'].get('visibility'),
                        'severity': data['current'].get('severity', 'low'),
                        'alerts': data.get('alerts', []),
                        'forecast': data.get('forecast', []),
                        'timestamp': datetime.now().isoformat()
                    }

                    self.csv.insert_weather(weather_record)
                    stored_count += 1

                    # Create alerts for severe weather
                    if data.get('alerts'):
                        for alert in data['alerts']:
                            if alert.get('severity') in ['high', 'medium']:
                                self._create_weather_alert(district, alert)

                    # Also create alert for severe weather conditions
                    if data['current'].get('severity') == 'high':
                        self._create_severe_weather_alert(district, data['current'])

                except Exception as e:
                    print(f"❌ Error storing weather for {district}: {e}")
                    continue

            self.stats['weather_updates'] += stored_count

            # Get weather summary using the data we just collected
            summary = self.weather_api.get_weather_summary(weather_data)

            print(f"  ✅ Stored weather for {stored_count} districts")
            print(f"  📊 Weather Summary:")
            print(f"     • Total districts: {summary.get('total_districts', 0)}")

            if summary.get('hottest_district'):
                hot = summary['hottest_district']
                print(f"     • Hottest: {hot['name']} ({hot['temperature']}°C)")

            if summary.get('coldest_district'):
                cold = summary['coldest_district']
                print(f"     • Coldest: {cold['name']} ({cold['temperature']}°C)")

            if summary.get('districts_with_alerts', 0) > 0:
                print(f"     • Alerts in: {summary['districts_with_alerts']} districts")

        except Exception as e:
            print(f"❌ Error collecting weather: {e}")

    def _create_severe_weather_alert(self, location: str, weather_data: Dict):
        """Create alert for severe weather conditions"""
        try:
            alert = {
                'title': f"Severe Weather Alert: {weather_data.get('weather', 'Severe Conditions')}",
                'description': f"{weather_data.get('description', 'Severe weather conditions')} in {location}. Temp: {weather_data.get('temperature')}°C, Wind: {weather_data.get('wind_speed')} m/s",
                'category': 'weather',
                'subcategory': self._determine_weather_subcategory(weather_data.get('weather', '')),
                'location': location,
                'severity': 'high',
                'source': 'weather',
                'source_id': f"weather_severe_{location}_{int(time.time())}",
                'start_time': datetime.now().isoformat(),
                'end_time': (datetime.now() + timedelta(hours=12)).isoformat(),
                'is_active': True,
                'metadata': {
                    'temperature': weather_data.get('temperature'),
                    'wind_speed': weather_data.get('wind_speed'),
                    'rain': weather_data.get('rain', 0),
                    'weather_condition': weather_data.get('weather')
                }
            }

            self.csv.insert_alert(alert)
            print(f"  🔔 Created severe weather alert for {location}")

        except Exception as e:
            print(f"❌ Error creating severe weather alert: {e}")

    def collect_tweets_api(self):
        """Collect tweets using Twitter API with rate limiting"""
        if not self.has_twitter_api:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Twitter API collection skipped - no API keys")
            return

        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🐦 Collecting tweets via Twitter API...")

            # Get usage stats first
            usage_stats = self.twitter_api.get_usage_stats()
            self.stats['twitter_usage'] = usage_stats

            print(f"  📊 API Usage: {usage_stats['monthly_used']}/{usage_stats['monthly_limit']} monthly")
            print(f"  📊 Daily: {usage_stats['daily_used']}/{usage_stats['daily_limit']}")

            # Check if we should collect based on rate limits
            if usage_stats['monthly_remaining'] <= 0:
                print(f"  ⚠️ Monthly limit reached, skipping collection")
                return

            if usage_stats['daily_remaining'] <= 0:
                print(f"  ⚠️ Daily limit reached, skipping collection")
                return

            # Get tweets from API (using simplified method)
            tweets = self.twitter_api.get_sri_lanka_tweets(
                max_tweets=self.config.MAX_TWEETS_PER_RUN
            )

            stored_count = 0
            for tweet in tweets:
                try:
                    # Convert TweetData to dict
                    tweet_dict = {
                        'id': tweet.id,
                        'text': tweet.text,
                        'author_id': tweet.author_id,
                        'retweet_count': tweet.retweet_count,
                        'like_count': tweet.like_count,
                        'hashtags': tweet.hashtags,
                        'mentions': tweet.mentions,
                        'timestamp': tweet.created_at,
                        'source': 'twitter_api'
                    }

                    # Classify the tweet
                    classification = self.classifier.classify(tweet.text)

                    # Add classification
                    tweet_dict['category'] = classification.category
                    tweet_dict['subcategory'] = classification.subcategory
                    tweet_dict['severity'] = classification.severity
                    tweet_dict['location'] = classification.location

                    # Store in CSV
                    self.csv.insert_tweet(tweet_dict)
                    stored_count += 1

                    # Update stats
                    self.stats['tweets_collected'] += 1

                    # Create alert for high severity tweets
                    if classification.severity == 'high':
                        self._create_tweet_alert(tweet_dict, classification)

                except Exception as e:
                    print(f"❌ Error storing tweet: {e}")

            if stored_count > 0:
                print(f"  ✅ Stored {stored_count} tweets (Total: {self.stats['tweets_collected']})")
                # Print updated usage
                usage_stats = self.twitter_api.get_usage_stats()
                print(f"  📊 Remaining this month: {usage_stats['monthly_remaining']}")
                print(f"  📊 Remaining today: {usage_stats['daily_remaining']}")
                print(f"  📊 Estimated daily limit: {usage_stats['estimated_daily_limit']}")
            else:
                print(f"  ⚠️ No tweets collected this cycle")
                print(f"  ℹ️  Free tier may have limited search access")

        except Exception as e:
            print(f"❌ Error collecting tweets via API: {e}")

    def collect_fuel_prices(self):
        """Collect fuel prices from Ceypetco"""
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⛽ Collecting fuel prices...")

            # Get ALL fuel prices (not just latest)
            all_prices = self.fuel_scraper.scrape_fuel_prices()

            if not all_prices:
                print("  ❌ No fuel price data collected")
                return

            print(f"  📊 Found {len(all_prices)} fuel price records")

            # Store ALL records in CSV
            stored_count = 0
            for price_data in all_prices:
                try:
                    fuel_id = self.csv.insert_fuel_price(price_data)
                    stored_count += 1

                    # Print progress for first few records
                    if stored_count <= 3:
                        date_str = price_data.get('date_str', 'Unknown date')
                        petrol_95 = price_data.get('petrol_95', 'N/A')
                        print(f"    • {date_str}: Petrol 95 = Rs.{petrol_95}")

                except Exception as e:
                    print(f"    ⚠️ Error storing record: {e}")
                    continue

            print(f"  ✅ Stored {stored_count}/{len(all_prices)} fuel price records")

            # Get latest for summary
            if all_prices:
                all_prices.sort(key=lambda x: x['date'], reverse=True)
                latest = all_prices[0]

                print(f"  📈 Latest prices (from {latest.get('date_str', 'N/A')}):")
                print(f"     • Petrol 95: Rs.{latest.get('petrol_95', 'N/A')}")
                print(f"     • Auto Diesel: Rs.{latest.get('auto_diesel', 'N/A')}")
                print(f"     • Kerosene: Rs.{latest.get('kerosene', 'N/A')}")

                # Get price changes
                changes = self.fuel_scraper.get_fuel_price_changes()
                if changes and 'changes' in changes:
                    # Create alerts for significant price changes
                    for fuel_type, change_data in changes['changes'].items():
                        if abs(change_data['change_pct']) >= 5:  # Alert for 5%+ changes
                            self._create_fuel_price_alert(fuel_type, change_data)

            # Update stats
            self.stats['fuel_updates'] = self.stats.get('fuel_updates', 0) + stored_count
            self.stats['last_success'] = datetime.now().isoformat()

            # Print historical data summary
            self._print_fuel_data_summary(all_prices)

        except Exception as e:
            print(f"❌ Error collecting fuel prices: {e}")
            import traceback
            traceback.print_exc()

    def _print_fuel_data_summary(self, fuel_data: List[Dict]):
        """Print summary of fuel data"""
        if not fuel_data:
            return

        # Sort by date
        fuel_data.sort(key=lambda x: x['date'])

        oldest = fuel_data[0]
        latest = fuel_data[-1]

        print(f"  📅 Data range: {oldest.get('date_str', 'N/A')} to {latest.get('date_str', 'N/A')}")

        # Calculate price ranges
        fuel_types = ['petrol_95', 'auto_diesel', 'kerosene']
        for fuel_type in fuel_types:
            prices = [d.get(fuel_type) for d in fuel_data if d.get(fuel_type) is not None]
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                latest_price = latest.get(fuel_type)

                fuel_name = fuel_type.replace('_', ' ').title()
                print(f"     • {fuel_name}: Rs.{latest_price} (Range: Rs.{min_price}-{max_price})")

    def generate_alerts(self):
        """Generate alerts from recent data"""
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔔 Generating alerts...")

            # Get high severity news from last hour
            recent_news = self.csv.get_recent_news(
                limit=20,
                severity='high',
                hours=1
            )

            alert_count = 0
            for news in recent_news:
                # Check if alert already exists for this news
                existing_alerts = self.csv.get_active_alerts(
                    source='news',
                    source_id=f"news_{news.get('id', 'unknown')}"
                )

                if not existing_alerts:
                    # Create new alert
                    alert_data = {
                        'title': news.get('title', ''),
                        'description': news.get('summary', ''),
                        'category': news.get('category', ''),
                        'subcategory': news.get('subcategory', ''),
                        'location': news.get('location', ''),
                        'severity': news.get('severity', ''),
                        'source': 'news',
                        'source_id': f"news_{news.get('id', 'unknown')}",
                        'start_time': datetime.now().isoformat(),
                        'end_time': (datetime.now() + timedelta(hours=24)).isoformat(),
                        'is_active': True
                    }

                    self.csv.insert_alert(alert_data)
                    alert_count += 1

            if alert_count > 0:
                print(f"  ✅ Generated {alert_count} new alerts")
            else:
                print(f"  ⚠️ No new alerts generated")

        except Exception as e:
            print(f"❌ Error generating alerts: {e}")

    def cleanup_data(self):
        """Clean up old data"""
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🧹 Cleaning up old data...")
            self.csv.cleanup_old_data(days_old=7)
            print("  ✅ Cleanup completed")
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")

    # ============ ALERT CREATION METHODS ============

    def _create_alert(self, news_data: Dict, classification):
        """Create alert from classified news"""
        try:
            alert_data = {
                'title': news_data.get('title', ''),
                'description': news_data.get('summary', 'No description available'),
                'category': classification.category,
                'subcategory': classification.subcategory,
                'location': classification.location,
                'severity': classification.severity,
                'source': 'news',
                'source_id': f"news_{int(time.time())}",
                'start_time': datetime.now().isoformat(),
                'end_time': (datetime.now() + timedelta(hours=24)).isoformat(),
                'is_active': True
            }

            self.csv.insert_alert(alert_data)
            self.stats['alerts_generated'] += 1

        except Exception as e:
            print(f"❌ Error creating alert: {e}")

    def _create_weather_alert(self, location: str, alert_data: Dict):
        """Create alert from weather data"""
        try:
            alert = {
                'title': f"Weather Alert: {alert_data.get('event', 'Severe Weather')}",
                'description': alert_data.get('description', 'Severe weather conditions'),
                'category': 'weather',
                'subcategory': self._determine_weather_subcategory(alert_data.get('event', '')),
                'location': location,
                'severity': alert_data.get('severity', 'medium'),
                'source': 'weather',
                'source_id': f"weather_{int(time.time())}",
                'start_time': datetime.now().isoformat(),
                'end_time': (datetime.now() + timedelta(hours=24)).isoformat(),
                'is_active': True
            }

            self.csv.insert_alert(alert)

        except Exception as e:
            print(f"❌ Error creating weather alert: {e}")

    def _create_tweet_alert(self, tweet: Dict, classification):
        """Create alert from tweet"""
        try:
            alert = {
                'title': f"Social Media Alert: {classification.category.title()}",
                'description': tweet.get('text', '')[:200],
                'category': classification.category,
                'subcategory': classification.subcategory,
                'location': classification.location,
                'severity': classification.severity,
                'source': 'twitter',
                'source_id': f"tweet_{tweet.get('id', 'unknown')}",
                'start_time': datetime.now().isoformat(),
                'end_time': (datetime.now() + timedelta(hours=12)).isoformat(),
                'is_active': True
            }

            self.csv.insert_alert(alert)

        except Exception as e:
            print(f"❌ Error creating tweet alert: {e}")

    def _create_fuel_price_alert(self, fuel_type: str, change_data: Dict):
        """Create alert for significant fuel price changes"""
        try:
            # Map fuel type to readable name
            fuel_names = {
                'petrol_95': 'Petrol 95 Octane',
                'petrol_92': 'Petrol 92 Octane',
                'auto_diesel': 'Auto Diesel',
                'super_diesel': 'Super Diesel',
                'kerosene': 'Kerosene'
            }

            fuel_name = fuel_names.get(fuel_type, fuel_type.replace('_', ' ').title())

            # Determine severity based on percentage change
            change_pct = abs(change_data['change_pct'])
            if change_pct >= 10:
                severity = 'high'
            elif change_pct >= 5:
                severity = 'medium'
            else:
                severity = 'low'

            # Determine impact description
            trend = change_data['trend']
            if trend == 'up':
                impact = f"Price increase may affect transportation and operating costs"
            elif trend == 'down':
                impact = f"Price decrease may reduce operational expenses"
            else:
                impact = f"Price stability maintained"

            alert = {
                'title': f"Fuel Price Alert: {fuel_name}",
                'description': f"{fuel_name} price changed from Rs.{change_data['previous']} to Rs.{change_data['latest']} ({change_data['change_pct']:+.1f}%)",
                'category': 'economy',
                'subcategory': 'fuel_prices',
                'location': 'Sri Lanka',
                'severity': severity,
                'source': 'fuel_prices',
                'source_id': f"fuel_{fuel_type}_{int(time.time())}",
                'start_time': datetime.now().isoformat(),
                'end_time': (datetime.now() + timedelta(days=7)).isoformat(),
                'is_active': True,
                'impact': impact,
                'metadata': {
                    'fuel_type': fuel_type,
                    'old_price': change_data['previous'],
                    'new_price': change_data['latest'],
                    'change_absolute': change_data['change_abs'],
                    'change_percentage': change_data['change_pct'],
                    'trend': trend
                }
            }

            self.csv.insert_alert(alert)
            print(f"  🔔 Created alert for {fuel_name} price change")

        except Exception as e:
            print(f"❌ Error creating fuel price alert: {e}")

    def _determine_weather_subcategory(self, event: str) -> str:
        """Determine weather subcategory from event name"""
        event_lower = event.lower()

        if any(word in event_lower for word in ['flood', 'inundat']):
            return 'floods'
        elif any(word in event_lower for word in ['rain', 'shower', 'precipitation']):
            return 'rainfall_alerts'
        elif any(word in event_lower for word in ['cyclone', 'storm', 'hurricane']):
            return 'cyclones'
        elif any(word in event_lower for word in ['landslide', 'mudslide']):
            return 'land_slides'
        elif any(word in event_lower for word in ['heat', 'hot', 'temperature']):
            return 'heatwaves'
        elif any(word in event_lower for word in ['earthquake', 'tremor']):
            return 'earthquakes'
        else:
            return 'weather_general'

    # ============ UTILITY METHODS ============

    def _print_schedule_info(self):
        """Print schedule information"""
        print("\n" + "=" * 60)
        print("📅 DATA COLLECTION SCHEDULE")
        print("=" * 60)
        print(f"📰 News:      Every {self.config.NEWS_INTERVAL // 60} minutes")
        if self.has_weather_api:
            print(f"🌤️ Weather:   Every {self.config.WEATHER_INTERVAL // 60} minutes")
        if self.has_twitter_api:
            print(f"🐦 Tweets:    Every {self.config.TWITTER_INTERVAL // 3600} hours (API)")
        print(f"⛽ Fuel:      Every 15 days")
        print(f"🔔 Alerts:    Every 10 minutes")
        print(f"🧹 Cleanup:   Every hour")
        print(f"⚙️  Custom Scripts: Every {getattr(self.config, 'CUSTOM_SCRIPTS_INTERVAL', 1800) // 60} minutes")
        print("=" * 60)
        print(f"📊 News limit:     {self.config.MAX_NEWS_PER_RUN} items per run")
        if self.has_twitter_api:
            print(f"📊 Tweets limit:   {self.config.MAX_TWEETS_PER_RUN} tweets per run")
            usage = self.twitter_api.get_usage_stats() if self.has_twitter_api else None
            if usage:
                print(f"📊 Twitter usage:  {usage['monthly_used']}/{usage['monthly_limit']} this month")
                print(f"📊 Daily:          {usage['daily_used']}/{usage['daily_limit']} today")
        print("=" * 60)
        categories = list(self.classifier.keyword_patterns.keys()) if hasattr(self.classifier,
                                                                              'keyword_patterns') else []
        print(f"🎯 Monitoring categories: {', '.join(categories)}")
        print("=" * 60)

    def get_stats(self):
        """Get scheduler statistics"""
        twitter_usage = self.twitter_api.get_usage_stats() if self.has_twitter_api else None

        return {
            **self.stats,
            'last_run': datetime.now().isoformat(),
            'running': self.running,
            'tasks': len(self.tasks),
            'weather_enabled': self.has_weather_api,
            'twitter_enabled': self.has_twitter_api,
            'custom_scripts_enabled': True,
            'scripts_directory': self.scripts_dir,
            'custom_scripts_interval_minutes': getattr(self.config, 'CUSTOM_SCRIPTS_INTERVAL', 1800) // 60,
            'twitter_interval_hours': self.config.TWITTER_INTERVAL // 3600 if self.has_twitter_api else 0,
            'twitter_usage': twitter_usage
        }