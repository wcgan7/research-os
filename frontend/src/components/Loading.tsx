export default function Loading() {
  return (
    <div className="flex items-center justify-center py-16" role="status" aria-label="Loading">
      <div className="w-5 h-5 border-2 border-[var(--color-border-strong)] border-t-[var(--color-ink-muted)] rounded-full animate-spin" />
      <span className="sr-only">Loading...</span>
    </div>
  );
}
