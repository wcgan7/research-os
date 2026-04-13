import { Inbox } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface Props {
  icon?: LucideIcon;
  title: string;
  description?: string;
}

export default function EmptyState({ icon: Icon = Inbox, title, description }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <Icon size={40} className="text-[var(--color-border-strong)] mb-4" strokeWidth={1.2} />
      <h3 className="font-serif text-lg text-[var(--color-ink-secondary)] mb-1">{title}</h3>
      {description && <p className="text-sm text-[var(--color-ink-muted)] max-w-sm">{description}</p>}
    </div>
  );
}
