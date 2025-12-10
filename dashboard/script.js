// Configuration
const CONFIG = {
    WEATHER_API_KEY: '72953b767da2b8b05a3871cdb2bd251d', // Replace with your OpenWeather API key
    WEATHER_API_URL: 'https://api.openweathermap.org/data/2.5/weather',
    CSV_SERVER_URL: 'http://localhost:3000/alerts', // Change to your server endpoint
    REFRESH_INTERVAL: 120000, // 2 minutes in milliseconds
    ALERT_SLIDE_INTERVAL: 10000, // 10 seconds per alert
    WEATHER_REFRESH_INTERVAL: 120000 // 2 minutes
};

// Global variables
let currentAlertIndex = 0;
let alerts = [];
let filteredAlerts = [];
let alertSlideInterval;
let refreshCountdown = 120;
let weatherRefreshCountdown = 120;
let userCoordinates = null;

// DOM Elements
const elements = {
    alertsTrack: document.getElementById('alertsTrack'),
    alertsIndicators: document.getElementById('alertsIndicators'),
    prevAlertBtn: document.getElementById('prevAlert'),
    nextAlertBtn: document.getElementById('nextAlert'),
    city: document.getElementById('city'),
    temp: document.getElementById('temp'),
    weatherDesc: document.getElementById('weatherDesc'),
    windSpeed: document.getElementById('windSpeed'),
    humidity: document.getElementById('humidity'),
    currentTime: document.getElementById('currentTime'),
    weatherIcon: document.getElementById('weatherIcon'),
    refreshWeatherBtn: document.getElementById('refreshWeather'),
    lastUpdated: document.getElementById('lastUpdated'),
    refreshCountdownEl: document.getElementById('refreshCountdown'),
    connectionStatus: document.getElementById('connectionStatus'),
    activeAlertsCount: document.getElementById('activeAlertsCount')
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
    setInterval(updateTime, 60000); // Update time every minute

    // Start countdown timers
    startCountdowns();

    // Get user location and fetch weather
    await initializeLocationAndWeather();

    // Load alerts
    await loadAlerts();

    // Set up event listeners
    setupEventListeners();

    // Start auto-slide for alerts
    startAlertSlide();
}

// Update current time
function updateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    if (elements.currentTime) {
        elements.currentTime.textContent = timeString;
    }
}

// Start countdown timers
function startCountdowns() {
    // Update refresh countdown every second
    setInterval(() => {
        refreshCountdown--;
        if (refreshCountdown <= 0) {
            refreshCountdown = 120;
            loadAlerts();
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

// Get user location with better accuracy
async function getUserLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocation is not supported by your browser'));
            return;
        }

        // Show loading state
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
                    lon: position.coords.longitude,
                    accuracy: position.coords.accuracy
                };

                console.log('Location obtained:', userCoordinates);
                resolve(userCoordinates);
            },
            (error) => {
                console.error('Geolocation error:', error);

                let errorMessage = 'Unable to get your location. ';
                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        errorMessage += 'Please enable location access in your browser settings.';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMessage += 'Location information is unavailable.';
                        break;
                    case error.TIMEOUT:
                        errorMessage += 'Location request timed out.';
                        break;
                    default:
                        errorMessage += 'An unknown error occurred.';
                }

                elements.city.textContent = 'Location access denied';
                elements.weatherDesc.textContent = errorMessage;
                reject(new Error(errorMessage));
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

        // Show error in weather display
        elements.city.textContent = 'Weather unavailable';
        elements.temp.textContent = '--';
        elements.weatherDesc.textContent = 'Unable to fetch weather data';
        elements.weatherIcon.className = 'fas fa-exclamation-triangle';
    }
}

// Update weather display
function updateWeatherDisplay(data) {
    const { name, main, weather, wind, sys } = data;

    // Update weather information
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

    // Update connection status with location accuracy
    if (userCoordinates?.accuracy) {
        console.log(`Location accuracy: ${userCoordinates.accuracy} meters`);
    }
}

