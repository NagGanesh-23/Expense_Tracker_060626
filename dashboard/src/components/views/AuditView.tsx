import { useState } from 'react';
import type { ResolvedTransaction } from '../../utils/dataLayer';
import { VirtualizedTransactionTable } from '../VirtualizedTransactionTable';
import { ShieldAlert } from 'lucide-react';

interface AuditViewProps {
  transactions: ResolvedTransaction[];
  onSelectCategory: (category: string) => void;
  onSelectBank: (bank: string) => void;
}

type SortField = 'date' | 'amount' | 'category' | 'status';
type SortOrder = 'asc' | 'desc';
type FilterTab = 'all' | 'flagged' | 'duplicates' | 'corrected';

export function AuditView({ transactions, onSelectCategory, onSelectBank }: AuditViewProps) {
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [activeTab, setActiveTab] = useState<FilterTab>('all');
  const [selectedTx, setSelectedTx] = useState<ResolvedTransaction | null>(null);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  // Filter transactions based on local Audit view tab
  const filteredTxns = transactions.filter((t) => {
    if (activeTab === 'flagged') return t.possible_duplicate || t.needs_review;
    if (activeTab === 'duplicates') return t.possible_duplicate;
    if (activeTab === 'corrected') return t.review_status.toLowerCase() === 'corrected';
    return true;
  });

  // Sort transactions
  const sortedTxns = [...filteredTxns].sort((a, b) => {
    let cmp = 0;
    if (sortField === 'date') {
      cmp = a.transaction_date.localeCompare(b.transaction_date);
    } else if (sortField === 'amount') {
      cmp = a.amount - b.amount;
    } else if (sortField === 'category') {
      cmp = a.effective_category.localeCompare(b.effective_category);
    } else if (sortField === 'status') {
      const aFlag = a.possible_duplicate ? 2 : a.needs_review ? 1 : 0;
      const bFlag = b.possible_duplicate ? 2 : b.needs_review ? 1 : 0;
      cmp = aFlag - bFlag;
    }
    return sortOrder === 'asc' ? cmp : -cmp;
  });

  const flaggedCount = transactions.filter(t => t.possible_duplicate || t.needs_review).length;
  const dupCount = transactions.filter(t => t.possible_duplicate).length;
  const correctedCount = transactions.filter(t => t.review_status.toLowerCase() === 'corrected').length;

  return (
    <div className="space-y-6">
      
      {/* Header & Local Filter Pills */}
      <div className="bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-400" />
            <span>Audit & Anomaly Ledger</span>
          </h3>
          <p className="text-xs text-brand-neutral mt-0.5">
            Empathetic human review queue. Click any transaction row to inspect raw bank memo strings and audit trails.
          </p>
        </div>

        {/* Sub-tab pills */}
        <div className="flex flex-wrap items-center gap-1.5 bg-slate-900 p-1 rounded-lg border border-brand-border">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors focus:ring-1 focus:ring-brand-primary focus:outline-none ${
              activeTab === 'all'
                ? 'bg-brand-primary text-white font-semibold'
                : 'text-brand-neutral hover:text-white hover:bg-slate-800'
            }`}
          >
            All ({transactions.length})
          </button>
          
          <button
            onClick={() => setActiveTab('flagged')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors flex items-center gap-1 focus:ring-1 focus:ring-brand-primary focus:outline-none ${
              activeTab === 'flagged'
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/50 font-semibold'
                : 'text-brand-neutral hover:text-white hover:bg-slate-800'
            }`}
          >
            <span>⚠ Flagged</span>
            <span className="px-1 py-0.2 rounded bg-amber-500/30 text-[10px] font-mono font-bold text-amber-300">{flaggedCount}</span>
          </button>

          <button
            onClick={() => setActiveTab('duplicates')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors flex items-center gap-1 focus:ring-1 focus:ring-brand-primary focus:outline-none ${
              activeTab === 'duplicates'
                ? 'bg-amber-950 text-amber-300 border border-amber-500 font-semibold'
                : 'text-brand-neutral hover:text-white hover:bg-slate-800'
            }`}
          >
            <span>Duplicates</span>
            <span className="px-1 py-0.2 rounded bg-amber-500/30 text-[10px] font-mono font-bold text-amber-300">{dupCount}</span>
          </button>

          <button
            onClick={() => setActiveTab('corrected')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors flex items-center gap-1 focus:ring-1 focus:ring-brand-primary focus:outline-none ${
              activeTab === 'corrected'
                ? 'bg-blue-950 text-blue-300 border border-blue-500 font-semibold'
                : 'text-brand-neutral hover:text-white hover:bg-slate-800'
            }`}
          >
            <span>Corrected</span>
            <span className="px-1 py-0.2 rounded bg-blue-500/30 text-[10px] font-mono font-bold text-blue-300">{correctedCount}</span>
          </button>
        </div>
      </div>

      {/* Main Virtualized Table */}
      <VirtualizedTransactionTable
        transactions={sortedTxns}
        selectedTxId={selectedTx?.transaction_id}
        onSelectTransaction={(t) => setSelectedTx(selectedTx?.transaction_id === t.transaction_id ? null : t)}
        onSelectCategory={onSelectCategory}
        onSelectBank={onSelectBank}
        onSort={(col) => handleSort(col as SortField)}
        sortColumn={sortField}
        sortDirection={sortOrder}
        height="600px"
      />

      {/* Transaction Inspection Drawer / Modal */}
      {selectedTx && (
        <div className="bg-slate-900 border-2 border-brand-primary rounded-xl p-5 shadow-2xl animate-in fade-in slide-in-from-bottom-3 duration-200">
          <div className="flex items-center justify-between border-b border-brand-border pb-3 mb-4">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-brand-primary text-white">
                {selectedTx.transaction_id || 'INSPECT'}
              </span>
              <h4 className="text-sm font-semibold text-white">Transaction Audit Inspection</h4>
            </div>
            <button
              onClick={() => setSelectedTx(null)}
              className="text-xs text-brand-neutral hover:text-white px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 transition-colors"
            >
              Close ✕
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            <div className="space-y-2 bg-brand-surface p-3 rounded-lg border border-brand-border">
              <div className="text-[10px] text-brand-neutral uppercase">Raw Bank Memo String</div>
              <div className="text-slate-200 break-words font-sans text-xs bg-slate-950 p-2.5 rounded border border-slate-800">
                {selectedTx.description_raw || selectedTx.description}
              </div>
              <div className="flex justify-between pt-1 text-[11px] text-brand-neutral">
                <span>Normalized Payee: <strong className="text-white font-mono">{selectedTx.merchant_normalized}</strong></span>
                <span>Date: <strong className="text-white font-mono">{selectedTx.transaction_date}</strong></span>
              </div>
            </div>

            <div className="space-y-2 bg-brand-surface p-3 rounded-lg border border-brand-border">
              <div className="text-[10px] text-brand-neutral uppercase">Resolution Trail (§6.1 Rule)</div>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div>Original Category: <span className="text-slate-300 block font-semibold">{selectedTx.category}</span></div>
                <div>Effective Category: <span className="text-brand-primary block font-semibold">{selectedTx.effective_category}</span></div>
                <div>Effective Bucket: <span className="text-emerald-400 block font-semibold">{selectedTx.effective_bucket}</span></div>
                <div>Method: <span className="text-purple-300 block font-semibold uppercase">{selectedTx.classification_method}</span></div>
              </div>
              <div className="pt-2 border-t border-brand-border/60 flex items-center justify-between">
                <span>Review Status: <strong className="text-white">{selectedTx.review_status || 'Confirmed'}</strong></span>
                <span>Confidence: <strong className="text-slate-300">{selectedTx.confidence}</strong></span>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
