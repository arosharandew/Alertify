import requests
import json
import time
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
from dataclasses import dataclass


@dataclass
class TweetData:
    id: str
    text: str
    author_id: str
    created_at: str
    retweet_count: int
    like_count: int
    reply_count: int
    quote_count: int
    hashtags: List[str]
    mentions: List[str]


class TwitterAPIClient:
    """Twitter/X API Client for Free Tier (100 posts/month)"""

    def __init__(self, bearer_token: str = None,
                 api_key: str = None, api_secret: str = None,
                 access_token: str = None, access_token_secret: str = None):

        # API v2 (Free tier - 100 posts/month)
        self.bearer_token = bearer_token or os.getenv('TWITTER_BEARER_TOKEN')

        # API v1.1 (Free tier has VERY limited access - mostly read-only)
        self.api_key = api_key or os.getenv('TWITTER_API_KEY')
        self.api_secret = api_secret or os.getenv('TWITTER_API_SECRET')
        self.access_token = access_token or os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_token_secret = access_token_secret or os.getenv('TWITTER_ACCESS_TOKEN_SECRET')

        self.base_url_v2 = "https://api.twitter.com/2"
        self.base_url_v1 = "https://api.twitter.com/1.1"

        self.headers_v2 = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }

        # Get v1.1 bearer token if we have API key/secret
        self.bearer_token_v1 = None
        self.v1_1_enabled = False  # Free tier has limited v1.1 access
        if self.api_key and self.api_secret:
            self.bearer_token_v1 = self._get_bearer_token_v1()
            if self.bearer_token_v1:
                # Test if v1.1 is actually accessible (free tier may not have access)
                self.v1_1_enabled = self._test_v1_access()

        # Rate limiting for free tier (100 posts/month)
        self.monthly_limit = 100
        self.monthly_count = 0
        self.last_reset = datetime.now()

        # Daily limit approximation (100/30 ≈ 3 per day)
        self.daily_limit = 3
        self.daily_count = 0

        # Request tracking for rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2  # Minimum 2 seconds between requests

        # Load usage stats from file if exists
        self._load_usage_stats()

        print(f"Twitter API Client initialized")
        print(f"  • API v2: {'✓ Enabled' if self.bearer_token else '✗ Disabled'}")
        print(f"  • API v1.1: {'✓ Enabled (limited)' if self.v1_1_enabled else '✗ Disabled or limited access'}")

    def _get_bearer_token_v1(self):
        """Get bearer token for API v1.1 using API key and secret"""
        try:
            print("Attempting to get Twitter API v1.1 bearer token...")

            # Encode API key and secret
            key_secret = f"{self.api_key}:{self.api_secret}".encode('ascii')
            b64_encoded_key = base64.b64encode(key_secret).decode('ascii')

            headers = {
                'Authorization': f'Basic {b64_encoded_key}',
                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
            }

            data = {'grant_type': 'client_credentials'}

            response = requests.post(
                'https://api.twitter.com/oauth2/token',
                headers=headers,
                data=data,
                timeout=30
            )

            if response.status_code == 200:
                token_data = response.json()
                token = token_data.get('access_token')
                print("✓ Twitter API v1.1 bearer token obtained")
                return token
            else:
                print(f"✗ Failed to get v1.1 bearer token: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"✗ Error getting v1.1 bearer token: {e}")
            return None

    def _test_v1_access(self):
        """Test if v1.1 API is accessible with free tier"""
        try:
            headers = {"Authorization": f"Bearer {self.bearer_token_v1}"}
            response = requests.get(
                f"{self.base_url_v1}/application/rate_limit_status.json",
                headers=headers,
                timeout=10
            )
            # Even if we get a 403, the API might still work for some endpoints
            # Free tier has limited v1.1 access
            return response.status_code in [200, 403]
        except:
            return False

    def _load_usage_stats(self):
        """Load usage statistics from file"""
        stats_file = "data/twitter_stats.json"
        if os.path.exists(stats_file):
            try:
                with open(stats_file, 'r') as f:
                    stats = json.load(f)
                    self.monthly_count = stats.get('monthly_count', 0)
                    self.daily_count = stats.get('daily_count', 0)
                    last_reset_str = stats.get('last_reset')
                    if last_reset_str:
                        self.last_reset = datetime.fromisoformat(last_reset_str)
                    print(f"Loaded Twitter API usage stats: {self.monthly_count}/{self.monthly_limit} monthly")
            except Exception as e:
                print(f"Error loading Twitter stats: {e}")
                pass

    def _save_usage_stats(self):
        """Save usage statistics to file"""
        try:
            stats_file = "data/twitter_stats.json"
            os.makedirs("data", exist_ok=True)
            stats = {
                'monthly_count': self.monthly_count,
                'daily_count': self.daily_count,
                'last_reset': self.last_reset.isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            print(f"Error saving Twitter stats: {e}")

    def _check_rate_limit(self) -> bool:
        """Check if we can make API calls within limits"""
        now = datetime.now()

        # Reset daily count if new day
        if now.date() > self.last_reset.date():
            self.daily_count = 0
            self.last_reset = now
            print("Daily Twitter API limit reset")

        # Check monthly limit
        if self.monthly_count >= self.monthly_limit:
            print(f"✗ Monthly Twitter API limit reached ({self.monthly_count}/{self.monthly_limit})")
            return False

        # Check daily limit
        if self.daily_count >= self.daily_limit:
            print(f"✗ Daily Twitter API limit reached ({self.daily_count}/{self.daily_limit})")
            return False

        # Check request interval (prevent 429 errors)
        current_time = time.time()
        if current_time - self.last_request_time < self.min_request_interval:
            time_to_wait = self.min_request_interval - (current_time - self.last_request_time)
            time.sleep(time_to_wait)

        return True

    def _increment_usage(self):
        """Increment usage counters"""
        self.monthly_count += 1
        self.daily_count += 1
        self._save_usage_stats()

    def _make_request_with_backoff(self, url, headers, params, max_retries=3):
        """Make HTTP request with exponential backoff for rate limits"""
        for attempt in range(max_retries):
            try:
                self.last_request_time = time.time()
                response = requests.get(url, headers=headers, params=params, timeout=30)

                if response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 60))
                    print(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue

                return response

            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise e
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Request failed, retrying in {wait_time} seconds...")
                time.sleep(wait_time)

        return None

    def search_tweets_v2(self, query: str, max_results: int = 10) -> List[TweetData]:
        """
        Search for recent tweets using Twitter API v2
        Free tier: 100 requests per month
        """
        if not self.bearer_token:
            print("✗ Twitter API v2 not configured (no bearer token)")
            return []

        if not self._check_rate_limit():
            print("✗ Twitter API rate limit reached, skipping")
            return []

        try:
            # Prepare query for Sri Lanka
            # Free tier has query limitations - keep it simple
            enhanced_query = f"{query} Sri Lanka -is:retweet lang:en"

            # Free tier requires max_results=10 (cannot be less)
            params = {
                'query': enhanced_query,
                'max_results': 10,  # Free tier FIXED at 10, cannot be lower
                'tweet.fields': 'created_at,public_metrics,author_id',
                'expansions': 'author_id',
                'user.fields': 'username',
                'start_time': (datetime.now() - timedelta(days=7)).isoformat() + 'Z'
            }

            print(f"🔍 Searching Twitter v2 for: {enhanced_query}")

            response = self._make_request_with_backoff(
                f"{self.base_url_v2}/tweets/search/recent",
                headers=self.headers_v2,
                params=params
            )

            if not response:
                print("✗ Failed to get response after retries")
                return []

            if response.status_code == 200:
                data = response.json()
                tweets = self._parse_tweets_v2(data)

                # Increment usage counter
                self._increment_usage()

                print(f"✓ Retrieved {len(tweets)} tweets from Twitter API v2")
                print(f"  Monthly usage: {self.monthly_count}/{self.monthly_limit}")
                print(f"  Daily usage: {self.daily_count}/{self.daily_limit}")

                return tweets
            else:
                error_msg = response.text[:200] if response.text else "No error message"
                print(f"✗ Twitter API v2 error {response.status_code}: {error_msg}")

                # If we get 403, free tier might not have search access
                if response.status_code == 403:
                    print("  ⚠️  Free tier may not have search API access")

                return []

        except Exception as e:
            print(f"✗ Error searching tweets v2: {str(e)[:100]}")
            return []

    def search_tweets_v1(self, query: str, count: int = 10) -> List[TweetData]:
        """
        Search for tweets using Twitter API v1.1
        Free tier has VERY limited v1.1 access
        """
        if not self.bearer_token_v1 or not self.v1_1_enabled:
            print("✗ Twitter API v1.1 not available (free tier limited access)")
            return []

        if not self._check_rate_limit():
            print("✗ Twitter API rate limit reached, skipping")
            return []

        try:
            headers = {
                "Authorization": f"Bearer {self.bearer_token_v1}"
            }

            # Free tier v1.1 has limited endpoints
            # Try a simple search endpoint that might work
            params = {
                'q': f"{query} Sri Lanka",
                'count': min(count, 100),
                'result_type': 'recent',
                'lang': 'en'
            }

            print(f"🔍 Searching Twitter v1.1 for: {query}")

            response = self._make_request_with_backoff(
                f"{self.base_url_v1}/search/tweets.json",
                headers=headers,
                params=params
            )

            if not response:
                print("✗ Failed to get response after retries")
                return []

            if response.status_code == 200:
                data = response.json()
                tweets = self._parse_tweets_v1(data)

                # Increment usage counter
                self._increment_usage()

                print(f"✓ Retrieved {len(tweets)} tweets from Twitter API v1.1")
                return tweets
            elif response.status_code == 403:
                print(f"✗ Twitter API v1.1 access denied (403)")
                print(f"  ⚠️  Free tier does not have v1.1 search access")
                self.v1_1_enabled = False  # Disable v1.1 for future attempts
                return []
            else:
                print(f"✗ Twitter API v1.1 error {response.status_code}")
                return []

        except Exception as e:
            print(f"✗ Error searching tweets v1.1: {str(e)[:100]}")
            return []

    def _parse_tweets_v2(self, api_response: Dict) -> List[TweetData]:
        """Parse Twitter API v2 response into TweetData objects"""
        tweets = []

        if 'data' not in api_response:
            return tweets

        # Get user mappings
        users = {}
        if 'includes' in api_response and 'users' in api_response['includes']:
            for user in api_response['includes']['users']:
                users[user['id']] = user

        for tweet_data in api_response['data']:
            try:
                # Extract hashtags and mentions (simplified for free tier)
                hashtags = []
                mentions = []

                if 'entities' in tweet_data:
                    if 'hashtags' in tweet_data['entities']:
                        hashtags = [tag['tag'] for tag in tweet_data['entities']['hashtags']]
                    if 'mentions' in tweet_data['entities']:
                        mentions = [mention['username'] for mention in tweet_data['entities']['mentions']]

                # Get metrics
                metrics = tweet_data.get('public_metrics', {})

                # Get author info
                author_id = tweet_data.get('author_id', '')
                author_username = users.get(author_id, {}).get('username', author_id)

                tweet = TweetData(
                    id=tweet_data['id'],
                    text=tweet_data['text'],
                    author_id=author_username,
                    created_at=tweet_data['created_at'],
                    retweet_count=metrics.get('retweet_count', 0),
                    like_count=metrics.get('like_count', 0),
                    reply_count=metrics.get('reply_count', 0),
                    quote_count=metrics.get('quote_count', 0),
                    hashtags=hashtags,
                    mentions=mentions
                )

                tweets.append(tweet)

            except Exception as e:
                print(f"Error parsing tweet v2: {str(e)[:50]}")
                continue

        return tweets

    def _parse_tweets_v1(self, api_response: Dict) -> List[TweetData]:
        """Parse Twitter API v1.1 response into TweetData objects"""
        tweets = []

        if 'statuses' not in api_response:
            return tweets

        for tweet_data in api_response['statuses']:
            try:
                # Extract hashtags
                hashtags = []
                if 'entities' in tweet_data and 'hashtags' in tweet_data['entities']:
                    hashtags = [tag['text'] for tag in tweet_data['entities']['hashtags']]

                # Extract mentions
                mentions = []
                if 'entities' in tweet_data and 'user_mentions' in tweet_data['entities']:
                    mentions = [mention['screen_name'] for mention in tweet_data['entities']['user_mentions']]

                # Get author info
                author_username = tweet_data.get('user', {}).get('screen_name', '')

                tweet = TweetData(
                    id=str(tweet_data['id']),
                    text=tweet_data['text'],
                    author_id=author_username,
                    created_at=tweet_data['created_at'],
                    retweet_count=tweet_data.get('retweet_count', 0),
                    like_count=tweet_data.get('favorite_count', 0),
                    reply_count=0,  # Not available in v1.1
                    quote_count=0,  # Not available in v1.1
                    hashtags=hashtags,
                    mentions=mentions
                )

                tweets.append(tweet)

            except Exception as e:
                print(f"Error parsing tweet v1.1: {str(e)[:50]}")
                continue

        return tweets

    def get_sri_lanka_tweets_simple(self, max_tweets: int = 3) -> List[TweetData]:
        """
        SIMPLIFIED: Get recent tweets about Sri Lanka
        Free tier has limitations, so we use a single query
        """
        if not self.bearer_token:
            print("✗ Twitter API v2 not configured")
            return []

        if not self._check_rate_limit():
            print("✗ Twitter API rate limit reached")
            return []

        try:
            # SIMPLIFIED QUERY for free tier
            # Just search for Sri Lanka with minimal filters
            query = "Sri Lanka"

            print(f"🔍 Simple Twitter search for: {query}")

            # Use v2 API only (free tier v1.1 doesn't work for search)
            tweets = self.search_tweets_v2(query, max_results=10)

            if not tweets:
                print("✗ No tweets found with simple search")
                return []

            # Filter to get tweets actually about Sri Lanka (basic filter)
            sri_lanka_tweets = []
            for tweet in tweets:
                text_lower = tweet.text.lower()
                if any(keyword in text_lower for keyword in
                       ['sri lanka', 'colombo', 'kandy', 'galle', '#srilanka', '#lka']):
                    sri_lanka_tweets.append(tweet)

            result = sri_lanka_tweets[:max_tweets]
            print(f"✅ Found {len(result)} relevant tweets")

            return result

        except Exception as e:
            print(f"✗ Error in simple tweet search: {str(e)[:100]}")
            return []

    def get_sri_lanka_tweets(self, max_tweets: int = 3) -> List[TweetData]:
        """
        Get recent tweets about Sri Lanka
        Uses simplified approach for free tier
        """
        return self.get_sri_lanka_tweets_simple(max_tweets)

    def get_usage_stats(self) -> Dict:
        """Get current usage statistics"""
        now = datetime.now()

        # Calculate days remaining in month
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month + 1, day=1)

        days_remaining = (next_month - now).days
        days_remaining = max(days_remaining, 1)

        estimated_daily = max((self.monthly_limit - self.monthly_count) // days_remaining, 0)

        return {
            'monthly_used': self.monthly_count,
            'monthly_limit': self.monthly_limit,
            'monthly_remaining': self.monthly_limit - self.monthly_count,
            'daily_used': self.daily_count,
            'daily_limit': self.daily_limit,
            'daily_remaining': self.daily_limit - self.daily_count,
            'estimated_daily_limit': estimated_daily,
            'last_reset': self.last_reset.isoformat(),
            'next_daily_reset': (now + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat(),
            'api_configured': {
                'v2_bearer_token': bool(self.bearer_token),
                'v1_1_oauth': self.v1_1_enabled
            },
            'status': 'active' if (
                        self.monthly_count < self.monthly_limit and self.daily_count < self.daily_limit) else 'limit_reached'
        }

    def test_connection(self) -> bool:
        """Test if Twitter API is working"""
        try:
            if self.bearer_token:
                # Test v2 with a simple request
                test_params = {
                    'ids': '20',  # Test tweet ID
                    'tweet.fields': 'text'
                }

                response = requests.get(
                    f"{self.base_url_v2}/tweets",
                    headers=self.headers_v2,
                    params=test_params,
                    timeout=10
                )

                # 200 = success, 404 = tweet not found (but API works), 403 = no access
                if response.status_code in [200, 404]:
                    print("✓ Twitter API v2 connection successful")
                    return True
                elif response.status_code == 403:
                    print("⚠️ Twitter API v2: Authenticated but limited access (free tier)")
                    return True
                else:
                    print(f"✗ Twitter API v2 test failed: {response.status_code}")
                    return False

            return False
        except Exception as e:
            print(f"✗ Twitter API connection test failed: {str(e)[:100]}")
            return False