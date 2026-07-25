import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import type { ResolvedTransaction, DashboardKPIs } from '../../utils/dataLayer';
import { TrendingUp, PieChart as PieIcon, ShoppingBag, ArrowUpRight } from 'lucide-react';

interface OverviewViewProps {
  transactions: ResolvedTransaction[];
  kpis: DashboardKPIs;
  onSelectCategory: (category: string) => void;
}

const COLORS = [
  '#3B82F6', // Blue 500
  '#6366F1', // Indigo 500
  '#8B5CF6', // Purple 500
  '#EC4899', // Pink 500
  '#10B981', // Emerald 500
  '#F59E0B', // Amber 500 (Used sparingly for category contrast)
  '#06B6D4', // Cyan 500
  '#64748B', // Slate 500
];

export function OverviewView({ transactions, kpis, onSelectCategory }: OverviewViewProps) {
  // Format currency in INR tabular nums
  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  // Build monthly spend trend data
  const monthlyDataMap: Record<string, number> = {};
  transactions.forEach((t) => {
    if (t.is_spend) {
      const key = `${t.year}-${t.month}`;
      monthlyDataMap[key] = (monthlyDataMap[key] || 0) + t.amount;
    }
  });

  const trendData = Object.entries(monthlyDataMap)
    .map(([date, amount]) => ({ date, amount }))
    .sort((a, b) => a.date.localeCompare(b.date));

  // Build category pie chart data
  const categoryData = Object.entries(kpis.spendByCategory)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="space-y-6">
      
      {/* Top Cards Row: Quick Highlights */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Expense Card */}
        <div className="bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-brand-neutral mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Total Expense Spend</span>
            <TrendingUp className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white mb-1">
            {formatINR(kpis.totalSpend)}
          </div>
          <p className="text-[11px] text-brand-neutral">
            Across {transactions.filter(t => t.is_spend).length} expense transactions
          </p>
        </div>

        {/* Total Income Card */}
        <div className="bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-brand-neutral mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Total Income / Dividends</span>
            <ArrowUpRight className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mb-1">
            {formatINR(kpis.totalIncome)}
          </div>
          <p className="text-[11px] text-brand-neutral">
            Net cash flow: <span className="font-mono text-white">{formatINR(kpis.netCashFlow)}</span>
          </p>
        </div>

        {/* Top Merchant Card */}
        <div className="bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-brand-neutral mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Top Merchant Spend</span>
            <ShoppingBag className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-lg font-bold text-white mb-1 truncate">
            {kpis.topMerchants[0]?.name || 'N/A'}
          </div>
          <p className="text-xs font-mono text-purple-300">
            {formatINR(kpis.topMerchants[0]?.amount || 0)}
          </p>
        </div>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left 2 Cols: Spend Trend Over Time */}
        <div className="lg:col-span-2 bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-brand-primary" />
                <span>Monthly Spend Trend</span>
              </h3>
              <p className="text-[11px] text-brand-neutral">Spend velocity across selected date ranges</p>
            </div>
          </div>

          <div className="h-64 w-full flex-1 min-h-[250px]">
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="spendGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis 
                    dataKey="date" 
                    stroke="#64748B" 
                    fontSize={11} 
                    tickLine={false} 
                    axisLine={{ stroke: '#1E293B' }} 
                  />
                  <YAxis 
                    stroke="#64748B" 
                    fontSize={11} 
                    tickLine={false} 
                    axisLine={false}
                    tickFormatter={(val) => `₹${(val / 1000).toFixed(0)}k`} 
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px' }}
                    itemStyle={{ color: '#E2E8F0', fontSize: '12px', fontFamily: 'monospace' }}
                    labelStyle={{ color: '#94A3B8', fontSize: '11px', marginBottom: '4px' }}
                    formatter={(val: any) => [formatINR(Number(val)), 'Spend']}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="amount" 
                    stroke="#3B82F6" 
                    strokeWidth={2} 
                    fillOpacity={1} 
                    fill="url(#spendGradient)" 
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-brand-neutral">
                No trend data available for selected filter
              </div>
            )}
          </div>
        </div>

        {/* Right Col: Category Breakdown Pie Chart */}
        <div className="bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <PieIcon className="w-4 h-4 text-purple-400" />
                <span>Spend by Category</span>
              </h3>
              <p className="text-[11px] text-brand-neutral">Click category to drill down</p>
            </div>
          </div>

          <div className="h-48 w-full flex items-center justify-center">
            {categoryData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={2}
                    dataKey="value"
                    onClick={(entry: any) => entry && entry.name && onSelectCategory(entry.name)}
                    className="cursor-pointer"
                  >
                    {categoryData.map((_entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px' }}
                    itemStyle={{ color: '#E2E8F0', fontSize: '12px', fontFamily: 'monospace' }}
                    formatter={(val: any) => [formatINR(Number(val)), 'Spend']}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-xs text-brand-neutral">No category data available</div>
            )}
          </div>

          {/* Top 4 Category Mini List */}
          <div className="mt-4 space-y-2 border-t border-brand-border pt-3">
            {categoryData.slice(0, 4).map((cat, idx) => {
              const share = kpis.totalSpend > 0 ? ((cat.value / kpis.totalSpend) * 100).toFixed(1) : '0';
              return (
                <button
                  key={cat.name}
                  onClick={() => onSelectCategory(cat.name)}
                  className="w-full flex items-center justify-between text-left text-xs p-1.5 rounded-lg hover:bg-brand-surface-hover transition-colors group focus:ring-1 focus:ring-brand-primary focus:outline-none"
                >
                  <div className="flex items-center gap-2 truncate pr-2">
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                    <span className="text-slate-300 group-hover:text-white truncate font-medium">{cat.name}</span>
                  </div>
                  <div className="flex items-center gap-3 text-right flex-shrink-0">
                    <span className="font-mono text-white text-[11px]">{formatINR(cat.value)}</span>
                    <span className="font-mono text-brand-neutral text-[10px] w-9 text-right">{share}%</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

      </div>

    </div>
  );
}