// Load alerts from CSV
async function loadAlerts() {
    try {
        const response = await fetch(CONFIG.CSV_SERVER_URL);

        if (!response.ok) {
            throw new Error(`Failed to fetch alerts: ${response.status}`);
        }

        const csvText = await response.text();
        alerts = parseCSV(csvText);

        // Filter active alerts (case-insensitive)
        filteredAlerts = alerts.filter(alert => {
            const isActive = String(alert.is_active || '').toUpperCase();
            return isActive === 'TRUE';
        });

        // Update active alerts count
        if (elements.activeAlertsCount) {
            elements.activeAlertsCount.textContent = filteredAlerts.length;
        }

        // Update last updated time
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        if (elements.lastUpdated) {
            elements.lastUpdated.textContent = `Last updated: ${timeString}`;
        }

        // Reset to first alert
        currentAlertIndex = 0;

        // Render alerts
        renderAlerts();

        // Update connection status
        updateConnectionStatus(true);

        console.log(`Loaded ${alerts.length} total alerts, ${filteredAlerts.length} active alerts`);
    } catch (error) {
        console.error('Error loading alerts:', error);
        updateConnectionStatus(false);
        showError('Failed to load alerts. Please check your connection.');
    }
}

// Parse CSV text with proper handling of quoted values
function parseCSV(csvText) {
    const lines = csvText.trim().split('\n');
    const headers = lines[0].split(',').map(header => header.trim());

    return lines.slice(1).map(line => {
        // Handle quoted values that might contain commas
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

        const alert = {};

        headers.forEach((header, index) => {
            let value = values[index] || '';
            // Remove surrounding quotes if present
            if (value.startsWith('"') && value.endsWith('"')) {
                value = value.slice(1, -1);
            }
            alert[header] = value;
        });

        return alert;
    });
}

