import { useState } from 'react';
import { fetchReport, fetchResources } from '../../api/client';
import { useFetch } from '../../api/hooks';
import MarkdownRenderer from '../../components/MarkdownRenderer';
import EmptyState from '../../components/EmptyState';
import ErrorMessage from '../../components/ErrorMessage';
import Loading from '../../components/Loading';
import { FileText, ExternalLink, ChevronDown, ChevronRight } from 'lucide-react';
import type { Resource } from '../../api/types';

const SECTIONS = [
  { key: 'landscape', label: 'Landscape' },
  { key: 'methods', label: 'Methods' },
  { key: 'sota', label: 'State of the Art' },
  { key: 'resources', label: 'Resources' },
  { key: 'gaps', label: 'Gaps' },
  { key: 'trends', label: 'Trends' },
  { key: 'conclusions', label: 'Conclusions' },
] as const;

function ResourcesAggregate({ reviewId }: { reviewId: string }) {
  const { data, loading, error } = useFetch(() => fetchResources(reviewId), [reviewId]);
  const [expanded, setExpanded] = useState(false);

  if (loading || error || !data) return null;
  const types = Object.keys(data);
  if (types.length === 0) return null;
  const total = types.reduce((sum, t) => sum + data[t].length, 0);

  return (
    <div className="mt-8 border-t border-[var(--color-border)] pt-6">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-sm font-medium text-[var(--color-ink-secondary)] hover:text-[var(--color-ink)] transition-colors"
      >
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        All Resources ({total})
      </button>
      {expanded && (
        <div className="mt-4 space-y-6">
          {types.map((type) => (
            <div key={type}>
              <h4 className="text-xs uppercase tracking-wide text-[var(--color-ink-muted)] font-medium mb-2">
                {type} ({data[type].length})
              </h4>
              <div className="space-y-2">
                {data[type].map((r: Resource, i: number) => (
                  <div key={i} className="flex items-start gap-3 text-sm py-1.5">
                    <ExternalLink size={14} className="mt-0.5 text-[var(--color-ink-muted)] shrink-0" />
                    <div className="min-w-0">
                      <a
                        href={r.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[var(--color-accent)] hover:underline break-all"
                      >
                        {r.url}
                      </a>
                      {r.description && (
                        <span className="text-[var(--color-ink-muted)]"> — {r.description}</span>
                      )}
                      <span className="text-xs text-[var(--color-ink-muted)] ml-2">
                        from {r.paper_title}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ReportTab({ reviewId }: { reviewId: string }) {
  const { data, loading, error } = useFetch(() => fetchReport(reviewId), [reviewId]);
  const [activeSection, setActiveSection] = useState<string>('landscape');

  if (loading) return <Loading />;
  if (error) return <ErrorMessage message={error} />;
  if (!data?.report) {
    return (
      <EmptyState
        icon={FileText}
        title="No report yet"
        description="The agent hasn't produced a review report yet. Check back when the review is further along."
      />
    );
  }

  const report = data.report;
  const sota = data.sota_summary;

  return (
    <div className="flex gap-8">
      {/* TOC Sidebar */}
      <nav className="hidden lg:block w-44 shrink-0 sticky top-36 self-start">
        <div className="text-xs uppercase tracking-wide text-[var(--color-ink-muted)] font-medium mb-3">
          Sections
        </div>
        <ul className="space-y-1">
          {SECTIONS.map(({ key, label }) => {
            const hasContent = report[key as keyof typeof report];
            if (!hasContent) return null;
            return (
              <li key={key}>
                <button
                  onClick={() => {
                    setActiveSection(key);
                    document.getElementById(`section-${key}`)?.scrollIntoView({ behavior: 'smooth' });
                  }}
                  className={`block w-full text-left px-3 py-1.5 rounded text-sm transition-colors ${
                    activeSection === key
                      ? 'bg-[var(--color-accent-light)] text-[var(--color-accent)] font-medium'
                      : 'text-[var(--color-ink-secondary)] hover:text-[var(--color-ink)] hover:bg-[var(--color-paper-warm)]'
                  }`}
                >
                  {label}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Report Content */}
      <div className="flex-1 min-w-0">
        <div className="bg-[var(--color-paper-card)] rounded-xl border border-[var(--color-border)] p-8">
          {SECTIONS.map(({ key, label }) => {
            const content = report[key as keyof typeof report];
            if (!content || typeof content !== 'string') return null;
            return (
              <section key={key} id={`section-${key}`} className="mb-8 last:mb-0 scroll-mt-40">
                <h2 className="font-serif text-xl text-[var(--color-ink)] mb-4 pb-2 border-b border-[var(--color-border)]">
                  {label}
                </h2>
                <MarkdownRenderer content={content} />
              </section>
            );
          })}
        </div>

        {/* SOTA Summary (legacy) */}
        {sota && (
          <div className="mt-6 bg-[var(--color-paper-card)] rounded-xl border border-[var(--color-border)] p-6">
            <h3 className="font-serif text-lg text-[var(--color-ink)] mb-4">SOTA Summary</h3>
            {sota.summary && <MarkdownRenderer content={sota.summary} />}
            {sota.best_methods?.length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-medium text-[var(--color-ink-secondary)] mb-2">Best Methods</h4>
                <ul className="list-disc list-inside text-sm text-[var(--color-ink-secondary)] space-y-1">
                  {sota.best_methods.map((m, i) => <li key={i}>{m}</li>)}
                </ul>
              </div>
            )}
            {sota.open_problems?.length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-medium text-[var(--color-ink-secondary)] mb-2">Open Problems</h4>
                <ul className="list-disc list-inside text-sm text-[var(--color-ink-secondary)] space-y-1">
                  {sota.open_problems.map((p, i) => <li key={i}>{p}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}

        <ResourcesAggregate reviewId={reviewId} />
      </div>
    </div>
  );
}
