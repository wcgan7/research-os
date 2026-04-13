import type { LucideIcon } from 'lucide-react';

interface Props {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  sublabel?: string;
}

export default function StatCard({ label, value, icon: Icon, sublabel }: Props) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-[var(--color-paper-card)] border border-[var(--color-border)]">
      {Icon && (
        <div className="p-2 rounded-md bg-[var(--color-paper-warm)]">
          <Icon size={18} className="text-[var(--color-ink-muted)]" />
        </div>
      )}
      <div>
        <div className="text-xl font-semibold text-[var(--color-ink)] leading-tight">{value}</div>
        <div className="text-xs text-[var(--color-ink-muted)] uppercase tracking-wide">{label}</div>
        {sublabel && <div className="text-xs text-[var(--color-ink-muted)]">{sublabel}</div>}
      </div>
    </div>
  );
}
