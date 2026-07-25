# PRD: Interactive Expense Dashboard
**Project:** Automated Expense Tracker — v1.1 Post-v1 Pipeline Extension
**Task ID:** DASH-v1.1 (to be logged under `05A_TASKS.md → v1.1 Post-v1 Pipeline Extensions`)
**Status:** Draft — ready for implementation handoff
**Owner:** Product/Eng (handoff target: autonomous coding agent workforce, e.g. Antigravity)
**Scope note:** This is a new capability outside the original v1 baseline (parsing → normalization → classification → sync). Per project rules, it is tracked as a v1.1 extension, not folded into v1 baseline scope.
**Revision:** Sections 5, 6, and 12 below have been updated against a real Google Sheets export (the `Transactions`, `Category_Map`, and `Merchant_Aliases` tabs) — the original schema was a placeholder and differed in several important ways. Everything else in this document is unchanged.

---

## 1. Background & Problem

The pipeline already produces clean, categorized, audited transaction data and writes it to Google Sheets (`gsheets_writer.py`), with feedback sync and formatting already implemented (T1.4.1, T1.4.2). What's missing is a way for a human to actually *see and interrogate* that data — currently the only view is the raw sheet itself. Users need an interactive layer for spend trends, category breakdowns, per-bank comparisons, classification-pipeline health, and anomaly review, without adding operational cost or vendor lock-in.

## 2. Goals

- Give a single, interactive view of categorized expense data across all connected banks.
- Surface anomalies/audit flags prominently, without alarming or guilt-framing the user (per fintech UX research below).
- Expose classification-pipeline health (Rule vs ML vs LLM tier usage, confidence) so degradation is visible before it becomes a data-quality problem.
- Ship at zero recurring cost.

## 3. Non-goals

- Not a transaction *editor* — read-only analytics layer (editing/correction stays in the existing feedback-sync flow).
- Not a budgeting/goal-setting product in v1.1 (flagged as a future v1.2 candidate).
- Not a replacement for the Google Sheet — the sheet remains source of truth; the dashboard is a lens on top of it.

## 4. Primary user

A solo developer or small-team finance owner who already runs the pipeline, checks in weekly, wants a fast read on "where did the money go and did anything weird happen" without opening a spreadsheet.

## 5. Data source & schema — confirmed against real export

The Google Sheet has three tabs (confirmed directly from a real export, not assumed):

### 5.1 `Transactions` (primary data)

| Field | Type | Notes |
|---|---|---|
| `transaction_date` | date | transaction date |
| `description` | string | cleaned narration — **can contain very long raw statement boilerplate text on some rows** (see 6.2) |
| `amount` | number | unsigned magnitude |
| `transaction_type` | enum | `debit` / `credit` |
| `category` | string | initial assigned category (rule/ML output) |
| `source_account` | enum | account-level identifier, e.g. `ICICI_CC`, `ICICI_SAVINGS`, `SBI_CASHBACK`, `AXIS_MYZONE`, `HDFC_PIXEL` — **bank** is the prefix before `_`; a bank can have multiple accounts |
| `month`, `year` | number | derived from `transaction_date`, redundant but convenient for grouping |
| `confidence` | number | classifier confidence — **observed constant at 1 in the sample reviewed; confirm it actually varies across the full sheet before building a confidence KPI around it** |
| `classification_method` | enum | tier that assigned `category` — **only `rule` and `ml_exact` observed**; confirm whether an LLM-tier value exists elsewhere before assuming the three-tier Rule/ML/LLM model |
| `review_status` | enum | `Confirmed` / `Corrected` (blank = not yet reviewed) |
| `reviewed_category` | string | human-corrected category, populated only when `review_status = Corrected` |
| `reviewed_at` | date | **observed constant across all sampled rows — looks like a bulk export/reprocessing timestamp, not a true per-row review time; do not build a "time since review" KPI on this without confirming** |
| `reviewer_notes` | string | free-text note left by the reviewer during correction |
| `transaction_id` | string | unique hash ID |
| `clean_amount` | number | cleaned unsigned amount, matches `amount` in the sample |
| `bucket` | enum | `Expense` / `Income` / `Transfer` / `Investment` — derived from the **original** `category` only; goes stale after a correction (see 6.1) |
| `signed_amount` | number | signed amount: negative for debit/expense, positive for credit/income — **use this for all financial math**, not `amount`/`clean_amount` |
| `needs_review` | flag | mostly blank in the sample; confirm how often it's actually set |
| `possible_duplicate` | flag | literal duplicate-detection flag (value seen: `⚠ Duplicate`) — this is the real audit signal, not a generic "audit_flag" |
| `description_raw` | string | raw narration — **frequently contains thousands of characters of statement footer/T&C text**, a parser boundary issue worth flagging back to the pipeline team (outside dashboard scope) |
| `merchant_normalized` | string | cleaned counterparty name — for P2P UPI transactions this is often a person's name, not a brand |

