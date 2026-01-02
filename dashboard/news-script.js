// Configuration
const CONFIG = {
    WEATHER_API_KEY: '72953b767da2b8b05a3871cdb2bd251d', // Same as in main script
    WEATHER_API_URL: 'https://api.openweathermap.org/data/2.5/weather',
    NEWS_CSV_URL: 'data/combined_newsdata.csv', // New endpoint for news CSV
    REFRESH_INTERVAL: 120000, // 2 minutes in milliseconds
    WEATHER_REFRESH_INTERVAL: 120000 // 2 minutes
};

// Global variables
let allNews = [];
let filteredNews = [];
let newsByCategory = {};
let userCoordinates = null;
let refreshCountdown = 120;

// Category configuration
const CATEGORIES = {
    traffic: { name: 'Traffic', icon: 'fa-car', color: '#3498db' },
    weather: { name: 'Weather', icon: 'fa-cloud-sun', color: '#f39c12' },
    safety: { name: 'Safety', icon: 'fa-shield-alt', color: '#e74c3c' },
    crime: { name: 'Crime', icon: 'fa-user-secret', color: '#8e44ad' },
    government: { name: 'Government', icon: 'fa-landmark', color: '#2c3e50' },
    economy: { name: 'Economy', icon: 'fa-chart-line', color: '#27ae60' },
    health: { name: 'Health', icon: 'fa-heartbeat', color: '#e74c3c' },
    environment: { name: 'Environment', icon: 'fa-leaf', color: '#16a085' },
    social: { name: 'Social', icon: 'fa-users', color: '#9b59b6' },
    community: { name: 'Community', icon: 'fa-hands-helping', color: '#34495e' }
};

// DOM Elements
const elements = {
    city: document.getElementById('city'),
    temp: document.getElementById('temp'),
    weatherDesc: document.getElementById('weatherDesc'),
    windSpeed: document.getElementById('windSpeed'),
    humidity: document.getElementById('humidity'),
    currentTime: document.getElementById('currentTime'),
    weatherIcon: document.getElementById('weatherIcon'),
    refreshWeatherBtn: document.getElementById('refreshWeather'),
    newsSearch: document.getElementById('newsSearch'),
    clearSearch: document.getElementById('clearSearch'),
    categoryFilter: document.getElementById('categoryFilter'),
    refreshNewsBtn: document.getElementById('refreshNews'),
    totalNewsCount: document.getElementById('totalNewsCount'),
    newsLastUpdated: document.getElementById('newsLastUpdated'),
    categoryCount: document.getElementById('categoryCount'),
    connectionStatus: document.getElementById('connectionStatus'),
    refreshCountdownEl: document.getElementById('refreshCountdown'),
    newsCategoriesContainer: document.querySelector('.news-categories'),
    newsModal: document.getElementById('newsModal'),
    closeModal: document.getElementById('closeModal'),
    modalTitle: document.getElementById('modalTitle'),
    modalCategory: document.getElementById('modalCategory'),
    modalDate: document.getElementById('modalDate'),
    modalSummary: document.getElementById('modalSummary'),
    modalTags: document.getElementById('modalTags'),
    modalLocation: document.getElementById('modalLocation'),
    modalImpact: document.getElementById('modalImpact')
};

// Weather icon mapping
const weatherIcons = {
    'Clear': 'fa-sun',
    'Clouds': 'fa-cloud',
    'Rain': 'fa-cloud-rain',
    'Drizzle': 'fa-cloud-rain',
    'Thunderstorm': 'fa-bolt',
    'Snow': 'fa-snowflake',
    'Mist': 'fa-smog',
    'Smoke': 'fa-smog',
    'Haze': 'fa-smog',
    'Dust': 'fa-smog',
    'Fog': 'fa-smog',
    'Sand': 'fa-smog',
    'Ash': 'fa-smog',
    'Squall': 'fa-wind',
    'Tornado': 'fa-tornado'
};

// Initialize the application
async function init() {
    updateTime();
    setInterval(updateTime, 60000);

    // Start countdown timer
    startCountdowns();

    // Initialize location and weather
    await initializeLocationAndWeather();

    // Load news data
    await loadNews();

    // Set up event listeners
    setupEventListeners();
}

// Update current time
function updateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    if (elements.currentTime) {
        elements.currentTime.textContent = timeString;
    }
}

