# data_collection/news_scraper.py
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import re
from typing import List, Dict, Optional
import time


class AdaDeranaScraper:
    """Real Ada Derana news scraper"""

    def __init__(self):
        self.base_url = "https://www.adaderana.lk"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.categories = {
            'hot-news': 'hot_news',
            'sports-news': 'sports',
            'entertainment-news': 'entertainment',
            'technology-news': 'technology',
            'business': 'business'
        }

    def scrape_homepage(self) -> List[Dict]:
        """Scrape latest news from Ada Derana homepage"""
        try:
            print(f"Scraping Ada Derana homepage: {self.base_url}")
            response = requests.get(self.base_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            news_items = []

            # Method 1: Hot News section
            hot_news_section = soup.find('div', class_='wr-hot-news')
            if hot_news_section:
                articles = hot_news_section.find_all('div', class_='hot-news')
                for article in articles[:15]:
                    news_item = self._extract_article_data(article)
                    if news_item:
                        news_items.append(news_item)

            # Method 2: News stories from main content
            news_stories = soup.find_all('div', class_='news-story')
            for story in news_stories[:10]:
                news_item = self._extract_article_data(story)
                if news_item:
                    news_items.append(news_item)

            # Method 3: Top stories
            top_story_section = soup.find('div', class_='top-story')
            if top_story_section:
                top_article = top_story_section.find('div', class_='news-story')
                if top_article:
                    news_item = self._extract_article_data(top_article)
                    if news_item:
                        news_items.append(news_item)

            deduplicated = self._deduplicate_news(news_items)
            print(f"Found {len(deduplicated)} unique news items")
            return deduplicated

        except Exception as e:
            print(f"Error scraping Ada Derana: {e}")
            return []

    def scrape_by_category(self, category: str) -> List[Dict]:
        """Scrape news by specific category"""
        if category not in self.categories:
            return []

        try:
            url = f"{self.base_url}/{category}"
            print(f"Scraping category: {url}")

            response = requests.get(url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')

            news_items = []
            articles = soup.find_all('div', class_='news-story')

            for article in articles[:20]:
                news_item = self._extract_article_data(article)
                if news_item:
                    news_item['category'] = self.categories[category]
                    news_items.append(news_item)

            print(f"Found {len(news_items)} items in category {category}")
            return news_items

        except Exception as e:
            print(f"Error scraping category {category}: {e}")
            return []

    def _extract_article_data(self, article) -> Optional[Dict]:
        """Extract structured data from article element"""
        try:
            # Extract title and link
            title_elem = article.find('h3') or article.find('a')
            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            if not title or len(title) < 5:
                return None

            link = title_elem.get('href')
            if link:
                if not link.startswith('http'):
                    link = self.base_url + link if link.startswith('/') else f"{self.base_url}/{link}"
            else:
                return None

            # Extract summary/description
            summary_elem = article.find('p')
            summary = summary_elem.get_text(strip=True) if summary_elem else ""

            # Extract image
            img_elem = article.find('img')
            image_url = img_elem.get('src') if img_elem else None
            if image_url and not image_url.startswith('http'):
                image_url = self.base_url + image_url if image_url.startswith('/') else f"{self.base_url}/{image_url}"

            # Extract timestamp
            time_elem = article.find('span', class_='comments') or article.find('span')
            time_text = time_elem.get_text() if time_elem else ""
            timestamp = self._extract_timestamp(time_text)

            # Extract location from title/content
            location = self._extract_location_from_text(title + " " + summary)

            return {
                'title': title,
                'summary': summary,
                'link': link,
                'image_url': image_url,
                'timestamp': timestamp,
                'location': location,
                'full_text': self._scrape_full_article(link) if link else "",
                'source': 'ada_derana'
            }

        except Exception as e:
            print(f"Error extracting article: {e}")
            return None

    def _scrape_full_article(self, url: str) -> str:
        """Scrape full article text from individual page"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find article content
            article_content = soup.find('div', class_='story-text') or soup.find('article')
            if article_content:
                # Remove script and style elements
                for element in article_content(['script', 'style', 'nav', 'footer', 'aside']):
                    element.decompose()

                # Get text with proper spacing
                text = article_content.get_text(separator=' ', strip=True)
                # Clean up multiple spaces
                text = re.sub(r'\s+', ' ', text)
                return text[:2000]  # Limit to 2000 chars

            return ""
        except:
            return ""

    def _extract_timestamp(self, text: str) -> str:
        """Extract and format timestamp from text"""
        try:
            # Patterns like "2 hours ago", "December 7, 2025 4:12 pm"
            patterns = [
                r'(\d+)\s+hours?\s+ago',
                r'(\d+)\s+minutes?\s+ago',
                r'(\w+\s+\d+,\s+\d{4}\s+\d+:\d+\s*(?:am|pm))',
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{2}\s+\w+\s+\d{4})'
            ]

            current_time = datetime.now()

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    timestamp_str = match.group(1)

                    if 'ago' in text.lower():
                        # Extract number
                        num_match = re.search(r'(\d+)', timestamp_str)
                        if num_match:
                            hours = int(num_match.group(1))
                            if 'minute' in text.lower():
                                time_delta = current_time - timedelta(minutes=hours)
                            else:
                                time_delta = current_time - timedelta(hours=hours)
                            return time_delta.isoformat()
                    else:
                        # Try to parse various date formats
                        date_formats = [
                            '%B %d, %Y %I:%M %p',
                            '%Y-%m-%d',
                            '%d %B %Y',
                            '%d %b %Y'
                        ]

                        for fmt in date_formats:
                            try:
                                dt = datetime.strptime(timestamp_str, fmt)
                                return dt.isoformat()
                            except:
                                continue

            return current_time.isoformat()
        except:
            return datetime.now().isoformat()

    def _extract_location_from_text(self, text: str) -> str:
        """Extract location from news text"""
        sri_lankan_locations = [
            # Provinces
            'Western Province', 'Central Province', 'Southern Province',
            'Northern Province', 'Eastern Province', 'North Western Province',
            'North Central Province', 'Uva Province', 'Sabaragamuwa Province',

            # Major Cities
            'Colombo', 'Kandy', 'Galle', 'Jaffna', 'Negombo', 'Kurunegala',
            'Anuradhapura', 'Polonnaruwa', 'Trincomalee', 'Batticaloa',
            'Matara', 'Ratnapura', 'Badulla', 'Hambantota', 'Kalutara',
            'Mannar', 'Vavuniya', 'Kilinochchi', 'Mullaitivu', 'Ampara',
            'Puttalam', 'Nuwara Eliya', 'Kegalle', 'Moneragala'
        ]

        # Check provinces
        for province in ['Western Province', 'Central Province', 'Southern Province',
                         'Northern Province', 'Eastern Province']:
            if province.lower() in text.lower():
                return province

        # Check cities
        for location in sri_lankan_locations:
            if location.lower() in text.lower():
                return location

        # Check for "in [location]" pattern
        location_patterns = [
            r'in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'near\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]

        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                possible_location = match.group(1)
                # Verify it's a Sri Lankan location
                for location in sri_lankan_locations:
                    if possible_location.lower() in location.lower() or location.lower() in possible_location.lower():
                        return location

        return "Sri Lanka"

    def _deduplicate_news(self, news_items: List[Dict]) -> List[Dict]:
        """Remove duplicate news items based on title"""
        seen_titles = set()
        unique_items = []

        for item in news_items:
            if not item:
                continue

            title_lower = item['title'].lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_items.append(item)

        return unique_items