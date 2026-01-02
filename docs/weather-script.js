// Global variables
let weatherData = [];
let currentLocation = null;
let charts = {
    humidity: null,
    temperature: null,
    wind: null
};
let refreshInterval = null;
let refreshCountdown = 30;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadWeatherData();
    setupEventListeners();
    startAutoRefresh();
});

// Load weather data from CSV file
async function loadWeatherData() {
    showLoading(true);

    try {
        const response = await fetch('data/new_weather.csv');
        const csvText = await response.text();
        weatherData = parseCSV(csvText);

        // Get only the last 10 rows (most recent data for each location)
        const recentData = getRecentData();

        // Populate location dropdown
        populateLocationDropdown(recentData);

        // Populate data table
        populateDataTable(recentData);

        // Update statistics
        updateStatistics();

        // Set default location to Colombo if available
        const colomboData = recentData.find(row => row.location === 'Colombo');
        if (colomboData) {
            selectLocation('Colombo');
        } else if (recentData.length > 0) {
            selectLocation(recentData[0].location);
        }

    } catch (error) {
        console.error('Error loading weather data:', error);
        alert('Error loading weather data. Please check console for details.');
    } finally {
        showLoading(false);
    }
}

// Get recent data (last 10 rows)
function getRecentData() {
    return weatherData.slice(-10);
}

// Parse CSV data
function parseCSV(csvText) {
    const lines = csvText.trim().split('\n');
    const headers = lines[0].split(',').map(h => h.trim());

    const data = [];
    for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;

        // Handle quoted fields with commas
        const regex = /(?:,|\n|^)("(?:(?:"")*[^"]*)*"|[^",\n]*|(?:\n|$))/g;
        const values = [];
        let match;

        while ((match = regex.exec(line + ',')) !== null) {
            let value = match[1];
            if (value.startsWith('"') && value.endsWith('"')) {
                value = value.slice(1, -1).replace(/""/g, '"');
            }
            values.push(value.trim());
        }

        const row = {};
        headers.forEach((header, index) => {
            row[header] = values[index] || '';
        });

        // Parse forecast JSON if it exists
        if (row.forecast && row.forecast.startsWith('[')) {
            try {
                row.forecast = JSON.parse(row.forecast.replace(/""/g, '"'));
            } catch (e) {
                console.error('Error parsing forecast:', e);
                row.forecast = [];
            }
        } else {
            row.forecast = [];
        }

        // Parse alerts if it exists
        if (row.alerts && row.alerts.startsWith('[')) {
            try {
                row.alerts = JSON.parse(row.alerts);
            } catch (e) {
                console.error('Error parsing alerts:', e);
                row.alerts = [];
            }
        } else {
            row.alerts = [];
        }

        // Ensure numeric values are properly parsed
        row.temperature = parseFloat(row.temperature) || 0;
        row.feels_like = parseFloat(row.feels_like) || 0;
        row.humidity = parseFloat(row.humidity) || 0;
        row.wind_speed = parseFloat(row.wind_speed) || 0;
        row.rain = parseFloat(row.rain) || 0;

        data.push(row);
    }

    return data;
}

// Populate location dropdown
function populateLocationDropdown(recentData) {
    const select = document.getElementById('locationSelect');

    // Clear existing options except the first one
    while (select.options.length > 1) {
        select.remove(1);
    }

    // Add options for each location
    recentData.forEach(row => {
        const option = document.createElement('option');
        option.value = row.location;
        option.textContent = row.location;
        select.appendChild(option);
    });
}

// Setup event listeners
function setupEventListeners() {
    // Location selection
    document.getElementById('locationSelect').addEventListener('change', function(e) {
        if (e.target.value) {
            selectLocation(e.target.value);
        }
    });

    // Refresh button
    document.getElementById('refreshWeather').addEventListener('click', function() {
        refreshWeatherData();
    });
}

// Select a location and update display
function selectLocation(locationName) {
    currentLocation = locationName;

    // Find the most recent data for this location
    const locationData = weatherData.filter(row => row.location === locationName);
    const currentData = locationData[locationData.length - 1]; // Get last entry

    // Update dropdown selection
    document.getElementById('locationSelect').value = locationName;

    // Update current weather display
    updateCurrentWeather(currentData);

    // Update detail cards
    updateDetailCards(currentData);

    // Update charts with historical data for this location
    updateCharts(locationData);

    // Update forecast display
    updateForecastDisplay(currentData.forecast || []);

    // Highlight current location in table
    highlightCurrentLocation(locationName);
}

