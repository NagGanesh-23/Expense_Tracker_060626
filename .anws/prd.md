# Product Requirements Document (PRD): Automated Expense Tracker

## 1. Product Overview
The Automated Expense Tracker is a streamlined pipeline application designed to automate the extraction, normalization, classification, and tracking of personal financial transactions. It takes raw bank/credit card statements from various sources, processes them through a multi-tiered classification engine (Rules -> Machine Learning -> Large Language Models), and outputs the categorized transactions to a centralized Google Sheet for personal finance management.

## 2. Target Audience
- **Primary User:** Individuals who want to maintain an automated, zero-friction expense tracking system without manual data entry.
- **Secondary User:** Developers or data enthusiasts who want a hackable and extensible personal finance tool.

## 3. Key Features
- **Multi-Source Support:** Out-of-the-box support for multiple Indian banking and credit card statements (ICICI Savings, ICICI CC, Axis MyZone, SBI Cashback, HDFC Pixel).
- **Google Drive Sync:** Automatically fetches new, unprocessed statements from a configured Google Drive folder.
- **Multi-Tier Classification Engine:**
  - **Rule-Based:** Fast, keyword-based categorization configured via `config.yaml`.
  - **Machine Learning (ML):** Trains on historical data (`training_data.csv`) for fast and private probabilistic classification.
  - **LLM-Based:** Falls back to AI models (e.g., Gemini, Nvidia APIs) with batching and caching for robust zero-shot classification of novel transactions.
  - **Interactive Manual Review:** CLI-based prompt for low-confidence or uncategorized transactions to train the ML model continuously.
- **Automated Export:** Syncs the processed transactions directly to a configured Google Sheet.
- **Audit & Reporting:** Generates a local CSV and a Markdown-based audit report to ensure data integrity and highlight missing or zero-value transactions.

## 4. Functional Requirements
### 4.1. Input & Ingestion
- **CLI Execution:** Users can run the application via CLI specifying files locally (`--files`) or trigger Google Drive synchronization (`--drive-sync`).
- **Auto-Detection:** The system must automatically detect the statement source (bank/card type) if `--source auto` is specified.
- **Password Management:** Should handle password-protected PDFs seamlessly using a local `passwords.txt` or the `PDF_PASSWORDS` environment variable.

### 4.2. Parsing & Normalization
- **Parsing Engines:** Must accurately parse specific PDF/CSV formats and extract date, description, amount, and transaction type (credit/debit).
- **Normalization:** Must convert all extracted data into a unified, standardized schema before classification.

### 4.3. Classification
- **Orchestration:** The system must evaluate transactions in a strict fallback sequence: Rule -> ML (confidence > threshold) -> LLM -> Manual (if requested/uncategorized).
- **Continuous Learning:** Manual corrections must be appended to the training dataset so the ML model improves over time.

### 4.4. Output & Logging
- **Google Sheets Integration:** Must append (or reset and write if `--reset-sheet` is used) data to a specific Google Sheet using a Service Account.
- **Dry Run Mode:** Must support a `--dry-run` flag to process data and test the pipeline without writing to Google Sheets.
- **Logging:** Must provide a rich CLI output with summaries and save a persistent log file (`logs/pipeline.log`).

## 5. Non-Functional Requirements
- **Performance:** Parsing and Rule/ML classification should be near-instantaneous. LLM calls should be batched to respect API rate limits and reduce latency.
- **Reliability:** The system should not crash on a single malformed transaction; it should flag it in the audit report. The continuous learning loop must automatically trigger ML retraining when a configured threshold (`retrain_trigger_count`) of synced corrections is reached, ensuring models stay up-to-date without human intervention.
- **Extensibility:** Adding a new parser for a new bank should require minimal changes outside of creating the specific parser class and mapping it.
- **Security:** Credentials (API keys, Service Account JSON, passwords) must be read from external configuration files and never hardcoded in the repository.

## 6. Future Scope
- Support for more banks and statement formats.
- Native dashboard visualization (e.g., Streamlit or Dash) for local analytics.
- Webhook integrations (e.g., WhatsApp/Telegram bot) for real-time transaction recording.
