import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


class CeypetcoFuelScraper:
    """Selenium-based scraper for Ceypetco historical fuel prices"""

    def __init__(self):
        self.base_url = "https://ceypetco.gov.lk/historical-prices/"

        # Fuel type mappings
        self.fuel_mappings = {
            'LP 95': 'petrol_95',
            'LP 92': 'petrol_92',
            'LAD': 'auto_diesel',
            'LSD': 'super_diesel',
            'LK': 'kerosene',
            'LIK': 'industrial_kerosene',
            'FUR. 800': 'furnace_800',
            'FUR 1500 (High)': 'furnace_1500_high',
            'FUR. 1500 (Low)': 'furnace_1500_low'
        }

        # Setup Chrome options for headless browsing
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')  # Run in background
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)

        # Set user agent
        self.chrome_options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    def _get_driver(self):
        """Initialize and return Chrome driver"""
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self.chrome_options)

            # Additional settings to avoid detection
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            return driver
        except Exception as e:
            print(f"❌ Error initializing Chrome driver: {e}")
            raise

    def scrape_fuel_prices(self) -> List[Dict]:
        """Scrape historical fuel prices from Ceypetco website using Selenium"""
        driver = None
        try:
            print(f"🔍 Scraping fuel prices from: {self.base_url}")

            # Initialize driver
            driver = self._get_driver()

            # Navigate to the page
            driver.get(self.base_url)

            # Wait for page to load
            time.sleep(5)  # Initial wait for page load

            # Try to find and interact with the table
            print("🔍 Looking for fuel price table...")

            # Wait for table to be present
            wait = WebDriverWait(driver, 20)

            # Try different selectors for the table
            table_selectors = [
                "table.ea-advanced-data-table",
                "table.ea-advanced-data-table-ceac013",
                "div.ea-advanced-data-table-wrap-inner table",
                "table",
                "#ceac013",  # The data-id from your HTML
                "div[data-id='ceac013'] table"
            ]

            table_element = None
            for selector in table_selectors:
                try:
                    if 'div[' in selector:
                        table_element = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                    else:
                        table_element = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                    print(f"✅ Found table using selector: {selector}")
                    break
                except:
                    continue

            if not table_element:
                print("❌ Could not find table element")

                # Take screenshot for debugging
                driver.save_screenshot('debug_page.png')
                print("📸 Saved screenshot as debug_page.png")

                # Get page source for debugging
                page_source = driver.page_source
                with open('debug_page.html', 'w', encoding='utf-8') as f:
                    f.write(page_source)
                print("📄 Saved page source as debug_page.html")

                return []

            # Scroll to the table to ensure it's fully loaded
            driver.execute_script("arguments[0].scrollIntoView(true);", table_element)
            time.sleep(2)

            # Try to click "Load More" or pagination buttons if they exist
            self._handle_pagination(driver)

            # Get the table HTML
            table_html = table_element.get_attribute('outerHTML')

            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(table_html, 'html.parser')

            # Parse the table
            return self._parse_fuel_table(soup)

        except Exception as e:
            print(f"❌ Error scraping fuel prices: {str(e)}")

            # Save debug information
            if driver:
                try:
                    driver.save_screenshot('error_screenshot.png')
                    print("📸 Saved error screenshot as error_screenshot.png")

                    with open('error_page.html', 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    print("📄 Saved error page source as error_page.html")
                except:
                    pass

            return []

        finally:
            if driver:
                driver.quit()

    def _handle_pagination(self, driver):
        """Handle pagination to load more rows if needed"""
        try:
            # Look for "Load More" button or pagination
            load_more_selectors = [
                "button.ea-advanced-data-table-load-more",
                "button.load-more",
                "a.ea-advanced-data-table-paginate-button",
                "button.paginate_button",
                "a[aria-label='Next']",
                "button:contains('Load More')",
                "a:contains('Next')"
            ]

            # Try to click multiple times to load more data
            for _ in range(3):  # Try up to 3 times
                clicked = False
                for selector in load_more_selectors:
                    try:
                        if 'contains' in selector:
                            # Handle text-based selectors
                            if 'Load More' in selector:
                                elements = driver.find_elements(By.XPATH, "//button[contains(text(), 'Load More')]")
                            elif 'Next' in selector:
                                elements = driver.find_elements(By.XPATH, "//a[contains(text(), 'Next')]")
                        else:
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)

                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                time.sleep(1)
                                element.click()
                                print("🔄 Clicked pagination/load more button")
                                time.sleep(3)  # Wait for data to load
                                clicked = True
                                break

                        if clicked:
                            break
                    except:
                        continue

                if not clicked:
                    break

            # Also try to find and click on pagination numbers
            try:
                pagination_links = driver.find_elements(By.CSS_SELECTOR, "a.ea-advanced-data-table-paginate-button")
                for link in pagination_links[:3]:  # Click first few pages
                    if link.is_displayed() and link.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView(true);", link)
                        time.sleep(0.5)
                        link.click()
                        time.sleep(2)
                        print(f"📄 Clicked pagination link")
            except:
                pass

        except Exception as e:
            print(f"⚠️ Could not handle pagination: {e}")

    def _parse_fuel_table(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse the fuel price table from BeautifulSoup object"""
        try:
            # Find all tables
            tables = soup.find_all('table')
            print(f"Found {len(tables)} tables")

            if not tables:
                print("❌ No tables found in parsed HTML")
                return []

            # Find the main fuel price table
            target_table = None
            for table in tables:
                # Look for table headers
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [cell.get_text(strip=True) for cell in header_row.find_all(['td', 'th'])]

                # Check if this looks like our fuel price table
                if headers and any(fuel in ' '.join(headers) for fuel in ['LP 95', 'LP 92', 'LAD', 'LSD']):
                    target_table = table
                    print(f"✅ Found fuel price table with headers: {headers[:5]}...")
                    break

            if not target_table:
                print("❌ Could not identify fuel price table")
                return []

            # Get all rows
            rows = target_table.find_all('tr')
            print(f"Found {len(rows)} rows in table")

            if len(rows) < 2:
                print("❌ No data rows found")
                return []

            # Get headers from first row
            headers = []
            header_cells = rows[0].find_all(['td', 'th'])
            for cell in header_cells:
                headers.append(cell.get_text(strip=True))

            print(f"📋 Table headers: {headers}")

            # Parse data rows
            fuel_data = []
            for row_idx, row in enumerate(rows[1:]):
                cells = row.find_all(['td', 'th'])

                # Skip rows with incorrect number of cells
                if len(cells) != len(headers):
                    continue

                try:
                    # Parse date (format: DD.MM.YYYY)
                    date_str = cells[0].get_text(strip=True)

                    # Skip if date is empty
                    if not date_str:
                        continue

                    # Handle special date formats (e.g., "01.11.2024(9.00 PM)")
                    if '(' in date_str:
                        date_str = date_str.split('(')[0].strip()

                    # Parse date
                    date_obj = self._parse_date(date_str)
                    if not date_obj:
                        print(f"⚠️ Could not parse date: {date_str}")
                        continue

                    # Create record
                    record = {
                        'date': date_obj.isoformat(),
                        'date_str': date_str,
                        'scraped_at': datetime.now().isoformat(),
                        'source': 'ceypetco',
                        'location': 'Sri Lanka'
                    }

                    # Add fuel prices
                    for i in range(1, min(len(headers), len(cells))):
                        header = headers[i]
                        value_str = cells[i].get_text(strip=True)

                        # Clean value
                        value_str = self._clean_price_value(value_str)

                        if value_str and value_str != '.' and value_str != '..':
                            try:
                                # Convert to float
                                value = float(value_str)
                                fuel_key = self.fuel_mappings.get(header,
                                                                  header.lower().replace(' ', '_').replace('.', ''))
                                record[fuel_key] = value
                            except (ValueError, TypeError) as e:
                                # Skip invalid values
                                fuel_key = self.fuel_mappings.get(header,
                                                                  header.lower().replace(' ', '_').replace('.', ''))
                                record[fuel_key] = None
                        else:
                            fuel_key = self.fuel_mappings.get(header, header.lower().replace(' ', '_').replace('.', ''))
                            record[fuel_key] = None

                    # Only add if we have at least some fuel data
                    fuel_values = [v for k, v in record.items() if k in self.fuel_mappings.values() and v is not None]
                    if len(fuel_values) >= 3:  # At least 3 fuel types with data
                        fuel_data.append(record)

                except Exception as e:
                    print(f"⚠️ Error parsing row {row_idx}: {e}")
                    continue

            print(f"✅ Successfully parsed {len(fuel_data)} fuel price records")
            return fuel_data

        except Exception as e:
            print(f"❌ Error parsing table: {e}")
            return []

    def _clean_price_value(self, value: str) -> str:
        """Clean price value string"""
        if not value:
            return ""

        # Remove non-numeric characters except dots and commas
        cleaned = re.sub(r'[^\d.,]', '', value)

        # Handle multiple dots (some values have formatting issues)
        if cleaned.count('.') > 1:
            # Keep only the last dot as decimal
            parts = cleaned.split('.')
            if len(parts) > 2:
                cleaned = '.'.join(parts[:-1]) + parts[-1]

        # Replace comma with dot for decimal
        cleaned = cleaned.replace(',', '.')

        return cleaned

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date from various formats"""
        if not date_str:
            return None

        try:
            # Clean the date string
            date_str = date_str.strip()

            # Try DD.MM.YYYY format (most common on the site)
            if '.' in date_str:
                parts = date_str.split('.')
                if len(parts) == 3:
                    day, month, year = parts
                    # Handle 2-digit years
                    if len(year) == 2:
                        year_int = int(year)
                        year = f'20{year}' if year_int < 50 else f'19{year}'
                    return datetime(int(year), int(month), int(day))

            # Try DD/MM/YYYY format
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts) == 3:
                    day, month, year = parts
                    if len(year) == 2:
                        year_int = int(year)
                        year = f'20{year}' if year_int < 50 else f'19{year}'
                    return datetime(int(year), int(month), int(day))

            # Try other common formats
            date_formats = [
                '%d-%m-%Y',
                '%Y-%m-%d',
                '%d %b %Y',
                '%d %B %Y',
                '%b %d, %Y',
                '%B %d, %Y'
            ]

            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except:
                    continue

            print(f"⚠️ Could not parse date: {date_str}")
            return None

        except Exception as e:
            print(f"Error parsing date '{date_str}': {e}")
            return None

    def get_latest_fuel_prices(self) -> Dict:
        """Get only the latest fuel prices"""
        all_data = self.scrape_fuel_prices()
        if not all_data:
            print("❌ No fuel data scraped")
            return {}

        # Sort by date (newest first)
        all_data.sort(key=lambda x: x['date'], reverse=True)

        # Get latest record
        latest = all_data[0]

        print(f"✅ Latest fuel prices from: {latest.get('date_str')}")
        return latest

    def get_fuel_price_changes(self) -> Dict:
        """Calculate price changes from previous month"""
        all_data = self.scrape_fuel_prices()
        if len(all_data) < 2:
            print("⚠️ Insufficient data for price change analysis")
            return {}

        # Sort by date
        all_data.sort(key=lambda x: x['date'], reverse=True)

        latest = all_data[0]
        previous = all_data[1]

        changes = {
            'latest_date': latest['date'],
            'latest_date_str': latest.get('date_str', ''),
            'previous_date': previous['date'],
            'previous_date_str': previous.get('date_str', ''),
            'changes': {}
        }

        # Calculate percentage changes for each fuel type
        fuel_types = [k for k in latest.keys() if k not in ['date', 'date_str', 'scraped_at', 'source', 'location']]

        for fuel_type in fuel_types:
            if fuel_type in latest and fuel_type in previous:
                latest_price = latest.get(fuel_type)
                previous_price = previous.get(fuel_type)

                if latest_price is not None and previous_price is not None and previous_price > 0:
                    change = ((latest_price - previous_price) / previous_price) * 100
                    changes['changes'][fuel_type] = {
                        'latest': latest_price,
                        'previous': previous_price,
                        'change_abs': round(latest_price - previous_price, 2),
                        'change_pct': round(change, 2),
                        'trend': 'up' if change > 0 else ('down' if change < 0 else 'stable')
                    }

        return changes


