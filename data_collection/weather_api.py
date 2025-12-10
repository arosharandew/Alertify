import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from config.config import Config


class WeatherAPI:
    """Real OpenWeatherMap API client for Sri Lankan districts"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"

        # Load Sri Lankan districts from config
        config = Config()
        self.sri_lanka_districts = config.SRI_LANKA_DISTRICTS

        # Rate limiting control
        self.last_request_time = 0
        self.min_request_interval = 1  # 1 second between requests to avoid rate limits

        print(f"WeatherAPI initialized with {len(self.sri_lanka_districts)} Sri Lankan districts")

    def _wait_for_rate_limit(self):
        """Wait if needed to avoid rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            time_to_wait = self.min_request_interval - time_since_last
            time.sleep(time_to_wait)

        self.last_request_time = time.time()

    def get_current_weather(self, city: str = None, lat: float = None, lon: float = None) -> Optional[Dict]:
        """Get real current weather for a location"""
        try:
            self._wait_for_rate_limit()

            if city:
                # For Sri Lankan cities, append country code
                url = f"{self.base_url}/weather?q={city},LK&appid={self.api_key}&units=metric"
            elif lat and lon:
                url = f"{self.base_url}/weather?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
            else:
                return None

            response = requests.get(url, timeout=15)
            data = response.json()

            if response.status_code == 200:
                weather_data = {
                    'location': data.get('name', 'Unknown'),
                    'temperature': data['main']['temp'],
                    'feels_like': data['main']['feels_like'],
                    'humidity': data['main']['humidity'],
                    'pressure': data['main']['pressure'],
                    'weather': data['weather'][0]['main'],
                    'description': data['weather'][0]['description'],
                    'wind_speed': data['wind']['speed'],
                    'wind_deg': data['wind'].get('deg', 0),
                    'visibility': data.get('visibility', 10000),
                    'clouds': data['clouds']['all'],
                    'rain': data.get('rain', {}).get('1h', 0),
                    'snow': data.get('snow', {}).get('1h', 0),
                    'timestamp': datetime.fromtimestamp(data['dt']).isoformat(),
                    'sunrise': datetime.fromtimestamp(data['sys']['sunrise']).isoformat(),
                    'sunset': datetime.fromtimestamp(data['sys']['sunset']).isoformat(),
                    'country': data['sys']['country'],
                    'coord': data['coord'],
                    'weather_id': data['weather'][0]['id'],
                    'weather_icon': data['weather'][0]['icon']
                }

                # Add weather severity based on conditions
                weather_data['severity'] = self._determine_weather_severity(
                    weather_data['weather'],
                    weather_data['weather_id'],
                    weather_data['rain'],
                    weather_data['snow'],
                    weather_data['wind_speed']
                )

                return weather_data
            else:
                print(f"Weather API error for {city if city else f'{lat},{lon}'}: {data.get('message', 'Unknown error')}")
                return None

        except Exception as e:
            print(f"Error getting weather: {e}")
            return None

    def get_hourly_forecast(self, city: str = None, lat: float = None, lon: float = None) -> List[Dict]:
        """Get real 48-hour hourly forecast"""
        try:
            self._wait_for_rate_limit()

            if city:
                url = f"{self.base_url}/forecast?q={city},LK&appid={self.api_key}&units=metric"
            elif lat and lon:
                url = f"{self.base_url}/forecast?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
            else:
                return []

            response = requests.get(url, timeout=15)
            data = response.json()

            if response.status_code == 200:
                forecast = []
                for item in data['list'][:16]:  # Next 48 hours (3-hour intervals)
                    forecast.append({
                        'time': datetime.fromtimestamp(item['dt']).isoformat(),
                        'temperature': item['main']['temp'],
                        'feels_like': item['main']['feels_like'],
                        'humidity': item['main']['humidity'],
                        'pressure': item['main']['pressure'],
                        'weather': item['weather'][0]['main'],
                        'description': item['weather'][0]['description'],
                        'weather_id': item['weather'][0]['id'],
                        'weather_icon': item['weather'][0]['icon'],
                        'wind_speed': item['wind']['speed'],
                        'wind_deg': item['wind']['deg'],
                        'precipitation': item.get('pop', 0) * 100,  # Probability of precipitation
                        'rain': item.get('rain', {}).get('3h', 0),
                        'snow': item.get('snow', {}).get('3h', 0),
                        'clouds': item['clouds']['all']
                    })
                return forecast
            else:
                print(f"Forecast API error: {data.get('message', 'Unknown error')}")
                return []

        except Exception as e:
            print(f"Error getting forecast: {e}")
            return []

    def get_weather_alerts(self, location: str) -> Dict:
        """Get weather alerts for a location"""
        try:
            self._wait_for_rate_limit()

            # Get coordinates for location
            geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location},LK&limit=1&appid={self.api_key}"
            geo_response = requests.get(geo_url, timeout=10)
            geo_data = geo_response.json()

            if geo_data:
                lat, lon = geo_data[0]['lat'], geo_data[0]['lon']

                # Use One Call API 3.0 for alerts
                url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,daily&appid={self.api_key}"

                response = requests.get(url, timeout=10)
                data = response.json()

                alerts = data.get('alerts', [])
                return {
                    'location': location,
                    'alerts': [{
                        'event': alert.get('event', ''),
                        'description': alert.get('description', ''),
                        'start': datetime.fromtimestamp(alert.get('start', 0)).isoformat() if alert.get('start') else None,
                        'end': datetime.fromtimestamp(alert.get('end', 0)).isoformat() if alert.get('end') else None,
                        'severity': self._determine_alert_severity(alert.get('event', ''))
                    } for alert in alerts]
                }
            return {'location': location, 'alerts': []}

        except Exception as e:
            print(f"Error getting alerts for {location}: {e}")
            return {'location': location, 'alerts': []}

    def get_all_districts_weather(self, max_districts: int = 10, show_progress: bool = True) -> Dict:
        """Get weather for Sri Lankan districts with rate limiting"""
        weather_data = {}

        # Only show progress if requested
        if show_progress:
            print(f"🌤️ Collecting weather for {max_districts} districts...")

        for i, district in enumerate(self.sri_lanka_districts[:max_districts]):
            try:
                if show_progress:
                    print(f"  {i + 1}. {district}...", end=" ")

                # Add delay between requests to avoid rate limiting
                time.sleep(1.2)  # Wait 1.2 seconds between calls

                current = self.get_current_weather(district)
                if current:
                    # Add small delay between subsequent API calls
                    time.sleep(0.5)
                    forecast = self.get_hourly_forecast(district)

                    time.sleep(0.5)
                    alerts = self.get_weather_alerts(district)

                    weather_data[district] = {
                        'current': current,
                        'forecast': forecast,
                        'alerts': alerts.get('alerts', []),
                        'collected_at': datetime.now().isoformat()
                    }

                    if show_progress:
                        print(f"✅")
                else:
                    if show_progress:
                        print(f"❌ (No data)")
                    continue

            except Exception as e:
                if show_progress:
                    print(f"❌ Error getting weather for {district}: {e}")
                continue

        return weather_data

    def get_weather_summary(self, weather_data: Dict = None) -> Dict:
        """Get summary of weather across all districts - uses existing data if provided"""
        # Use provided weather data if available, otherwise collect minimal data silently
        if weather_data is None:
            all_weather = self.get_all_districts_weather(max_districts=5, show_progress=False)  # Silent mode
        else:
            all_weather = weather_data

        summary = {
            'total_districts': len(all_weather),
            'districts_with_alerts': 0,
            'hottest_district': None,
            'coldest_district': None,
            'rainiest_district': None,
            'districts': {}
        }

        if not all_weather:
            return summary

        max_temp = -float('inf')
        min_temp = float('inf')
        max_rain = -float('inf')

        for district, data in all_weather.items():
            current = data.get('current', {})
            alerts = data.get('alerts', [])

            summary['districts'][district] = {
                'temperature': current.get('temperature'),
                'weather': current.get('weather'),
                'severity': current.get('severity', 'low'),
                'alerts_count': len(alerts)
            }

            # Track extremes
            temp = current.get('temperature', 0)
            rain = current.get('rain', 0)

            if temp > max_temp:
                max_temp = temp
                summary['hottest_district'] = {
                    'name': district,
                    'temperature': temp
                }

            if temp < min_temp:
                min_temp = temp
                summary['coldest_district'] = {
                    'name': district,
                    'temperature': temp
                }

            if rain > max_rain:
                max_rain = rain
                summary['rainiest_district'] = {
                    'name': district,
                    'rain': rain
                }

            if alerts:
                summary['districts_with_alerts'] += 1

        return summary

    def get_weather_summary_only(self) -> Dict:
        """Get summary only (no district collection) - for API endpoints"""
        return self.get_weather_summary()

    def _determine_weather_severity(self, weather: str, weather_id: int,
                                    rain: float, snow: float, wind_speed: float) -> str:
        """Determine weather severity based on conditions"""

        # Check for extreme conditions
        if weather_id in [781, 900, 901, 902, 903, 904, 905, 906]:  # Tornado, hurricane, etc.
            return 'high'

        # Check wind speed (Beaufort scale)
        if wind_speed > 20:  # Strong gale or higher
            return 'high'
        elif wind_speed > 15:  # Gale
            return 'medium'

        # Check precipitation
        if rain > 20:  # Heavy rain
            return 'high'
        elif rain > 10:  # Moderate rain
            return 'medium'

        if snow > 10:  # Heavy snow
            return 'high'
        elif snow > 5:  # Moderate snow
            return 'medium'

        # Check weather type
        severe_weather = ['Thunderstorm', 'Squall', 'Tornado']
        moderate_weather = ['Rain', 'Snow', 'Drizzle']

        if weather in severe_weather:
            return 'high'
        elif weather in moderate_weather:
            return 'medium'
        else:
            return 'low'

    def _determine_alert_severity(self, event: str) -> str:
        """Determine severity based on weather event"""
        event_lower = event.lower()

        high_severity = ['cyclone', 'hurricane', 'tsunami', 'flood warning',
                         'landslide', 'tornado', 'severe thunderstorm', 'extreme']
        medium_severity = ['heavy rain', 'thunderstorm', 'lightning',
                           'strong wind', 'storm', 'warning', 'alert']
        low_severity = ['rain', 'cloudy', 'fog', 'haze', 'drizzle', 'advisory']

        for keyword in high_severity:
            if keyword in event_lower:
                return 'high'

        for keyword in medium_severity:
            if keyword in event_lower:
                return 'medium'

        for keyword in low_severity:
            if keyword in event_lower:
                return 'low'

        return 'low'