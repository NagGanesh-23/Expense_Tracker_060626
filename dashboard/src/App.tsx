import { useEffect, useState } from 'react';
import { fetchDashboardData } from './utils/dataIngestion';
import type { DashboardData } from './utils/dataIngestion';
import { filterTransactions, computeKPIs } from './utils/dataLayer';

// Phase 2 components
import { AuditTape } from './components/AuditTape';
import { GlobalFilterBar } from './components/GlobalFilterBar';
import type { FilterState } from './components/GlobalFilterBar';
import { NavigationTabs } from './components/NavigationTabs';
import type { TabId } from './components/NavigationTabs';

// Phase 3 views
import { OverviewView } from './components/views/OverviewView';
import { CategoriesView } from './components/views/CategoriesView';
import { BanksView } from './components/views/BanksView';
import { HealthView } from './components/views/HealthView';
import { AuditView } from './components/views/AuditView';
import { EmptyState } from './components/views/EmptyState';

const INITIAL_FILTERS: FilterState = {
  bank: 'All',
  category: 'All',
  searchTerm: '',
  onlyFlagged: false,
  dateRange: 'all',
};

function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS);

  useEffect(() => {
    fetchDashboardData().then((d) => {
      setData(d);
      setLoading(false);
    });
  }, []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      const refreshedData = await fetchDashboardData();
      setData(refreshedData);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleFilterChange = (newFilters: Partial<FilterState>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  };

  const handleResetFilters = () => {
    setFilters(INITIAL_FILTERS);
  };

  if (loading || !data) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex flex-col items-center justify-center font-mono text-slate-400 gap-3">
        <div className="w-8 h-8 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
        <span>Loading ExpenseAudit Vault...</span>
      </div>
    );
  }

  // Reactive filtering without page reload
  const filteredTransactions = filterTransactions(data.transactions, filters);
  const filteredKpis = computeKPIs(filteredTransactions);

  return (
    <div className="min-h-screen bg-[#0F172A] text-slate-100 flex flex-col font-sans selection:bg-brand-primary selection:text-white">
      
      {/* 1. Signature Element: The Live Audit Tape (Top Ledger Strip) */}
      <AuditTape kpis={filteredKpis} />

      {/* 2. Navigation Tabs (5 Reactive Views) */}
      <NavigationTabs
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        auditFlagCount={filteredKpis.possibleDuplicatesCount + filteredKpis.needsReviewCount}
      />

      {/* 3. Sticky Global Filter Bar */}
      <GlobalFilterBar
        filters={filters}
        onFilterChange={handleFilterChange}
        onReset={handleResetFilters}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        availableCategories={data.availableCategories}
        totalCount={data.totalCount}
        filteredCount={filteredTransactions.length}
      />

      {/* 4. Main View Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        {filteredTransactions.length === 0 ? (
          <EmptyState onResetFilters={handleResetFilters} />
        ) : (
          <>
            {activeTab === 'overview' && (
              <OverviewView
                transactions={filteredTransactions}
                kpis={filteredKpis}
                onSelectCategory={(cat) => {
                  handleFilterChange({ category: cat });
                }}
              />
            )}

            {activeTab === 'categories' && (
              <CategoriesView
                transactions={filteredTransactions}
                kpis={filteredKpis}
                onSelectCategory={(cat) => {
                  handleFilterChange({ category: cat });
                  setActiveTab('overview'); // Drill into overview or stay
                }}
              />
            )}

            {activeTab === 'banks' && (
              <BanksView
                kpis={filteredKpis}
                onSelectBank={(bank) => {
                  handleFilterChange({ bank });
                }}
              />
            )}

            {activeTab === 'health' && (
              <HealthView
                kpis={filteredKpis}
                totalTransactions={filteredTransactions.length}
              />
            )}

            {activeTab === 'audit' && (
              <AuditView
                transactions={filteredTransactions}
                onSelectCategory={(cat) => handleFilterChange({ category: cat })}
                onSelectBank={(bank) => handleFilterChange({ bank })}
              />
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-brand-border py-6 px-6 bg-slate-950/60 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between text-xs text-brand-neutral gap-2">
          <div className="flex items-center gap-2 font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Section 6.1 Resolution Layer Engine Active</span>
          </div>
          <div className="font-mono text-[11px]">
            ExpenseAudit v1.0 • INR (₹) Tabular Monospace Ledger
          </div>
        </div>
      </footer>

    </div>
  );
}

export default App;
