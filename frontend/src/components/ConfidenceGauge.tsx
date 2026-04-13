export default function ConfidenceGauge({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color =
    confidence >= 0.8 ? 'bg-emerald-500' :
    confidence >= 0.6 ? 'bg-amber-500' :
    confidence >= 0.4 ? 'bg-orange-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-3">
      <div
        className="flex-1 h-2.5 bg-[var(--color-paper-warm)] rounded-full overflow-hidden border border-[var(--color-border)]"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Coverage confidence: ${pct}%`}
      >
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-sm font-semibold text-[var(--color-ink)] tabular-nums w-12 text-right">
        {pct}%
      </span>
    </div>
  );
}