// Start countdown timer
function startCountdowns() {
    setInterval(() => {
        refreshCountdown--;
        if (refreshCountdown <= 0) {
            refreshCountdown = 120;
            loadNews();
        }

        if (elements.refreshCountdownEl) {
            elements.refreshCountdownEl.textContent = refreshCountdown;
        }
    }, 1000);
}

// Initialize location and weather
async function initializeLocationAndWeather() {
    try {
        await getUserLocation();
        if (userCoordinates) {
            await fetchWeather();
        }
    } catch (error) {
        console.error('Failed to initialize location and weather:', error);
        elements.city.textContent = 'Location not available';
        elements.weatherDesc.textContent = 'Enable location access for accurate weather';
    }
}

// Get user location
async function getUserLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocation is not supported by your browser'));
            return;
        }

        elements.city.textContent = 'Detecting location...';
        elements.weatherDesc.textContent = 'Getting your current location...';

        const options = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        };

        navigator.geolocation.getCurrentPosition(
            (position) => {
                userCoordinates = {
                    lat: position.coords.latitude,
                    lon: position.coords.longitude
                };
                console.log('Location obtained:', userCoordinates);
                resolve(userCoordinates);
            },
            (error) => {
                console.error('Geolocation error:', error);
                elements.city.textContent = 'Location access denied';
                elements.weatherDesc.textContent = 'Please enable location access';
                reject(error);
            },
            options
        );
    });
}

// Fetch weather data
async function fetchWeather() {
    if (!userCoordinates) {
        console.error('No coordinates available');
        return;
    }

    try {
        elements.weatherDesc.textContent = 'Loading weather...';

        const url = `${CONFIG.WEATHER_API_URL}?lat=${userCoordinates.lat}&lon=${userCoordinates.lon}&appid=${CONFIG.WEATHER_API_KEY}&units=metric`;
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`Weather API error: ${response.status}`);
        }

        const data = await response.json();
        updateWeatherDisplay(data);
        updateConnectionStatus(true);

        console.log('Weather data fetched for:', data.name);
    } catch (error) {
        console.error('Error fetching weather:', error);
        updateConnectionStatus(false);

        elements.city.textContent = 'Weather unavailable';
        elements.temp.textContent = '--';
        elements.weatherDesc.textContent = 'Unable to fetch weather data';
        elements.weatherIcon.className = 'fas fa-exclamation-triangle';
    }
}

// Update weather display
function updateWeatherDisplay(data) {
    const { name, main, weather, wind } = data;

    elements.city.textContent = name || 'Your Location';
    elements.temp.textContent = Math.round(main.temp);
    elements.weatherDesc.textContent = weather[0].description;
    elements.windSpeed.textContent = wind.speed.toFixed(1);
    elements.humidity.textContent = main.humidity;

    // Add feels like temperature
    const feelsLike = Math.round(main.feels_like);
    if (feelsLike !== Math.round(main.temp)) {
        elements.weatherDesc.textContent += ` (Feels like ${feelsLike}°C)`;
    }

    // Update weather icon
    const weatherMain = weather[0].main;
    const iconClass = weatherIcons[weatherMain] || 'fa-cloud';
    elements.weatherIcon.className = `fas ${iconClass}`;
}

// Load news from CSV
async function loadNews() {
    try {
        elements.newsCategoriesContainer.innerHTML = `
            <div class="loading-section">
                <div class="loading-spinner"></div>
                <p>Loading news data...</p>
            </div>
        `;

        const response = await fetch(CONFIG.NEWS_CSV_URL);

        if (!response.ok) {
            throw new Error(`Failed to fetch news: ${response.status}`);
        }

        const csvText = await response.text();
        allNews = parseCSV(csvText);

        console.log('Raw CSV data loaded:', allNews);
        console.log('First few news items:', allNews.slice(0, 3));

        // Update stats
        elements.totalNewsCount.textContent = allNews.length;

        // Count unique categories
        const uniqueCategories = [...new Set(allNews.map(item => item.category).filter(Boolean))];
        elements.categoryCount.textContent = uniqueCategories.length;

        // Update last updated time
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        elements.newsLastUpdated.textContent = timeString;

        // Process and display news
        processNewsData();

        // Update connection status
        updateConnectionStatus(true);

        console.log(`Loaded ${allNews.length} news items with ${uniqueCategories.length} unique categories`);
    } catch (error) {
        console.error('Error loading news:', error);
        updateConnectionStatus(false);

        elements.newsCategoriesContainer.innerHTML = `
            <div class="no-news-message">
                <i class="fas fa-exclamation-triangle"></i>
                <h3>Unable to Load News</h3>
                <p>Please check your connection and try again.</p>
                <button onclick="loadNews()" style="margin-top: 20px; padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer;">
                    Retry
                </button>
            </div>
        `;
    }
}

