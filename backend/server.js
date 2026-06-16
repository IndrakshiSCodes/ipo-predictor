const express = require('express');
const axios = require('axios');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = 3000;
const PYTHON_API = 'http://localhost:5000';

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public'), { index: false }));

// ── Default route → landing page ──────────────────────────────────────────────
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'landing.html'));
});

app.get('/app', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'app.html'));
});

app.get('/auth', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'auth.html'));
});

// ── Auth routes ───────────────────────────────────────────────────────────────
app.post('/api/auth/signup', async (req, res) => {
    try {
        const response = await axios.post(`${PYTHON_API}/auth/signup`, req.body);
        res.json(response.data);
    } catch (err) {
        const status = err.response?.status || 500;
        const detail = err.response?.data?.detail || 'Signup failed';
        res.status(status).json({ error: detail });
    }
});

app.post('/api/auth/login', async (req, res) => {
    try {
        const response = await axios.post(`${PYTHON_API}/auth/login`, req.body);
        res.json(response.data);
    } catch (err) {
        const status = err.response?.status || 500;
        const detail = err.response?.data?.detail || 'Login failed';
        res.status(status).json({ error: detail });
    }
});

// ── App routes ────────────────────────────────────────────────────────────────
app.post('/api/predict', async (req, res) => {
    try {
        const response = await axios.post(`${PYTHON_API}/predict`, req.body);
        res.json(response.data);
    } catch (err) {
        res.status(500).json({ error: 'Prediction failed', detail: err.message });
    }
});

app.get('/api/historical', async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_API}/historical`);
        res.json(response.data);
    } catch (err) {
        res.status(500).json({ error: 'Failed to fetch historical data' });
    }
});

app.get('/api/analytics', async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_API}/analytics/summary`);
        res.json(response.data);
    } catch (err) {
        res.status(500).json({ error: 'Failed to fetch analytics' });
    }
});

app.listen(PORT, () => {
    console.log(`ListIQ backend running at http://localhost:${PORT}`);
});