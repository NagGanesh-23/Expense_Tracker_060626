// dataLayer.ts
// Client-side and Node-compatible data resolution layer enforcing Section 6.1 rules.
import type { FilterState } from '../components/GlobalFilterBar';

export interface ResolvedTransaction {
  transaction_id: string;
  transaction_date: string;
  description: string;
  description_raw: string;
  amount: number;
  signed_amount: number;
  transaction_type: string;
  source_account: string;
  bank: string;
  category: string;
  review_status: string;
  reviewed_category: string;
  effective_category: string;
  effective_bucket: string;
  is_spend: boolean;
  is_income: boolean;
  is_investment: boolean;
  is_transfer: boolean;
  confidence: number;
  classification_method: string;
  possible_duplicate: boolean;
  needs_review: boolean;
  merchant_normalized: string;
  month: string;
  year: string;
  reviewer_notes: string;
}

export interface DashboardKPIs {
  totalSpend: number;
  totalIncome: number;
  totalInvestment: number;
  netCashFlow: number;
  spendByCategory: Record<string, number>;
  spendByBank: Record<string, number>;
  spendByAccount: Record<string, number>;
  txCountByBank: Record<string, number>;
  txCountByAccount: Record<string, number>;
  methodDistribution: Record<string, number>;
  correctionRate: number;
  hasConfidenceVariance: boolean;
  avgConfidence: number;
  possibleDuplicatesCount: number;
  needsReviewCount: number;
  topMerchants: { name: string; amount: number }[];
}

export function parseCategoryMap(rawRows: any[][] | null | undefined): Record<string, string> {
  const map: Record<string, string> = {};
  if (!rawRows || rawRows.length < 2) return map;
  
  const headers = rawRows[0].map((h: any) => String(h).trim().toLowerCase());
  const catIdx = headers.indexOf('category');
  const bucketIdx = headers.indexOf('bucket');
  
  if (catIdx === -1 || bucketIdx === -1) {
    rawRows.slice(1).forEach(row => {
      if (row[0] && row[1]) {
        map[String(row[0]).trim()] = String(row[1]).trim();
      }
    });
    return map;
  }

  rawRows.slice(1).forEach(row => {
    const cat = row[catIdx];
    const bucket = row[bucketIdx];
    if (cat && bucket) {
      map[String(cat).trim()] = String(bucket).trim();
    }
  });
  return map;
}

export function resolveTransaction(
  row: Record<string, any>,
  catMap: Record<string, string> = {},
  _aliasMap: Record<string, string> = {}
): ResolvedTransaction {
  const revStatus = String(row.review_status || "").trim();
  const revCat = String(row.reviewed_category || "").trim();
  const origCat = String(row.category || "Uncategorized").trim() || "Uncategorized";

  let effective_category = origCat;
  if (revStatus.toLowerCase() === "corrected" && revCat !== "") {
    effective_category = revCat;
  }

  let effective_bucket = catMap[effective_category] || "Expense";

  let signed_amount = 0.0;
  if (row.signed_amount !== undefined && String(row.signed_amount).trim() !== "") {
    const parsed = parseFloat(String(row.signed_amount).replace(/₹|,/g, "").trim());
    signed_amount = isNaN(parsed) ? 0.0 : parsed;
  } else {
    const rawAmt = row.clean_amount !== undefined ? row.clean_amount : (row.amount || 0);
    const amt = parseFloat(String(rawAmt).replace(/₹|,/g, "").trim());
    const val = isNaN(amt) ? 0.0 : amt;
    const txType = String(row.transaction_type || "").trim().toLowerCase();
    signed_amount = txType === "credit" ? val : -val;
  }

  const abs_amount = Math.abs(signed_amount);

  const is_spend = (effective_bucket === "Expense");
  const is_income = (effective_bucket === "Income");
  const is_investment = (effective_bucket === "Investment");
  const is_transfer = (effective_bucket === "Transfer");

  const source_account = String(row.source_account || "").trim();
  const bank = source_account.includes("_") ? source_account.split("_")[0] : (source_account || "UNKNOWN");

  const desc = String(row.description || "").trim().substring(0, 60);
  const desc_raw = String(row.description_raw || row.raw_description || "").trim().substring(0, 60);

  const dupVal = String(row.possible_duplicate || "").trim().toLowerCase();
  const possible_duplicate = Boolean(dupVal && dupVal !== "false" && dupVal !== "0");

  const revVal = String(row.needs_review || "").trim().toLowerCase();
  const needs_review = Boolean(revVal && revVal !== "false" && revVal !== "0");

  const confParsed = parseFloat(row.confidence);
  const confidence = isNaN(confParsed) ? 1.0 : confParsed;

  let classification_method = String(row.classification_method || "").trim().toLowerCase();
  if (!classification_method) classification_method = "none";

  const merchant_normalized = String(row.merchant_normalized || "").trim() || desc.toUpperCase();

  return {
    transaction_id: String(row.transaction_id || "").trim(),
    transaction_date: String(row.transaction_date || "").trim(),
    description: desc,
    description_raw: desc_raw,
    amount: abs_amount,
    signed_amount: signed_amount,
    transaction_type: String(row.transaction_type || "").trim().toLowerCase(),
    source_account: source_account,
    bank: bank,
    category: origCat,
    review_status: revStatus,
    reviewed_category: revCat,
    effective_category: effective_category,
    effective_bucket: effective_bucket,
    is_spend: is_spend,
    is_income: is_income,
    is_investment: is_investment,
    is_transfer: is_transfer,
    confidence: confidence,
    classification_method: classification_method,
    possible_duplicate: possible_duplicate,
    needs_review: needs_review,
    merchant_normalized: merchant_normalized,
    month: String(row.month || "").trim(),
    year: String(row.year || "").trim(),
    reviewer_notes: String(row.reviewer_notes || "").trim(),
  };
}