### 5.2 `Category_Map` (lookup)

Maps every `category` value to a `bucket`: `Expense`, `Income`, `Transfer`, or `Investment`. Confirmed categories in use include everyday ones (Food & Dining, Groceries & Supermarket, Shopping, Fuel & Transport, Medical & Health, Travel & Accommodation, Subscriptions & Software) alongside very specific personal-tracking categories (**Chicken**, **Mutton**, **Un Wanted**, **Domestic Help & Services**, **Jewellery & Gifts**) and non-expense buckets (**DIVIDEND**, **Cashback & Rewards** → Income; **Investments & Finance** → Investment; **Credit Card Payment**, **CC Bill Payment**, **Self Transfer** → Transfer). The dashboard should treat this as a live lookup table, not a hardcoded category list — new categories can appear over time.

### 5.3 `Merchant_Aliases` (lookup)

Maps raw text patterns (e.g. `SWIGGY`, `AMZN`/`AMAZON`, `BLINKIT`) to a normalized merchant name. `merchant_normalized` on the Transactions tab is already the output of this join, so the dashboard doesn't need to re-run it — it's provided here for reference/audit only.

## 6. KPI definitions

**All KPI formulas below assume the resolution rules in 6.1 have already been applied.**

**Spending overview**
- **Total spend (period)** — Σ `|signed_amount|` where `effective_bucket = Expense`, filtered to selected date range.
- **MTD / YTD spend** — same, fixed to month-to-date / year-to-date window.
- **Average daily spend** — Total spend ÷ number of days in period.
- **Net cash flow** — Σ `signed_amount` where `effective_bucket = Income` minus Total spend (Transfer and Investment buckets excluded from both sides).

**Category**
- **Top categories by share** — sum of `|signed_amount|` grouped by `effective_category` (Expense bucket only), ranked descending.
- **Month-over-month category delta** — (this month's category total − last month's) ÷ last month's, per `effective_category`.

**Bank / account**
- **Spend by bank** — Σ `|signed_amount|` (Expense bucket) grouped by the bank prefix of `source_account`.
- **Spend by account** — same, grouped by full `source_account` (useful since ICICI alone has two accounts: CC and Savings).
- **Transaction count by bank/account** — row count, same groupings.

**Trend**
- **Monthly spend trend** — Σ `|signed_amount|` (Expense bucket) grouped by month, last 6–12 months.
- **Burn-rate pace** — cumulative spend so far this month vs. same-day-of-month average of prior 3 months.

**Investment** (new — the real data has a distinct Investment bucket, e.g. Zerodha/mutual-fund SIPs)
- **Total invested (period)** — Σ `|signed_amount|` where `effective_bucket = Investment`. Kept as its own card, separate from spend, so investing isn't misread as discretionary expense.

**Classification / pipeline health**
- **Method distribution** — % of transactions by `classification_method` — build this from whatever distinct values actually exist in the full sheet rather than assuming Rule/ML/LLM; only `rule` and `ml_exact` are confirmed so far.
- **Correction rate** — % of transactions where `review_status = Corrected` (i.e. `reviewed_category` is populated) — this is the real signal for the `T1.4.3` retraining trigger, since there's no separate "Manual" method value.
- **Average confidence** — include only if the full sheet shows real variance; if `confidence` is constant at 1 across the dataset, drop this card rather than ship a KPI with no information content.

