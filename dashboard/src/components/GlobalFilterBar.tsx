import { Filter, Search, RotateCcw, Calendar, RefreshCw } from 'lucide-react';

export interface FilterState {
  bank: string;
  category: string;
  searchTerm: string;
  onlyFlagged: boolean;
  dateRange: 'all' | 'this_month' | 'last_month' | 'last_3_months' | 'ytd' | 'custom';
  dateFrom?: string;
  dateTo?: string;
}

interface GlobalFilterBarProps {
  filters: FilterState;
  onFilterChange: (newFilters: Partial<FilterState>) => void;
  onReset: () => void;
  onRefresh: () => void;
  isRefreshing?: boolean;
  availableCategories: string[];
  totalCount: number;
  filteredCount: number;
}

const BANKS = ['All', 'ICICI', 'AXIS', 'SBI', 'HDFC'];

const DATE_PRESETS: { id: FilterState['dateRange']; label: string }[] = [
  { id: 'all', label: 'All Time' },
  { id: 'this_month', label: 'This Month' },
  { id: 'last_month', label: 'Last Month' },
  { id: 'last_3_months', label: 'Last 3 Months' },
  { id: 'ytd', label: 'YTD' },
  { id: 'custom', label: 'Custom Range' },
];

export function GlobalFilterBar({
  filters,
  onFilterChange,
  onReset,
  onRefresh,
  isRefreshing,
  availableCategories,
  totalCount,
  filteredCount,
}: GlobalFilterBarProps) {
  const isFiltered =
    filters.bank !== 'All' ||
    filters.category !== 'All' ||
    filters.searchTerm !== '' ||
    filters.onlyFlagged ||
    filters.dateRange !== 'all' ||
    Boolean(filters.dateFrom) ||
    Boolean(filters.dateTo);

  return (
    <div className="sticky top-0 z-30 bg-[#0F172A]/95 backdrop-blur-md border-b border-brand-border px-6 py-2.5 shadow-md">
      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-start lg:items-center justify-between gap-3">
        
        {/* Left: Date Range & Bank Pills */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Date Range Selector */}
          <div className="flex items-center gap-1 bg-brand-surface border border-brand-border rounded-lg p-0.5">
            <Calendar className="w-3.5 h-3.5 text-brand-neutral ml-1.5" />
            {DATE_PRESETS.map((preset) => {
              const isActive = filters.dateRange === preset.id;
              return (
                <button
                  key={preset.id}
                  onClick={() => onFilterChange({ dateRange: preset.id })}
                  className={`px-2 py-1 rounded-md text-[11px] font-medium transition-colors focus:ring-1 focus:ring-brand-primary focus:outline-none ${
                    isActive
                      ? 'bg-brand-primary text-white font-semibold'
                      : 'text-brand-neutral hover:text-white hover:bg-brand-surface-hover'
                  }`}
                >
                  {preset.label}
                </button>
              );
            })}
          </div>

          {filters.dateRange === 'custom' && (
            <div className="flex items-center gap-1.5 bg-brand-surface border border-brand-primary/40 rounded-lg px-2 py-1 shadow-sm">
              <span className="text-[11px] text-brand-neutral font-medium">From:</span>
              <input
                type="date"
                value={filters.dateFrom || ''}
                onChange={(e) => onFilterChange({ dateFrom: e.target.value })}
                className="bg-transparent text-[11px] text-slate-200 border-none focus:outline-none focus:ring-0 cursor-pointer font-mono"
              />
              <span className="text-[11px] text-brand-neutral font-medium">To:</span>
              <input
                type="date"
                value={filters.dateTo || ''}
                onChange={(e) => onFilterChange({ dateTo: e.target.value })}
                className="bg-transparent text-[11px] text-slate-200 border-none focus:outline-none focus:ring-0 cursor-pointer font-mono"
              />
            </div>
          )}

          <div className="h-4 w-px bg-brand-border mx-0.5 hidden sm:block" />

          {/* Bank Pills */}
          <div className="flex items-center gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-brand-neutral mr-1 hidden sm:inline flex items-center gap-1">
              <Filter className="w-3 h-3" /> Bank:
            </span>
            {BANKS.map((bank) => {
              const isActive = filters.bank === bank;
              return (
                <button
                  key={bank}
                  onClick={() => onFilterChange({ bank })}
                  className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors focus:ring-2 focus:ring-brand-primary focus:outline-none ${
                    isActive
                      ? 'bg-brand-primary text-white shadow-sm font-semibold'
                      : 'bg-brand-surface text-brand-neutral hover:text-white hover:bg-brand-surface-hover border border-brand-border'
                  }`}
                >
                  {bank}
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Flagged Toggle, Category Dropdown, Search & Reset */}
        <div className="flex flex-wrap items-center gap-2 w-full lg:w-auto justify-end">
          {/* Only Flagged quick toggle */}
          <button
            onClick={() => onFilterChange({ onlyFlagged: !filters.onlyFlagged })}
            className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors flex items-center gap-1 focus:ring-2 focus:ring-brand-flag focus:outline-none border ${
              filters.onlyFlagged
                ? 'bg-amber-500/20 text-amber-400 border-amber-500 font-semibold'
                : 'bg-brand-surface text-brand-neutral hover:text-white hover:bg-brand-surface-hover border-brand-border'
            }`}
            title="Show only transactions flagged as possible duplicate or needing review"
          >
            <span>⚠</span>
            <span>Flagged Only</span>
          </button>

          {/* Category Selector */}
          <select
            value={filters.category}
            onChange={(e) => onFilterChange({ category: e.target.value })}
            className="bg-brand-surface text-xs text-white border border-brand-border rounded-lg px-2.5 py-1 focus:ring-2 focus:ring-brand-primary focus:outline-none max-w-[150px]"
            aria-label="Filter by category"
          >
            <option value="All">All Categories</option>
            {availableCategories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>

          {/* Search Input */}
          <div className="relative flex-1 sm:w-48">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-brand-neutral" />
            <input
              type="text"
              placeholder="Search payee or memo..."
              value={filters.searchTerm}
              onChange={(e) => onFilterChange({ searchTerm: e.target.value })}
              className="w-full bg-brand-surface text-xs text-white border border-brand-border rounded-lg pl-7 pr-2.5 py-1 focus:ring-2 focus:ring-brand-primary focus:outline-none placeholder-brand-neutral"
            />
          </div>

          {/* Reset Filter Button */}
          {isFiltered && (
            <button
              onClick={onReset}
              className="p-1 text-brand-neutral hover:text-white bg-brand-surface hover:bg-brand-surface-hover border border-brand-border rounded-lg transition-colors focus:ring-2 focus:ring-brand-primary focus:outline-none flex items-center gap-1 text-xs px-2"
              title="Reset all filters"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset</span>
            </button>
          )}

          {/* Manual Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className={`p-1 text-brand-neutral hover:text-white bg-brand-surface hover:bg-brand-surface-hover border border-brand-border rounded-lg transition-colors focus:ring-2 focus:ring-brand-primary focus:outline-none flex items-center gap-1 text-xs px-2 ${
              isRefreshing ? 'opacity-60 cursor-not-allowed' : ''
            }`}
            title="Refresh dashboard data from source"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-brand-primary' : ''}`} />
            <span className="hidden sm:inline">{isRefreshing ? 'Syncing...' : 'Refresh'}</span>
          </button>

          {/* Row count pill */}
          <div className="text-[11px] font-mono text-brand-neutral whitespace-nowrap pl-1">
            {filteredCount}/{totalCount}
          </div>
        </div>

      </div>
    </div>
  );
}
