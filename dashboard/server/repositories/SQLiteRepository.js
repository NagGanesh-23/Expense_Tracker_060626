import initSqlJs from 'sql.js';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { StorageRepository } from './StorageRepository.js';
import { resolveAllTransactions, filterTransactions, computeKPIs } from '../../src/utils/dataLayer.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DB_PATH = path.join(__dirname, '..', '..', 'data', 'expense_vault.db');

export class SQLiteRepository extends StorageRepository {
  constructor(dbPath = DB_PATH) {
    super();
    this.dbPath = dbPath;
    this.db = null;
    this.SQL = null;
  }

  async init() {
    if (this.db) return this;
    
    if (!this.SQL) {
      this.SQL = await initSqlJs();
    }

    const dir = path.dirname(this.dbPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    if (fs.existsSync(this.dbPath)) {
      const fileBuffer = fs.readFileSync(this.dbPath);
      this.db = new this.SQL.Database(fileBuffer);
    } else {
      this.db = new this.SQL.Database();
    }

    // Create tables for transactions and reference maps
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS transactions (
        transaction_id TEXT PRIMARY KEY,
        transaction_date TEXT,
        bank TEXT,
        source_account TEXT,
        description_raw TEXT,
        description TEXT,
        amount REAL,
        is_spend INTEGER,
        category TEXT,
        effective_category TEXT,
        effective_bucket TEXT,
        classification_method TEXT,
        review_status TEXT,
        needs_review INTEGER,
        confidence TEXT,
        possible_duplicate INTEGER
      );

      CREATE TABLE IF NOT EXISTS merchant_aliases (
        alias TEXT PRIMARY KEY,
        canonical_merchant TEXT,
        category TEXT,
        confidence TEXT
      );

      CREATE TABLE IF NOT EXISTS category_map (
        raw_category TEXT PRIMARY KEY,
        target_category TEXT,
        bucket TEXT
      );
    `);
    
    this.saveToDisk();
    return this;
  }

  saveToDisk() {
    if (!this.db) return;
    const dataBuffer = this.db.export();
    fs.writeFileSync(this.dbPath, Buffer.from(dataBuffer));
  }

  queryAll(sql, params = []) {
    if (!this.db) return [];
    const res = this.db.exec(sql, params);
    if (!res || res.length === 0) return [];
    const { columns, values } = res[0];
    return values.map(valArray => {
      const row = {};
      columns.forEach((col, idx) => {
        row[col] = valArray[idx];
      });
      return row;
    });
  }

  async syncData(data) {
    if (!this.db) await this.init();

    const { transactions = [], merchantAliases = [], categoryMap = [] } = data;
    
    // Resolve transactions against reference tables before storing in SQLite
    const { transactions: resolvedTxns } = resolveAllTransactions(
      transactions,
      categoryMap,
      merchantAliases
    );

    this.db.exec('BEGIN TRANSACTION;');
    this.db.exec('DELETE FROM transactions; DELETE FROM merchant_aliases; DELETE FROM category_map;');

    const insertTx = this.db.prepare(`
      INSERT OR REPLACE INTO transactions (
        transaction_id, transaction_date, bank, source_account,
        description_raw, description, amount, is_spend,
        category, effective_category, effective_bucket, classification_method,
        review_status, needs_review, confidence, possible_duplicate
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    for (const t of resolvedTxns) {
      insertTx.run([
        t.transaction_id || `${t.transaction_date}-${t.amount}-${t.description}`,
        t.transaction_date || '',
        t.bank || '',
        t.source_account || '',
        t.description_raw || '',
        t.description || '',
        t.amount || 0,
        t.is_spend ? 1 : 0,
        t.category || '',
        t.effective_category || '',
        t.effective_bucket || '',
        t.classification_method || '',
        t.review_status || '',
        t.needs_review ? 1 : 0,
        t.confidence || '',
        t.possible_duplicate ? 1 : 0
      ]);
    }
    insertTx.free();

    const insertAlias = this.db.prepare(`
      INSERT OR REPLACE INTO merchant_aliases (alias, canonical_merchant, category, confidence)
      VALUES (?, ?, ?, ?)
    `);
    for (const row of merchantAliases) {
      if (row && row[0]) {
        insertAlias.run([row[0], row[1] || '', row[2] || '', row[3] || '']);
      }
    }
    insertAlias.free();

    const insertCat = this.db.prepare(`
      INSERT OR REPLACE INTO category_map (raw_category, target_category, bucket)
      VALUES (?, ?, ?)
    `);
    for (const row of categoryMap) {
      if (row && row[0]) {
        insertCat.run([row[0], row[1] || '', row[2] || '']);
      }
    }
    insertCat.free();

    this.db.exec('COMMIT;');
    this.saveToDisk();

    return { count: resolvedTxns.length };
  }

  async getAllResolvedTransactions() {
    if (!this.db) await this.init();
    const rows = this.queryAll('SELECT * FROM transactions');
    return rows.map(r => ({
      ...r,
      is_spend: Boolean(r.is_spend),
      needs_review: Boolean(r.needs_review),
      possible_duplicate: Boolean(r.possible_duplicate)
    }));
  }

  async getFilteredTransactions(filters) {
    const allTxns = await this.getAllResolvedTransactions();
    const filtered = filterTransactions(allTxns, filters);
    return {
      transactions: filtered,
      totalCount: allTxns.length,
      filteredCount: filtered.length,
    };
  }

  async getSummary(filters) {
    const allTxns = await this.getAllResolvedTransactions();
    const filtered = filterTransactions(allTxns, filters);
    const kpis = computeKPIs(filtered);

    const categoriesSet = new Set();
    allTxns.forEach((t) => {
      if (t.effective_category && t.effective_category !== 'Uncategorized') {
        categoriesSet.add(t.effective_category);
      }
    });

    return {
      kpis,
      totalCount: allTxns.length,
      filteredCount: filtered.length,
      availableCategories: Array.from(categoriesSet).sort(),
    };
  }

  async getRawData() {
    if (!this.db) await this.init();
    const txns = this.queryAll('SELECT * FROM transactions');
    const aliases = this.queryAll('SELECT alias, canonical_merchant, category, confidence FROM merchant_aliases');
    const cats = this.queryAll('SELECT raw_category, target_category, bucket FROM category_map');

    return {
      transactions: txns.map(t => [
        t.transaction_id, t.transaction_date, t.bank, t.source_account,
        t.description_raw, t.description, t.amount, t.is_spend ? 'TRUE' : 'FALSE',
        t.category, t.effective_category, t.effective_bucket, t.classification_method,
        t.review_status, t.needs_review ? 'TRUE' : 'FALSE', t.confidence, t.possible_duplicate ? 'TRUE' : 'FALSE'
      ]),
      merchantAliases: aliases.map(r => [r.alias, r.canonical_merchant, r.category, r.confidence]),
      categoryMap: cats.map(r => [r.raw_category, r.target_category, r.bucket])
    };
  }
}
