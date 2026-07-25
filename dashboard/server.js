import express from 'express';
import cors from 'cors';
import { google } from 'googleapis';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = 3001;

app.use(cors());

// The path to your service account key file relative to the server script
const KEY_FILE_PATH = path.join(__dirname, '..', 'credentials', 'service_account.json');

// The spreadsheet ID from config.yaml
const SPREADSHEET_ID = '1gnmlyYsQrzhBDEtsXrdjHZxcU40rzwtZpvSxxx5OSTI';

// Authenticate with Google
const auth = new google.auth.GoogleAuth({
  keyFile: KEY_FILE_PATH,
  scopes: ['https://www.googleapis.com/auth/spreadsheets.readonly'],
});

const sheets = google.sheets({ version: 'v4', auth });

app.get('/api/data', async (req, res) => {
  try {
    // Fetch data from the three tabs
    const [transactionsRes, aliasesRes, categoriesRes] = await Promise.all([
      sheets.spreadsheets.values.get({
        spreadsheetId: SPREADSHEET_ID,
        range: 'Transactions', 
      }),
      sheets.spreadsheets.values.get({
        spreadsheetId: SPREADSHEET_ID,
        range: 'Merchant_Aliases', // Update if tab name differs
      }).catch(() => ({ data: { values: null } })), // Fallback if tab doesn't exist
      sheets.spreadsheets.values.get({
        spreadsheetId: SPREADSHEET_ID,
        range: 'Category_Map', // Update if tab name differs
      }).catch(() => ({ data: { values: null } }))
    ]);

    res.json({
      transactions: transactionsRes.data.values || [],
      merchantAliases: aliasesRes.data.values || [],
      categoryMap: categoriesRes.data.values || []
    });
  } catch (error) {
    console.error('Error fetching data from Google Sheets:', error);
    res.status(500).json({ error: 'Failed to fetch data' });
  }
});

app.listen(port, () => {
  console.log(`Server listening at http://localhost:${port}`);
});