// Parse CSV text with improved column mapping
function parseCSV(csvText) {
    const lines = csvText.trim().split('\n');

    // Detect headers
    const headers = lines[0].split(',').map(header => {
        // Clean header: remove quotes and trim
        let cleanHeader = header.trim();
        if (cleanHeader.startsWith('"') && cleanHeader.endsWith('"')) {
            cleanHeader = cleanHeader.slice(1, -1);
        }
        return cleanHeader.toLowerCase();
    });

    console.log('Detected headers:', headers);

    return lines.slice(1).map((line, lineIndex) => {
        // Handle quoted values with commas
        const values = [];
        let current = '';
        let inQuotes = false;

        for (let i = 0; i < line.length; i++) {
            const char = line[i];

            if (char === '"') {
                inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
                values.push(current.trim());
                current = '';
            } else {
                current += char;
            }
        }
        values.push(current.trim());

        const newsItem = {};

        // Map headers to news item properties
        headers.forEach((header, index) => {
            let value = values[index] || '';

            // Remove surrounding quotes if present
            if (value.startsWith('"') && value.endsWith('"')) {
                value = value.slice(1, -1);
            }

            // Map common column names
            switch(header) {
                case 'title':
                case 'headline':
                    newsItem.title = value;
                    break;
                case 'summary':
                case 'description':
                case 'content':
                    newsItem.summary = value;
                    break;
                case 'category':
                case 'type':
                    newsItem.category = value.toLowerCase();
                    break;
                case 'subcategory':
                case 'sub_type':
                    newsItem.subcategory = value;
                    break;
                case 'location':
                case 'region':
                case 'area':
                    newsItem.location = value;
                    break;
                case 'impact':
                case 'severity':
                case 'importance':
                    newsItem.impact = value;
                    break;
                case 'date':
                case 'time':
                case 'timestamp':
                case 'published_date':
                    newsItem.date = value;
                    break;
                default:
                    // For any other column, just add it as-is
                    newsItem[header] = value;
            }
        });

        // If category wasn't found in standard headers, try to find it
        if (!newsItem.category) {
            // Check if any column name contains 'category'
            headers.forEach((header, index) => {
                if (header.includes('category') && !newsItem.category) {
                    let value = values[index] || '';
                    if (value.startsWith('"') && value.endsWith('"')) {
                        value = value.slice(1, -1);
                    }
                    newsItem.category = value.toLowerCase();
                }
            });
        }

        // If still no category, default to 'uncategorized'
        if (!newsItem.category) {
            newsItem.category = 'uncategorized';
        }

        // Clean up category string
        newsItem.category = newsItem.category.trim().toLowerCase();

        // Map common variations to standard categories
        const categoryMapping = {
            'traffic': 'traffic',
            'transport': 'traffic',
            'weather': 'weather',
            'safety': 'safety',
            'security': 'safety',
            'crime': 'crime',
            'criminal': 'crime',
            'government': 'government',
            'govt': 'government',
            'politics': 'government',
            'economy': 'economy',
            'economic': 'economy',
            'finance': 'economy',
            'health': 'health',
            'medical': 'health',
            'environment': 'environment',
            'ecological': 'environment',
            'social': 'social',
            'community': 'community',
            'local': 'community',
            'regional': 'community'
        };

        if (categoryMapping[newsItem.category]) {
            newsItem.category = categoryMapping[newsItem.category];
        }

        // Validate against our known categories
        if (!CATEGORIES[newsItem.category]) {
            console.log(`Unknown category "${newsItem.category}" mapped to community:`, newsItem.title);
            newsItem.category = 'community';
        }

        return newsItem;
    });
}

