import { useState } from 'react';
import { fetchNotes } from '../../api/client';
import { useFetch } from '../../api/hooks';
import KindBadge from '../../components/KindBadge';
import PaperChip from '../../components/PaperChip';
import MarkdownRenderer from '../../components/MarkdownRenderer';
import EmptyState from '../../components/EmptyState';
import ErrorMessage from '../../components/ErrorMessage';
import Loading from '../../components/Loading';
import { StickyNote, AlertCircle } from 'lucide-react';

export default function NotesTab({ reviewId }: { reviewId: string }) {
  const [activeKind, setActiveKind] = useState<string>('');
  // Fetch all notes to determine available kinds
  const { data: allNotes, loading: loadingAll, error: errorAll } = useFetch(
    () => fetchNotes(reviewId),
    [reviewId]
  );

  const availableKinds = allNotes
    ? [...new Set(allNotes.map((n) => n.kind))].sort()
    : [];

  const data = activeKind
    ? allNotes?.filter((n) => n.kind === activeKind) ?? null
    : allNotes;
  const loading = loadingAll;
  const error = errorAll;

  return (
    <div>
      {/* Kind filter chips */}
      <div className="flex flex-wrap gap-2 mb-5">
        <button
          onClick={() => setActiveKind('')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            !activeKind
              ? 'bg-[var(--color-ink)] text-white'
              : 'bg-[var(--color-paper-card)] border border-[var(--color-border)] text-[var(--color-ink-secondary)] hover:bg-[var(--color-paper-warm)]'
          }`}
        >
          All
        </button>
        {availableKinds.map((k) => (
          <button
            key={k}
            onClick={() => setActiveKind(activeKind === k ? '' : k)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeKind === k
                ? 'bg-[var(--color-ink)] text-white'
                : 'bg-[var(--color-paper-card)] border border-[var(--color-border)] text-[var(--color-ink-secondary)] hover:bg-[var(--color-paper-warm)]'
            }`}
          >
            {k.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorMessage message={error} />
      ) : !data || data.length === 0 ? (
        <EmptyState icon={StickyNote} title="No notes" description="The agent hasn't recorded any notes yet." />
      ) : (
        <div className="space-y-3">
          {data.map((note) => (
            <div
              key={note.id}
              className="bg-[var(--color-paper-card)] rounded-xl border border-[var(--color-border)] p-5"
            >
              <div className="flex items-center gap-3 mb-2">
                <KindBadge kind={note.kind} />
                {note.priority != null && note.priority > 0 && (
                  <span className="flex items-center gap-1 text-xs text-amber-600">
                    <AlertCircle size={12} /> Priority {note.priority}
                  </span>
                )}
                <span className="text-xs text-[var(--color-ink-muted)] ml-auto">
                  {new Date(note.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <div className="text-sm text-[var(--color-ink-secondary)]">
                <MarkdownRenderer content={note.content} />
              </div>
              {note.paper_ids?.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-[var(--color-border)]">
                  {note.paper_ids.map((pid) => (
                    <PaperChip key={pid} paperId={pid} />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
