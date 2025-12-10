from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os
import pandas as pd
import numpy as np
import time

from data_storage.csv_manager import CSVDataManager
from data_processing.classifier import NewsClassifier
from data_collection.weather_api import WeatherAPI
from data_collection.twitter_api import TwitterAPIClient
from data_collection.fuel_scraper import CeypetcoFuelScraper
from config.config import Config


def create_api_app(csv_manager: CSVDataManager, config):
    app = Flask(__name__)
    CORS(app)

    classifier = NewsClassifier()
    weather_api = WeatherAPI(config.OPENWEATHER_API_KEY) if config.OPENWEATHER_API_KEY else None
    twitter_api = TwitterAPIClient(config.TWITTER_BEARER_TOKEN) if config.TWITTER_BEARER_TOKEN else None
    fuel_scraper = CeypetcoFuelScraper()

    # ============ HELPER FUNCTIONS ============

    def get_district_coordinates(district_name):
        """Get coordinates for a Sri Lankan district"""
        district_coords = {
            'Colombo': {'lat': 6.9271, 'lon': 79.8612},
            'Gampaha': {'lat': 7.0917, 'lon': 79.9997},
            'Kalutara': {'lat': 6.5896, 'lon': 79.9573},
            'Kandy': {'lat': 7.2906, 'lon': 80.6337},
            'Matale': {'lat': 7.4675, 'lon': 80.6234},
            'Nuwara Eliya': {'lat': 6.9497, 'lon': 80.7891},
            'Galle': {'lat': 6.0535, 'lon': 80.2210},
            'Matara': {'lat': 5.9485, 'lon': 80.5353},
            'Jaffna': {'lat': 9.6615, 'lon': 80.0255},
            'Batticaloa': {'lat': 7.7172, 'lon': 81.6996}
        }
        return district_coords.get(district_name, {'lat': 6.9271, 'lon': 79.8612})  # Default to Colombo

    # ============ HOME ENDPOINT ============

    @app.route('/')
    def home():
        return jsonify({
            'name': 'Sri Lanka Situational Awareness API',
            'version': '1.0',
            'description': 'Real-time news, weather, social media, and fuel prices for Sri Lanka',
            'features': {
                'news': 'Real news from Ada Derana',
                'weather': f'Weather data for {len(config.SRI_LANKA_DISTRICTS)} districts' if weather_api else 'Weather data (API not configured)',
                'twitter': 'Tweets from Twitter/X API v2' if twitter_api else 'Twitter data (API not configured)',
                'fuel_prices': 'Ceypetco historical fuel prices',
                'alerts': 'Automated alerts from classified data',
                'storage': 'CSV file storage (no database)'
            },
            'endpoints': {
                '/': 'API documentation',
                '/api/news': 'GET - Get all news items with filters',
                '/api/weather': 'GET - Get weather data for location',
                '/api/weather/districts': f'GET - Get weather for all {len(config.SRI_LANKA_DISTRICTS)} districts',
                '/api/weather/refresh-all': 'POST - Refresh all district weather',
                '/api/weather/summary': 'GET - Get weather summary',
                '/api/weather/district/<name>': 'GET - Get weather for specific district',
                '/api/weather/map': 'GET - Get weather data for map visualization',
                '/api/weather/debug': 'GET - Debug weather API issues',
                '/api/twitter/stats': 'GET - Get Twitter API usage stats',
                '/api/tweets': 'GET - Get recent tweets',
                '/api/alerts': 'GET - Get active alerts',
                '/api/classify': 'POST - Classify text into categories',
                '/api/stats': 'GET - Get system statistics',
                '/api/health': 'GET - Health check',
                '/api/export/<type>': 'GET - Export data as CSV',
                '/api/locations': 'GET - Get available locations',
                '/api/data/current-location': 'POST - Get data for user location',
                '/api/data/summary': 'GET - Get summary of all data',
                '/api/fuel/latest': 'GET - Get latest fuel prices',
                '/api/fuel/history': 'GET - Get fuel price history',
                '/api/fuel/stats': 'GET - Get fuel price statistics',
                '/api/fuel/all': 'GET - Get all fuel price data',
                '/api/fuel/scrape-now': 'POST - Manually scrape fuel prices',
                '/api/fuel/analyze': 'GET - Analyze fuel price trends',
                '/api/fuel/trend/<fuel_type>': 'GET - Get fuel price trend analysis'
            },
            'districts_covered': config.SRI_LANKA_DISTRICTS,
            'timestamp': datetime.now().isoformat()
        })

    # ============ NEWS ENDPOINTS ============

    @app.route('/api/news', methods=['GET'])
    def get_news():
        """Get news with filtering options"""
        try:
            # Get query parameters
            category = request.args.get('category')
            location = request.args.get('location')
            severity = request.args.get('severity')
            limit = int(request.args.get('limit', 50))
            hours = int(request.args.get('hours', 24))

            # Get news from CSV
            news_items = csv_manager.get_recent_news(
                limit=limit,
                category=category,
                severity=severity,
                location=location,
                hours=hours
            )

            return jsonify({
                'count': len(news_items),
                'data': news_items,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    # ============ WEATHER ENDPOINTS ============

    @app.route('/api/weather', methods=['GET'])
    def get_weather():
        """Get weather data for a location - ONLY IF API AVAILABLE"""
        if not weather_api:
            return jsonify({
                'error': 'Weather API not configured. Please add OPENWEATHER_API_KEY to .env file.',
                'timestamp': datetime.now().isoformat()
            }), 503  # Service Unavailable

        try:
            location = request.args.get('location', 'Colombo')
            include_forecast = request.args.get('forecast', 'false').lower() == 'true'
            include_alerts = request.args.get('alerts', 'false').lower() == 'true'

            # Get latest weather from CSV first
            weather_data_list = csv_manager.get_latest_weather(location=location, limit=1)

            # If not in CSV or forced refresh, fetch from API
            force_refresh = request.args.get('refresh', 'false').lower() == 'true'

            if force_refresh or not weather_data_list:
                current = weather_api.get_current_weather(location)
                if not current:
                    return jsonify({
                        'error': f'Could not fetch weather data for {location}',
                        'timestamp': datetime.now().isoformat()
                    }), 404

                forecast = weather_api.get_hourly_forecast(location) if include_forecast else []
                alerts_data = weather_api.get_weather_alerts(location) if include_alerts else {'alerts': []}

                weather_data = {
                    'location': location,
                    'temperature': current.get('temperature'),
                    'feels_like': current.get('feels_like'),
                    'humidity': current.get('humidity'),
                    'weather': current.get('weather'),
                    'description': current.get('description'),
                    'wind_speed': current.get('wind_speed'),
                    'rain': current.get('rain', 0),
                    'alerts': alerts_data.get('alerts', []),
                    'forecast': forecast,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'api_fresh'
                }

                # Store in CSV
                csv_manager.insert_weather(weather_data)
                weather_data_list = [weather_data]
            else:
                # Mark as from cache
                weather_data = weather_data_list[0]
                weather_data['source'] = 'csv_cache'

            if weather_data_list:
                weather_data = weather_data_list[0]

                # Ensure forecast and alerts are included if they're strings
                if 'forecast' in weather_data and isinstance(weather_data['forecast'], str):
                    try:
                        weather_data['forecast'] = json.loads(weather_data['forecast'])
                    except:
                        weather_data['forecast'] = []

                if 'alerts' in weather_data and isinstance(weather_data['alerts'], str):
                    try:
                        weather_data['alerts'] = json.loads(weather_data['alerts'])
                    except:
                        weather_data['alerts'] = []

                # Limit forecast to next 24 hours
                if include_forecast and 'forecast' in weather_data:
                    weather_data['hourly_forecast'] = weather_data['forecast'][:24]

                return jsonify(weather_data)
            else:
                return jsonify({
                    'error': f'No weather data available for {location}',
                    'timestamp': datetime.now().isoformat()
                }), 404

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    @app.route('/api/weather/districts', methods=['GET'])
    def get_all_districts_weather():
        """Get weather for 10 Sri Lankan districts"""
        if not weather_api:
            return jsonify({
                'error': 'Weather API not configured',
                'timestamp': datetime.now().isoformat()
            }), 503

        try:
            limit = int(request.args.get('limit', 10))  # Default to 10
            refresh = request.args.get('refresh', 'false').lower() == 'true'
            delay = float(request.args.get('delay', 1.5))  # 1.5 second delay between calls

            all_districts = []

            # Get only the first 10 districts from config
            districts = config.SRI_LANKA_DISTRICTS[:limit]

            for i, district in enumerate(districts):
                if refresh:
                    # Force fresh API call with rate limiting
                    try:
                        # Add delay between API calls
                        if i > 0:  # Don't delay first call
                            time.sleep(delay)

                        print(f"Fetching weather for {district} ({i + 1}/{len(districts)})...")

                        current = weather_api.get_current_weather(district)
                        if current:
                            # For efficiency, only get current weather, not forecast/alerts
                            weather_record = {
                                'location': district,
                                'temperature': current.get('temperature'),
                                'feels_like': current.get('feels_like'),
                                'humidity': current.get('humidity'),
                                'weather': current.get('weather'),
                                'description': current.get('description'),
                                'wind_speed': current.get('wind_speed'),
                                'rain': current.get('rain', 0),
                                'timestamp': datetime.now().isoformat()
                            }

                            csv_manager.insert_weather(weather_record)

                            all_districts.append({
                                'district': district,
                                'weather': weather_record,
                                'source': 'api_fresh'
                            })
                            print(f"  ✅ {district}: {current.get('temperature')}°C, {current.get('weather')}")
                        else:
                            print(f"  ❌ Failed to fetch {district}")

                    except Exception as e:
                        print(f"  ❌ Error fetching {district}: {e}")
                        continue
                else:
                    # Get from CSV cache
                    weather_data = csv_manager.get_latest_weather(location=district, limit=1)
                    if weather_data:
                        weather = weather_data[0] if isinstance(weather_data, list) else weather_data

                        # Parse JSON fields if needed
                        if 'forecast' in weather and isinstance(weather['forecast'], str):
                            try:
                                weather['forecast'] = json.loads(weather['forecast'])
                            except:
                                weather['forecast'] = []

                        if 'alerts' in weather and isinstance(weather['alerts'], str):
                            try:
                                weather['alerts'] = json.loads(weather['alerts'])
                            except:
                                weather['alerts'] = []

                        all_districts.append({
                            'district': district,
                            'weather': weather,
                            'source': 'csv_cache'
                        })

            return jsonify({
                'count': len(all_districts),
                'total_districts': len(config.SRI_LANKA_DISTRICTS),
                'districts': all_districts,
                'note': f'Showing {len(all_districts)}/{len(config.SRI_LANKA_DISTRICTS)} districts. Use ?refresh=true to update.',
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    @app.route('/api/weather/refresh-all', methods=['POST'])
    def refresh_all_districts():
        """Refresh weather for all 10 districts"""
        if not weather_api:
            return jsonify({
                'error': 'Weather API not configured',
                'timestamp': datetime.now().isoformat()
            }), 503

        try:
            data = request.json or {}
            delay = data.get('delay', 2.0)  # 2-second delay between calls

            districts = config.SRI_LANKA_DISTRICTS  # All 10 districts
            collected = []
            failed = []

            print(f"🔄 Refreshing weather for {len(districts)} districts...")

            for i, district in enumerate(districts):
                try:
                    print(f"  {i + 1}. {district}...", end=" ")

                    current = weather_api.get_current_weather(district)
                    if current:
                        weather_record = {
                            'location': district,
                            'temperature': current.get('temperature'),
                            'feels_like': current.get('feels_like'),
                            'humidity': current.get('humidity'),
                            'weather': current.get('weather'),
                            'description': current.get('description'),
                            'wind_speed': current.get('wind_speed'),
                            'rain': current.get('rain', 0),
                            'timestamp': datetime.now().isoformat()
                        }

                        csv_manager.insert_weather(weather_record)
                        collected.append({
                            'district': district,
                            'temperature': current.get('temperature'),
                            'weather': current.get('weather')
                        })
                        print(f"✅ {current.get('temperature')}°C")
                    else:
                        failed.append(district)
                        print("❌ Failed")

                    # Add delay between calls (except last one)
                    if i < len(districts) - 1:
                        time.sleep(delay)

                except Exception as e:
                    print(f"❌ Error: {e}")
                    failed.append(district)
                    continue

            return jsonify({
                'success': True,
                'message': f'Refreshed {len(collected)} out of {len(districts)} districts',
                'collected': collected,
                'failed': failed,
                'total_time': f"{len(districts) * delay} seconds estimated",
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    @app.route('/api/weather/summary', methods=['GET'])
    def get_weather_summary():
        """Get weather summary across 10 districts"""
        if not weather_api:
            return jsonify({
                'error': 'Weather API not configured',
                'timestamp': datetime.now().isoformat()
            }), 503

        try:
            # Get weather data from CSV for all 10 districts
            recent_weather = []

            for district in config.SRI_LANKA_DISTRICTS:
                weather = csv_manager.get_latest_weather(location=district, limit=1)
                if weather:
                    recent_weather.append(weather[0] if isinstance(weather, list) else weather)

            summary = {
                'total_districts': len(config.SRI_LANKA_DISTRICTS),
                'districts_with_data': len(recent_weather),
                'districts_with_alerts': 0,
                'districts': {},
                'statistics': {}
            }

            if recent_weather:
                temperatures = []
                humidities = []
                wind_speeds = []

                for weather in recent_weather:
                    district = weather.get('location', 'Unknown')
                    temp = weather.get('temperature')
                    humidity = weather.get('humidity')
                    wind = weather.get('wind_speed')

                    if temp is not None:
                        temperatures.append(temp)
                    if humidity is not None:
                        humidities.append(humidity)
                    if wind is not None:
                        wind_speeds.append(wind)

                    alerts = weather.get('alerts', [])
                    if isinstance(alerts, str):
                        try:
                            alerts = json.loads(alerts)
                        except:
                            alerts = []

                    summary['districts'][district] = {
                        'temperature': temp,
                        'weather': weather.get('weather'),
                        'humidity': humidity,
                        'wind_speed': wind,
                        'alerts_count': len(alerts)
                    }

                    if len(alerts) > 0:
                        summary['districts_with_alerts'] += 1

                # Calculate statistics
                if temperatures:
                    summary['statistics']['temperature'] = {
                        'average': round(sum(temperatures) / len(temperatures), 1),
                        'min': min(temperatures),
                        'max': max(temperatures)
                    }

                if humidities:
                    summary['statistics']['humidity'] = {
                        'average': round(sum(humidities) / len(humidities), 1),
                        'min': min(humidities),
                        'max': max(humidities)
                    }

                if wind_speeds:
                    summary['statistics']['wind_speed'] = {
                        'average': round(sum(wind_speeds) / len(wind_speeds), 1),
                        'min': min(wind_speeds),
                        'max': max(wind_speeds)
                    }

            return jsonify({
                'summary': summary,
                'districts_list': config.SRI_LANKA_DISTRICTS,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    @app.route('/api/weather/district/<district_name>', methods=['GET'])
    def get_district_weather(district_name):
        """Get detailed weather for specific district"""
        if not weather_api:
            return jsonify({
                'error': 'Weather API not configured',
                'timestamp': datetime.now().isoformat()
            }), 503

        try:
            # Check if district is in our list
            if district_name not in config.SRI_LANKA_DISTRICTS:
                return jsonify({
                    'error': f'District "{district_name}" not in monitored districts. Available: {config.SRI_LANKA_DISTRICTS}',
                    'timestamp': datetime.now().isoformat()
                }), 404

            # Get coordinates for the district
            coords = get_district_coordinates(district_name)

            # Check if refresh is requested
            refresh = request.args.get('refresh', 'false').lower() == 'true'

            # Get from CSV first, unless refresh is requested
            if not refresh:
                weather_data = csv_manager.get_latest_weather(location=district_name, limit=1)
                if weather_data:
                    # Return from CSV
                    weather = weather_data[0] if isinstance(weather_data, list) else weather_data

                    # Parse forecast and alerts if they're strings
                    if 'forecast' in weather and isinstance(weather['forecast'], str):
                        try:
                            weather['forecast'] = json.loads(weather['forecast'])
                        except:
                            weather['forecast'] = []

                    if 'alerts' in weather and isinstance(weather['alerts'], str):
                        try:
                            weather['alerts'] = json.loads(weather['alerts'])
                        except:
                            weather['alerts'] = []

                    return jsonify({
                        'district': district_name,
                        'coordinates': coords,
                        'source': 'csv_cache',
                        'data': weather,
                        'timestamp': datetime.now().isoformat()
                    })

            # Fetch from API (either because refresh=true or no cached data)
            current = weather_api.get_current_weather(district_name)
            if not current:
                return jsonify({
                    'error': f'Could not fetch weather for {district_name}',
                    'timestamp': datetime.now().isoformat()
                }), 404

            # Get optional forecast and alerts
            include_forecast = request.args.get('forecast', 'false').lower() == 'true'
            include_alerts = request.args.get('alerts', 'false').lower() == 'true'

            forecast = weather_api.get_hourly_forecast(district_name) if include_forecast else []
            alerts = weather_api.get_weather_alerts(district_name) if include_alerts else {'alerts': []}

            # Store in CSV for future
            weather_record = {
                'location': district_name,
                'temperature': current.get('temperature'),
                'feels_like': current.get('feels_like'),
                'humidity': current.get('humidity'),
                'weather': current.get('weather'),
                'description': current.get('description'),
                'wind_speed': current.get('wind_speed'),
                'rain': current.get('rain', 0),
                'alerts': alerts.get('alerts', []),
                'forecast': forecast,
                'timestamp': datetime.now().isoformat()
            }

            csv_manager.insert_weather(weather_record)

            return jsonify({
                'district': district_name,
                'coordinates': coords,
                'source': 'api_fresh',
                'data': {
                    'current': current,
                    'forecast': forecast[:8] if forecast else [],  # Next 24 hours
                    'alerts': alerts.get('alerts', [])
                },
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    @app.route('/api/weather/map', methods=['GET'])
    def get_weather_map_data():
        """Get weather data formatted for map visualization - 10 districts only"""
        try:
            # Get all 10 districts with their coordinates
            map_data = []

            # Use only the 10 districts from config
            for district in config.SRI_LANKA_DISTRICTS:
                coords = get_district_coordinates(district)

                # Get weather data from CSV cache
                weather = csv_manager.get_latest_weather(location=district, limit=1)

                if weather:
                    weather = weather[0] if isinstance(weather, list) else weather

                    # Parse alerts if string
                    alerts = weather.get('alerts', [])
                    if isinstance(alerts, str):
                        try:
                            alerts = json.loads(alerts)
                        except:
                            alerts = []

                    map_data.append({
                        'name': district,
                        'coordinates': coords,
                        'weather': {
                            'temperature': weather.get('temperature'),
                            'condition': weather.get('weather'),
                            'description': weather.get('description'),
                            'humidity': weather.get('humidity'),
                            'wind_speed': weather.get('wind_speed'),
                            'rain': weather.get('rain', 0)
                        },
                        'alerts_count': len(alerts),
                        'updated': weather.get('timestamp'),
                        'source': 'cache'
                    })
                else:
                    # No data yet for this district
                    map_data.append({
                        'name': district,
                        'coordinates': coords,
                        'weather': None,
                        'alerts_count': 0,
                        'updated': None,
                        'source': 'no_data'
                    })

            return jsonify({
                'map_data': map_data,
                'total_districts': len(map_data),
                'note': f'Showing {len(map_data)} districts. Use /api/weather/refresh-all to update.',
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    @app.route('/api/weather/debug', methods=['GET'])
    def debug_weather_api():
        """Debug weather API issues"""
        if not weather_api:
            return jsonify({
                'status': 'not_configured',
                'message': 'Weather API not configured',
                'timestamp': datetime.now().isoformat()
            }), 503

        try:
            # Test API with a simple call
            test_location = "Colombo"
            result = weather_api.get_current_weather(test_location)

            return jsonify({
                'status': 'working' if result else 'failed',
                'test_location': test_location,
                'result': result,
                'api_key_configured': bool(weather_api.api_key and len(weather_api.api_key) > 10),
                'api_key_length': len(weather_api.api_key) if weather_api.api_key else 0,
                'districts_configured': len(config.SRI_LANKA_DISTRICTS),
                'districts_list': config.SRI_LANKA_DISTRICTS,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    @app.route('/api/weather/current', methods=['POST'])
    def get_weather_for_current_location():
        """Get weather for device's current location - ONLY IF API AVAILABLE"""
        if not weather_api:
            return jsonify({
                'error': 'Weather API not configured',
                'timestamp': datetime.now().isoformat()
            }), 503

        try:
            data = request.json
            if not data:
                return jsonify({'error': 'No JSON data provided', 'timestamp': datetime.now().isoformat()}), 400

            latitude = data.get('latitude')
            longitude = data.get('longitude')

            if not latitude or not longitude:
                return jsonify(
                    {'error': 'Latitude and longitude are required', 'timestamp': datetime.now().isoformat()}), 400

            # Get weather for current location
            weather_data = weather_api.get_current_weather(lat=latitude, lon=longitude)
            if not weather_data:
                return jsonify({
                    'error': 'Could not fetch weather for current location',
                    'timestamp': datetime.now().isoformat()
                }), 404

            forecast = weather_api.get_hourly_forecast(lat=latitude, lon=longitude)
            alerts = weather_api.get_weather_alerts(weather_data.get('location', 'Unknown'))

            return jsonify({
                'current': weather_data,
                'hourly_forecast': forecast[:24] if forecast else [],  # Next 24 hours
                'alerts': alerts.get('alerts', []),
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    # ============ TWITTER ENDPOINTS ============

    @app.route('/api/twitter/stats', methods=['GET'])
    def get_twitter_stats():
        """Get Twitter API usage statistics"""
        try:
            if not twitter_api:
                return jsonify({
                    'error': 'Twitter API not configured',
                    'timestamp': datetime.now().isoformat()
                }), 503

            stats = twitter_api.get_usage_stats()
            return jsonify({
                'stats': stats,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    @app.route('/api/tweets', methods=['GET'])
    def get_tweets():
        """Get recent tweets from Twitter API"""
        try:
            category = request.args.get('category')
            limit = int(request.args.get('limit', 10))
            hours = int(request.args.get('hours', 24))

            tweets = csv_manager.get_recent_tweets(
                limit=limit,
                category=category,
                hours=hours
            )

            return jsonify({
                'count': len(tweets),
                'data': tweets,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    # ============ ALERT ENDPOINTS ============

    @app.route('/api/alerts', methods=['GET'])
    def get_alerts():
        """Get active alerts with filtering"""
        try:
            category = request.args.get('category')
            severity = request.args.get('severity')
            location = request.args.get('location')
            source = request.args.get('source')
            hours = int(request.args.get('hours', 24))

            alerts = csv_manager.get_active_alerts(
                severity=severity,
                category=category,
                location=location,
                source=source,
                hours=hours
            )

            return jsonify({
                'count': len(alerts),
                'data': alerts,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    # ============ CLASSIFICATION ENDPOINT ============

    @app.route('/api/classify', methods=['POST'])
    def classify_text():
        """Classify a text input into categories"""
        try:
            data = request.json
            if not data:
                return jsonify({'error': 'No JSON data provided', 'timestamp': datetime.now().isoformat()}), 400

            text = data.get('text', '')
            if not text:
                return jsonify({'error': 'No text provided', 'timestamp': datetime.now().isoformat()}), 400

            # Classify the text
            result = classifier.classify(text)

            return jsonify({
                'category': result.category,
                'subcategory': result.subcategory,
                'location': result.location,
                'impact': result.impact,
                'severity': result.severity,
                'confidence': result.confidence,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    # ============ STATISTICS ENDPOINT ============

    @app.route('/api/stats', methods=['GET'])
    def get_stats():
        """Get system statistics"""
        try:
            stats = csv_manager.get_statistics()
            # Add API status
            stats['apis'] = {
                'weather': bool(weather_api),
                'twitter': bool(twitter_api),
                'fuel_scraper': True
            }
            # Add districts info
            stats['districts'] = {
                'total': len(config.SRI_LANKA_DISTRICTS),
                'list': config.SRI_LANKA_DISTRICTS
            }
            return jsonify(stats)
        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    # ============ HEALTH CHECK ============

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        try:
            # Get statistics
            stats = csv_manager.get_statistics()

            # Check CSV files
            csv_files = ['news.csv', 'weather.csv', 'tweets.csv', 'alerts.csv', 'fuel_prices.csv']
            data_dir = 'data'

            file_status = {}
            for file in csv_files:
                file_path = os.path.join(data_dir, file)
                exists = os.path.exists(file_path)
                readable = False
                lines = 0

                if exists:
                    try:
                        with open(file_path, 'r') as f:
                            lines = len(f.readlines())
                        readable = lines > 0
                    except:
                        readable = False

                file_status[file] = {
                    'exists': exists,
                    'readable': readable,
                    'lines': lines
                }

            # Check weather data for districts
            district_weather = {}
            for district in config.SRI_LANKA_DISTRICTS:
                weather = csv_manager.get_latest_weather(location=district, limit=1)
                district_weather[district] = len(weather) > 0 if weather else False

            return jsonify({
                'status': 'healthy',
                'storage': 'csv_files',
                'timestamp': datetime.now().isoformat(),
                'file_status': file_status,
                'district_weather_status': district_weather,
                'data_summary': {
                    'total_news': stats.get('total_news', 0),
                    'total_tweets': stats.get('total_tweets', 0),
                    'total_weather': stats.get('total_weather', 0),
                    'total_fuel_prices': stats.get('total_fuel_prices', 0),
                    'active_alerts': stats.get('active_alerts', 0)
                },
                'apis_configured': {
                    'weather': bool(weather_api),
                    'twitter': bool(twitter_api),
                    'fuel_scraper': True
                },
                'districts_monitored': {
                    'count': len(config.SRI_LANKA_DISTRICTS),
                    'list': config.SRI_LANKA_DISTRICTS
                }
            })
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    # ============ EXPORT ENDPOINT ============

    @app.route('/api/export/<data_type>', methods=['GET'])
    def export_data(data_type):
        """Export data as CSV file"""
        try:
            if data_type == 'news':
                file_path = csv_manager.news_file
                filename = 'news_export.csv'
            elif data_type == 'weather':
                file_path = csv_manager.weather_file
                filename = 'weather_export.csv'
            elif data_type == 'tweets':
                file_path = csv_manager.tweets_file
                filename = 'tweets_export.csv'
            elif data_type == 'alerts':
                file_path = csv_manager.alerts_file
                filename = 'alerts_export.csv'
            elif data_type == 'fuel':
                file_path = csv_manager.fuel_file
                filename = 'fuel_prices_export.csv'
            else:
                return jsonify({'error': 'Invalid data type', 'timestamp': datetime.now().isoformat()}), 400

            if not os.path.exists(file_path):
                return jsonify(
                    {'error': f'No {data_type} data available', 'timestamp': datetime.now().isoformat()}), 404

            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='text/csv'
            )

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    # ============ LOCATIONS ENDPOINT ============

    @app.route('/api/locations', methods=['GET'])
    def get_locations():
        """Get available locations in Sri Lanka (10 districts)"""
        sri_lanka_locations = []

        # Add all 10 districts
        for district in config.SRI_LANKA_DISTRICTS:
            coords = get_district_coordinates(district)
            sri_lanka_locations.append({
                "name": district,
                "type": "district",
                "lat": coords['lat'],
                "lon": coords['lon']
            })

        return jsonify({
            'count': len(sri_lanka_locations),
            'locations': sri_lanka_locations,
            'timestamp': datetime.now().isoformat()
        })

    # ============ CURRENT LOCATION DATA ============

    @app.route('/api/data/current-location', methods=['POST'])
    def get_data_for_current_location():
        """Get all data (news, weather, alerts, tweets) for user's current location"""
        try:
            data = request.json
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            city = data.get('city')
            district = data.get('district')

            results = {
                'location': {},
                'weather': {},
                'news': [],
                'alerts': [],
                'tweets': [],
                'fuel_prices': {}
            }

            # Determine location name
            location_name = None
            if district:
                location_name = district
                results['location'] = {
                    'name': district,
                    'type': 'district',
                    'source': 'user_selected'
                }
            elif city:
                location_name = city
                results['location'] = {
                    'name': city,
                    'type': 'city',
                    'source': 'user_selected'
                }
            elif latitude and longitude:
                # Try to get location name from coordinates
                if weather_api:
                    current_weather = weather_api.get_current_weather(lat=latitude, lon=longitude)
                    if current_weather:
                        location_name = current_weather.get('location', 'Unknown')
                        results['location'] = {
                            'name': location_name,
                            'coordinates': {'latitude': latitude, 'longitude': longitude},
                            'type': 'gps',
                            'source': 'gps'
                        }
                    else:
                        location_name = "Unknown"
                        results['location'] = {
                            'name': 'Unknown',
                            'coordinates': {'latitude': latitude, 'longitude': longitude},
                            'type': 'gps',
                            'source': 'gps'
                        }
                else:
                    location_name = "Unknown"
                    results['location'] = {
                        'name': 'Unknown',
                        'coordinates': {'latitude': latitude, 'longitude': longitude},
                        'type': 'gps',
                        'source': 'gps'
                    }
            else:
                return jsonify({'error': 'Provide location information (city, district, or coordinates)',
                                'timestamp': datetime.now().isoformat()}), 400

            # 1. Get weather for location
            if weather_api:
                if latitude and longitude:
                    current_weather = weather_api.get_current_weather(lat=latitude, lon=longitude)
                    forecast = weather_api.get_hourly_forecast(lat=latitude, lon=longitude)
                elif location_name:
                    current_weather = weather_api.get_current_weather(location_name)
                    forecast = weather_api.get_hourly_forecast(location_name)

                if current_weather:
                    results['weather'] = {
                        'current': current_weather,
                        'forecast': forecast[:8] if forecast else []  # Next 24 hours
                    }

            # 2. Get news for this location
            news_items = csv_manager.get_recent_news(
                limit=10,
                location=location_name,
                hours=24
            )
            results['news'] = news_items

            # 3. Get alerts for this location
            alerts = csv_manager.get_active_alerts(
                location=location_name,
                hours=24
            )
            results['alerts'] = alerts

            # 4. Get tweets mentioning this location
            tweets = csv_manager.get_recent_tweets(
                limit=10,
                hours=24
            )
            # Filter tweets mentioning this location
            if location_name != "Unknown":
                location_tweets = [tweet for tweet in tweets if location_name.lower() in tweet.get('text', '').lower()]
                results['tweets'] = location_tweets
            else:
                results['tweets'] = tweets[:5]  # Just get some recent tweets

            # 5. Get latest fuel prices (national level)
            fuel_prices = csv_manager.get_latest_fuel_price()
            if fuel_prices:
                results['fuel_prices'] = fuel_prices

            return jsonify({
                'success': True,
                'location_info': results['location'],
                'data': {
                    'weather': results['weather'],
                    'news_count': len(results['news']),
                    'news': results['news'][:5],  # Limit to 5 news items
                    'alerts_count': len(results['alerts']),
                    'alerts': results['alerts'],
                    'tweets_count': len(results['tweets']),
                    'tweets': results['tweets'][:5],  # Limit to 5 tweets
                    'fuel_prices': results['fuel_prices']
                },
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    # ============ DATA SUMMARY ============

    @app.route('/api/data/summary', methods=['GET'])
    def get_data_summary():
        """Get summary of all data"""
        try:
            # Get recent news count
            recent_news = csv_manager.get_recent_news(limit=100, hours=24)

            # Get active alerts count
            active_alerts = csv_manager.get_active_alerts()

            # Get recent tweets count
            recent_tweets = csv_manager.get_recent_tweets(limit=100, hours=24)

            # Get weather data for our 10 districts
            weather_data = {}
            for district in config.SRI_LANKA_DISTRICTS:
                weather = csv_manager.get_latest_weather(location=district, limit=1)
                if weather:
                    weather_data[district] = weather[0] if isinstance(weather, list) else weather

            # Get latest fuel prices
            fuel_prices = csv_manager.get_latest_fuel_price()

            # Get statistics by category
            news_by_category = {}
            if recent_news:
                for news in recent_news:
                    category = news.get('category', 'unknown')
                    news_by_category[category] = news_by_category.get(category, 0) + 1

            # Get alerts by severity
            alerts_by_severity = {}
            if active_alerts:
                for alert in active_alerts:
                    severity = alert.get('severity', 'unknown')
                    alerts_by_severity[severity] = alerts_by_severity.get(severity, 0) + 1

            # Get weather summary
            weather_summary = {
                'districts_monitored': len(weather_data),
                'total_districts': len(config.SRI_LANKA_DISTRICTS),
                'sample_districts': list(weather_data.keys())
            }

            return jsonify({
                'summary': {
                    'total_news_24h': len(recent_news),
                    'total_alerts_active': len(active_alerts),
                    'total_tweets_24h': len(recent_tweets),
                    'weather_districts_monitored': weather_summary['districts_monitored'],
                    'fuel_prices_available': fuel_prices is not None
                },
                'distribution': {
                    'news_by_category': news_by_category,
                    'alerts_by_severity': alerts_by_severity
                },
                'sample_weather': weather_data,
                'fuel_prices': fuel_prices,
                'weather_summary': weather_summary,
                'districts_list': config.SRI_LANKA_DISTRICTS,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    # ============ FUEL PRICE ENDPOINTS ============

    @app.route('/api/fuel/latest', methods=['GET'])
    def get_latest_fuel():
        """Get latest fuel prices"""
        try:
            latest = csv_manager.get_latest_fuel_price()

            if not latest:
                return jsonify({
                    'error': 'No fuel price data available',
                    'timestamp': datetime.now().isoformat()
                }), 404

            return jsonify({
                'data': latest,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    @app.route('/api/fuel/history', methods=['GET'])
    def get_fuel_history():
        """Get fuel price history"""
        try:
            limit = int(request.args.get('limit', 30))
            days = int(request.args.get('days', 90))

            # Calculate start date
            start_date = (datetime.now() - timedelta(days=days)).isoformat()

            history = csv_manager.get_fuel_price_history(
                limit=limit,
                start_date=start_date
            )

            return jsonify({
                'count': len(history),
                'data': history,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    @app.route('/api/fuel/stats', methods=['GET'])
    def get_fuel_stats():
        """Get fuel price statistics"""
        try:
            stats = csv_manager.get_fuel_price_stats()

            return jsonify({
                'stats': stats,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    @app.route('/api/fuel/all', methods=['GET'])
    def get_all_fuel():
        """Get all fuel price data"""
        try:
            all_fuel = csv_manager.get_all_fuel_prices()

            return jsonify({
                'count': len(all_fuel),
                'data': all_fuel,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    @app.route('/api/fuel/scrape-now', methods=['POST'])
    def scrape_fuel_now():
        """Manually trigger fuel price scraping"""
        try:
            print("Manual fuel price scraping triggered via API")

            # Get latest prices
            latest_prices = fuel_scraper.get_latest_fuel_prices()

            if not latest_prices:
                return jsonify({
                    'error': 'Could not scrape fuel prices',
                    'timestamp': datetime.now().isoformat()
                }), 500

            # Store in CSV
            fuel_id = csv_manager.insert_fuel_price(latest_prices)

            # Get price changes
            changes = fuel_scraper.get_fuel_price_changes()

            return jsonify({
                'success': True,
                'message': f'Fuel prices scraped and stored (ID: {fuel_id})',
                'record_id': fuel_id,
                'latest_date': latest_prices.get('date'),
                'price_changes': changes.get('changes', {}),
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    @app.route('/api/fuel/analyze', methods=['GET'])
    def analyze_fuel_trends():
        """Analyze fuel price trends"""
        try:
            days = int(request.args.get('days', 30))
            history = csv_manager.get_fuel_price_history(limit=60)

            if not history or len(history) < 2:
                return jsonify({
                    'error': 'Insufficient data for analysis',
                    'timestamp': datetime.now().isoformat()
                }), 400

            # Convert to DataFrame for analysis
            df = pd.DataFrame(history)

            # Convert date strings to datetime
            df['date'] = pd.to_datetime(df['date'])

            # Sort by date
            df = df.sort_values('date')

            analysis = {
                'trends': {},
                'volatility': {},
                'recommendations': []
            }

            # Analyze key fuel types
            key_fuels = ['petrol_95', 'auto_diesel', 'kerosene']

            for fuel in key_fuels:
                if fuel in df.columns:
                    prices = df[fuel].dropna()
                    if len(prices) > 1:
                        # Calculate trend (simple linear regression)
                        x = np.arange(len(prices))
                        slope, intercept = np.polyfit(x, prices, 1)

                        # Calculate volatility (standard deviation)
                        volatility = prices.std()

                        # Determine trend direction
                        if slope > 0.5:
                            trend = 'strong_up'
                        elif slope > 0.1:
                            trend = 'up'
                        elif slope < -0.5:
                            trend = 'strong_down'
                        elif slope < -0.1:
                            trend = 'down'
                        else:
                            trend = 'stable'

                        analysis['trends'][fuel] = {
                            'current_price': prices.iloc[-1] if len(prices) > 0 else None,
                            'trend': trend,
                            'slope_per_day': round(slope, 3),
                            'volatility': round(volatility, 2),
                            'min_price': prices.min(),
                            'max_price': prices.max(),
                            'change_30d': round(((prices.iloc[-1] - prices.iloc[0]) / prices.iloc[0]) * 100, 2) if len(
                                prices) > 1 and prices.iloc[0] > 0 else 0
                        }

            # Generate business recommendations
            if 'petrol_95' in analysis['trends']:
                petrol_trend = analysis['trends']['petrol_95']['trend']
                if petrol_trend in ['strong_up', 'up']:
                    analysis['recommendations'].append({
                        'type': 'warning',
                        'message': 'Petrol prices are rising. Consider optimizing fuel consumption and transportation routes.',
                        'impact': 'high',
                        'action': 'Review fuel efficiency strategies'
                    })

            if 'auto_diesel' in analysis['trends']:
                diesel_trend = analysis['trends']['auto_diesel']['trend']
                if diesel_trend == 'strong_up':
                    analysis['recommendations'].append({
                        'type': 'alert',
                        'message': 'Diesel prices increasing significantly. This affects transportation and logistics costs.',
                        'impact': 'high',
                        'action': 'Consider fuel surcharges or alternative logistics'
                    })

            return jsonify({
                'analysis': analysis,
                'data_points': len(history),
                'period': {
                    'start': history[-1]['date'] if history else None,
                    'end': history[0]['date'] if history else None
                },
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    @app.route('/api/fuel/trend/<fuel_type>', methods=['GET'])
    def get_fuel_trend(fuel_type):
        """Get fuel price trend analysis for specific fuel type"""
        try:
            days = int(request.args.get('days', 30))

            trend_data = csv_manager.get_fuel_price_trend(fuel_type=fuel_type, days=days)

            if not trend_data:
                return jsonify({
                    'error': f'No trend data available for {fuel_type}',
                    'timestamp': datetime.now().isoformat()
                }), 404

            return jsonify({
                'trend': trend_data,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'error': str(e), 'timestamp': datetime.now().isoformat()}), 500

    return app