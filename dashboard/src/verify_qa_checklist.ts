// verify_qa_checklist.ts
// Automated QA verification harness enforcing Phase 4 criteria from dashboard-testing/SKILL.md
import { resolveAllTransactions, resolveTransaction, computeKPIs, filterTransactions } from './utils/dataLayer.ts';

declare const process: any;
let passCount = 0;
let failCount = 0;

function check(testName: string, condition: boolean, details?: string) {
  if (condition) {
    console.log(`[PASS] ${testName}`);
    passCount++;
  } else {
    console.error(`[FAIL] ${testName}${details ? ` -> ${details}` : ''}`);
    failCount++;
  }
}

console.log("================================================================");
console.log("    EXPENSEAUDIT DASHBOARD - PHASE 4 QA VERIFICATION HARNESS    ");
console.log("================================================================\n");

// -----------------------------------------------------------------------------
// SECTION 1: THE 7 OBSERVED DATA-QUALITY EDGE CASES (PRD §6.2)
// -----------------------------------------------------------------------------
console.log("--- SECTION 1: 7 Observed Data-Quality Edge Cases ---");

// Edge Case 1: Correction resolution
const catMap = {
  "Groceries & Supermarket": "Expense",
  "Food & Dining": "Expense",
  "Self Transfer": "Transfer",
  "CC Bill Payment": "Transfer",
  "DIVIDEND": "Income",
  "Investments & Finance": "Investment",
};

const rowCorrected = {
  transaction_id: "EC1",
  category: "Self Transfer",
  bucket: "Transfer", // Stale bucket in sheet
  review_status: "Corrected",
  reviewed_category: "Groceries & Supermarket",
  signed_amount: "-1800.00",
  amount: "1800.00",
  transaction_type: "debit",
};
const res1 = resolveTransaction(rowCorrected, catMap);
check(
  "Edge Case 1: Correction Resolution & Stale Bucket Override",
  res1.effective_category === "Groceries & Supermarket" && res1.effective_bucket === "Expense" && res1.is_spend === true && res1.is_transfer === false,
  `Got category=${res1.effective_category}, bucket=${res1.effective_bucket}`
);

// Edge Case 2: Transfer exclusion from totals
const rowTransfer1 = { transaction_id: "EC2a", category: "Self Transfer", amount: "50000.00", signed_amount: "-50000.00" };
const rowTransfer2 = { transaction_id: "EC2b", category: "CC Bill Payment", amount: "50000.00", signed_amount: "50000.00", transaction_type: "credit" };
const rowSpend = { transaction_id: "EC2c", category: "Food & Dining", amount: "500.00", signed_amount: "-500.00" };
const resEC2 = [rowTransfer1, rowTransfer2, rowSpend].map(r => resolveTransaction(r, catMap));
const kpiEC2 = computeKPIs(resEC2);
check(
  "Edge Case 2: Transfer Exclusion from Spend/Income Totals",
  kpiEC2.totalSpend === 500.0 && kpiEC2.totalIncome === 0 && kpiEC2.netCashFlow === -500.0,
  `totalSpend=${kpiEC2.totalSpend}, totalIncome=${kpiEC2.totalIncome}`
);

// Edge Case 3: Description truncation
const longBoilerplate = "SWIGGY LIMITED BANGALORE IN TRANSACTIONS HIGHLIGHTED IN GREY COLOR IF ANY DO NOT FORM PART OF PURCHASES OTHER DEBITS TRANSACTIONS FULLY PARTIALLY CONV AND TERMS AND CONDITIONS APPLY SEE DETAILS ON STATEMENT FOOTER PAGE 2 OF 4";
const rowLong = { transaction_id: "EC3", description: longBoilerplate, description_raw: longBoilerplate, amount: "350.00" };
const resEC3 = resolveTransaction(rowLong, catMap);
check(
  "Edge Case 3: Boilerplate Description Truncation (<= 60 chars)",
  resEC3.description.length <= 60 && resEC3.description_raw.length <= 60 && resEC3.description === longBoilerplate.substring(0, 60).trim(),
  `Length=${resEC3.description.length}`
);

// Edge Case 4: Duplicate flagging & Boolean evaluation
const rowDup = { transaction_id: "EC4", possible_duplicate: "⚠ Duplicate", needs_review: "⚠ Review", amount: "450.00" };
const resEC4 = resolveTransaction(rowDup, catMap);
check(
  "Edge Case 4: Duplicate Flagging & Boolean Evaluation",
  resEC4.possible_duplicate === true && resEC4.needs_review === true,
  `dup=${resEC4.possible_duplicate}, rev=${resEC4.needs_review}`
);

// Edge Case 5: Dynamic classification method distribution
const methodRows = [
  { classification_method: "rule", amount: "100" },
  { classification_method: "rule", amount: "200" },
  { classification_method: "ml_exact", amount: "300" },
  { classification_method: "manual", amount: "400" },
];
const kpiEC5 = computeKPIs(methodRows.map(r => resolveTransaction(r, catMap)));
const methodsPresent = Object.keys(kpiEC5.methodDistribution).sort();
check(
  "Edge Case 5: Dynamic Classification Method Breakdown (No hardcoded tiers)",
  methodsPresent.includes("rule") && methodsPresent.includes("ml_exact") && methodsPresent.includes("manual") && kpiEC5.methodDistribution["rule"] === 50.0,
  `Methods=${methodsPresent.join(",")}`
);

