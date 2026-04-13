import { Globe, BookOpen, Database } from 'lucide-react';

const icons: Record<string, { icon: typeof Globe; label: string }> = {
  arxiv: { icon: BookOpen, label: 'arXiv' },
  semantic_scholar: { icon: Database, label: 'Semantic Scholar' },
  openalex: { icon: Globe, label: 'OpenAlex' },
};

export default function SourceIcon({ source }: { source: string }) {
  const config = icons[source];
  if (!config) return <span className="text-xs text-[var(--color-ink-muted)]">{source}</span>;
  const Icon = config.icon;
  return (
    <span className="inline-flex items-center gap-1 text-xs text-[var(--color-ink-muted)]" title={config.label}>
      <Icon size={13} />
      <span className="hidden sm:inline">{config.label}</span>
    </span>
  );
}