// Render alerts
function renderAlerts() {
    // Clear existing alerts
    elements.alertsTrack.innerHTML = '';
    elements.alertsIndicators.innerHTML = '';

    if (filteredAlerts.length === 0) {
        elements.alertsTrack.innerHTML = `
            <div class="alert-placeholder">
                <i class="fas fa-check-circle" style="font-size: 3rem; color: #27ae60; margin-bottom: 20px;"></i>
                <h3>No Active Alerts</h3>
                <p>All clear! No active alerts at the moment.</p>
            </div>
        `;

        // Disable navigation buttons
        elements.prevAlertBtn.disabled = true;
        elements.nextAlertBtn.disabled = true;

        return;
    }

    // Create alert cards
    filteredAlerts.forEach((alert, index) => {
        // Create alert card
        const alertCard = document.createElement('div');
        alertCard.className = `alert-card ${index === 0 ? 'active' : ''} alert-${alert.severity?.toLowerCase() || 'medium'}`;
        alertCard.dataset.index = index;

        // Format severity for display
        const severity = alert.severity?.toLowerCase() || 'medium';
        const severityDisplay = severity.charAt(0).toUpperCase() + severity.slice(1);

        alertCard.innerHTML = `
            <div class="alert-header">
                <h3 class="alert-title">${escapeHtml(alert.title || 'No title')}</h3>
                <span class="alert-severity severity-${severity}">${severityDisplay}</span>
            </div>
            <div class="alert-description">
                ${escapeHtml(alert.description || 'No description available')}
            </div>
            <div class="alert-footer">
                <div class="alert-categories">
                    <span class="category-tag">${escapeHtml(alert.category || 'General')}</span>
                    ${alert.subcategory ? `<span class="category-tag">${escapeHtml(alert.subcategory)}</span>` : ''}
                    ${alert.location ? `<span class="category-tag"><i class="fas fa-map-marker-alt"></i> ${escapeHtml(alert.location)}</span>` : ''}
                </div>
                <div class="alert-tags">
                    ${alert.source ? `<span class="hashtag">${escapeHtml(alert.source)}</span>` : ''}
                    ${alert.source_id ? `<span class="hashtag">#${escapeHtml(alert.source_id)}</span>` : ''}
                    <span class="hashtag"><i class="fas fa-clock"></i> Just now</span>
                </div>
            </div>
        `;

        elements.alertsTrack.appendChild(alertCard);

        // Create indicator
        const indicator = document.createElement('div');
        indicator.className = `indicator ${index === 0 ? 'active' : ''}`;
        indicator.dataset.index = index;
        indicator.addEventListener('click', () => goToAlert(index));
        elements.alertsIndicators.appendChild(indicator);
    });

    // Enable navigation buttons if there are multiple alerts
    elements.prevAlertBtn.disabled = filteredAlerts.length <= 1;
    elements.nextAlertBtn.disabled = filteredAlerts.length <= 1;
}

// Navigate to specific alert
function goToAlert(index) {
    if (index < 0 || index >= filteredAlerts.length) return;

    // Update current index
    const oldIndex = currentAlertIndex;
    currentAlertIndex = index;

    // Update cards
    const cards = document.querySelectorAll('.alert-card');
    const indicators = document.querySelectorAll('.indicator');

    cards.forEach(card => {
        card.classList.remove('active', 'previous');
        if (parseInt(card.dataset.index) === index) {
            card.classList.add('active');
        } else if (parseInt(card.dataset.index) === oldIndex) {
            card.classList.add('previous');
        }
    });

    // Update indicators
    indicators.forEach(indicator => {
        indicator.classList.remove('active');
        if (parseInt(indicator.dataset.index) === index) {
            indicator.classList.add('active');
        }
    });

    // Reset auto-slide timer
    resetAlertSlide();
}

// Go to next alert
function nextAlert() {
    const nextIndex = (currentAlertIndex + 1) % filteredAlerts.length;
    goToAlert(nextIndex);
}

// Go to previous alert
function prevAlert() {
    const prevIndex = (currentAlertIndex - 1 + filteredAlerts.length) % filteredAlerts.length;
    goToAlert(prevIndex);
}

// Start auto-slide for alerts
function startAlertSlide() {
    if (alertSlideInterval) {
        clearInterval(alertSlideInterval);
    }

    alertSlideInterval = setInterval(() => {
        if (filteredAlerts.length > 1) {
            nextAlert();
        }
    }, CONFIG.ALERT_SLIDE_INTERVAL);
}

// Reset auto-slide timer
function resetAlertSlide() {
    if (alertSlideInterval) {
        clearInterval(alertSlideInterval);
        startAlertSlide();
    }
}

// Set up event listeners
function setupEventListeners() {
    // Alert navigation
    elements.prevAlertBtn.addEventListener('click', prevAlert);
    elements.nextAlertBtn.addEventListener('click', nextAlert);

    // Weather refresh - now fetches fresh location and weather
    elements.refreshWeatherBtn.addEventListener('click', async () => {
        try {
            await getUserLocation();
            if (userCoordinates) {
                await fetchWeather();
            }
        } catch (error) {
            console.error('Failed to refresh location:', error);
        }

        // Add visual feedback
        elements.refreshWeatherBtn.style.animation = 'spin 1s ease';
        setTimeout(() => {
            elements.refreshWeatherBtn.style.animation = '';
        }, 1000);
    });

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowLeft') {
            prevAlert();
        } else if (e.key === 'ArrowRight') {
            nextAlert();
        }
    });

    // Auto-refresh alerts every 2 minutes
    setInterval(() => {
        loadAlerts();
    }, CONFIG.REFRESH_INTERVAL);

    // Auto-refresh weather every 2 minutes using existing coordinates
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

// Show error message
function showError(message) {
    // Create error overlay
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-overlay';
    errorDiv.innerHTML = `
        <div class="error-content">
            <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: #e74c3c; margin-bottom: 20px;"></i>
            <h3>Connection Error</h3>
            <p>${message}</p>
            <button onclick="this.parentElement.parentElement.remove()" style="margin-top: 20px; padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer;">
                Dismiss
            </button>
        </div>
    `;

    // Add styles
    errorDiv.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    `;

    errorDiv.querySelector('.error-content').style.cssText = `
        background: white;
        padding: 40px;
        border-radius: 10px;
        text-align: center;
        max-width: 400px;
    `;

    document.body.appendChild(errorDiv);
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', init);