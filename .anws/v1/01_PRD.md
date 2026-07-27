# Product Requirements Document (PRD): Automated Expense Tracker

> **Version:** v1.1 (Baseline & Extensions)  
> **Status:** Approved / Active Implementation  

---

## 1. Product Overview
The **Automated Expense Tracker** is a comprehensive, production-grade personal finance pipeline and analytics suite. It automates the end-to-end lifecycle of financial transaction management—from ingesting raw bank and credit card statements (PDF/CSV) across diverse banking institutions to standardizing data schemas, classifying transactions via a multi-tiered AI engine (Rule -> ML -> LLM -> Interactive Manual Review), and synchronizing structured outputs to Google Sheets. 

With the **v1.1 extensions**, the suite features a continuous learning feedback loop that feeds manual corrections back into the machine learning models, automated data formatting tools for Google Sheets, an extensive developer utility suite, and an interactive, high-performance web dashboard for real-time reactive expense analytics without recurring cloud infrastructure costs.

---

## 2. Target Audience
- **Primary Users:** Individuals seeking a zero-friction, highly automated financial tracking system with complete privacy, custom categorization, and instant analytical visibility.
- **Secondary Users:** Developers, data scientists, and power users seeking an extensible, modular, and hackable personal finance platform with robust API integrations and custom machine learning pipelines.

---

## 3. Key Features

### 3.1. Multi-Source Ingestion & Pre-Processing
- **Out-of-the-Box Indian Banking Support:** Dedicated parsers for major Indian savings accounts and credit cards (ICICI Savings, ICICI Credit Card, Axis MyZone Credit Card, SBI Cashback Credit Card, HDFC Pixel Credit Card).
- **Google Drive Automated Sync:** Seamlessly monitors and retrieves unprocessed statement files from configured Google Drive folders using GCP Service Accounts (`--drive-sync`), preventing duplicate processing.
- **Secure Password Handling:** Automatically unlocks password-protected PDFs using local credential stores (`passwords.txt`) or environment variables (`PDF_PASSWORDS`) without hardcoding secrets.
- **Auto-Detection Engine:** Automatically identifies statement issuing banks and card types from raw file headers and content structure when invoked with `--source auto`.

### 3.2. Multi-Tiered Classification Engine
- **Tier 1: Rule-Based Classifier:** Deterministic, instantaneous keyword and regex pattern matching configured via `config.yaml`.
- **Tier 2: Machine Learning (ML) Classifier:** Fast, probabilistic text classification trained locally on historical transaction records (`training_data.csv`).
- **Tier 3: LLM Classifier:** Generative AI fallback (Google Gemini / Nvidia APIs) with batching and local caching (`.cache/llm_responses`) to accurately categorize novel, zero-shot transactions while minimizing API costs and latency.
- **Tier 4: Interactive Manual Review:** CLI prompt (`--interactive`) for low-confidence or uncategorized transactions, allowing real-time human assignment.

### 3.3. v1.1 Continuous Learning & Feedback Loop
- **Google Sheets Feedback Sync:** Reads human-reviewed corrections (`review_status = 'corrected'`) directly from live Google Sheets back into the local training dataset (`--sync-feedback`).
- **Automated Retraining Trigger:** Continuously monitors synced corrections and automatically invokes ML model retraining when a configurable threshold (`retrain_trigger_count` in `config.yaml`, default: 10) is reached.
- **Standalone Retraining:** CLI capability (`--retrain`) to rebuild ML embedding caches on demand after bulk data updates.

### 3.4. Output Synchronization & Formatting
- **Google Sheets Integration:** Synchronizes standardized transactions to target sheets via Service Account API, supporting append and clean reset (`--reset-sheet`) modes.
- **Automated Sheet Formatting (`gsheets_setup.py`):** Injects professional styling, custom header formatting, data validation dropdowns for categories, and conditional formatting rules (`--setup-sheet`) via `gspread-formatting`.
- **Audit & Anomaly Reporting:** Generates detailed Markdown audit reports (`audit_output.py`) flagging zero amounts, missing descriptions, and unreviewed entries while respecting a configurable whitelist of optional review fields (`audit_optional_fields`).
- **Duplicate Retention Strategy:** Identifies duplicate transactions across overlapping statements and retains them with explicit audit flags rather than silently deleting them, ensuring full financial auditability.

### 3.5. Interactive Expense Dashboard (`DASH-v1.1`)
- **Modern Web Application:** A high-performance, responsive React + Vite + Tailwind CSS frontend served by an Express backend (`server.js`), providing instantaneous data exploration.
- **Dynamic Category & Bucket Resolution:** Evaluates raw transaction data against live Sheet mapping tabs (`Category_Map` and `Merchant_Aliases`), dynamically computing `effective_category` and `effective_bucket` (e.g., Needs, Wants, Savings, Investments) with stale bucket override rules.
- **Five Reactive Views:**
  1. **Overview:** High-level KPIs, monthly spend trends, and expense breakdown by bucket.
  2. **Categories:** Deep dive into spending categories, interactive charts, and category-specific filtering.
  3. **Banks & Accounts:** Expenditure and credit utilization tracking across individual payment sources.
  4. **Classification Health:** Real-time visibility into AI confidence scores, classification method distribution (Rule vs ML vs LLM vs Manual), and unverified transaction queues.
  5. **Audit & Anomalies:** Direct view of flagged duplicates, missing data fields, and review status tracking.
- **Smart Data Truncation & Exclusion:** Excludes inter-account transfer rows from total spend/income calculations and cleanly truncates long merchant descriptions to ~60 characters for UI scannability.

