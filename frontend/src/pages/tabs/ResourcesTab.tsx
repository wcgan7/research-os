import { ExternalLink, Code, Database, BarChart3, Globe, BookOpen, Package } from 'lucide-react';
import { fetchResources } from '../../api/client';
import { useFetch } from '../../api/hooks';
import type { Resource } from '../../api/types';
import PaperChip from '../../components/PaperChip';
import EmptyState from '../../components/EmptyState';
import ErrorMessage from '../../components/ErrorMessage';
import Loading from '../../components/Loading';

const TYPE_CONFIG: Record<string, { icon: typeof Code; label: string }> = {
  code: { icon: Code, label: 'Code Repositories' },
  dataset: { icon: Database, label: 'Datasets' },
  benchmark: { icon: BarChart3, label: 'Benchmarks' },
  demo: { icon: Globe, label: 'Demos' },
  blog: { icon: BookOpen, label: 'Blog Posts' },
  other: { icon: Package, label: 'Other Resources' },
};

function ResourceGroup({ type, resources }: { type: string; resources: Resource[] }) {
  const config = TYPE_CONFIG[type] || TYPE_CONFIG.other;
  const Icon = config.icon;

  return (
    <div className="bg-[var(--color-paper-card)] rounded-xl border border-[var(--color-border)] overflow-hidden">
      <div className="px-5 py-3 border-b border-[var(--color-border)] bg-[var(--color-paper-warm)] flex items-center gap-2">
        <Icon size={15} className="text-[var(--color-ink-muted)]" />
        <h3 className="text-sm font-medium text-[var(--color-ink)]">
          {config.label} ({resources.length})
        </h3>
      </div>
      <div className="divide-y divide-[var(--color-border)]">
        {resources.map((r, i) => (
          <div key={i} className="px-5 py-3 flex items-start gap-3">
            <ExternalLink size={14} className="mt-0.5 text-[var(--color-ink-muted)] shrink-0" />
            <div className="flex-1 min-w-0">
              <a
                href={r.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-[var(--color-accent)] hover:underline break-all"
              >
                {r.url}
              </a>
              {r.description && (
                <p className="text-sm text-[var(--color-ink-secondary)] mt-0.5">{r.description}</p>
              )}
              <div className="flex items-center gap-2 mt-1.5">
                <PaperChip paperId={r.paper_id} title={r.paper_title} />
                {r.paper_year && (
                  <span className="text-xs text-[var(--color-ink-muted)]">{r.paper_year}</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ResourcesTab({ reviewId }: { reviewId: string }) {
  const { data, loading, error } = useFetch(() => fetchResources(reviewId), [reviewId]);

  if (loading) return <Loading />;
  if (error) return <ErrorMessage message={error} />;
  if (!data || Object.keys(data).length === 0) {
    return (
      <EmptyState
        icon={Package}
        title="No resources tracked"
        description="The agent hasn't recorded any code repos, datasets, or other resources yet."
      />
    );
  }

  const total = Object.values(data).reduce((sum, arr) => sum + arr.length, 0);
  const typeOrder = ['code', 'dataset', 'benchmark', 'demo', 'blog', 'other'];
  const sortedTypes = Object.keys(data).sort(
    (a, b) => (typeOrder.indexOf(a) === -1 ? 99 : typeOrder.indexOf(a)) - (typeOrder.indexOf(b) === -1 ? 99 : typeOrder.indexOf(b))
  );

  return (
    <div className="space-y-5">
      <div className="text-sm text-[var(--color-ink-muted)]">
        <strong className="text-[var(--color-ink)]">{total}</strong> resources across {sortedTypes.length} categories
      </div>
      {sortedTypes.map((type) => (
        <ResourceGroup key={type} type={type} resources={data[type]} />
      ))}
    </div>
  );
}