// Edge Case 6: Confidence variance check & suppression trigger
const confRowsConstant = [
  { confidence: "1", amount: "100" },
  { confidence: "1.0", amount: "200" },
];
const confRowsVarying = [
  { confidence: "1.0", amount: "100" },
  { confidence: "0.85", amount: "200" },
];
const kpiConstant = computeKPIs(confRowsConstant.map(r => resolveTransaction(r, catMap)));
const kpiVarying = computeKPIs(confRowsVarying.map(r => resolveTransaction(r, catMap)));
check(
  "Edge Case 6: Confidence Variance Check (Suppresses flat 1.0 confidence)",
  kpiConstant.hasConfidenceVariance === false && kpiVarying.hasConfidenceVariance === true,
  `constant=${kpiConstant.hasConfidenceVariance}, varying=${kpiVarying.hasConfidenceVariance}`
);

// Edge Case 7: Multi-account bank rollup
const acctRows = [
  { source_account: "ICICI_CC", amount: "1000", category: "Shopping" },
  { source_account: "ICICI_SAVINGS", amount: "2000", category: "Shopping" },
  { source_account: "SBI_CASHBACK", amount: "500", category: "Shopping" },
];
const kpiEC7 = computeKPIs(acctRows.map(r => resolveTransaction(r, catMap)));
check(
  "Edge Case 7: Multi-Account Rollup (ICICI_CC & ICICI_SAVINGS -> ICICI)",
  kpiEC7.spendByBank["ICICI"] === 3000 && kpiEC7.spendByAccount["ICICI_CC"] === 1000 && kpiEC7.spendByAccount["ICICI_SAVINGS"] === 2000,
  `ICICI Bank Total=${kpiEC7.spendByBank["ICICI"]}, CC=${kpiEC7.spendByAccount["ICICI_CC"]}, SAVINGS=${kpiEC7.spendByAccount["ICICI_SAVINGS"]}`
);

// -----------------------------------------------------------------------------
// SECTION 2: ACCEPTANCE CRITERIA VERIFICATION AGAINST SAMPLE DATASET
// -----------------------------------------------------------------------------
console.log("\n--- SECTION 2: Acceptance Criteria Verification on Real Sample Data ---");

const { transactions: allTxns, kpis: allKpis } = resolveAllTransactions(null);
check(
  "AC 1: Sample Dataset Ingestion & KPI Computation",
  allTxns.length === 9 && allKpis.totalSpend > 0,
  `Loaded ${allTxns.length} rows, totalSpend=₹${allKpis.totalSpend}`
);

// Verify filtering consistency across views
const filteredByBank = filterTransactions(allTxns, { bank: "ICICI", category: "All", searchTerm: "", onlyFlagged: false, dateRange: "all" });
const kpisICICI = computeKPIs(filteredByBank);
check(
  "AC 2: Global Bank Filter Consistency",
  filteredByBank.every(t => t.bank === "ICICI") && kpisICICI.totalSpend < allKpis.totalSpend,
  `ICICI count=${filteredByBank.length}, ICICI spend=₹${kpisICICI.totalSpend}`
);

const filteredByFlagged = filterTransactions(allTxns, { bank: "All", category: "All", searchTerm: "", onlyFlagged: true, dateRange: "all" });
check(
  "AC 3: Flagged Only Filter Consistency",
  filteredByFlagged.length > 0 && filteredByFlagged.every(t => t.possible_duplicate || t.needs_review),
  `Flagged count=${filteredByFlagged.length}`
);

const filteredBySearch = filterTransactions(allTxns, { bank: "All", category: "All", searchTerm: "swiggy", onlyFlagged: false, dateRange: "all" });
check(
  "AC 4: Multi-field Search Term Filter",
  filteredBySearch.length === 2 && filteredBySearch.every(t => t.merchant_normalized.includes("SWIGGY")),
  `Search match count=${filteredBySearch.length}`
);

const filteredByCustomDate = filterTransactions(allTxns, { bank: "All", category: "All", searchTerm: "", onlyFlagged: false, dateRange: "custom", dateFrom: "2026-05-20", dateTo: "2026-05-21" });
const filteredByThisMonth = filterTransactions(allTxns, { bank: "All", category: "All", searchTerm: "", onlyFlagged: false, dateRange: "this_month" });
check(
  "AC 5: Custom Date Range & Preset Filtering Consistency",
  filteredByCustomDate.length > 0 &&
  filteredByCustomDate.every(t => t.transaction_date >= "2026-05-20" && t.transaction_date <= "2026-05-21") &&
  filteredByThisMonth.length > 0 &&
  filteredByThisMonth.every(t => t.transaction_date.startsWith("2026-05")),
  `Custom range count=${filteredByCustomDate.length}, This month count=${filteredByThisMonth.length}`
);

console.log("\n================================================================");
console.log(`FINAL RESULT: ${passCount} PASSED | ${failCount} FAILED`);
console.log("================================================================");

if (failCount > 0) {
  process.exit(1);
} else {
  process.exit(0);
}
