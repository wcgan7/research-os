import { fetchCoverage } from '../../api/client';
import { useFetch } from '../../api/hooks';
import ConfidenceGauge from '../../components/ConfidenceGauge';
import EmptyState from '../../components/EmptyState';
import ErrorMessage from '../../components/ErrorMessage';
import Loading from '../../components/Loading';
import MarkdownRenderer from '../../components/MarkdownRenderer';
import { Shield, CheckCircle, AlertTriangle, ArrowRight, TrendingUp, TrendingDown, Minus } from 'lucide-react';

export default function CoverageTab({ reviewId }: { reviewId: string }) {
  const { data, loading, error } = useFetch(() => fetchCoverage(reviewId), [reviewId]);

  if (loading) return <Loading />;
  if (error) return <ErrorMessage message={error} />;
  if (!data || data.length === 0) {
    return (
      <EmptyState
        icon={Shield}
        title="No coverage assessments yet"
        description="The agent hasn't assessed coverage yet."
      />
    );
  }

  const latest = data[0];

  return (
    <div className="space-y-6">
      {/* Latest Coverage */}
      <div className="bg-[var(--color-paper-card)] rounded-xl border border-[var(--color-border)] p-6">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-serif text-lg text-[var(--color-ink)]">Latest Coverage</h3>
          <span className="text-xs text-[var(--color-ink-muted)]">
            {new Date(latest.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
        <p className="text-xs text-[var(--color-ink-muted)] mb-4 italic">
          Self-assessed by the agent. Confidence, areas, and gaps reflect the agent's own judgment of its coverage — not an independent evaluation.
        </p>

        <div className="mb-5">
          <div className="text-xs uppercase tracking-wide text-[var(--color-ink-muted)] font-medium mb-2">Confidence</div>
          <ConfidenceGauge confidence={latest.confidence} />
        </div>

        {latest.summary && (
          <div className="mb-5">
            <div className="text-xs uppercase tracking-wide text-[var(--color-ink-muted)] font-medium mb-2">Summary</div>
            <MarkdownRenderer content={latest.summary} />
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-5">
          <div>
            <div className="text-xs uppercase tracking-wide text-[var(--color-ink-muted)] font-medium mb-2 flex items-center gap-1.5">
              <CheckCircle size={13} className="text-emerald-500" /> Areas Covered ({latest.areas_covered.length})
            </div>
            <ul className="space-y-1.5">
              {latest.areas_covered.map((area, i) => (
                <li key={i} className="text-sm text-[var(--color-ink-secondary)] pl-4 border-l-2 border-emerald-200 py-0.5">
                  {area}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <div className="text-xs uppercase tracking-wide text-[var(--color-ink-muted)] font-medium mb-2 flex items-center gap-1.5">
              <AlertTriangle size={13} className="text-amber-500" /> Gaps ({latest.gaps.length})
            </div>
            <ul className="space-y-1.5">
              {latest.gaps.map((gap, i) => (
                <li key={i} className="text-sm text-[var(--color-ink-secondary)] pl-4 border-l-2 border-amber-200 py-0.5">
                  {gap}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {latest.next_actions?.length > 0 && (
          <div className="mt-5 pt-4 border-t border-[var(--color-border)]">
            <div className="text-xs uppercase tracking-wide text-[var(--color-ink-muted)] font-medium mb-2 flex items-center gap-1.5">
              <ArrowRight size={13} /> Next Actions
            </div>
            <ul className="space-y-1">
              {latest.next_actions.map((action, i) => (
                <li key={i} className="text-sm text-[var(--color-ink-secondary)] flex items-start gap-2">
                  <span className="text-[var(--color-ink-muted)] mt-0.5">-</span>
                  {action}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Timeline */}
      {data.length > 1 && (
        <div>
          <h3 className="font-serif text-lg text-[var(--color-ink)] mb-4">Coverage Over Time</h3>
          <div className="space-y-3">
            {data.map((c, i) => {
              const prev = data[i + 1];
              const delta = prev ? c.confidence - prev.confidence : 0;
              const DeltaIcon = delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus;
              const deltaColor = delta > 0 ? 'text-emerald-600' : delta < 0 ? 'text-red-500' : 'text-gray-400';

              return (
                <div key={c.id} className="flex items-start gap-4">
                  <div className="w-20 shrink-0 text-right">
                    <div className="text-xs text-[var(--color-ink-muted)]">
                      {new Date(c.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    </div>
                    <div className="text-xs text-[var(--color-ink-muted)]">
                      {new Date(c.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                  <div className="w-3 flex flex-col items-center">
                    <div className="w-2.5 h-2.5 rounded-full bg-[var(--color-border-strong)] mt-1" />
                    {i < data.length - 1 && <div className="w-px flex-1 bg-[var(--color-border)]" />}
                  </div>
                  <div className="flex-1 bg-[var(--color-paper-card)] border border-[var(--color-border)] rounded-lg p-4 mb-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-sm font-semibold text-[var(--color-ink)] tabular-nums">
                        {Math.round(c.confidence * 100)}%
                      </span>
                      {prev && (
                        <span className={`flex items-center gap-0.5 text-xs ${deltaColor}`}>
                          <DeltaIcon size={12} />
                          {delta > 0 ? '+' : ''}{Math.round(delta * 100)}%
                        </span>
                      )}
                      <span className="text-xs text-[var(--color-ink-muted)]">
                        {c.areas_covered.length} areas, {c.gaps.length} gaps
                      </span>
                    </div>
                    {c.summary && (
                      <p className="text-sm text-[var(--color-ink-secondary)] line-clamp-2">{c.summary}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