# Test function
def test_scraper():
    """Test the scraper"""
    print("🧪 Testing Ceypetco fuel scraper...")

    scraper = CeypetcoFuelScraper()

    # Test scraping
    print("\n1. Testing scrape_fuel_prices()...")
    data = scraper.scrape_fuel_prices()
    print(f"   Scraped {len(data)} records")

    if data:
        print(f"   First record date: {data[0].get('date_str')}")
        print(f"   Petrol 95: Rs.{data[0].get('petrol_95', 'N/A')}")
        print(f"   Auto Diesel: Rs.{data[0].get('auto_diesel', 'N/A')}")

    # Test getting latest prices
    print("\n2. Testing get_latest_fuel_prices()...")
    latest = scraper.get_latest_fuel_prices()
    if latest:
        print(f"   Latest date: {latest.get('date_str')}")
        print(f"   Petrol 95: Rs.{latest.get('petrol_95', 'N/A')}")
        print(f"   Petrol 92: Rs.{latest.get('petrol_92', 'N/A')}")
        print(f"   Auto Diesel: Rs.{latest.get('auto_diesel', 'N/A')}")

    # Test price changes
    print("\n3. Testing get_fuel_price_changes()...")
    changes = scraper.get_fuel_price_changes()
    if changes and changes.get('changes'):
        print(f"   Found changes for {len(changes['changes'])} fuel types")
        for fuel_type, change_data in list(changes['changes'].items())[:3]:
            print(f"   {fuel_type}: {change_data['change_pct']:+.2f}%")

    return data is not None


if __name__ == "__main__":
    test_scraper()