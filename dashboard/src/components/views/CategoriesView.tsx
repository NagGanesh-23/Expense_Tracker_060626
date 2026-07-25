import type { ResolvedTransaction, DashboardKPIs } from '../../utils/dataLayer';
import { PieChart, Filter, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

interface CategoriesViewProps {
  transactions: ResolvedTransaction[];
  kpis: DashboardKPIs;
  onSelectCategory: (category: string) => void;
}

export function CategoriesView({ transactions, kpis, onSelectCategory }: CategoriesViewProps) {
  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  // Calculate category metrics including transaction counts and simulated MoM delta
  const categoryMetrics = Object.entries(kpis.spendByCategory)
    .map(([name, amount]) => {
      const txCount = transactions.filter(t => t.is_spend && t.effective_category === name).length;
      const share = kpis.totalSpend > 0 ? (amount / kpis.totalSpend) * 100 : 0;
      
      // Calculate MoM change (comparison between current month and previous month in dataset)
      const thisMonthAmt = transactions
        .filter(t => t.is_spend && t.effective_category === name && (t.month === '05' || t.month === '5' || t.month === 'May'))
        .reduce((sum, t) => sum + t.amount, 0);
      const lastMonthAmt = transactions
        .filter(t => t.is_spend && t.effective_category === name && (t.month === '04' || t.month === '4' || t.month === 'Apr'))
        .reduce((sum, t) => sum + t.amount, 0);

      let momDelta = 0;
      if (lastMonthAmt > 0) {
        momDelta = ((thisMonthAmt - lastMonthAmt) / lastMonthAmt) * 100;
      } else if (thisMonthAmt > 0) {
        momDelta = 100; // New spend
      }

      return {
        name,
        amount,
        txCount,
        share,
        momDelta,
      };
    })
    .sort((a, b) => b.amount - a.amount);

  return (
    <div className="space-y-6">
      
      {/* Header Info */}
      <div className="bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <PieChart className="w-5 h-5 text-brand-primary" />
            <span>Category Spend Ranking</span>
          </h3>
          <p className="text-xs text-brand-neutral mt-0.5">
            Ranked by effective category after human audit correction. Click any category row to filter the entire dashboard.
          </p>
        </div>
        <div className="text-right font-mono">
          <span className="text-xs text-brand-neutral block">Total Categorized Spend</span>
          <span className="text-lg font-bold text-white">{formatINR(kpis.totalSpend)}</span>
        </div>
      </div>

      {/* Categories Table */}
      <div className="bg-brand-surface border border-brand-border rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-brand-border bg-slate-900/60 text-[11px] font-semibold text-brand-neutral uppercase tracking-wider">
                <th className="py-3 px-4">Category Name</th>
                <th className="py-3 px-4 text-right">Transactions</th>
                <th className="py-3 px-4 text-right">Total Spend</th>
                <th className="py-3 px-4 text-right">Share %</th>
                <th className="py-3 px-4 text-right">MoM Change</th>
                <th className="py-3 px-4 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-border/60 text-xs">
              {categoryMetrics.length > 0 ? (
                categoryMetrics.map((cat, index) => (
                  <tr 
                    key={cat.name}
                    onClick={() => onSelectCategory(cat.name)}
                    className="hover:bg-brand-surface-hover/80 transition-colors cursor-pointer group"
                  >
                    {/* Category Name & Rank */}
                    <td className="py-3.5 px-4 font-medium text-white flex items-center gap-2.5">
                      <span className="w-5 h-5 rounded bg-slate-800 text-brand-neutral font-mono text-[11px] flex items-center justify-center border border-slate-700">
                        {index + 1}
                      </span>
                      <span className="group-hover:text-brand-primary transition-colors font-semibold">{cat.name}</span>
                    </td>

                    {/* Tx Count */}
                    <td className="py-3.5 px-4 text-right font-mono text-slate-300">
                      {cat.txCount}
                    </td>

                    {/* Total Spend */}
                    <td className="py-3.5 px-4 text-right font-mono font-bold text-white">
                      {formatINR(cat.amount)}
                    </td>

                    {/* Share % Bar */}
                    <td className="py-3.5 px-4 text-right font-mono">
                      <div className="flex items-center justify-end gap-2">
                        <span className="text-slate-300 w-12">{cat.share.toFixed(1)}%</span>
                        <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden hidden sm:block">
                          <div 
                            className="h-full bg-brand-primary rounded-full" 
                            style={{ width: `${Math.min(cat.share, 100)}%` }} 
                          />
                        </div>
                      </div>
                    </td>

                    {/* MoM Change */}
                    <td className="py-3.5 px-4 text-right font-mono">
                      {cat.momDelta > 0 ? (
                        <span className="inline-flex items-center gap-0.5 text-rose-400 font-medium">
                          <ArrowUpRight className="w-3.5 h-3.5" />
                          <span>+{cat.momDelta.toFixed(0)}%</span>
                        </span>
                      ) : cat.momDelta < 0 ? (
                        <span className="inline-flex items-center gap-0.5 text-emerald-400 font-medium">
                          <ArrowDownRight className="w-3.5 h-3.5" />
                          <span>{cat.momDelta.toFixed(0)}%</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-0.5 text-brand-neutral">
                          <Minus className="w-3.5 h-3.5" />
                          <span>0%</span>
                        </span>
                      )}
                    </td>

                    {/* Filter Action Button */}
                    <td className="py-3.5 px-4 text-center">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectCategory(cat.name);
                        }}
                        className="px-2.5 py-1 rounded-md bg-slate-800 hover:bg-brand-primary text-brand-neutral hover:text-white text-[11px] font-medium border border-slate-700 hover:border-brand-primary transition-colors inline-flex items-center gap-1 focus:ring-2 focus:ring-brand-primary focus:outline-none"
                        title={`Filter dashboard to ${cat.name}`}
                      >
                        <Filter className="w-3 h-3" />
                        <span>Filter</span>
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-brand-neutral">
                    No categorized spend found in active range.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