### 3.6. Developer Utility Suite
- A comprehensive collection of 11 specialized scripts under `scripts/` for dataset labeling (`export_for_labeling.py`), LLM prompt testing (`export_for_llm.py`), hex encoding debugging (`hex_exposer.py`), sheet category verification (`check_sheet_cats.py`), and data cleanup (`cleanup_transactions.py`).

---

## 4. Functional Requirements

### 4.1. CLI Execution & Ingestion
- **REQ-CLI:** The system must support command-line execution with flags for local file ingestion (`--files`), Google Drive synchronization (`--drive-sync`), source selection (`--source`), and dry-run execution (`--dry-run`).
- **REQ-AUTO-DETECT:** When `--source auto` is passed, the ingestion engine must inspect file metadata and text patterns to route the statement to the correct parser class.
- **REQ-SECURE-PASS:** The system must decrypt protected PDFs using credentials loaded from `passwords.txt` or environment variables without exposing passwords in logs or traces.

### 4.2. Parsing & Normalization
- **REQ-PARSE:** Each bank parser must extract raw transaction records (date, narrative description, amount, credit/debit indicator) and gracefully handle malformed rows or empty files by raising structured exceptions or audit warnings.
- **REQ-NORM:** The `Normalizer` module must transform raw extracted records into a standardized unified schema, converting dates to `YYYY-MM-DD`, stripping whitespace/hex artifacts, and casting amounts to absolute floating-point numbers.

### 4.3. Multi-Tier Classification & Feedback Loop
- **REQ-CLASS-CASCADE:** The `ClassificationOrchestrator` must evaluate transactions sequentially: Rule -> ML -> LLM -> Interactive Manual Review. If a tier achieves a confidence score exceeding configured thresholds, subsequent tiers must be bypassed.
- **REQ-FEEDBACK-SYNC:** When invoked with `--sync-feedback`, `feedback_sync.py` must query the target Google Sheet for rows where `review_status == 'corrected'`, append these records to `models/training_data.csv`, update their sheet status to `'synced'`, and log progress.
- **REQ-AUTO-RETRAIN:** During feedback synchronization, if the count of newly synced records is greater than or equal to `retrain_trigger_count` in `config.yaml`, the system must automatically invoke `MLClassifier.train()` to rebuild model embeddings and log the triggering event.

### 4.4. Export, Audit & Data Integrity
- **REQ-GSHEETS-WRITE:** The writer module must authenticate via GCP Service Account and append processed records without altering previously verified historical rows.
- **REQ-GSHEETS-SETUP:** Invoking `--setup-sheet` must configure data validation dropdown menus on category columns and apply visual formatting rules without overwriting existing data.
- **REQ-AUDIT-REPORT:** The `audit_output.py` script must scan final transaction logs for anomalies (0.0 amounts, null core fields) while ignoring legitimate null values in human review columns specified in `config.yaml` under `audit_optional_fields` (e.g., `reviewed_category`, `reviewed_at`, `reviewer_notes`).
- **REQ-DUPLICATE-RETENTION:** Transactions detected as duplicates must be flagged in metadata (`is_duplicate = True`) and retained in output logs and sheets for transparent auditing.

### 4.5. Interactive Analytics Dashboard (`DASH-v1.1`)
- **REQ-DASH-DATA-LAYER:** The frontend data layer (`dataLayer.ts`) must ingest transaction JSON, merge corrections, apply category overrides from `Category_Map`, and derive standardized bank names from account strings.
- **REQ-DASH-EXCLUSIONS:** Transfer transactions (e.g., credit card bill payments, self-transfers) must be dynamically filtered out from aggregate expenditure and income KPIs.
- **REQ-DASH-VIEWS:** The dashboard must render 5 distinct, responsive views (Overview, Categories, Banks, Classification Health, Audit/Anomalies) supporting real-time cross-filtering without page reloads or database queries.

---

## 5. Non-Functional Requirements
- **Performance & Latency:** Local parsing, normalization, and Rule/ML classification must execute in sub-second timeframes for standard monthly statements. LLM requests must be batched and persistently cached to guarantee minimal latency and prevent redundant token consumption.
- **Reliability & Autonomous Operation:** The pipeline must be resilient against individual row formatting errors. With automated retraining triggers (`retrain_trigger_count`) and local quality gates (enforced via `pre-commit` hooks for `pytest` and `black`), the system autonomously maintains AI accuracy and code hygiene without manual intervention.
- **Extensibility:** The architecture must allow adding new bank parsers by implementing a standard parser interface and registering the class in `detector.py`, requiring zero modifications to downstream normalization or classification logic.
- **Security & Privacy:** All financial records, API keys, Service Account tokens, and PDF passwords must remain strictly within local environment boundaries or secure Google Cloud projects. Secrets must never be committed to source control.
- **Zero Recurring Cost:** The interactive dashboard and analytical engine must run entirely on local compute or free-tier static/serverless hosting without requiring paid cloud databases or active server instances.

---

## 6. Future Scope
- **Additional Institution Support:** Expanding parser coverage for international credit cards, investment statements (Zerodha, Groww), and UPI transaction archives.
- **Real-Time Messaging Bot:** WhatsApp/Telegram bot integration via webhooks for instant on-the-go cash expense logging.
- **Budgeting & Forecasting:** Predictive monthly spend forecasting and automated budget overrun alerts integrated into the interactive dashboard.
- **Multi-Currency Support:** Automated exchange rate conversion for international transactions and travel expenses.
