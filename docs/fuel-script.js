// Global variables
let fuelData = [];
let filteredData = [];
let charts = {};
let currentPage = 1;
const rowsPerPage = 10;
let refreshInterval = null;
let refreshCountdown = 30;
let currentView = 'all'; // 'all', 'petrol', 'diesel', 'furnace'

// Color scheme for charts
const chartColors = {
    petrol95: '#e74c3c',
    petrol92: '#e67e22',
    autoDiesel: '#3498db',
    superDiesel: '#2980b9',
    kerosene: '#9b59b6',
    industrialKerosene: '#8e44ad',
    furnace800: '#e74c3c',
    furnace1500High: '#c0392b',
    furnace1500Low: '#d35400'
};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadFuelData();
    setupEventListeners();
    setupDateInputs();
    startAutoRefresh();
});

// Load fuel data from CSV file
async function loadFuelData() {
    showLoading(true);

    try {
        const response = await fetch('data/new_fuel.csv');
        const csvText = await response.text();
        fuelData = parseCSV(csvText);

        // Sort data by date
        fuelData.sort((a, b) => new Date(a.date) - new Date(b.date));

        // Set filtered data to all data initially
        filteredData = [...fuelData];

        // Initialize view
        applyViewFilter(currentView);

        // Update displays
        updateStats();
        updateCharts();
        updateTable();

        // Update last update time
        const lastDate = fuelData.length > 0 ? fuelData[fuelData.length - 1].date_str : 'N/A';
        document.getElementById('lastUpdate').textContent = lastDate;

    } catch (error) {
        console.error('Error loading fuel data:', error);
        alert('Error loading fuel price data. Please check console for details.');
    } finally {
        showLoading(false);
    }
}

// Parse CSV data
function parseCSV(csvText) {
    const lines = csvText.trim().split('\n');
    const headers = lines[0].split(',').map(h => h.trim());

    const data = [];
    for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;

        const values = line.split(',').map(v => v.trim());
        const row = {};

        headers.forEach((header, index) => {
            let value = values[index] || '';

            // Parse numeric values
            if (header.includes('date')) {
                row[header] = value;
            } else {
                row[header] = parseFloat(value) || 0;
            }
        });

        // Ensure all required fields exist
        if (!row.date_str) {
            if (row.date) {
                const date = new Date(row.date);
                row.date_str = date.toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                });
            } else {
                row.date_str = `Record ${i}`;
            }
        }

        data.push(row);
    }

    return data;
}

// Setup event listeners
function setupEventListeners() {
    // Date range filter
    document.getElementById('applyDateRange').addEventListener('click', applyDateRangeFilter);
    document.getElementById('resetFilters').addEventListener('click', resetFilters);

    // View toggles
    document.getElementById('viewAll').addEventListener('click', () => setView('all'));
    document.getElementById('viewPetrol').addEventListener('click', () => setView('petrol'));
    document.getElementById('viewDiesel').addEventListener('click', () => setView('diesel'));
    document.getElementById('viewFurnace').addEventListener('click', () => setView('furnace'));

    // Table search
    document.getElementById('tableSearch').addEventListener('input', filterTable);

    // Pagination
    document.getElementById('prevPage').addEventListener('click', goToPrevPage);
    document.getElementById('nextPage').addEventListener('click', goToNextPage);

    // Export data
    document.getElementById('exportData').addEventListener('click', exportData);
}

// Setup date inputs with default values
function setupDateInputs() {
    const today = new Date();
    const oneMonthAgo = new Date();
    oneMonthAgo.setMonth(today.getMonth() - 1);

    document.getElementById('startDate').valueAsDate = oneMonthAgo;
    document.getElementById('endDate').valueAsDate = today;
}

// Update statistics
function updateStats() {
    if (fuelData.length === 0) return;

    const latest = fuelData[fuelData.length - 1];
    const previous = fuelData.length > 1 ? fuelData[fuelData.length - 2] : latest;

    // Update header stats
    document.getElementById('latestPetrol95').textContent = formatPrice(latest.petrol_95);
    document.getElementById('latestAutoDiesel').textContent = formatPrice(latest.auto_diesel);
    document.getElementById('dataPoints').textContent = fuelData.length;

    // Update current prices in chart headers
    document.getElementById('currentPetrol95').textContent = formatPrice(latest.petrol_95);
    document.getElementById('currentPetrol92').textContent = formatPrice(latest.petrol_92);
    document.getElementById('currentAutoDiesel').textContent = formatPrice(latest.auto_diesel);
    document.getElementById('currentSuperDiesel').textContent = formatPrice(latest.super_diesel);
    document.getElementById('currentKerosene').textContent = formatPrice(latest.kerosene);
    document.getElementById('currentIndustrialKerosene').textContent = formatPrice(latest.industrial_kerosene);
    document.getElementById('currentFurnace800').textContent = formatPrice(latest.furnace_800);
    document.getElementById('currentFurnace1500High').textContent = formatPrice(latest.furnace_1500_high);
    document.getElementById('currentFurnace1500Low').textContent = formatPrice(latest.furnace_1500_low);

    // Calculate and update changes
    updateChangeIndicator('changePetrol95', latest.petrol_95, previous.petrol_95);
    updateChangeIndicator('changePetrol92', latest.petrol_92, previous.petrol_92);
    updateChangeIndicator('changeAutoDiesel', latest.auto_diesel, previous.auto_diesel);
    updateChangeIndicator('changeSuperDiesel', latest.super_diesel, previous.super_diesel);
    updateChangeIndicator('changeKerosene', latest.kerosene, previous.kerosene);
    updateChangeIndicator('changeIndustrialKerosene', latest.industrial_kerosene, previous.industrial_kerosene);
    updateChangeIndicator('changeFurnace800', latest.furnace_800, previous.furnace_800);
    updateChangeIndicator('changeFurnace1500High', latest.furnace_1500_high, previous.furnace_1500_high);
    updateChangeIndicator('changeFurnace1500Low', latest.furnace_1500_low, previous.furnace_1500_low);
}

