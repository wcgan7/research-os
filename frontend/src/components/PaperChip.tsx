import { useNavigate, useParams } from 'react-router-dom';
import { FileText } from 'lucide-react';

interface Props {
  paperId: string;
  title?: string;
  reviewId?: string;
}

export default function PaperChip({ paperId, title, reviewId: reviewIdProp }: Props) {
  const navigate = useNavigate();
  const params = useParams();
  const reviewId = reviewIdProp || params.reviewId;
  const display = title || paperId.slice(0, 8) + '...';

  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        if (reviewId) navigate(`/review/${reviewId}/papers?detail=${paperId}`);
      }}
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[var(--color-paper-warm)] hover:bg-[var(--color-border)] text-xs text-[var(--color-ink-secondary)] transition-colors cursor-pointer border border-[var(--color-border)] max-w-[220px] truncate"
      title={title || paperId}
      aria-label={`View paper: ${display}`}
    >
      <FileText size={11} className="shrink-0" aria-hidden="true" />
      <span className="truncate">{display}</span>
    </button>
  );
}
