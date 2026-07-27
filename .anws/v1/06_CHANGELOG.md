# 06_CHANGELOG.md — Architecture & Pipeline Evolution Log

> **Version:** v1 (Baseline to v1.1 Extensions)  

---

## [v1.1] - 2026-07-27 (Post-v1 Pipeline Extensions & Dashboard)
### Added
- **Interactive Expense Dashboard (`DASH-v1.1`):** Complete React + Vite + Tailwind web application with Express backend (`dashboard/`), providing 5 reactive analytical views (Overview, Categories, Banks, Classification Health, Audit/Anomalies) and dynamic category/bucket resolution against live Google Sheets tabs (`Category_Map`, `Merchant_Aliases`).
- **Continuous Learning Feedback Loop (`T1.4.1` & `T1.4.3`):** Added `pipeline/feedback_sync.py` and CLI flags `--sync-feedback` and `--retrain`. Automatically syncs human review corrections from Google Sheets to local training data (`training_data.csv`) and triggers ML classifier model retraining upon reaching `retrain_trigger_count` (default: 10).
- **Automated Sheet Formatting (`T1.4.2`):** Added `output/gsheets_setup.py` and CLI flag `--setup-sheet` using `gspread-formatting` to inject category data validation dropdowns and conditional formatting rules into Google Sheets.
- **Developer Utility Suite (`T1.4.4`):** Added 11 specialized scripts under `scripts/` for anomaly auditing (`audit_output.py`), data sanitization (`cleanup_transactions.py`), hex inspection (`hex_exposer.py`), dataset extraction (`pull_training_data.py`, `export_for_labeling.py`), and CLI debugging (`terminal_peek.py`).
- **Duplicate Retention Tracking:** Flagged duplicate transactions (`is_duplicate = True`) are now preserved in output logs and sheets for full audit traceability instead of being dropped.
- **Optional Fields Whitelist:** Added `audit_optional_fields` to `config.yaml` to allow human review columns (`reviewed_category`, `reviewed_at`, `reviewer_notes`) to legitimately remain blank without triggering false-positive audit anomalies.

### Changed
- Promoted architecture specification documents from `.anws/prd.md` and `.anws/system_architecture.md` into the versioned ANWS root `.anws/v1/01_PRD.md` and `.anws/v1/02_ARCHITECTURE_OVERVIEW.md` while maintaining root copies for backwards compatibility.
- Updated `AGENTS.md` to strictly follow English language standards across all headings and rules.
- Expanded automated test suite from 27 to 33 passing unit and integration tests (including comprehensive dashboard data layer verification in `test_dashboard_data_layer.py`).

---

## [v1.0] - 2026-07-25 (Baseline Tagged)
### Added
- Core ingestion, parsing, normalization, and multi-tiered classification engine (Rule -> ML -> LLM -> Interactive Review).
- Google Drive synchronization via Service Account (`drive_fetcher.py`).
- Google Sheets writer with `--dry-run` safety mode.
- Local quality gates: 27 Pytest unit/integration tests and Black formatting check enforcement via Pre-Commit hooks.
