import { google } from 'googleapis';
import path from 'path';
import { fileURLToPath } from 'url';
import { resolveAllTransactions, filterTransactions, computeKPIs } from '../../src/utils/dataLayer.ts';
import fs from 'fs';
import { SQLiteRepository } from '../repositories/SQLiteRepository.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const KEY_FILE_PATH = path.join(__dirname, '..', '..', '..', 'credentials', 'service_account.json');
const SPREADSHEET_ID = '1gnmlyYsQrzhBDEtsXrdjHZxcU40rzwtZpvSxxx5OSTI';

const auth = new google.auth.GoogleAuth({
  keyFile: KEY_FILE_PATH,
  scopes: ['https://www.googleapis.com/auth/spreadsheets.readonly'],
});
const sheets = google.sheets({ version: 'v4', auth });

const sqliteRepo = new SQLiteRepository();

// In-memory TTL cache (60 seconds) to avoid Google Sheets API rate limits
let cache = {
  data: null,
  timestamp: 0,
};
const CACHE_TTL_MS = 60 * 1000;

export async function getRawSheetsData(forceRefresh = false) {
  const now = Date.now();
  if (!forceRefresh && cache.data && (now - cache.timestamp < CACHE_TTL_MS)) {
    return cache.data;
  }

  const dbExists = fs.existsSync(sqliteRepo.dbPath);
  if (!forceRefresh && dbExists) {
    try {
      const dbData = await sqliteRepo.getRawData();
      if (dbData.transactions && dbData.transactions.length > 0) {
        cache = { data: dbData, timestamp: now };
        return dbData;
      }
    } catch (e) {
      console.warn('Fallback to Sheets API: SQLite read error:', e.message);
    }
  }

  const [transactionsRes, aliasesRes, categoriesRes] = await Promise.all([
    sheets.spreadsheets.values.get({ spreadsheetId: SPREADSHEET_ID, range: 'Transactions' }),
    sheets.spreadsheets.values.get({ spreadsheetId: SPREADSHEET_ID, range: 'Merchant_Aliases' }).catch(() => ({ data: { values: null } })),
    sheets.spreadsheets.values.get({ spreadsheetId: SPREADSHEET_ID, range: 'Category_Map' }).catch(() => ({ data: { values: null } })),
  ]);

  const raw = {
    transactions: transactionsRes.data.values || [],
    merchantAliases: aliasesRes.data.values || [],
    categoryMap: categoriesRes.data.values || [],
  };

  try {
    await sqliteRepo.syncData(raw);
    console.log(`Synced ${raw.transactions.length} rows to SQLite cache`);
  } catch (err) {
    console.warn('Failed to sync to SQLite cache:', err.message);
  }

  cache = {
    data: raw,
    timestamp: now,
  };

  return raw;
}

export async function getResolvedData(forceRefresh = false) {
  const raw = await getRawSheetsData(forceRefresh);
  const { transactions, kpis } = resolveAllTransactions(
    raw.transactions,
    raw.categoryMap,
    raw.merchantAliases
  );

  const categoriesSet = new Set();
  transactions.forEach((t) => {
    if (t.effective_category && t.effective_category !== 'Uncategorized') {
      categoriesSet.add(t.effective_category);
    }
  });

  return {
    transactions,
    kpis,
    totalCount: transactions.length,
    availableCategories: Array.from(categoriesSet).sort(),
  };
}

export function parseFiltersFromQuery(query) {
  return {
    dateRange: query.dateRange || 'all',
    dateFrom: query.dateFrom || undefined,
    dateTo: query.dateTo || undefined,
    category: query.category || 'all',
    bank: query.bank || 'all',
    search: query.search || '',
    onlyFlagged: query.onlyFlagged === 'true',
  };
}

export async function getSummary(query, forceRefresh = false) {
  const resolved = await getResolvedData(forceRefresh);
  const filters = parseFiltersFromQuery(query);
  const filteredTxns = filterTransactions(resolved.transactions, filters);
  const kpis = computeKPIs(filteredTxns);

  return {
    kpis,
    totalCount: resolved.totalCount,
    filteredCount: filteredTxns.length,
    availableCategories: resolved.availableCategories,
  };
}

export async function getFilteredTransactions(query, forceRefresh = false) {
  const resolved = await getResolvedData(forceRefresh);
  const filters = parseFiltersFromQuery(query);
  const filteredTxns = filterTransactions(resolved.transactions, filters);

  return {
    transactions: filteredTxns,
    totalCount: resolved.totalCount,
    filteredCount: filteredTxns.length,
  };
}