export function computeKPIs(txns: ResolvedTransaction[]): DashboardKPIs {
  if (!txns || txns.length === 0) {
    return {
      totalSpend: 0,
      totalIncome: 0,
      totalInvestment: 0,
      netCashFlow: 0,
      spendByCategory: {},
      spendByBank: {},
      spendByAccount: {},
      txCountByBank: {},
      txCountByAccount: {},
      methodDistribution: {},
      correctionRate: 0,
      hasConfidenceVariance: false,
      avgConfidence: 1.0,
      possibleDuplicatesCount: 0,
      needsReviewCount: 0,
      topMerchants: [],
    };
  }

  let totalSpend = 0;
  let totalIncome = 0;
  let totalInvestment = 0;

  const spendByCategory: Record<string, number> = {};
  const spendByBank: Record<string, number> = {};
  const spendByAccount: Record<string, number> = {};
  const txCountByBank: Record<string, number> = {};
  const txCountByAccount: Record<string, number> = {};
  const merchantMap: Record<string, number> = {};

  let correctedCount = 0;
  let possibleDuplicatesCount = 0;
  let needsReviewCount = 0;
  const methodCounts: Record<string, number> = {};
  
  let minConf = txns[0].confidence;
  let maxConf = txns[0].confidence;
  let sumConf = 0;

  for (const t of txns) {
    if (t.is_spend) {
      totalSpend += t.amount;
      spendByCategory[t.effective_category] = (spendByCategory[t.effective_category] || 0) + t.amount;
      spendByBank[t.bank] = (spendByBank[t.bank] || 0) + t.amount;
      spendByAccount[t.source_account] = (spendByAccount[t.source_account] || 0) + t.amount;
      
      txCountByBank[t.bank] = (txCountByBank[t.bank] || 0) + 1;
      txCountByAccount[t.source_account] = (txCountByAccount[t.source_account] || 0) + 1;
      
      merchantMap[t.merchant_normalized] = (merchantMap[t.merchant_normalized] || 0) + t.amount;
    } else if (t.is_income) {
      totalIncome += t.signed_amount;
    } else if (t.is_investment) {
      totalInvestment += t.amount;
    }

    if (t.review_status.toLowerCase() === "corrected") {
      correctedCount += 1;
    }
    if (t.possible_duplicate) {
      possibleDuplicatesCount += 1;
    }
    if (t.needs_review) {
      needsReviewCount += 1;
    }

    methodCounts[t.classification_method] = (methodCounts[t.classification_method] || 0) + 1;
    
    if (t.confidence < minConf) minConf = t.confidence;
    if (t.confidence > maxConf) maxConf = t.confidence;
    sumConf += t.confidence;
  }

  const netCashFlow = totalIncome - totalSpend;
  const totalCount = txns.length;
  const correctionRate = totalCount > 0 ? (correctedCount / totalCount) * 100 : 0;
  const avgConfidence = totalCount > 0 ? sumConf / totalCount : 1.0;
  const hasConfidenceVariance = maxConf !== minConf;

  const methodDistribution: Record<string, number> = {};
  for (const [m, count] of Object.entries(methodCounts)) {
    methodDistribution[m] = (count / totalCount) * 100;
  }

  const topMerchants = Object.entries(merchantMap)
    .map(([name, amount]) => ({ name, amount }))
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 10);

  return {
    totalSpend,
    totalIncome,
    totalInvestment,
    netCashFlow,
    spendByCategory,
    spendByBank,
    spendByAccount,
    txCountByBank,
    txCountByAccount,
    methodDistribution,
    correctionRate,
    hasConfidenceVariance,
    avgConfidence,
    possibleDuplicatesCount,
    needsReviewCount,
    topMerchants,
  };
}

