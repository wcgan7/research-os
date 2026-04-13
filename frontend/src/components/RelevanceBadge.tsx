const styles: Record<string, string> = {
  essential: 'bg-[var(--color-essential-bg)] text-[var(--color-essential)] ring-1 ring-amber-300',
  relevant: 'bg-[var(--color-relevant-bg)] text-[var(--color-relevant)]',
  tangential: 'bg-[var(--color-tangential-bg)] text-[var(--color-tangential)]',
  not_relevant: 'bg-[var(--color-not-relevant-bg)] text-[var(--color-not-relevant)]',
};

export default function RelevanceBadge({ relevance }: { relevance: string }) {
  if (!relevance) return null;
  const cls = styles[relevance] || 'bg-gray-100 text-gray-600';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {relevance.replace(/_/g, ' ')}
    </span>
  );
}
