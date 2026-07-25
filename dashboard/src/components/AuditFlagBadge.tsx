import { HelpCircle, CheckCircle2 } from 'lucide-react';

interface AuditFlagBadgeProps {
  possibleDuplicate: boolean;
  needsReview: boolean;
  reviewStatus: string;
}

export function AuditFlagBadge({ possibleDuplicate, needsReview, reviewStatus }: AuditFlagBadgeProps) {
  const isCorrected = reviewStatus.toLowerCase() === 'corrected';

  if (!possibleDuplicate && !needsReview && !isCorrected) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium text-brand-neutral bg-brand-surface border border-brand-border" title="Confirmed transaction">
        <CheckCircle2 className="w-3 h-3 text-emerald-500" />
        <span>Confirmed</span>
      </span>
    );
  }

  return (
    <div className="flex flex-wrap items-center justify-center gap-1.5">
      {possibleDuplicate && (
        <span 
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold text-amber-300 bg-amber-950/60 border border-amber-500/80 shadow-sm"
          title="Flagged as a possible duplicate transaction"
          role="status"
        >
          <span aria-hidden="true" className="text-amber-400 font-extrabold">⚠</span>
          <span className="underline decoration-dotted underline-offset-2">Duplicate</span>
        </span>
      )}

      {needsReview && (
        <span 
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold text-amber-200 bg-amber-900/40 border border-amber-500/60"
          title="Flagged for manual audit review"
          role="status"
        >
          <HelpCircle className="w-3 h-3 text-amber-400" />
          <span>Review Needed</span>
        </span>
      )}

      {isCorrected && (
        <span 
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium text-blue-300 bg-blue-950/60 border border-blue-500/60"
          title="Category was corrected by human review"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
          <span>Corrected</span>
        </span>
      )}
    </div>
  );
}
