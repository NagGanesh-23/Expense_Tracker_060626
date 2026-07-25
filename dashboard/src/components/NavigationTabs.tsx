import { LayoutDashboard, PieChart, Building2, Activity, ShieldAlert } from 'lucide-react';

export type TabId = 'overview' | 'categories' | 'banks' | 'health' | 'audit';

interface NavigationTabsProps {
  activeTab: TabId;
  onSelectTab: (tab: TabId) => void;
  auditFlagCount: number;
}

export function NavigationTabs({ activeTab, onSelectTab, auditFlagCount }: NavigationTabsProps) {
  const tabs: { id: TabId; label: string; icon: React.ReactNode; count?: number }[] = [
    { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: 'categories', label: 'Categories', icon: <PieChart className="w-4 h-4" /> },
    { id: 'banks', label: 'Bank Accounts', icon: <Building2 className="w-4 h-4" /> },
    { id: 'health', label: 'Classification Health', icon: <Activity className="w-4 h-4" /> },
    { 
      id: 'audit', 
      label: 'Audit / Anomalies', 
      icon: <ShieldAlert className="w-4 h-4" />,
      count: auditFlagCount > 0 ? auditFlagCount : undefined 
    },
  ];

  return (
    <div className="bg-[#0F172A] border-b border-brand-border px-6 pt-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between overflow-x-auto scrollbar-none">
        
        {/* Brand Title */}
        <div className="flex items-center gap-2 pr-6 border-r border-brand-border mr-4 py-2 hidden sm:flex">
          <div className="w-7 h-7 bg-brand-primary text-white rounded flex items-center justify-center font-bold text-sm shadow-sm">
            <span>₹</span>
          </div>
          <span className="font-bold text-base tracking-wide text-white">ExpenseAudit</span>
        </div>

        {/* Tab Buttons */}
        <div className="flex items-center gap-1 min-w-max" role="tablist">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                role="tab"
                aria-selected={isActive}
                onClick={() => onSelectTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-all focus:ring-2 focus:ring-brand-primary focus:outline-none ${
                  isActive
                    ? 'border-brand-primary text-white bg-brand-surface/40 font-semibold'
                    : 'border-transparent text-brand-neutral hover:text-white hover:bg-brand-surface/20'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
                {tab.count !== undefined && (
                  <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${
                    isActive ? 'bg-amber-500 text-slate-950' : 'bg-amber-500/20 text-amber-400 border border-amber-500/50'
                  }`}>
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

      </div>
    </div>
  );
}
