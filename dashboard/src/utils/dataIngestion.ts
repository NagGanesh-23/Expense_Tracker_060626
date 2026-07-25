// dataIngestion.ts
// Bridge between backend /api/data endpoint and our Section 6.1 Data Layer
import { resolveAllTransactions } from './dataLayer';
import type { ResolvedTransaction, DashboardKPIs } from './dataLayer';

export interface DashboardData {
  transactions: ResolvedTransaction[];
  kpis: DashboardKPIs;
  totalCount: number;
  availableCategories: string[];
}

export async function fetchDashboardData(): Promise<DashboardData> {
  try {
    let data = null;
    try {
      const res = await fetch('./api/data.json');
      if (res.ok) {
        data = await res.json();
      }
    } catch (e) {
      console.warn("Could not fetch ./api/data.json directly:", e);
    }

    if (!data) {
      const endpointUrl = import.meta.env.VITE_API_URL || import.meta.env.VITE_GSHEETS_READONLY_URL || '/api/data';
      const res = await fetch(endpointUrl);
      if (!res.ok) {
        throw new Error(`Server returned ${res.status} from ${endpointUrl}`);
      }
      data = await res.json();
    }
    
    // Resolve using our robust dataLayer rules
    const { transactions, kpis } = resolveAllTransactions(
      data.transactions,
      data.categoryMap,
      data.merchantAliases
    );

    const categoriesSet = new Set<string>();
    transactions.forEach(t => {
      if (t.effective_category && t.effective_category !== 'Uncategorized') {
        categoriesSet.add(t.effective_category);
      }
    });

    return {
      transactions,
      kpis,
      totalCount: transactions.length,
      availableCategories: Array.from(categoriesSet).sort(),
    };
  } catch (err) {
    console.warn("Could not fetch live GSheets data from /api/data, falling back to sample data:", err);
    
    // Offline / Preview fallback using realistic sample transactions
    const { transactions, kpis } = resolveAllTransactions(null, null, null);
    const categoriesSet = new Set<string>();
    transactions.forEach(t => {
      if (t.effective_category) {
        categoriesSet.add(t.effective_category);
      }
    });

    return {
      transactions,
      kpis,
      totalCount: transactions.length,
      availableCategories: Array.from(categoriesSet).sort(),
    };
  }
}
