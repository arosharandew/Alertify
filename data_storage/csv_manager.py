import csv
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from pathlib import Path


class CSVDataManager:
    """Manages data storage in CSV files instead of database"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Define CSV file paths
        self.news_file = self.data_dir / "news.csv"
        self.weather_file = self.data_dir / "weather.csv"
        self.tweets_file = self.data_dir / "tweets.csv"
        self.alerts_file = self.data_dir / "alerts.csv"
        self.fuel_file = self.data_dir / "fuel_prices.csv"

        # Initialize CSV files with headers if they don't exist
        self._initialize_csv_files()

    def _initialize_csv_files(self):
        """Create CSV files with headers if they don't exist"""

        # News CSV
        if not self.news_file.exists():
            with open(self.news_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'id', 'title', 'summary', 'full_text', 'link', 'source',
                    'category', 'subcategory', 'location', 'impact', 'severity',
                    'keywords', 'timestamp', 'processed_at'
                ])

        # Weather CSV
        if not self.weather_file.exists():
            with open(self.weather_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'id', 'location', 'temperature', 'feels_like', 'humidity',
                    'weather', 'description', 'wind_speed', 'rain', 'alerts',
                    'forecast', 'timestamp'
                ])

        # Tweets CSV
        if not self.tweets_file.exists():
            with open(self.tweets_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'id', 'text', 'author_id', 'retweet_count', 'like_count',
                    'hashtags', 'mentions', 'location', 'category', 'severity',
                    'timestamp', 'source', 'scraped_at'
                ])

        # Alerts CSV
        if not self.alerts_file.exists():
            with open(self.alerts_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'id', 'title', 'description', 'category', 'subcategory',
                    'location', 'severity', 'source', 'source_id', 'start_time',
                    'end_time', 'created_at', 'is_active'
                ])

        # Fuel Prices CSV
        if not self.fuel_file.exists():
            with open(self.fuel_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'id', 'date', 'date_str', 'petrol_95', 'petrol_92',
                    'auto_diesel', 'super_diesel', 'kerosene', 'industrial_kerosene',
                    'furnace_800', 'furnace_1500_high', 'furnace_1500_low',
                    'location', 'source', 'scraped_at', 'recorded_at'
                ])

    def _generate_id(self) -> str:
        """Generate a unique ID"""
        return str(int(datetime.now().timestamp() * 1000))

    def _parse_timestamp(self, timestamp_str: str) -> pd.Timestamp:
        """Parse timestamp string to pandas Timestamp (force timezone-naive)"""
        if pd.isna(timestamp_str) or timestamp_str is None or timestamp_str == '':
            return pd.Timestamp.now()

        try:
            # Parse as pandas Timestamp and FORCE timezone-naive
            dt = pd.to_datetime(timestamp_str)

            # If it has timezone, remove it
            if dt.tz is not None:
                dt = dt.tz_localize(None)

            return dt
        except:
            try:
                # Try any format
                dt = pd.to_datetime(timestamp_str, errors='coerce')
                if pd.isna(dt):
                    return pd.Timestamp.now()

                # If it has timezone, remove it
                if dt.tz is not None:
                    dt = dt.tz_localize(None)

                return dt
            except:
                return pd.Timestamp.now()
    # ============ NEWS OPERATIONS ============

    def insert_news(self, news_data: Dict) -> str:
        """Insert news item into CSV"""
        news_id = self._generate_id()

        # Prepare data for CSV
        row = [
            news_id,
            news_data.get('title', ''),
            news_data.get('summary', ''),
            news_data.get('full_text', ''),
            news_data.get('link', ''),
            news_data.get('source', ''),
            news_data.get('category', ''),
            news_data.get('subcategory', ''),
            news_data.get('location', ''),
            news_data.get('impact', ''),
            news_data.get('severity', ''),
            json.dumps(news_data.get('keywords', [])),
            news_data.get('timestamp', pd.Timestamp.now().isoformat()),
            pd.Timestamp.now().isoformat()
        ]

        with open(self.news_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)

        return news_id

    def get_recent_news(self, limit: int = 50, category: str = None,
                        severity: str = None, location: str = None,
                        hours: int = 24) -> List[Dict]:
        """Get recent news with filters"""
        try:
            df = pd.read_csv(self.news_file)

            if df.empty:
                return []

            # Parse timestamps
            df['timestamp'] = df['timestamp'].apply(self._parse_timestamp)

            # Filter by time
            time_threshold = pd.Timestamp.now() - pd.Timedelta(hours=hours)
            df = df[df['timestamp'] >= time_threshold]

            # Apply filters
            if category:
                df = df[df['category'] == category]
            if severity:
                df = df[df['severity'] == severity]
            if location:
                df = df[df['location'].str.contains(location, na=False)]

            # Sort and limit
            df = df.sort_values('timestamp', ascending=False).head(limit)

            # Convert to list of dictionaries
            result = []
            for _, row in df.iterrows():
                item = row.to_dict()
                # Convert pandas types
                for col in ['timestamp', 'processed_at']:
                    if col in item and isinstance(item[col], pd.Timestamp):
                        item[col] = item[col].isoformat()
                # Parse JSON fields
                if 'keywords' in item and isinstance(item['keywords'], str):
                    try:
                        item['keywords'] = json.loads(item['keywords'])
                    except:
                        item['keywords'] = []
                result.append(item)

            return result

        except Exception as e:
            print(f"Error reading news CSV: {e}")
            return []

    # ============ WEATHER OPERATIONS ============

    def insert_weather(self, weather_data: Dict) -> str:
        """Insert weather data into CSV"""
        weather_id = self._generate_id()

        # Prepare alerts and forecast as JSON strings
        alerts_str = json.dumps(weather_data.get('alerts', []))
        forecast_str = json.dumps(weather_data.get('forecast', []))

        row = [
            weather_id,
            weather_data.get('location', ''),
            weather_data.get('temperature', 0),
            weather_data.get('feels_like', 0),
            weather_data.get('humidity', 0),
            weather_data.get('weather', ''),
            weather_data.get('description', ''),
            weather_data.get('wind_speed', 0),
            weather_data.get('rain', 0),
            alerts_str,
            forecast_str,
            weather_data.get('timestamp', pd.Timestamp.now().isoformat())
        ]

        with open(self.weather_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)

        return weather_id

    def get_latest_weather(self, location: str = None, limit: int = 10) -> List[Dict]:
        """Get latest weather data"""
        try:
            df = pd.read_csv(self.weather_file)

            if df.empty:
                return []

            # Parse timestamps
            df['timestamp'] = df['timestamp'].apply(self._parse_timestamp)

            # Filter by location if specified
            if location:
                df = df[df['location'] == location]

            # Sort and limit
            df = df.sort_values('timestamp', ascending=False).head(limit)

            # Convert to list of dictionaries
            result = []
            for _, row in df.iterrows():
                item = row.to_dict()
                # Convert pandas types
                if 'timestamp' in item and isinstance(item['timestamp'], pd.Timestamp):
                    item['timestamp'] = item['timestamp'].isoformat()
                # Parse JSON fields
                for field in ['alerts', 'forecast']:
                    if field in item and isinstance(item[field], str):
                        try:
                            item[field] = json.loads(item[field])
                        except:
                            item[field] = []
                result.append(item)

            return result

        except Exception as e:
            print(f"Error reading weather CSV: {e}")
            return []

    def get_weather_by_district(self, district: str = None, limit: int = 10) -> Dict:
        """Get weather data by district"""
        try:
            if district:
                # Get specific district
                weather_data = self.get_latest_weather(location=district, limit=limit)
                return {
                    'district': district,
                    'count': len(weather_data),
                    'data': weather_data
                }
            else:
                # Get all districts weather
                from config.config import Config
                config = Config()
                districts = config.SRI_LANKA_DISTRICTS

                all_weather = {}
                for district in districts[:20]:  # Limit to 20 districts
                    weather = self.get_latest_weather(location=district, limit=1)
                    if weather:
                        all_weather[district] = weather[0] if isinstance(weather, list) else weather

                return {
                    'total_districts': len(all_weather),
                    'data': all_weather
                }

        except Exception as e:
            print(f"Error getting weather by district: {e}")
            return {}

    # ============ TWEET OPERATIONS ============

    def insert_tweet(self, tweet_data: Dict) -> str:
        """Insert tweet into CSV"""
        tweet_id = tweet_data.get('id', self._generate_id())

        # Check if tweet already exists
        try:
            df = pd.read_csv(self.tweets_file)
            if tweet_id in df['id'].values:
                return tweet_id  # Already exists
        except:
            pass

        row = [
            tweet_id,
            tweet_data.get('text', ''),
            tweet_data.get('author_id', ''),
            tweet_data.get('retweet_count', 0),
            tweet_data.get('like_count', 0),
            json.dumps(tweet_data.get('hashtags', [])),
            json.dumps(tweet_data.get('mentions', [])),
            tweet_data.get('location', ''),
            tweet_data.get('category', ''),
            tweet_data.get('severity', ''),
            tweet_data.get('timestamp', pd.Timestamp.now().isoformat()),
            tweet_data.get('source', 'twitter_api'),
            pd.Timestamp.now().isoformat()
        ]

        with open(self.tweets_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)

        return tweet_id

    def get_recent_tweets(self, limit: int = 10, category: str = None,
                          hours: int = 24) -> List[Dict]:
        """Get recent tweets"""
        try:
            df = pd.read_csv(self.tweets_file)

            if df.empty:
                return []

            # Parse timestamps
            df['timestamp'] = df['timestamp'].apply(self._parse_timestamp)

            # Filter by time
            time_threshold = pd.Timestamp.now() - pd.Timedelta(hours=hours)
            df = df[df['timestamp'] >= time_threshold]

            # Apply category filter
            if category:
                df = df[df['category'] == category]

            # Sort and limit
            df = df.sort_values('timestamp', ascending=False).head(limit)

            # Convert to list of dictionaries
            result = []
            for _, row in df.iterrows():
                item = row.to_dict()
                # Convert pandas types
                for col in ['timestamp', 'scraped_at']:
                    if col in item and isinstance(item[col], pd.Timestamp):
                        item[col] = item[col].isoformat()
                # Parse JSON fields
                for field in ['hashtags', 'mentions']:
                    if field in item and isinstance(item[field], str):
                        try:
                            item[field] = json.loads(item[field])
                        except:
                            item[field] = []
                result.append(item)

            return result

        except Exception as e:
            print(f"Error reading tweets CSV: {e}")
            return []

    # ============ ALERT OPERATIONS ============

    def insert_alert(self, alert_data: Dict) -> str:
        """Insert alert into CSV"""
        alert_id = self._generate_id()

        row = [
            alert_id,
            alert_data.get('title', ''),
            alert_data.get('description', ''),
            alert_data.get('category', ''),
            alert_data.get('subcategory', ''),
            alert_data.get('location', ''),
            alert_data.get('severity', ''),
            alert_data.get('source', ''),
            alert_data.get('source_id', ''),
            alert_data.get('start_time', pd.Timestamp.now().isoformat()),
            alert_data.get('end_time', (pd.Timestamp.now() + pd.Timedelta(hours=24)).isoformat()),
            pd.Timestamp.now().isoformat(),
            alert_data.get('is_active', True)
        ]

        with open(self.alerts_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)

        return alert_id

    def get_active_alerts(self, severity: str = None, category: str = None,
                          location: str = None, source: str = None,
                          source_id: str = None, hours: int = 24) -> List[Dict]:
        """Get active alerts with filters"""
        try:
            df = pd.read_csv(self.alerts_file)

            if df.empty:
                return []

            # Filter active alerts
            df = df[df['is_active'] == True]

            # Apply filters
            if severity:
                df = df[df['severity'] == severity]
            if category:
                df = df[df['category'] == category]
            if location:
                df = df[df['location'].str.contains(location, na=False)]
            if source:
                df = df[df['source'] == source]
            if source_id:
                df = df[df['source_id'] == source_id]

            # Parse timestamps
            df['created_at'] = df['created_at'].apply(self._parse_timestamp)
            df['start_time'] = df['start_time'].apply(self._parse_timestamp)
            df['end_time'] = df['end_time'].apply(self._parse_timestamp)

            # Filter by time if specified
            if hours:
                time_threshold = pd.Timestamp.now() - pd.Timedelta(hours=hours)
                df = df[df['created_at'] >= time_threshold]

            # Sort by created_at
            df = df.sort_values('created_at', ascending=False)

            # Convert to list of dictionaries
            result = []
            for _, row in df.iterrows():
                item = row.to_dict()
                # Convert pandas types
                for col in ['created_at', 'start_time', 'end_time']:
                    if col in item and isinstance(item[col], pd.Timestamp):
                        item[col] = item[col].isoformat()
                result.append(item)

            return result

        except Exception as e:
            print(f"Error reading alerts CSV: {e}")
            return []

    # ============ FUEL PRICE OPERATIONS ============

    def insert_fuel_price(self, fuel_data: Dict) -> str:
        """Insert fuel price data into CSV with duplicate checking"""
        fuel_id = self._generate_id()

        # Check if this date already exists
        duplicate_found = False
        existing_id = None

        try:
            if self.fuel_file.exists() and os.path.getsize(self.fuel_file) > 0:
                df = pd.read_csv(self.fuel_file)
                if not df.empty and 'date_str' in df.columns:
                    current_date_str = str(fuel_data.get('date_str', '')).strip()
                    existing_dates = df['date_str'].astype(str).str.strip()

                    # Check for exact match
                    if current_date_str in existing_dates.values:
                        duplicate_found = True
                        existing_idx = df[existing_dates == current_date_str].index
                        if not existing_idx.empty:
                            existing_id = df.loc[existing_idx[0], 'id']
                            print(f"  ⚠️ Fuel price for '{current_date_str}' already exists (ID: {existing_id})")
                            return existing_id
        except Exception as e:
            print(f"  ⚠️ Error checking duplicates: {e}")
            # Continue with insertion

        # Prepare the row data
        row_data = {
            'id': fuel_id,
            'date': fuel_data.get('date', ''),
            'date_str': fuel_data.get('date_str', ''),
            'petrol_95': fuel_data.get('petrol_95'),
            'petrol_92': fuel_data.get('petrol_92'),
            'auto_diesel': fuel_data.get('auto_diesel'),
            'super_diesel': fuel_data.get('super_diesel'),
            'kerosene': fuel_data.get('kerosene'),
            'industrial_kerosene': fuel_data.get('industrial_kerosene'),
            'furnace_800': fuel_data.get('furnace_800'),
            'furnace_1500_high': fuel_data.get('furnace_1500_high'),
            'furnace_1500_low': fuel_data.get('furnace_1500_low'),
            'location': fuel_data.get('location', 'Sri Lanka'),
            'source': fuel_data.get('source', 'ceypetco'),
            'scraped_at': fuel_data.get('scraped_at', pd.Timestamp.now().isoformat()),
            'recorded_at': pd.Timestamp.now().isoformat()
        }

        # Write to CSV using pandas for better handling
        try:
            # Read existing data if file exists
            if self.fuel_file.exists() and os.path.getsize(self.fuel_file) > 0:
                df = pd.read_csv(self.fuel_file)

                # Ensure all columns exist
                for col in ['id', 'date', 'date_str', 'petrol_95', 'petrol_92', 'auto_diesel',
                            'super_diesel', 'kerosene', 'industrial_kerosene', 'furnace_800',
                            'furnace_1500_high', 'furnace_1500_low', 'location', 'source',
                            'scraped_at', 'recorded_at']:
                    if col not in df.columns:
                        df[col] = None

                # Append new row
                new_df = pd.DataFrame([row_data])
                df = pd.concat([df, new_df], ignore_index=True)
            else:
                # Create new dataframe
                df = pd.DataFrame([row_data])

            # Save back to CSV
            df.to_csv(self.fuel_file, index=False)
            return fuel_id

        except Exception as e:
            print(f"Error writing fuel price with pandas: {e}")
            # Fallback to CSV writer
            try:
                file_exists = self.fuel_file.exists() and os.path.getsize(self.fuel_file) > 0

                with open(self.fuel_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)

                    # Write headers if file is empty
                    if not file_exists:
                        writer.writerow([
                            'id', 'date', 'date_str', 'petrol_95', 'petrol_92',
                            'auto_diesel', 'super_diesel', 'kerosene', 'industrial_kerosene',
                            'furnace_800', 'furnace_1500_high', 'furnace_1500_low',
                            'location', 'source', 'scraped_at', 'recorded_at'
                        ])

                    writer.writerow([
                        row_data['id'],
                        row_data['date'],
                        row_data['date_str'],
                        row_data['petrol_95'],
                        row_data['petrol_92'],
                        row_data['auto_diesel'],
                        row_data['super_diesel'],
                        row_data['kerosene'],
                        row_data['industrial_kerosene'],
                        row_data['furnace_800'],
                        row_data['furnace_1500_high'],
                        row_data['furnace_1500_low'],
                        row_data['location'],
                        row_data['source'],
                        row_data['scraped_at'],
                        row_data['recorded_at']
                    ])
                return fuel_id
            except Exception as e2:
                print(f"Fallback CSV write also failed: {e2}")
                return fuel_id

    def get_latest_fuel_price(self) -> Optional[Dict]:
        """Get the latest fuel price data"""
        try:
            if not self.fuel_file.exists() or os.path.getsize(self.fuel_file) == 0:
                return None

            df = pd.read_csv(self.fuel_file)
            if df.empty:
                return None

            # Ensure date column exists
            if 'date' not in df.columns:
                return None

            # Parse dates
            df['date'] = pd.to_datetime(df['date'], errors='coerce')

            # Remove rows with invalid dates
            df = df.dropna(subset=['date'])

            if df.empty:
                return None

            # Get latest record
            latest_idx = df['date'].idxmax()
            latest = df.loc[latest_idx].to_dict()

            # Convert numpy types to Python types
            for key, value in latest.items():
                if pd.isna(value):
                    latest[key] = None
                elif isinstance(value, (np.integer, np.floating)):
                    latest[key] = float(value)
                elif isinstance(value, pd.Timestamp):
                    latest[key] = value.isoformat()

            return latest

        except Exception as e:
            print(f"Error getting latest fuel price: {e}")
            return None

    def get_fuel_price_history(self, limit: int = 30, start_date: str = None) -> List[Dict]:
        """Get fuel price history"""
        try:
            if not self.fuel_file.exists():
                return []

            df = pd.read_csv(self.fuel_file)
            if df.empty:
                return []

            # Ensure date column exists
            if 'date' not in df.columns:
                return []

            # Parse dates
            df['date'] = pd.to_datetime(df['date'], errors='coerce')

            # Remove rows with invalid dates
            df = df.dropna(subset=['date'])

            # Filter by start date if provided
            if start_date:
                try:
                    start_dt = pd.to_datetime(start_date)
                    df = df[df['date'] >= start_dt]
                except:
                    pass

            # Sort by date descending
            df = df.sort_values('date', ascending=False)

            # Limit results
            df = df.head(limit)

            # Convert to list of dictionaries
            result = []
            for _, row in df.iterrows():
                item = row.to_dict()
                # Convert pandas types
                for key, value in item.items():
                    if pd.isna(value):
                        item[key] = None
                    elif isinstance(value, (np.integer, np.floating)):
                        item[key] = float(value)
                    elif isinstance(value, pd.Timestamp):
                        item[key] = value.isoformat()
                result.append(item)

            return result

        except Exception as e:
            print(f"Error getting fuel price history: {e}")
            return []

    def get_all_fuel_prices(self) -> List[Dict]:
        """Get ALL fuel price data"""
        try:
            if not self.fuel_file.exists():
                return []

            df = pd.read_csv(self.fuel_file)
            if df.empty:
                return []

            # Ensure date column exists
            if 'date' not in df.columns:
                return []

            # Parse dates
            df['date'] = pd.to_datetime(df['date'], errors='coerce')

            # Remove rows with invalid dates
            df = df.dropna(subset=['date'])

            # Sort by date descending
            df = df.sort_values('date', ascending=False)

            # Convert to list of dictionaries
            result = []
            for _, row in df.iterrows():
                item = row.to_dict()
                # Convert pandas types
                for key, value in item.items():
                    if pd.isna(value):
                        item[key] = None
                    elif isinstance(value, (np.integer, np.floating)):
                        item[key] = float(value)
                    elif isinstance(value, pd.Timestamp):
                        item[key] = value.isoformat()
                result.append(item)

            return result

        except Exception as e:
            print(f"Error getting all fuel prices: {e}")
            return []

    def get_fuel_price_stats(self) -> Dict:
        """Get fuel price statistics"""
        try:
            if not self.fuel_file.exists():
                return {}

            df = pd.read_csv(self.fuel_file)
            if df.empty:
                return {}

            # Ensure date column exists
            if 'date' not in df.columns:
                return {}

            # Convert date column
            df['date'] = pd.to_datetime(df['date'], errors='coerce')

            # Remove invalid dates
            df_valid = df.dropna(subset=['date'])

            if df_valid.empty:
                return {}

            # Get date range
            earliest = df_valid['date'].min()
            latest = df_valid['date'].max()

            stats = {
                'total_records': len(df_valid),
                'date_range': {
                    'earliest': earliest.isoformat() if not pd.isna(earliest) else None,
                    'latest': latest.isoformat() if not pd.isna(latest) else None
                }
            }

            # Get latest prices
            latest_data = self.get_latest_fuel_price()
            if latest_data:
                stats['current_prices'] = {}
                fuel_columns = ['petrol_95', 'petrol_92', 'auto_diesel', 'super_diesel', 'kerosene']

                for col in fuel_columns:
                    if col in latest_data and latest_data[col] is not None:
                        stats['current_prices'][col] = latest_data[col]

            # Calculate price ranges for key fuels
            key_fuels = ['petrol_95', 'auto_diesel', 'kerosene']
            price_ranges = {}

            for fuel in key_fuels:
                if fuel in df_valid.columns:
                    prices = df_valid[fuel].dropna()
                    if len(prices) > 0:
                        price_ranges[fuel] = {
                            'min': float(prices.min()),
                            'max': float(prices.max()),
                            'average': float(prices.mean()),
                            'latest': latest_data.get(fuel) if latest_data else None
                        }

            if price_ranges:
                stats['price_ranges'] = price_ranges

            return stats

        except Exception as e:
            print(f"Error getting fuel price stats: {e}")
            return {}

    def get_fuel_price_trend(self, fuel_type: str = 'petrol_95', days: int = 30) -> Dict:
        """Get fuel price trend for specific fuel type"""
        try:
            if not self.fuel_file.exists():
                return {}

            df = pd.read_csv(self.fuel_file)
            if df.empty or fuel_type not in df.columns:
                return {}

            # Ensure date column exists
            if 'date' not in df.columns:
                return {}

            # Parse dates
            df['date'] = pd.to_datetime(df['date'], errors='coerce')

            # Remove rows with invalid dates or missing fuel price
            df = df.dropna(subset=['date', fuel_type])

            # Sort by date
            df = df.sort_values('date')

            # Filter by last N days if requested
            if days > 0:
                cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=days)
                df = df[df['date'] >= cutoff_date]

            if df.empty:
                return {}

            # Prepare trend data
            trend_data = {
                'fuel_type': fuel_type,
                'data_points': len(df),
                'start_date': df['date'].min().isoformat(),
                'end_date': df['date'].max().isoformat(),
                'prices': []
            }

            # Add price points
            for _, row in df.iterrows():
                trend_data['prices'].append({
                    'date': row['date'].isoformat(),
                    'date_str': row.get('date_str', ''),
                    'price': float(row[fuel_type])
                })

            # Calculate trend (simple linear regression)
            if len(df) > 1:
                x = np.arange(len(df))
                y = df[fuel_type].values

                # Fit linear regression
                slope, intercept = np.polyfit(x, y, 1)

                # Calculate percentage change
                first_price = y[0]
                last_price = y[-1]
                if first_price > 0:
                    pct_change = ((last_price - first_price) / first_price) * 100
                else:
                    pct_change = 0

                trend_data['trend_analysis'] = {
                    'slope_per_day': float(slope),
                    'percentage_change': float(pct_change),
                    'trend': 'up' if slope > 0 else ('down' if slope < 0 else 'stable'),
                    'start_price': float(first_price),
                    'end_price': float(last_price),
                    'absolute_change': float(last_price - first_price)
                }

            return trend_data

        except Exception as e:
            print(f"Error getting fuel price trend: {e}")
            return {}

    # ============ STATISTICS ============

    def get_statistics(self) -> Dict:
        """Get system statistics"""
        stats = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'storage_type': 'csv_files'
        }

        try:
            # Count news items
            if self.news_file.exists() and os.path.getsize(self.news_file) > 0:
                df = pd.read_csv(self.news_file)
                stats['total_news'] = len(df)

                # News by category
                if 'category' in df.columns:
                    news_by_category = df['category'].value_counts().to_dict()
                    stats['news_by_category'] = news_by_category

            # Count tweets
            if self.tweets_file.exists() and os.path.getsize(self.tweets_file) > 0:
                df = pd.read_csv(self.tweets_file)
                stats['total_tweets'] = len(df)

            # Count weather records
            if self.weather_file.exists() and os.path.getsize(self.weather_file) > 0:
                df = pd.read_csv(self.weather_file)
                stats['total_weather'] = len(df)

            # Count active alerts
            if self.alerts_file.exists() and os.path.getsize(self.alerts_file) > 0:
                df = pd.read_csv(self.alerts_file)
                active_alerts = df[df['is_active'] == True]
                stats['active_alerts'] = len(active_alerts)

                # Alerts by severity
                if 'severity' in df.columns:
                    alerts_by_severity = df['severity'].value_counts().to_dict()
                    stats['alerts_by_severity'] = alerts_by_severity

            # Count fuel price records
            if self.fuel_file.exists() and os.path.getsize(self.fuel_file) > 0:
                df = pd.read_csv(self.fuel_file)
                stats['total_fuel_prices'] = len(df)

                # Get fuel price stats
                fuel_stats = self.get_fuel_price_stats()
                if fuel_stats:
                    stats['fuel_stats'] = fuel_stats

        except Exception as e:
            print(f"Error getting statistics: {e}")

        return stats

    # ============ CLEANUP OPERATIONS ============

    def cleanup_old_data(self, days_old: int = 7):
        """Remove data older than specified days"""
        try:
            # Create cutoff date
            cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=days_old)

            print(f"🧹 Cleaning up data older than {cutoff_date.date()}...")

            # Clean weather (keep 30 days)
            if self.weather_file.exists() and os.path.getsize(self.weather_file) > 0:
                df = pd.read_csv(self.weather_file)
                if 'timestamp' in df.columns and not df.empty:
                    df['timestamp'] = df['timestamp'].apply(self._parse_timestamp)
                    weather_cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
                    df = df[df['timestamp'] >= weather_cutoff]
                    df.to_csv(self.weather_file, index=False)
                    print(f"  ✅ Cleaned weather data: kept {len(df)} records")

            # Clean tweets (keep 30 days)
            if self.tweets_file.exists() and os.path.getsize(self.tweets_file) > 0:
                df = pd.read_csv(self.tweets_file)
                if 'timestamp' in df.columns and not df.empty:
                    df['timestamp'] = df['timestamp'].apply(self._parse_timestamp)
                    tweets_cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
                    df = df[df['timestamp'] >= tweets_cutoff]
                    df.to_csv(self.tweets_file, index=False)
                    print(f"  ✅ Cleaned tweet data: kept {len(df)} records")

            # Deactivate old alerts (older than 3 days)
            if self.alerts_file.exists() and os.path.getsize(self.alerts_file) > 0:
                df = pd.read_csv(self.alerts_file)
                if 'created_at' in df.columns and not df.empty:
                    df['created_at'] = df['created_at'].apply(self._parse_timestamp)
                    alerts_cutoff = pd.Timestamp.now() - pd.Timedelta(days=3)

                    # Mark old alerts as inactive
                    mask = df['created_at'] < alerts_cutoff
                    if mask.any():
                        df.loc[mask, 'is_active'] = False
                        df.to_csv(self.alerts_file, index=False)
                        print(f"  ✅ Deactivated {mask.sum()} old alerts")
                    else:
                        print(f"  ℹ️ No old alerts to deactivate")

            # Keep ALL fuel prices (historical data is valuable)
            # No cleanup needed for fuel prices

            print(f"✅ Cleanup completed successfully")

        except Exception as e:
            print(f"❌ Error cleaning up data: {e}")
            import traceback
            traceback.print_exc()

    # ============ EXPORT OPERATIONS ============

    def export_to_dataframe(self, data_type: str) -> Optional[pd.DataFrame]:
        """Export data as pandas DataFrame"""
        try:
            if data_type == 'news':
                file_path = self.news_file
            elif data_type == 'weather':
                file_path = self.weather_file
            elif data_type == 'tweets':
                file_path = self.tweets_file
            elif data_type == 'alerts':
                file_path = self.alerts_file
            elif data_type == 'fuel':
                file_path = self.fuel_file
            else:
                return None

            if not file_path.exists() or os.path.getsize(file_path) == 0:
                return None

            df = pd.read_csv(file_path)
            return df

        except Exception as e:
            print(f"Error exporting {data_type} to DataFrame: {e}")
            return None

    # ============ BACKUP OPERATIONS ============

    def create_backup(self, backup_dir: str = "backups"):
        """Create backup of all CSV files"""
        try:
            backup_path = Path(backup_dir)
            backup_path.mkdir(exist_ok=True)

            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")

            files_to_backup = [
                (self.news_file, f"news_backup_{timestamp}.csv"),
                (self.weather_file, f"weather_backup_{timestamp}.csv"),
                (self.tweets_file, f"tweets_backup_{timestamp}.csv"),
                (self.alerts_file, f"alerts_backup_{timestamp}.csv"),
                (self.fuel_file, f"fuel_backup_{timestamp}.csv")
            ]

            for source_file, backup_name in files_to_backup:
                if source_file.exists() and os.path.getsize(source_file) > 0:
                    backup_file = backup_path / backup_name
                    import shutil
                    shutil.copy2(source_file, backup_file)

            print(f"✅ Created backup in {backup_dir}/")
            return True

        except Exception as e:
            print(f"❌ Error creating backup: {e}")
            return False