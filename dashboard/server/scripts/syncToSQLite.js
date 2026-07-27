import { getRawSheetsData } from '../services/aggregationService.js';
import { SQLiteRepository } from '../repositories/SQLiteRepository.js';

async function sync() {
  console.log('Starting data sync from Google Sheets to SQLite...');
  try {
    const rawData = await getRawSheetsData(true);
    console.log(`Fetched ${rawData.transactions.length} transactions from Google Sheets.`);

    const repo = new SQLiteRepository();
    await repo.init();
    const result = await repo.syncData(rawData);
    console.log(`Successfully synced ${result.count} transactions into expense_vault.db!`);
    process.exit(0);
  } catch (err) {
    console.error('Error syncing to SQLite:', err);
    process.exit(1);
  }
}

sync();
