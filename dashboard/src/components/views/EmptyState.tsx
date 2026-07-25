import { FilterX, RotateCcw } from 'lucide-react';

interface EmptyStateProps {
  onResetFilters: () => void;
  message?: string;
}

export function EmptyState({ onResetFilters, message }: EmptyStateProps) {
  return (
    <div className="w-full py-16 px-6 bg-brand-surface border border-brand-border rounded-xl flex flex-col items-center justify-center text-center my-6 shadow-sm">
      <div className="w-12 h-12 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center text-brand-neutral mb-4">
        <FilterX className="w-6 h-6 text-slate-400" />
      </div>
      <h3 className="text-base font-semibold text-white mb-1">
        No Transactions Found
      </h3>
      <p className="text-xs text-brand-neutral max-w-md mb-6">
        {message || "There are no transactions matching your active filters. Try selecting a broader date range or clearing your bank and category filters."}
      </p>
      <button
        onClick={onResetFilters}
        className="inline-flex items-center gap-2 px-4 py-2 bg-brand-primary hover:bg-brand-primary-hover text-white text-xs font-medium rounded-lg transition-colors shadow-sm focus:ring-2 focus:ring-brand-primary focus:outline-none"
      >
        <RotateCcw className="w-3.5 h-3.5" />
        <span>Reset All Filters</span>
      </button>
    </div>
  );
}
