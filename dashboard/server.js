const express = require('express');
const fs = require('fs');
const path = require('path');
const cors = require('cors');

const app = express();
const PORT = 3000;

// Middleware
app.use(cors());
app.use(express.static('.')); // Serve static files from current directory

// Sample CSV data route
app.get('/alerts', (req, res) => {
    const csvPath = path.join(__dirname, 'data', 'new_alerts.csv');

    // Check if file exists
    if (fs.existsSync(csvPath)) {
        res.setHeader('Content-Type', 'text/csv');
        res.sendFile(csvPath);
    } else {
        // Return sample data if file doesn't exist
        const sampleData = `empty`;

        res.setHeader('Content-Type', 'text/csv');
        res.send(sampleData);
    }
});

app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
    console.log(`CSV data available at http://localhost:${PORT}/alerts`);
});
// News CSV data route
// News CSV data route
app.get('/news-data', (req, res) => {
    const csvPath = path.join(__dirname, 'data', 'combined_newsdata.csv');

    // Check if file exists
    if (fs.existsSync(csvPath)) {
        try {
            const csvData = fs.readFileSync(csvPath, 'utf8');
            const lines = csvData.trim().split('\n');
            console.log(`Serving news CSV file with ${lines.length - 1} news items`);
            console.log('Headers:', lines[0]);

            // Log first few lines to debug
            if (lines.length > 1) {
                console.log('First news item:', lines[1]);
            }

            res.setHeader('Content-Type', 'text/csv');
            res.send(csvData);
        } catch (error) {
            console.error('Error reading news CSV file:', error);
            res.status(500).send('Error reading news CSV file');
        }
    } else {
        console.log('News CSV file not found, serving sample news data');
        // Sample news data with proper category column
        const sampleNews = `empty`;

        res.setHeader('Content-Type', 'text/csv');
        res.send(sampleNews);
    }
});