// Update current weather display
function updateCurrentWeather(data) {
    const timestamp = formatTimestamp(data.timestamp);

    // Update weather icon based on condition
    const weatherIcon = document.getElementById('weatherIcon');
    updateWeatherIcon(weatherIcon, data.description);

    document.getElementById('currentLocation').textContent = data.location;
    document.getElementById('currentTemp').textContent = data.temperature.toFixed(1);
    document.getElementById('currentWeatherDesc').textContent = data.description;
    document.getElementById('currentHumidity').textContent = data.humidity;
    document.getElementById('currentWind').textContent = data.wind_speed.toFixed(1);
    document.getElementById('currentTime').textContent = formatTimestamp(data.timestamp);
}

// Update weather icon based on description
function updateWeatherIcon(iconElement, description) {
    const desc = description.toLowerCase();
    iconElement.className = 'fas ';

    if (desc.includes('clear')) {
        iconElement.classList.add('fa-sun');
    } else if (desc.includes('cloud')) {
        iconElement.classList.add('fa-cloud');
    } else if (desc.includes('rain')) {
        iconElement.classList.add('fa-cloud-rain');
    } else if (desc.includes('thunder') || desc.includes('storm')) {
        iconElement.classList.add('fa-bolt');
    } else if (desc.includes('snow')) {
        iconElement.classList.add('fa-snowflake');
    } else if (desc.includes('mist') || desc.includes('fog')) {
        iconElement.classList.add('fa-smog');
    } else {
        iconElement.classList.add('fa-cloud');
    }
}

// Update detail cards
function updateDetailCards(data) {
    document.getElementById('detailTemp').textContent = `${data.temperature.toFixed(1)}°C`;
    document.getElementById('detailFeelsLike').textContent = `${data.feels_like.toFixed(1)}°C`;
    document.getElementById('detailHumidity').textContent = `${data.humidity}%`;
    document.getElementById('detailRain').textContent = `${data.rain.toFixed(1)} mm`;
    document.getElementById('detailWind').textContent = `${data.wind_speed.toFixed(1)} m/s`;
    document.getElementById('detailCondition').textContent = data.description;

    // Handle alerts
    const alerts = data.alerts || [];
    const alertCount = Array.isArray(alerts) ? alerts.length : 0;
    document.getElementById('detailAlerts').textContent = alertCount > 0 ? `${alertCount} active` : 'None';

    // Handle forecast
    const forecast = data.forecast || [];
    const forecastCount = Array.isArray(forecast) ? forecast.length : 0;
    document.getElementById('detailForecast').textContent = `${forecastCount} periods`;
}

// Update charts with historical data
function updateCharts(locationData) {
    // Sort data by timestamp
    locationData.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    // Extract data for charts
    const timestamps = locationData.map(row => formatTimestamp(row.timestamp, true)); // true means chart format
    const temperatures = locationData.map(row => row.temperature);
    const humidities = locationData.map(row => row.humidity);
    const windSpeeds = locationData.map(row => row.wind_speed);

    // Update or create charts
    updateChart('humidityChart', 'Humidity (%)', timestamps, humidities, '#4ecdc4');
    updateChart('temperatureChart', 'Temperature (°C)', timestamps, temperatures, '#ff6b6b');
    updateChart('windChart', 'Wind Speed (m/s)', timestamps, windSpeeds, '#3498db');
}

