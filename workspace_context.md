# CORE CONTEXT & WORKFLOW SPECIFICATION

## 1. Project Meta & Environment
- **Project Goal**: Automated Expense Tracker for parsing multi-bank PDF/CSV statements, normalizing transaction records, executing multi-tiered categorization (Rule -> ML -> LLM), auditing anomalies, and synchronizing structured data & feedback with Google Sheets.
- **Tech Stack**: Python 3.10+, pytest, black, pyright, pandas, scikit-learn, gspread, gspread-formatting, pdfplumber, pypdf.
- **Key Architecture**:
  - `expense_tracker.py`: Main CLI orchestrator and entry point.
  - `parsers/`: Bank statement extraction modules (ICICI, Axis, SBI, HDFC).
  - `pipeline/`: Core business logic including `normalizer.py`, `classification_orchestrator.py`, and `feedback_sync.py`.
  - `models/`: ML classifiers, training dataset (`training_data.csv`), and embeddings cache.
  - `output/`: Report generation, Google Sheets synchronization (`gsheets_writer.py`), audit loggers, and sheet setup (`gsheets_setup.py`).
  - `scripts/`: Auxiliary development, data manipulation, labeling, and auditing utilities.
  - `tests/`: Comprehensive unit (`tests/unit/`) and integration (`tests/integration/`) test suites.
  - `.anws/v1/`: Unified Architecture Specification (v1.0 Baseline Frozen, `05A_TASKS.md`, `05B_VERIFICATION_PLAN.md`).

## 2. Active Rules & Constraints
- **Pipeline Compliance**: Development and task execution must strictly follow `.anws/v1/05A_TASKS.md` and `05B_VERIFICATION_PLAN.md`.
- **Quality Gate Enforcement**: Any code modifications must pass 100% of formatting and test requirements before presentation (`black --check .` and `python -m pytest tests/ -v`).
- **Simplicity & Surgical Edits**: Touch only necessary code blocks, avoid speculative abstractions, preserve existing code style and docstrings.
- **Scope-Creep Tracking**: New capabilities or out-of-scope features must be tracked within the `v1.1 Post-v1 Pipeline Extensions` section of `05A_TASKS.md`.
- **Explicit Assumptions**: State assumptions clearly and surface design trade-offs before proceeding.

## 3. Workflows & Skills Map
- **Active Workflows**:
  - `/quickstart`: Intelligent pipeline auto-diagnostics and orchestration.
  - `/genesis`: Initial PRD, architecture, and ADR creation.
  - `/probe`: Risk analysis, dependency mapping, and runtime inspection.
  - `/design-system`: Detailed system-level L0/L1 design creation.
  - `/blueprint`: WBS task decomposition (`05A_TASKS.md` & `05B_VERIFICATION_PLAN.md`).
  - `/change`: Scoped task revision and architecture updates.
  - `/explore`: Structured research and exploration reporting.
  - `/challenge`: Pre-decision specification and implementation challenge reviews.
  - `/forge`: Code implementation execution following defined waves.
  - `/craft`: Custom workflow, skill, and prompt authoring.
  - `/upgrade`: Post-CLI upgrade analysis and migration routing.
- **Loaded Skills**:
  - `code-reviewer`: Static implementation review against specification contracts.
  - `concept-modeler`: Interactive domain concept clarification and entity modeling.
  - `craft-authoring`: Workflow and skill creation guidelines.
  - `design-reviewer`: Architecture and design document contract validation.
  - `e2e-testing-guide`: Standardized manual & E2E verification test reports.
  - `nexus-mapper` & `nexus-query`: Codebase structural index and dependency querying.
  - `output-contract`: Standardized output and task outcome reporting.
  - `runtime-inspector`: Process boundary and runtime interface inspection.
  - `sequential-thinking`: Dynamic multi-step reasoning and problem decomposition.
  - `spec-writer`: Detailed PRD specification generation.
  - `system-designer`: L0/L1 system architecture design authoring.
  - `task-planner` & `task-reviewer`: WBS generation and verification plan auditing.
  - `tech-evaluator`: Architecture decision evaluation and tech stack trade-off analysis.

## 4. Current Execution State
- **Completed Steps**:
  - Refactored and added unit tests for bank parsers (`T1.1.1`).
  - Implemented transaction normalization rules (`T1.1.2`).
  - Verified multi-tier classification orchestrator (Rule -> ML -> LLM) (`T1.2.1`).
  - Validated Google Sheets dry-run and audit logging (`T1.3.1`).
  - Achieved 100% test pass rate across unit & integration suites (27/27 pytest tests passing, 0 pyright errors, black formatted).
  - Implemented v1.1 extensions: Continuous Learning Feedback Sync (`T1.4.1`), GSheets Formatting Setup (`T1.4.2`), Standalone ML Retraining Trigger (`T1.4.3`), and Auxiliary Dev Scripts (`T1.4.4`).
- **Active Task**:
  - `INT-S1`: End-to-End Pipeline Run & System Context Documentation Export.
- **Next Required Actions**:
  - Execute full E2E dry-run verification against mock statements.
  - Validate local CSV output structural integrity and CLI flags (`--dry-run`, `--sync-feedback`, `--setup-sheet`, `--retrain`).

## 5. System Context Injection for Downstream LLM
> "You are resuming an active software engineering task. Use the above constraints, active workflows, and task history to execute the next steps without deviating from established conventions."
