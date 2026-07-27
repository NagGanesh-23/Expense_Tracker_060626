import { z } from 'zod';

export const TransactionSchema = z.object({
  transaction_id: z.string().optional(),
  transaction_date: z.string(),
  bank: z.string(),
  source_account: z.string(),
  description_raw: z.string(),
  description: z.string(),
  amount: z.number(),
  is_spend: z.boolean(),
  category: z.string(),
  effective_category: z.string().optional(),
  effective_bucket: z.string().optional(),
  classification_method: z.string().optional(),
  review_status: z.string().optional(),
  needs_review: z.boolean().optional(),
  confidence: z.string().optional(),
  possible_duplicate: z.boolean().optional(),
}).passthrough();

export const KPISchema = z.object({
  totalSpend: z.number(),
  inflow: z.number(),
  netSavings: z.number(),
  savingsRate: z.number(),
  spendByCategory: z.record(z.string(), z.number()),
  monthlyTrend: z.array(z.object({
    month: z.string(),
    spend: z.number(),
    inflow: z.number(),
  })),
  needsReviewCount: z.number(),
  uncategorizedSpend: z.number(),
}).passthrough();

export const SummaryResponseSchema = z.object({
  kpis: KPISchema,
  totalCount: z.number(),
  filteredCount: z.number(),
  availableCategories: z.array(z.string()),
}).passthrough();

export const TransactionsResponseSchema = z.object({
  transactions: z.array(TransactionSchema),
  totalCount: z.number(),
  filteredCount: z.number(),
}).passthrough();

export type ValidatedTransaction = z.infer<typeof TransactionSchema>;
export type ValidatedSummaryResponse = z.infer<typeof SummaryResponseSchema>;
export type ValidatedTransactionsResponse = z.infer<typeof TransactionsResponseSchema>;

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:3001/api/v1';

export async function fetchSummary(params: Record<string, any> = {}): Promise<ValidatedSummaryResponse> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== 'all' && val !== '') {
      query.set(key, String(val));
    }
  });

  const res = await fetch(`${API_BASE}/summary?${query.toString()}`);
  if (!res.ok) {
    throw new Error(`Summary API error: ${res.statusText}`);
  }
  const data = await res.json();
  return SummaryResponseSchema.parse(data);
}

export async function fetchTransactions(params: Record<string, any> = {}): Promise<ValidatedTransactionsResponse> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== 'all' && val !== '') {
      query.set(key, String(val));
    }
  });

  const res = await fetch(`${API_BASE}/transactions?${query.toString()}`);
  if (!res.ok) {
    throw new Error(`Transactions API error: ${res.statusText}`);
  }
  const data = await res.json();
  return TransactionsResponseSchema.parse(data);
}

export async function triggerDataSync(): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE}/sync`, { method: 'POST' });
  if (!res.ok) {
    throw new Error(`Sync API error: ${res.statusText}`);
  }
  return res.json();
}
