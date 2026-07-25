import { TrendingUp, TrendingDown, Layers, Activity } from 'lucide-react';
import type { DashboardKPIs } from '../utils/dataLayer';

interface AuditTapeProps {
  kpis: DashboardKPIs;
}

export function AuditTape({ kpis }: AuditTapeProps) {
  const formatINR = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div className="w-full bg-brand-surface border-b border-brand-border overflow-x-auto snap-x scrollbar-none shadow-sm">
      <div className="min-w-max flex items-center justify-between divide-x divide-brand-border">
        
        {/* Metric 1: Total Spend */}
        <div className="px-6 py-4 flex flex-col justify-center min-w-[200px] snap-start hover:bg-brand-surface-hover/30 transition-colors">
          <div className="flex items-center justify-between text-xs font-semibold text-brand-neutral uppercase tracking-wider mb-1">
            <span>Total Spend (Expense)</span>
            <TrendingDown className="w-4 h-4 text-rose-400" />
          </div>
          <div className="font-mono text-2xl font-bold text-white tracking-tight">
            {formatINR(kpis.totalSpend)}
          </div>
          <div className="text-[11px] text-brand-neutral mt-1">
            Excludes Transfers & Investments per §6.1
          </div>
        </div>

        {/* Metric 2: Net Cash Flow */}
        <div className="px-6 py-4 flex flex-col justify-center min-w-[200px] snap-start hover:bg-brand-surface-hover/30 transition-colors">
          <div className="flex items-center justify-between text-xs font-semibold text-brand-neutral uppercase tracking-wider mb-1">
            <span>Net Cash Flow</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className={`font-mono text-2xl font-bold tracking-tight ${kpis.netCashFlow >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {formatINR(kpis.netCashFlow)}
          </div>
          <div className="text-[11px] text-brand-neutral mt-1">
            Income ({formatINR(kpis.totalIncome)}) − Spend
          </div>
        </div>

        {/* Metric 3: Total Invested */}
        <div className="px-6 py-4 flex flex-col justify-center min-w-[200px] snap-start hover:bg-brand-surface-hover/30 transition-colors">
          <div className="flex items-center justify-between text-xs font-semibold text-brand-neutral uppercase tracking-wider mb-1">
            <span>Total Invested</span>
            <Layers className="w-4 h-4 text-purple-400" />
          </div>
          <div className="font-mono text-2xl font-bold text-purple-300 tracking-tight">
            {formatINR(kpis.totalInvestment)}
          </div>
          <div className="text-[11px] text-brand-neutral mt-1">
            Separated from operating expenses
          </div>
        </div>

        {/* Metric 4: Human Correction Rate */}
        <div className="px-6 py-4 flex flex-col justify-center min-w-[200px] snap-start hover:bg-brand-surface-hover/30 transition-colors">
          <div className="flex items-center justify-between text-xs font-semibold text-brand-neutral uppercase tracking-wider mb-1">
            <span>Correction Rate</span>
            <Activity className="w-4 h-4 text-blue-400" />
          </div>
          <div className="font-mono text-2xl font-bold text-white tracking-tight">
            {kpis.correctionRate.toFixed(1)}%
          </div>
          <div className="text-[11px] text-brand-neutral mt-1 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
            <span>Manual category overrides</span>
          </div>
        </div>

      </div>
    </div>
  );
}