// Update change indicator with appropriate color
function updateChangeIndicator(elementId, current, previous) {
    const element = document.getElementById(elementId);
    const change = current - previous;

    element.textContent = change >= 0 ? `+${change.toFixed(2)}` : change.toFixed(2);

    // Remove existing classes
    element.classList.remove('change-positive', 'change-negative', 'change-neutral');

    // Add appropriate class
    if (change > 0) {
        element.classList.add('change-negative');
    } else if (change < 0) {
        element.classList.add('change-positive');
    } else {
        element.classList.add('change-neutral');
    }
}

// Format price
function formatPrice(price) {
    return `LKR ${price.toFixed(2)}`;
}

// Apply date range filter
function applyDateRangeFilter() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    if (!startDate || !endDate) {
        alert('Please select both start and end dates');
        return;
    }

    const start = new Date(startDate);
    const end = new Date(endDate);

    if (start > end) {
        alert('Start date cannot be after end date');
        return;
    }

    filteredData = fuelData.filter(row => {
        const rowDate = new Date(row.date);
        return rowDate >= start && rowDate <= end;
    });

    applyViewFilter(currentView);
    updateCharts();
    updateTable();
}

// Reset all filters
function resetFilters() {
    filteredData = [...fuelData];
    document.getElementById('startDate').valueAsDate = new Date();
    document.getElementById('endDate').valueAsDate = new Date();
    document.getElementById('tableSearch').value = '';
    applyViewFilter('all');
    setView('all');
    updateCharts();
    updateTable();
}

// Set view type
function setView(view) {
    currentView = view;

    // Update active button
    document.querySelectorAll('.btn-toggle').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`view${view.charAt(0).toUpperCase() + view.slice(1)}`).classList.add('active');

    applyViewFilter(view);
    updateCharts();
    updateTableVisibility();
}

// Apply view filter
function applyViewFilter(view) {
    const chartContainers = document.querySelectorAll('.chart-container');

    chartContainers.forEach(container => {
        container.style.display = 'block';

        if (view === 'petrol' && !container.classList.contains('petrol-chart')) {
            container.style.display = 'none';
        } else if (view === 'diesel' && !container.classList.contains('diesel-chart')) {
            container.style.display = 'none';
        } else if (view === 'furnace' && !container.classList.contains('furnace-chart')) {
            container.style.display = 'none';
        }
    });
}

// Update charts visibility
function updateTableVisibility() {
    const chartContainers = document.querySelectorAll('.chart-container');
    let visibleCount = 0;

    chartContainers.forEach(container => {
        if (container.style.display !== 'none') {
            visibleCount++;
        }
    });

    // Adjust grid based on visible charts
    const grid = document.querySelector('.charts-grid');
    if (visibleCount <= 2) {
        grid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(500px, 1fr))';
    } else {
        grid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(400px, 1fr))';
    }
}

// Update all charts
function updateCharts() {
    if (filteredData.length === 0) return;

    // Extract data for charts
    const dates = filteredData.map(row => row.date_str);

    // Update each chart
    updateSingleChart('petrol95Chart', 'Petrol 95 Octane', dates,
        filteredData.map(row => row.petrol_95), chartColors.petrol95);

    updateSingleChart('petrol92Chart', 'Petrol 92 Octane', dates,
        filteredData.map(row => row.petrol_92), chartColors.petrol92);

    updateSingleChart('autoDieselChart', 'Auto Diesel', dates,
        filteredData.map(row => row.auto_diesel), chartColors.autoDiesel);

    updateSingleChart('superDieselChart', 'Super Diesel', dates,
        filteredData.map(row => row.super_diesel), chartColors.superDiesel);

    updateSingleChart('keroseneChart', 'Kerosene', dates,
        filteredData.map(row => row.kerosene), chartColors.kerosene);

    updateSingleChart('industrialKeroseneChart', 'Industrial Kerosene', dates,
        filteredData.map(row => row.industrial_kerosene), chartColors.industrialKerosene);

    updateSingleChart('furnace800Chart', 'Furnace Oil 800', dates,
        filteredData.map(row => row.furnace_800), chartColors.furnace800);

    updateSingleChart('furnace1500HighChart', 'Furnace 1500 High', dates,
        filteredData.map(row => row.furnace_1500_high), chartColors.furnace1500High);

    updateSingleChart('furnace1500LowChart', 'Furnace 1500 Low', dates,
        filteredData.map(row => row.furnace_1500_low), chartColors.furnace1500Low);
}

