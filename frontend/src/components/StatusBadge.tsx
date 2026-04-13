const styles: Record<string, string> = {
  active: 'bg-[var(--color-active-bg)] text-[var(--color-active)]',
  completed: 'bg-[var(--color-completed-bg)] text-[var(--color-completed)]',
  paused: 'bg-[var(--color-paused-bg)] text-[var(--color-paused)]',
  relevant: 'bg-[var(--color-relevant-bg)] text-[var(--color-relevant)]',
  essential: 'bg-[var(--color-essential-bg)] text-[var(--color-essential)]',
  not_relevant: 'bg-[var(--color-not-relevant-bg)] text-[var(--color-not-relevant)]',
  discovered: 'bg-blue-50 text-blue-600',
  seed: 'bg-purple-50 text-purple-600',
  uncertain: 'bg-yellow-50 text-yellow-700',
  deferred: 'bg-gray-100 text-gray-500',
  reviewed: 'bg-teal-50 text-teal-600',
};

export default function StatusBadge({ status }: { status: string }) {
  const cls = styles[status] || 'bg-gray-100 text-gray-600';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium tracking-wide uppercase ${cls}`}>
      {status.replace(/_/g, ' ')}
    </span>
  );
}