// Update or create a chart
function updateChart(canvasId, label, labels, data, color) {
    const ctx = document.getElementById(canvasId).getContext('2d');

    // Destroy existing chart if it exists
    const chartKey = canvasId.replace('Chart', '');
    if (charts[chartKey]) {
        charts[chartKey].destroy();
    }

    // Create new chart
    charts[chartKey] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                borderColor: color,
                backgroundColor: color + '20',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: color,
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        font: {
                            family: "'Roboto', sans-serif",
                            size: 12
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    titleColor: '#2c3e50',
                    bodyColor: '#2c3e50',
                    borderColor: '#3498db',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            return `${label.split(' ')[0]}: ${context.parsed.y.toFixed(1)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Time',
                        color: '#666',
                        font: {
                            family: "'Roboto', sans-serif",
                            size: 12
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        color: '#666',
                        maxRotation: 45,
                        font: {
                            family: "'Roboto', sans-serif",
                            size: 10
                        }
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: label.split(' ')[0],
                        color: '#666',
                        font: {
                            family: "'Roboto', sans-serif",
                            size: 12
                        }
                    },
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        color: '#666',
                        font: {
                            family: "'Roboto', sans-serif",
                            size: 10
                        }
                    }
                }
            }
        }
    });
}

// Update forecast display
function updateForecastDisplay(forecastData) {
    const forecastScroll = document.getElementById('forecastScroll');
    forecastScroll.innerHTML = '';

    if (!Array.isArray(forecastData) || forecastData.length === 0) {
        forecastScroll.innerHTML = '<p class="no-forecast">No forecast data available</p>';
        return;
    }

    // Display only next 8 periods for better visibility
    const displayForecast = forecastData.slice(0, 8);

    displayForecast.forEach(forecast => {
        const forecastCard = document.createElement('div');
        forecastCard.className = 'forecast-card';

        const time = new Date(forecast.time);
        const formattedTime = time.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });

        forecastCard.innerHTML = `
            <div class="forecast-time">${formattedTime}</div>
            <div class="forecast-temp">${forecast.temperature.toFixed(1)}°C</div>
            <div class="forecast-details">
                <div>
                    <span>Feels like:</span>
                    <span>${forecast.feels_like.toFixed(1)}°C</span>
                </div>
                <div>
                    <span>Humidity:</span>
                    <span>${forecast.humidity}%</span>
                </div>
                <div>
                    <span>Wind:</span>
                    <span>${forecast.wind_speed.toFixed(1)} m/s</span>
                </div>
                <div>
                    <span>Rain:</span>
                    <span>${forecast.rain.toFixed(1)} mm</span>
                </div>
            </div>
        `;

        forecastScroll.appendChild(forecastCard);
    });
}

// Populate data table
function populateDataTable(recentData) {
    const tableBody = document.getElementById('weatherTableBody');
    tableBody.innerHTML = '';

    recentData.forEach(row => {
        const tr = document.createElement('tr');

        tr.innerHTML = `
            <td>${row.location}</td>
            <td>${row.temperature.toFixed(1)}</td>
            <td>${row.feels_like.toFixed(1)}</td>
            <td>${row.humidity}</td>
            <td>${row.description}</td>
            <td>${row.wind_speed.toFixed(1)}</td>
            <td>${row.rain.toFixed(1)}</td>
            <td>${formatTimestamp(row.timestamp)}</td>
        `;

        tableBody.appendChild(tr);
    });
}

// Highlight current location in table
function highlightCurrentLocation(locationName) {
    const rows = document.querySelectorAll('#weatherTable tbody tr');

    rows.forEach(row => {
        row.classList.remove('current-location');
        const locationCell = row.cells[0];
        if (locationCell.textContent === locationName) {
            row.classList.add('current-location');
        }
    });
}

// Update statistics
function updateStatistics() {
    const recentData = getRecentData();
    const lastUpdate = recentData[0] ? new Date(recentData[0].timestamp) : new Date();

    document.getElementById('dataCount').textContent = recentData.length;
    document.getElementById('lastUpdate').textContent = formatTimestamp(lastUpdate.toISOString());
}

// Format timestamp
// Format timestamp
function formatTimestamp(timestamp, chart = false) {
    if (!timestamp) return '--';

    try {
        const date = new Date(timestamp);

        if (chart) {
            // For chart labels - show both date and time
            return date.toLocaleString([], {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } else {
            // For table and detailed display
            return date.toLocaleString([], {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }
    } catch (e) {
        return timestamp;
    }
}

// Refresh weather data
function refreshWeatherData() {
    loadWeatherData();
    resetRefreshCountdown();
}

// Start auto-refresh timer
function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        refreshCountdown--;
        document.getElementById('refreshCountdown').textContent = refreshCountdown;
        document.getElementById('footerRefreshCountdown').textContent = refreshCountdown;

        if (refreshCountdown <= 0) {
            refreshWeatherData();
        }
    }, 1000);
}

// Reset refresh countdown
function resetRefreshCountdown() {
    refreshCountdown = 30;
    document.getElementById('refreshCountdown').textContent = refreshCountdown;
    document.getElementById('footerRefreshCountdown').textContent = refreshCountdown;
}

// Show/hide loading overlay
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (show) {
        overlay.classList.add('active');
    } else {
        overlay.classList.remove('active');
    }
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});