// Process news data and categorize
function processNewsData() {
    // Reset data structures
    newsByCategory = {};
    filteredNews = [...allNews];

    // Filter by search term if any
    const searchTerm = elements.newsSearch.value.toLowerCase();
    if (searchTerm) {
        filteredNews = filteredNews.filter(news =>
            (news.title && news.title.toLowerCase().includes(searchTerm)) ||
            (news.summary && news.summary.toLowerCase().includes(searchTerm))
        );
    }

    // Filter by category if not "all"
    const selectedCategory = elements.categoryFilter.value;
    if (selectedCategory !== 'all') {
        filteredNews = filteredNews.filter(news =>
            news.category && news.category.toLowerCase() === selectedCategory
        );
    }

    // Group by category
    filteredNews.forEach(news => {
        const category = news.category || 'community';

        if (!newsByCategory[category]) {
            newsByCategory[category] = [];
        }
        newsByCategory[category].push(news);
    });

    // Log category distribution for debugging
    console.log('News by category:', Object.keys(newsByCategory).map(cat => ({
        category: cat,
        count: newsByCategory[cat].length
    })));

    // Render categories
    renderCategories();
}

// Render categories
function renderCategories() {
    if (filteredNews.length === 0) {
        elements.newsCategoriesContainer.innerHTML = `
            <div class="no-news-message">
                <i class="fas fa-search"></i>
                <h3>No News Found</h3>
                <p>Try adjusting your search or filter criteria.</p>
            </div>
        `;
        return;
    }

    let html = '';

    // First, render categories that we have configured
    Object.keys(CATEGORIES).forEach(categoryKey => {
        const category = CATEGORIES[categoryKey];
        const categoryNews = newsByCategory[categoryKey] || [];

        if (categoryNews.length > 0) {
            html += `
                <div class="category-section category-${categoryKey}">
                    <div class="category-header">
                        <h2 class="category-title">
                            <i class="fas ${category.icon}"></i>
                            ${category.name}
                            <span class="category-count">${categoryNews.length}</span>
                        </h2>
                    </div>
                    <div class="category-news-grid">
                        ${categoryNews.map((news, index) => createNewsCard(news, categoryKey, index)).join('')}
                    </div>
                </div>
            `;
        }
    });

    // Then render any other categories that appeared in the data
    const otherCategories = Object.keys(newsByCategory).filter(key => !CATEGORIES[key]);

    otherCategories.forEach(categoryKey => {
        const categoryNews = newsByCategory[categoryKey] || [];

        if (categoryNews.length > 0) {
            // Create a display name from the category key
            const displayName = categoryKey.charAt(0).toUpperCase() + categoryKey.slice(1);

            html += `
                <div class="category-section category-community">
                    <div class="category-header">
                        <h2 class="category-title">
                            <i class="fas fa-newspaper"></i>
                            ${displayName}
                            <span class="category-count">${categoryNews.length}</span>
                        </h2>
                    </div>
                    <div class="category-news-grid">
                        ${categoryNews.map((news, index) => createNewsCard(news, categoryKey, index)).join('')}
                    </div>
                </div>
            `;
        }
    });

    elements.newsCategoriesContainer.innerHTML = html;

    // Add click event listeners to news cards
    document.querySelectorAll('.news-card').forEach(card => {
        card.addEventListener('click', function() {
            const index = this.dataset.index;
            const category = this.dataset.category;
            const newsItem = newsByCategory[category][index];
            openNewsModal(newsItem);
        });
    });
}

// Create news card HTML
function createNewsCard(news, category, index) {
    // Get category config or use community as default
    let categoryConfig = CATEGORIES[category];
    if (!categoryConfig) {
        // Create a default config for unknown categories
        categoryConfig = {
            name: category.charAt(0).toUpperCase() + category.slice(1),
            icon: 'fa-newspaper',
            color: '#34495e'
        };
    }

    return `
        <div class="news-card" data-index="${index}" data-category="${category}">
            <div class="news-header">
                <h3 class="news-title">${escapeHtml(news.title || 'Untitled News')}</h3>
                <span class="news-category-badge" style="background-color: ${categoryConfig.color}">${categoryConfig.name}</span>
            </div>
            <div class="news-summary">
                ${escapeHtml(truncateText(news.summary || 'No summary available', 150))}
            </div>
            <div class="news-tags">
                ${news.location ? `<span class="hashtag"><i class="fas fa-map-marker-alt"></i> ${escapeHtml(news.location)}</span>` : ''}
                ${news.subcategory ? `<span class="hashtag">${escapeHtml(news.subcategory)}</span>` : ''}
                ${news.impact ? `<span class="hashtag"><i class="fas fa-chart-line"></i> ${escapeHtml(news.impact)}</span>` : ''}
                ${news.date ? `<span class="hashtag"><i class="fas fa-calendar"></i> ${escapeHtml(news.date)}</span>` : ''}
            </div>
        </div>
    `;
}

