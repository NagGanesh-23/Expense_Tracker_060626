import express from 'express';
import cors from 'cors';
import compression from 'compression';
import { getRawSheetsData, getSummary, getFilteredTransactions } from './server/services/aggregationService.js';

const app = express();
const port = process.env.PORT || 3001;

// Enable CORS and Brotli/Gzip response compression
app.use(cors());
app.use(compression());

// v1 REST API: Backend Aggregation Layer
app.get('/api/v1/summary', async (req, res) => {
  try {
    const forceRefresh = req.query.refresh === 'true';
    const summary = await getSummary(req.query, forceRefresh);
    res.json(summary);
  } catch (error) {
    console.error('Error in /api/v1/summary:', error);
    res.status(500).json({ error: 'Failed to compute summary' });
  }
});

app.get('/api/v1/transactions', async (req, res) => {
  try {
    const forceRefresh = req.query.refresh === 'true';
    const txns = await getFilteredTransactions(req.query, forceRefresh);
    res.json(txns);
  } catch (error) {
    console.error('Error in /api/v1/transactions:', error);
    res.status(500).json({ error: 'Failed to fetch transactions' });
  }
app.post('/api/v1/sync', async (req, res) => {
  try {
    const raw = await getRawSheetsData(true);
    res.json({ status: 'success', message: `Synced ${raw.transactions.length} rows to SQLite` });
  } catch (error) {
    console.error('Error in /api/v1/sync:', error);
    res.status(500).json({ error: 'Failed to sync data' });
  }
});

// Legacy raw data endpoint (caching enabled)
app.get('/api/data', async (req, res) => {
  try {
    const forceRefresh = req.query.refresh === 'true';
    const raw = await getRawSheetsData(forceRefresh);
    res.json(raw);
  } catch (error) {
    console.error('Error fetching data from Google Sheets:', error);
    res.status(500).json({ error: 'Failed to fetch data' });
  }
});

app.listen(port, () => {
  console.log(`Server listening at http://localhost:${port}`);
});