// Update a single chart
function updateSingleChart(canvasId, label, labels, data, color) {
    const ctx = document.getElementById(canvasId).getContext('2d');

    // Destroy existing chart if it exists
    if (charts[canvasId]) {
        charts[canvasId].destroy();
    }

    // Create new chart
    charts[canvasId] = new Chart(ctx, {
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
                pointRadius: 3,
                pointHoverRadius: 5
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
                            return `${label}: LKR ${context.parsed.y.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Date',
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
                        text: 'Price (LKR)',
                        color: '#666',
                        font: {
                            family: "'Roboto', sans-serif",
                            size: 12
                        }
                    },
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        color: '#666',
                        font: {
                            family: "'Roboto', sans-serif",
                            size: 10
                        },
                        callback: function(value) {
                            return 'LKR ' + value.toFixed(2);
                        }
                    }
                }
            }
        }
    });
}

// Update table with pagination
function updateTable() {
    const tableBody = document.getElementById('fuelTableBody');
    const searchTerm = document.getElementById('tableSearch').value.toLowerCase();

    // Filter data based on search term
    let displayData = filteredData;
    if (searchTerm) {
        displayData = filteredData.filter(row =>
            Object.values(row).some(value =>
                value.toString().toLowerCase().includes(searchTerm)
            )
        );
    }

    // Calculate pagination
    const totalRows = displayData.length;
    const totalPages = Math.ceil(totalRows / rowsPerPage);
    const startIndex = (currentPage - 1) * rowsPerPage;
    const endIndex = Math.min(startIndex + rowsPerPage, totalRows);
    const pageData = displayData.slice(startIndex, endIndex);

    // Clear table
    tableBody.innerHTML = '';

    // Populate table with page data
    pageData.forEach(row => {
        const tr = document.createElement('tr');

        tr.innerHTML = `
            <td>${row.date_str}</td>
            <td>${row.petrol_95.toFixed(2)}</td>
            <td>${row.petrol_92.toFixed(2)}</td>
            <td>${row.auto_diesel.toFixed(2)}</td>
            <td>${row.super_diesel.toFixed(2)}</td>
            <td>${row.kerosene.toFixed(2)}</td>
            <td>${row.industrial_kerosene.toFixed(2)}</td>
            <td>${row.furnace_800.toFixed(2)}</td>
            <td>${row.furnace_1500_high.toFixed(2)}</td>
            <td>${row.furnace_1500_low.toFixed(2)}</td>
        `;

        tableBody.appendChild(tr);
    });

    // Update pagination controls
    updatePaginationControls(totalPages, totalRows, startIndex, endIndex);
}

// Update pagination controls
function updatePaginationControls(totalPages, totalRows, startIndex, endIndex) {
    document.getElementById('currentPage').textContent = currentPage;
    document.getElementById('totalPages').textContent = totalPages;
    document.getElementById('rowsShown').textContent = totalRows > 0 ? `${startIndex + 1}-${endIndex}` : '0';
    document.getElementById('totalRows').textContent = totalRows;

    document.getElementById('prevPage').disabled = currentPage === 1;
    document.getElementById('nextPage').disabled = currentPage === totalPages || totalPages === 0;
}

// Filter table based on search input
function filterTable() {
    currentPage = 1;
    updateTable();
}

// Go to previous page
function goToPrevPage() {
    if (currentPage > 1) {
        currentPage--;
        updateTable();
    }
}

// Go to next page
function goToNextPage() {
    const totalPages = Math.ceil(filteredData.length / rowsPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        updateTable();
    }
}

// Export data as CSV
function exportData() {
    if (filteredData.length === 0) {
        alert('No data to export');
        return;
    }

    // Create CSV content
    const headers = ['Date', 'Petrol 95', 'Petrol 92', 'Auto Diesel', 'Super Diesel',
                     'Kerosene', 'Industrial Kerosene', 'Furnace 800',
                     'Furnace 1500 High', 'Furnace 1500 Low'];

    let csvContent = headers.join(',') + '\n';

    filteredData.forEach(row => {
        const rowData = [
            row.date_str,
            row.petrol_95.toFixed(2),
            row.petrol_92.toFixed(2),
            row.auto_diesel.toFixed(2),
            row.super_diesel.toFixed(2),
            row.kerosene.toFixed(2),
            row.industrial_kerosene.toFixed(2),
            row.furnace_800.toFixed(2),
            row.furnace_1500_high.toFixed(2),
            row.furnace_1500_low.toFixed(2)
        ];
        csvContent += rowData.join(',') + '\n';
    });

    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fuel_prices_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// Start auto-refresh timer
function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        refreshCountdown--;
        document.getElementById('refreshCountdown').textContent = refreshCountdown;
        document.getElementById('footerRefreshCountdown').textContent = refreshCountdown;

        if (refreshCountdown <= 0) {
            loadFuelData();
            resetRefreshCountdown();
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