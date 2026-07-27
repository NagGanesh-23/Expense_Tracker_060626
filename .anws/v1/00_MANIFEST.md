# 00_MANIFEST.md — Versioned Architecture Manifest

> **Version:** v1 (Baseline & v1.1 Extensions)  
> **Project:** Automated Expense Tracker  

---

## 1. Document Index & Verification Status

| Document | Path | Status | Last Verified |
|---|---|:---:|---|
| **Product Requirements Document (PRD)** | `.anws/v1/01_PRD.md` | ✅ Verified | 2026-07-27 |
| **System Architecture Overview** | `.anws/v1/02_ARCHITECTURE_OVERVIEW.md` | ✅ Verified | 2026-07-27 |
| **Task Execution Checklist** | `.anws/v1/05A_TASKS.md` | ✅ Active / Tracking | 2026-07-27 |
| **Verification & Quality Plan** | `.anws/v1/05B_VERIFICATION_PLAN.md` | ✅ 100% Passing | 2026-07-27 |
| **Changelog & Upgrade Logs** | `.anws/v1/06_CHANGELOG.md` | ✅ Updated | 2026-07-27 |

---

## 2. Quality Gate Integrity
- **Test Suite:** 33/33 Pytest unit and integration tests passing (`pytest tests/ -v`).
- **Code Formatting:** Clean formatting check (`black --check .`).
- **Pre-Commit Enforcement:** `.pre-commit-config.yaml` configured to enforce tests and style gates before commit.
