import { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { ResolvedTransaction } from '../utils/dataLayer';
import { formatINR } from '../utils/formatters';
import { AuditFlagBadge } from './AuditFlagBadge';
import { Filter, Eye, ArrowUpDown } from 'lucide-react';

interface VirtualizedTransactionTableProps {
  transactions: ResolvedTransaction[];
  selectedTxId?: string | null;
  onSelectTransaction?: (tx: ResolvedTransaction) => void;
  onSelectCategory?: (category: string) => void;
  onSelectBank?: (bank: string) => void;
  height?: string;
  onSort?: (column: string) => void;
  sortColumn?: string;
  sortDirection?: 'asc' | 'desc';
}

export function VirtualizedTransactionTable({
  transactions,
  selectedTxId,
  onSelectTransaction,
  onSelectCategory,
  onSelectBank,
  height = '600px',
  onSort,
}: VirtualizedTransactionTableProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  const rowVirtualizer = useVirtualizer({
    count: transactions.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 48, // estimated row height in px
    overscan: 12,
  });

  const virtualRows = rowVirtualizer.getVirtualItems();
  const totalSize = rowVirtualizer.getTotalSize();
  const paddingTop = virtualRows.length > 0 ? virtualRows[0]?.start || 0 : 0;
  const paddingBottom = virtualRows.length > 0 ? totalSize - (virtualRows[virtualRows.length - 1]?.end || 0) : 0;

  if (transactions.length === 0) {
    return (
      <div className="p-12 text-center text-brand-neutral font-mono text-sm bg-brand-surface rounded-xl border border-brand-border">
        No transactions match the current filter criteria.
      </div>
    );
  }

  return (
    <div 
      ref={parentRef} 
      style={{ height, maxHeight: '75vh' }} 
      className="overflow-auto rounded-xl border border-brand-border bg-brand-surface shadow-sm scrollbar-thin"
    >
      <table className="w-full text-left border-collapse relative">
        <thead className="sticky top-0 z-10 bg-slate-900 border-b border-brand-border text-[11px] font-semibold text-brand-neutral uppercase tracking-wider shadow-sm">
          <tr>
            <th 
              onClick={() => onSort && onSort('date')}
              className={`py-3 px-4 ${onSort ? 'cursor-pointer hover:text-white transition-colors select-none' : ''}`}
            >
              <div className="flex items-center gap-1">
                <span>Date</span>
                {onSort && <ArrowUpDown className="w-3 h-3 text-slate-500" />}
              </div>
            </th>
            <th className="py-3 px-4">Account / Bank</th>
            <th className="py-3 px-4">Description (Truncated per §6)</th>
            <th 
              onClick={() => onSort && onSort('category')}
              className={`py-3 px-4 ${onSort ? 'cursor-pointer hover:text-white transition-colors select-none' : ''}`}
            >
              <div className="flex items-center gap-1">
                <span>Effective Category</span>
                {onSort && <ArrowUpDown className="w-3 h-3 text-slate-500" />}
              </div>
            </th>
            <th 
              onClick={() => onSort && onSort('amount')}
              className={`py-3 px-4 text-right ${onSort ? 'cursor-pointer hover:text-white transition-colors select-none' : ''}`}
            >
              <div className="flex items-center justify-end gap-1">
                <span>Amount</span>
                {onSort && <ArrowUpDown className="w-3 h-3 text-slate-500" />}
              </div>
            </th>
            <th 
              onClick={() => onSort && onSort('status')}
              className={`py-3 px-4 text-center ${onSort ? 'cursor-pointer hover:text-white transition-colors select-none' : ''}`}
            >
              <div className="flex items-center justify-center gap-1">
                <span>Audit Status</span>
                {onSort && <ArrowUpDown className="w-3 h-3 text-slate-500" />}
              </div>
            </th>
            <th className="py-3 px-4 text-center">Inspect</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-brand-border/60 text-xs">
          {paddingTop > 0 && (
            <tr>
              <td style={{ height: `${paddingTop}px` }} colSpan={7} />
            </tr>
          )}
          {virtualRows.map((virtualRow) => {
            const t = transactions[virtualRow.index];
            const isSelected = selectedTxId === t.transaction_id;

            return (
              <tr
                key={t.transaction_id || `${t.transaction_date}-${t.amount}-${virtualRow.index}`}
                onClick={() => onSelectTransaction && onSelectTransaction(t)}
                style={{ height: '48px' }}
                className={`transition-colors cursor-pointer group ${
                  isSelected 
                    ? 'bg-brand-primary/20 border-l-2 border-brand-primary' 
                    : t.possible_duplicate 
                      ? 'bg-amber-950/20 hover:bg-amber-950/30' 
                      : 'hover:bg-brand-surface-hover/80'
                }`}
              >
                {/* Date */}
                <td className="py-3 px-4 font-mono text-slate-300 whitespace-nowrap">
                  {t.transaction_date}
                </td>

                {/* Account / Bank */}
                <td className="py-3 px-4 font-mono">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectBank && onSelectBank(t.bank);
                    }}
                    className="px-2 py-0.5 rounded bg-slate-800 hover:bg-brand-primary text-slate-300 hover:text-white text-[11px] font-medium border border-slate-700 hover:border-brand-primary transition-colors focus:ring-1 focus:ring-brand-primary focus:outline-none"
                  >
                    {t.source_account || t.bank}
                  </button>
                </td>

                {/* Description */}
                <td className="py-3 px-4 max-w-xs truncate text-white font-medium group-hover:text-blue-300 transition-colors" title={t.description_raw}>
                  {t.description}
                </td>

                {/* Category */}
                <td className="py-3 px-4">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectCategory && onSelectCategory(t.effective_category);
                    }}
                    className="inline-flex items-center gap-1 text-slate-200 hover:text-white font-medium hover:underline decoration-brand-primary underline-offset-2"
                  >
                    <span>{t.effective_category}</span>
                    <Filter className="w-2.5 h-2.5 opacity-0 group-hover:opacity-100 transition-opacity text-brand-primary" />
                  </button>
                </td>

                {/* Amount */}
                <td className={`py-3 px-4 text-right font-mono font-bold ${t.is_spend ? 'text-white' : 'text-emerald-400'}`}>
                  {formatINR(t.amount)}
                </td>

                {/* Status Badge */}
                <td className="py-3 px-4 text-center">
                  <AuditFlagBadge
                    possibleDuplicate={t.possible_duplicate}
                    needsReview={t.needs_review}
                    reviewStatus={t.review_status}
                  />
                </td>

                {/* Inspect Button */}
                <td className="py-3 px-4 text-center">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectTransaction && onSelectTransaction(t);
                    }}
                    className={`p-1.5 rounded-lg transition-colors focus:ring-2 focus:ring-brand-primary focus:outline-none ${
                      isSelected ? 'bg-brand-primary text-white' : 'bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white'
                    }`}
                    title="Inspect raw bank memo and audit trail"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            );
          })}
          {paddingBottom > 0 && (
            <tr>
              <td style={{ height: `${paddingBottom}px` }} colSpan={7} />
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