export function resolveAllTransactions(
  rawTxns: any[][] | null | undefined,
  rawCatMap?: any[][] | null | undefined,
  _rawAliasMap?: any[][] | null | undefined
): { transactions: ResolvedTransaction[]; kpis: DashboardKPIs } {
  if (!rawTxns || rawTxns.length < 2) {
    const mockTxns = getRealisticSampleTransactions();
    return { transactions: mockTxns, kpis: computeKPIs(mockTxns) };
  }

  const catMap = parseCategoryMap(rawCatMap);
  const headers = rawTxns[0].map((h: any) => String(h).trim());
  
  const transactions: ResolvedTransaction[] = rawTxns.slice(1).map((row: any[]) => {
    const obj: Record<string, any> = {};
    headers.forEach((h: string, idx: number) => {
      obj[h] = row[idx];
    });
    return resolveTransaction(obj, catMap);
  });

  const kpis = computeKPIs(transactions);
  return { transactions, kpis };
}

export function filterTransactions(txns: ResolvedTransaction[], filters: FilterState): ResolvedTransaction[] {
  return txns.filter((t) => {
    // Bank filter
    if (filters.bank !== 'All' && t.bank.toUpperCase() !== filters.bank.toUpperCase()) {
      return false;
    }
    // Category filter
    if (filters.category !== 'All' && t.effective_category !== filters.category) {
      return false;
    }
    // Flagged only filter
    if (filters.onlyFlagged && !t.possible_duplicate && !t.needs_review) {
      return false;
    }
    // Search term filter
    if (filters.searchTerm.trim() !== '') {
      const term = filters.searchTerm.toLowerCase().trim();
      const matchDesc = t.description.toLowerCase().includes(term);
      const matchRaw = t.description_raw.toLowerCase().includes(term);
      const matchMerchant = t.merchant_normalized.toLowerCase().includes(term);
      const matchAcct = t.source_account.toLowerCase().includes(term);
      if (!matchDesc && !matchRaw && !matchMerchant && !matchAcct) {
        return false;
      }
    }
    // Date range filter
    if (filters.dateRange !== 'all') {
      // Simple string/year/month filter approximation for demo
      const nowYear = '2026';
      if (filters.dateRange === 'this_month' && (t.month !== '05' && t.month !== '5' && t.month !== 'May')) {
        return false;
      }
      if (filters.dateRange === 'ytd' && t.year !== nowYear && t.year !== '26') {
        return false;
      }
    }
    return true;
  });
}

