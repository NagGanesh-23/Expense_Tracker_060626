import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import type { DashboardKPIs } from '../../utils/dataLayer';
import { Building2, CreditCard, Filter } from 'lucide-react';

interface BanksViewProps {
  kpis: DashboardKPIs;
  onSelectBank: (bank: string) => void;
}

const BANK_COLORS: Record<string, string> = {
  ICICI: '#3B82F6', // Blue
  AXIS: '#8B5CF6',  // Purple
  SBI: '#10B981',   // Emerald
  HDFC: '#EC4899',  // Pink
  UNKNOWN: '#64748B'
};

export function BanksView({ kpis, onSelectBank }: BanksViewProps) {
  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  // Build Spend by Bank Data
  const bankData = Object.entries(kpis.spendByBank)
    .map(([bank, amount]) => ({
      bank,
      amount,
      count: kpis.txCountByBank[bank] || 0,
    }))
    .sort((a, b) => b.amount - a.amount);

  // Build Spend by Account Data (surfacing ICICI_CC vs ICICI_SAVINGS separately)
  const accountData = Object.entries(kpis.spendByAccount)
    .map(([account, amount]) => {
      const bank = account.includes('_') ? account.split('_')[0] : account;
      return {
        account,
        bank,
        amount,
        count: kpis.txCountByAccount[account] || 0,
      };
    })
    .sort((a, b) => b.amount - a.amount);

  // Hardcoded known accounts list to ensure empty state visibility if filtered
  const KNOWN_ACCOUNTS = [
    { id: 'ICICI_CC', name: 'ICICI Bank Credit Card', type: 'Credit Card', bank: 'ICICI' },
    { id: 'ICICI_SAVINGS', name: 'ICICI Bank Savings Account', type: 'Savings Account', bank: 'ICICI' },
    { id: 'AXIS_MYZONE', name: 'Axis Bank MyZone Credit Card', type: 'Credit Card', bank: 'AXIS' },
    { id: 'SBI_CASHBACK', name: 'SBI Cashback Credit Card', type: 'Credit Card', bank: 'SBI' },
    { id: 'HDFC_PIXEL', name: 'HDFC Pixel Play Credit Card', type: 'Credit Card', bank: 'HDFC' },
  ];

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <Building2 className="w-5 h-5 text-blue-400" />
            <span>Bank & Account Breakdown</span>
          </h3>
          <p className="text-xs text-brand-neutral mt-0.5">
            Multi-bank cash flow reconciliation across 5 active instruments. Notice ICICI is separated into Credit Card and Savings accounts per PRD §5.
          </p>
        </div>
      </div>

      {/* Account Breakdown Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {KNOWN_ACCOUNTS.map((acct) => {
          const spendAmt = kpis.spendByAccount[acct.id] || 0;
          const txCount = kpis.txCountByAccount[acct.id] || 0;
          const isSavings = acct.type === 'Savings Account';

          return (
            <div 
              key={acct.id}
              className="bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm flex flex-col justify-between hover:border-slate-600 transition-all"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-800 text-white border border-slate-700 font-mono">
                    <span 
                      className="w-2 h-2 rounded-full" 
                      style={{ backgroundColor: BANK_COLORS[acct.bank] || '#64748B' }} 
                    />
                    {acct.id}
                  </span>
                  <span className="text-[11px] font-medium text-brand-neutral flex items-center gap-1">
                    <CreditCard className="w-3.5 h-3.5 text-slate-400" />
                    {acct.type}
                  </span>
                </div>

                <h4 className="text-sm font-semibold text-white mb-1">{acct.name}</h4>
                <p className="text-xs text-brand-neutral mb-4">
                  {txCount} transaction{txCount !== 1 ? 's' : ''} in selected period
                </p>
              </div>

              <div className="border-t border-brand-border pt-3 flex items-center justify-between mt-2">
                <div>
                  <span className="text-[10px] uppercase tracking-wider text-brand-neutral block">
                    {isSavings ? 'Total Outflow' : 'Total Card Spend'}
                  </span>
                  <span className="text-lg font-bold font-mono text-white">
                    {formatINR(spendAmt)}
                  </span>
                </div>
                
                <button
                  onClick={() => onSelectBank(acct.bank)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-brand-primary text-slate-200 hover:text-white text-xs font-medium border border-slate-700 hover:border-brand-primary transition-colors inline-flex items-center gap-1.5 focus:ring-2 focus:ring-brand-primary focus:outline-none"
                  title={`Filter dashboard to ${acct.bank}`}
                >
                  <Filter className="w-3 h-3" />
                  <span>Filter</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts Row: Spend by Bank & Spend by Account */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Left Chart: Spend by Bank */}
        <div className="bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm flex flex-col">
          <h3 className="text-sm font-semibold text-white mb-1">Spend by Bank</h3>
          <p className="text-[11px] text-brand-neutral mb-4">Aggregated across all accounts under each banking institution</p>

          <div className="h-64 w-full flex-1 min-h-[220px]">
            {bankData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={bankData} layout="vertical" margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
                  <XAxis 
                    type="number" 
                    stroke="#64748B" 
                    fontSize={11} 
                    axisLine={{ stroke: '#1E293B' }} 
                    tickFormatter={(val) => `₹${(val / 1000).toFixed(0)}k`} 
                  />
                  <YAxis type="category" dataKey="bank" stroke="#E2E8F0" fontSize={12} fontStyle="bold" axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px' }}
                    itemStyle={{ color: '#E2E8F0', fontSize: '12px', fontFamily: 'monospace' }}
                    formatter={(val: any) => [formatINR(Number(val)), 'Spend']}
                  />
                  <Bar dataKey="amount" radius={[0, 6, 6, 0]} onClick={(entry: any) => entry && entry.bank && onSelectBank(entry.bank)} className="cursor-pointer">
                    {bankData.map((entry) => (
                      <Cell key={entry.bank} fill={BANK_COLORS[entry.bank] || '#3B82F6'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-brand-neutral">No bank spend data</div>
            )}
          </div>
        </div>

        {/* Right Chart: Spend by Specific Account */}
        <div className="bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm flex flex-col">
          <h3 className="text-sm font-semibold text-white mb-1">Spend by Account (Instrument)</h3>
          <p className="text-[11px] text-brand-neutral mb-4">Granular comparison separating CC and Savings accounts</p>

          <div className="h-64 w-full flex-1 min-h-[220px]">
            {accountData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={accountData} layout="vertical" margin={{ top: 5, right: 20, left: 40, bottom: 5 }}>
                  <XAxis 
                    type="number" 
                    stroke="#64748B" 
                    fontSize={11} 
                    axisLine={{ stroke: '#1E293B' }} 
                    tickFormatter={(val) => `₹${(val / 1000).toFixed(0)}k`} 
                  />
                  <YAxis type="category" dataKey="account" stroke="#E2E8F0" fontSize={11} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px' }}
                    itemStyle={{ color: '#E2E8F0', fontSize: '12px', fontFamily: 'monospace' }}
                    formatter={(val: any) => [formatINR(Number(val)), 'Spend']}
                  />
                  <Bar dataKey="amount" radius={[0, 6, 6, 0]}>
                    {accountData.map((entry) => (
                      <Cell key={entry.account} fill={BANK_COLORS[entry.bank] || '#6366F1'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-brand-neutral">No account spend data</div>
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