**Audit / anomaly**
- **Possible duplicates (period)** — count and Σ `|signed_amount|` where `possible_duplicate` is set — a direct, literal flag already in the data, not something the dashboard needs to infer.
- **Needs review (period)** — count where `needs_review` is set.
- **Top payees/merchants** — group by `merchant_normalized` within the Expense bucket only (excludes self-transfers, CC bill payments, and other Transfer-bucket counterparties like "PAYMENT RECEIVED" or "BBPS PAYMENT").

### 6.1 Data resolution rules (critical — apply before any KPI above)

1. **Effective category:** `effective_category = reviewed_category` if `review_status = Corrected` and `reviewed_category` is non-blank, **else** `category`. Never use `category` alone for anything user-facing — several real rows show the original category was wrong (e.g. a `Self Transfer` or `CC Bill Payment` row later corrected to `Groceries & Supermarket` or `Investments & Finance`).
2. **Effective bucket:** look up `effective_category` in `Category_Map` at query time. **Do not trust the stored `bucket` column** — it's derived from the original `category` only and goes stale the moment a row is corrected, which would silently misclassify real spend as a Transfer (or vice versa) and skew every downstream total.
3. **Exclude Transfer-bucket rows from spend entirely** (`Credit Card Payment`, `CC Bill Payment`, `Self Transfer`). These represent money moving between the person's own accounts (e.g. paying off a credit card from a savings account) — counting them as spend would double-count transactions already captured on the card side.
4. **Use `signed_amount` for all math**, not `amount`/`clean_amount`, since it's the only field that's already sign-normalized for debit vs. credit.

### 6.2 Data quality findings from the real export (feed back to the pipeline team, outside dashboard scope)

- **Description bloat:** a meaningful share of rows have `description`/`description_raw` values that are actually the *entire* trailing statement — thousands of characters of T&C, fee schedules, and disclosures — rather than just the transaction line. This looks like a parser boundary-detection issue in statement extraction. **Dashboard implication:** always hard-truncate `description`/`description_raw` before rendering (first ~60 characters is plenty); never pass the raw field into a table cell or export unbounded.
- **Salary miscategorized:** at least one clear salary credit (`NET BANKING INF ... SALARY JUN2026`) is filed under `Cashback & Rewards`. It nets out correctly as Income, but a dedicated Salary category would make the category breakdown more meaningful.
- **`reviewed_at` looks like a batch timestamp**, not a per-transaction event — every sampled row shows the same date regardless of when the underlying transaction happened. Confirm before using it for any recency-based KPI.
- **`confidence` shows no variance in the sample** (always 1) — confirm across the full sheet before building a KPI around it.

## 7. Functional requirements

Global filter bar (applies to every view): date range (presets: this month, last month, last 3 months, YTD, custom), bank multi-select, category multi-select.

Views:
1. **Overview** — KPI strip (total spend, MTD, net flow, flagged count) + category breakdown chart + monthly trend chart.
2. **Categories** — ranked category table with share and MoM delta; drill-in filters the whole dashboard to that category.
3. **Banks** — per-bank spend comparison, transaction count, share of wallet.
4. **Classification health** — tier-distribution chart, confidence average, correction rate — ties directly to the pipeline's ML retraining loop.
5. **Audit & anomalies** — table of flagged transactions, sortable, with the reason/rule that triggered the flag if the audit logger exposes it.

All charts and the KPI strip must react live to filter changes — no page reload.

## 8. UI/UX design direction

Grounded in current fintech UX research rather than a generic admin-template look:

- **Empathetic framing over guilt-based framing** for anomalies and overspend — state what happened and offer context, not alarm language. This is a recurring 2026 fintech UX theme: financial wellness tools are increasingly judged on how in-control they make people feel, not how "advanced" they look.
- **KPI-forward, card-based layout** with clear number hierarchy — large tabular figures, small supporting labels, sparklines where useful. This matches the pattern used by current open-source fintech dashboard kits (e.g. Tremor's component approach: KPI cards + bar/area charts + trackers composed into one view, built for exactly this kind of data).
- **Restraint on color** — reserve a strong accent color exclusively for anomaly/flag states so it stays meaningful (a red badge in a portfolio dashboard should read as signal, not decoration).
- **Accessible by default** — sufficient contrast, keyboard-navigable filters, no color-only encoding of flagged vs. normal transactions (pair color with an icon/label).
- **Responsive** — usable at both desktop and mobile widths; the KPI strip should reflow to a stacked layout below ~640px.

Visual inspiration pulled (expense/finance dashboard layouts — KPI tiles + charts + transaction tables) from Dribbble-style expense dashboard concepts and current fintech dashboard-kit examples (Tremor, shadcn finance kits) — used as *directional* reference only, not copied.

## 9. Non-functional requirements

- **Zero recurring cost.** Static hosting (GitHub Pages / Vercel free tier / Streamlit Community Cloud) reading from Google Sheets via a read-only API key or service account — no paid BI tool, no paid hosting tier.
- **Refresh cadence:** poll/re-fetch on load, minimum manual-refresh button; near-real-time is not required (pipeline itself is not real-time).
- **Scale target:** smooth interaction up to ~50,000 transaction rows client-side; beyond that, pre-aggregate before serving to the frontend rather than shipping raw rows.
- **No new paid dependencies** — consistent with project's existing free/open-source stack (pandas, gspread already in use).

## 10. Recommended tech stack (for the implementing agent)

- **Frontend:** React (or plain HTML/Chart.js for a lighter build) — component approach compatible with **Tremor** (Tailwind-based, open-source, purpose-built for exactly this KPI-card + chart + table composition) is a strong fit if the agent scaffolds a Next.js app.
- **Data access:** `gspread` (already a project dependency) exposed via a small read-only API layer, or direct Google Sheets API v4 calls from the frontend using a restricted API key.
- **Hosting:** Vercel free tier, GitHub Pages, or Streamlit Community Cloud — all zero-cost.
- **Charts:** Chart.js, Recharts, or Tremor's built-in chart components — any is acceptable; prioritize one with good default currency/number formatting.

This is a recommendation, not a constraint — the implementing agent should confirm against whatever frontend conventions the rest of the codebase already uses, if any exist.

## 11. Acceptance criteria

- [ ] All 5 views implemented and reachable without page reload.
- [ ] Global filters (date range, bank, category) affect every view consistently.
- [ ] All KPIs in Section 6 computed and displayed with the formulas above (spot-check against a manual pandas calculation on sample data).
- [ ] Audit/anomaly view clearly distinguishes flagged rows without color-only encoding.
- [ ] Fully responsive down to mobile width.
- [ ] Zero paid services introduced.
- [ ] Deployed to a live, zero-cost URL.

## 12. Open questions / assumptions to confirm before build

Resolved against the real export (see Sections 5 and 6.1–6.2):
- ~~Sign convention for amount~~ — resolved: use `signed_amount`.
- ~~Whether credit/income rows exist~~ — resolved: yes, both credit and debit rows are present.
- ~~Exact column names~~ — resolved: confirmed against a real export (Section 5).

Still open:
- Whether `classification_method` has any values beyond `rule` and `ml_exact` elsewhere in the full sheet (confirms or drops the LLM-tier KPI).
- Whether `confidence` varies at all outside the sampled rows.
- Whether `reviewed_at` is ever a genuine per-row timestamp, or always a batch value.
- How often `needs_review` is actually set (near-zero in the sample reviewed).

## Appendix: Design references consulted

- Fintech UX best-practices research (2026) — empathetic vs. guilt-based framing, personalization, accessibility: eleken.co, wildnetedge.com, theskinsfactory.com, webstacks.com
- Open-source fintech dashboard component patterns: Tremor (Tailwind-based KPI/chart/table components), shadcn finance kits — referenced via adminlte.io's 2026 dashboard roundup
- Visual layout inspiration: expense-tracker dashboard concepts (KPI tiles + category donut/bar + transaction table pattern), sourced via general image search, used directionally only