function getRealisticSampleTransactions(): ResolvedTransaction[] {
  const catMap: Record<string, string> = {
    "Food & Dining": "Expense",
    "Groceries & Supermarket": "Expense",
    "Shopping": "Expense",
    "Fuel & Transport": "Expense",
    "Utilities & Bills": "Expense",
    "Subscriptions & Software": "Expense",
    "DIVIDEND": "Income",
    "Investments & Finance": "Investment",
    "Self Transfer": "Transfer",
    "CC Bill Payment": "Transfer",
  };

  const sampleRows = [
    {
      transaction_id: "TX001",
      transaction_date: "2026-05-21",
      description: "SWIGGY BANGALORE IN",
      description_raw: "SWIGGY LIMITED BANGALORE IN TRANSACTIONS HIGHLIGHTED IN GREY COLOR IF ANY DO NOT FORM PART",
      amount: "450.00",
      signed_amount: "-450.00",
      transaction_type: "debit",
      source_account: "ICICI_CC",
      category: "Food & Dining",
      review_status: "Confirmed",
      confidence: "1",
      classification_method: "rule",
      merchant_normalized: "SWIGGY",
      month: "05",
      year: "2026",
    },
    {
      transaction_id: "TX002",
      transaction_date: "2026-05-20",
      description: "AMAZON INDIA PAYMENTS",
      description_raw: "AMAZON INDIA PAYMENTS PVT LTD BANGALORE IN",
      amount: "2499.00",
      signed_amount: "-2499.00",
      transaction_type: "debit",
      source_account: "AXIS_MYZONE",
      category: "Uncategorized",
      review_status: "Corrected",
      reviewed_category: "Shopping",
      confidence: "1",
      classification_method: "ml_exact",
      merchant_normalized: "AMAZON INDIA",
      month: "05",
      year: "2026",
    },
    {
      transaction_id: "TX003",
      transaction_date: "2026-05-18",
      description: "ZEPTO INSTANT GROCERIES",
      description_raw: "ZEPTO MARKETPLACE MUMBAI IN",
      amount: "680.50",
      signed_amount: "-680.50",
      transaction_type: "debit",
      source_account: "SBI_CASHBACK",
      category: "Groceries & Supermarket",
      review_status: "Confirmed",
      confidence: "1",
      classification_method: "rule",
      merchant_normalized: "ZEPTO",
      month: "05",
      year: "2026",
    },
    {
      transaction_id: "TX004",
      transaction_date: "2026-05-15",
      description: "SHELL PETROL PUMP",
      description_raw: "SHELL INDIA MARKETS BANGALORE",
      amount: "3200.00",
      signed_amount: "-3200.00",
      transaction_type: "debit",
      source_account: "HDFC_PIXEL",
      category: "Fuel & Transport",
      review_status: "Confirmed",
      confidence: "1",
      classification_method: "rule",
      merchant_normalized: "SHELL PETROL",
      month: "05",
      year: "2026",
    },
    {
      transaction_id: "TX005",
      transaction_date: "2026-05-12",
      description: "ZERODHA BROKING LTD",
      description_raw: "ZERODHA BROKING LTD NSE BSE MUTUAL FUNDS INVESTMENTS",
      amount: "15000.00",
      signed_amount: "-15000.00",
      transaction_type: "debit",
      source_account: "ICICI_SAVINGS",
      category: "Investments & Finance",
      review_status: "Confirmed",
      confidence: "1",
      classification_method: "rule",
      merchant_normalized: "ZERODHA BROKING",
      month: "05",
      year: "2026",
    },
    {
      transaction_id: "TX006",
      transaction_date: "2026-05-10",
      description: "CREDIT CARD BILL PAYMENT",
      description_raw: "NEFT CREDIT CARD BILL PAYMENT ICICI BANK",
      amount: "25000.00",
      signed_amount: "-25000.00",
      transaction_type: "debit",
      source_account: "ICICI_SAVINGS",
      category: "CC Bill Payment",
      review_status: "Confirmed",
      confidence: "1",
      classification_method: "rule",
      merchant_normalized: "CC BILL PAYMENT",
      month: "05",
      year: "2026",
    },
    {
      transaction_id: "TX007",
      transaction_date: "2026-05-08",
      description: "INFOSYS DIVIDEND CREDIT",
      description_raw: "ACH CR INFOSYS LTD DIVIDEND PYMT",
      amount: "4500.00",
      signed_amount: "4500.00",
      transaction_type: "credit",
      source_account: "ICICI_SAVINGS",
      category: "DIVIDEND",
      review_status: "Confirmed",
      confidence: "1",
      classification_method: "rule",
      merchant_normalized: "INFOSYS DIVIDEND",
      month: "05",
      year: "2026",
    },
    {
      transaction_id: "TX008",
      transaction_date: "2026-05-05",
      description: "SWIGGY BANGALORE IN",
      description_raw: "SWIGGY LIMITED BANGALORE IN TRANSACTIONS HIGHLIGHTED",
      amount: "450.00",
      signed_amount: "-450.00",
      transaction_type: "debit",
      source_account: "ICICI_CC",
      category: "Food & Dining",
      review_status: "Confirmed",
      confidence: "1",
      classification_method: "rule",
      possible_duplicate: "⚠ Duplicate",
      merchant_normalized: "SWIGGY",
      month: "05",
      year: "2026",
    },
    {
      transaction_id: "TX009",
      transaction_date: "2026-05-03",
      description: "NETFLIX ENTERTAINMENT",
      description_raw: "NETFLIX ENTERTAINMENT SERVICES INDIA",
      amount: "649.00",
      signed_amount: "-649.00",
      transaction_type: "debit",
      source_account: "ICICI_CC",
      category: "Subscriptions & Software",
      review_status: "Confirmed",
      confidence: "1",
      classification_method: "rule",
      needs_review: "⚠ Review",
      merchant_normalized: "NETFLIX",
      month: "05",
      year: "2026",
    },
  ];

  return sampleRows.map((row) => resolveTransaction(row, catMap));
}