// Open news modal
function openNewsModal(news) {
    const category = news.category || 'community';
    let categoryConfig = CATEGORIES[category];

    // If category not found in config, create a default
    if (!categoryConfig) {
        categoryConfig = {
            name: category.charAt(0).toUpperCase() + category.slice(1),
            color: '#34495e'
        };
    }

    // Set modal content
    elements.modalTitle.textContent = news.title || 'Untitled News';
    elements.modalCategory.textContent = categoryConfig.name;
    elements.modalCategory.style.backgroundColor = categoryConfig.color;
    elements.modalDate.textContent = news.date || 'No date available';
    elements.modalSummary.textContent = news.summary || 'No summary available';
    elements.modalLocation.textContent = news.location || 'Not specified';
    elements.modalImpact.textContent = news.impact || 'Not specified';

    // Set tags
    elements.modalTags.innerHTML = `
        ${news.subcategory ? `<span class="hashtag">${escapeHtml(news.subcategory)}</span>` : ''}
        ${news.location ? `<span class="hashtag"><i class="fas fa-map-marker-alt"></i> ${escapeHtml(news.location)}</span>` : ''}
        ${news.impact ? `<span class="hashtag"><i class="fas fa-chart-line"></i> ${escapeHtml(news.impact)}</span>` : ''}
        ${news.date ? `<span class="hashtag"><i class="fas fa-calendar"></i> ${escapeHtml(news.date)}</span>` : ''}
    `;

    // Show modal
    elements.newsModal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

// Close news modal
function closeNewsModal() {
    elements.newsModal.classList.remove('active');
    document.body.style.overflow = 'auto';
}

// Set up event listeners
function setupEventListeners() {
    // Weather refresh
    elements.refreshWeatherBtn.addEventListener('click', async () => {
        try {
            await getUserLocation();
            if (userCoordinates) {
                await fetchWeather();
            }
        } catch (error) {
            console.error('Failed to refresh location:', error);
        }

        elements.refreshWeatherBtn.style.animation = 'spin 1s ease';
        setTimeout(() => {
            elements.refreshWeatherBtn.style.animation = '';
        }, 1000);
    });

    // News search
    elements.newsSearch.addEventListener('input', () => {
        elements.clearSearch.style.display = elements.newsSearch.value ? 'block' : 'none';
        processNewsData();
    });

    // Clear search
    elements.clearSearch.addEventListener('click', () => {
        elements.newsSearch.value = '';
        elements.clearSearch.style.display = 'none';
        processNewsData();
    });

    // Category filter
    elements.categoryFilter.addEventListener('change', processNewsData);

    // Refresh news button
    elements.refreshNewsBtn.addEventListener('click', () => {
        elements.refreshNewsBtn.style.animation = 'spin 1s ease';
        setTimeout(() => {
            elements.refreshNewsBtn.style.animation = '';
        }, 1000);
        loadNews();
    });

    // Modal close
    elements.closeModal.addEventListener('click', closeNewsModal);
    elements.newsModal.addEventListener('click', (e) => {
        if (e.target === elements.newsModal) {
            closeNewsModal();
        }
    });

    // Close modal on ESC key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && elements.newsModal.classList.contains('active')) {
            closeNewsModal();
        }
    });

    // Auto-refresh news every 2 minutes
    setInterval(() => {
        loadNews();
    }, CONFIG.REFRESH_INTERVAL);

    // Auto-refresh weather every 2 minutes
    setInterval(() => {
        if (userCoordinates) {
            fetchWeather();
        }
    }, CONFIG.WEATHER_REFRESH_INTERVAL);
}

// Update connection status
function updateConnectionStatus(connected) {
    if (elements.connectionStatus) {
        if (connected) {
            elements.connectionStatus.innerHTML = '<i class="fas fa-circle" style="color: #4CAF50;"></i> Connected';
        } else {
            elements.connectionStatus.innerHTML = '<i class="fas fa-circle" style="color: #e74c3c;"></i> Disconnected';
        }
    }
}

// Utility functions
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', init);