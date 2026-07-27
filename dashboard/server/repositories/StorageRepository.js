/**
 * StorageRepository Interface / Base Class
 * Defines the contract for data storage implementations (e.g., Google Sheets, SQLite, Postgres).
 */
export class StorageRepository {
  /**
   * Initialize the database schema or storage connection.
   */
  async init() {
    throw new Error('Method not implemented: init');
  }

  /**
   * Retrieve all raw data (transactions, merchant aliases, category map).
   */
  async getRawData() {
    throw new Error('Method not implemented: getRawData');
  }

  /**
   * Save or sync transactions and reference data into the repository.
   * @param {Object} data - { transactions, merchantAliases, categoryMap }
   */
  async syncData(data) {
    throw new Error('Method not implemented: syncData');
  }

  /**
   * Retrieve resolved and filtered transactions.
   * @param {Object} filters
   */
  async getFilteredTransactions(filters) {
    throw new Error('Method not implemented: getFilteredTransactions');
  }

  /**
   * Retrieve KPI summary for a given set of filters.
   * @param {Object} filters
   */
  async getSummary(filters) {
    throw new Error('Method not implemented: getSummary');
  }
}
