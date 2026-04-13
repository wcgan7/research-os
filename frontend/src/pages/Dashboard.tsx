import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, FileText, CheckCircle, BookOpen, X, Loader2 } from 'lucide-react';
import { fetchReviews, createReview } from '../api/client';
import { useFetch } from '../api/hooks';
import type { Review } from '../api/types';
import StatusBadge from '../components/StatusBadge';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import EmptyState from '../components/EmptyState';

function ReviewCard({ review }: { review: Review }) {
  const navigate = useNavigate();
  const counts = review.paper_status_counts || {};
  const relevant = (counts.relevant || 0) + (counts.seed || 0);

  return (
    <button
      onClick={() => navigate(`/review/${review.id}`)}
      className="text-left w-full p-5 rounded-xl bg-[var(--color-paper-card)] border border-[var(--color-border)] hover:border-[var(--color-border-strong)] hover:shadow-sm transition-all cursor-pointer group"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <h3 className="font-serif text-lg text-[var(--color-ink)] group-hover:text-[var(--color-accent)] transition-colors leading-snug">
          {review.topic}
        </h3>
        <StatusBadge status={review.status} />
      </div>
      <p className="text-sm text-[var(--color-ink-secondary)] mb-4 line-clamp-2">
        {review.objective}
      </p>
      <div className="flex items-center gap-4 text-xs text-[var(--color-ink-muted)]">
        <span className="flex items-center gap-1">
          <BookOpen size={13} />
          {review.paper_count || 0} papers
        </span>
        <span className="flex items-center gap-1">
          <CheckCircle size={13} />
          {review.assessment_count || 0} assessed
        </span>
        {relevant > 0 && (
          <span className="text-[var(--color-relevant)] font-medium">
            {relevant} relevant
          </span>
        )}
        {review.has_report && (
          <span className="flex items-center gap-1 text-[var(--color-completed)]">
            <FileText size={13} />
            Report
          </span>
        )}
      </div>
      <div className="mt-3 pt-3 border-t border-[var(--color-border)] text-xs text-[var(--color-ink-muted)]">
        Created {new Date(review.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
      </div>
    </button>
  );
}

function NewReviewModal({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
  const [topic, setTopic] = useState('');
  const [objective, setObjective] = useState('');
  const [seeds, setSeeds] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const seedUrls = seeds.split('\n').map(s => s.trim()).filter(Boolean);
      const result = await createReview(topic, objective, seedUrls.length ? seedUrls : undefined);
      onCreated(result.review_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create review');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <form
        onSubmit={handleSubmit}
        className="relative bg-[var(--color-paper-card)] rounded-xl border border-[var(--color-border)] shadow-xl w-full max-w-lg mx-4 p-6"
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-serif text-lg text-[var(--color-ink)]">New Literature Review</h2>
          <button type="button" onClick={onClose} className="p-1.5 rounded-md hover:bg-[var(--color-paper-warm)] text-[var(--color-ink-muted)]" aria-label="Close">
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label htmlFor="topic" className="block text-sm font-medium text-[var(--color-ink-secondary)] mb-1">Topic</label>
            <input
              id="topic"
              type="text"
              required
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., KV cache compression for large language models"
              className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-paper)] focus:outline-none focus:border-[var(--color-border-strong)]"
            />
          </div>
          <div>
            <label htmlFor="objective" className="block text-sm font-medium text-[var(--color-ink-secondary)] mb-1">Objective</label>
            <textarea
              id="objective"
              required
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              placeholder="What should this review cover? What questions should it answer?"
              rows={3}
              className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-paper)] focus:outline-none focus:border-[var(--color-border-strong)] resize-none"
            />
          </div>
          <div>
            <label htmlFor="seeds" className="block text-sm font-medium text-[var(--color-ink-secondary)] mb-1">
              Seed Papers <span className="font-normal text-[var(--color-ink-muted)]">(optional)</span>
            </label>
            <textarea
              id="seeds"
              value={seeds}
              onChange={(e) => setSeeds(e.target.value)}
              placeholder={"One per line: arXiv URLs, DOIs, or Semantic Scholar IDs\ne.g., https://arxiv.org/abs/2312.10997\ne.g., 2401.15884"}
              rows={3}
              className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-paper)] focus:outline-none focus:border-[var(--color-border-strong)] resize-none font-mono"
            />
          </div>
        </div>

        {error && <div className="mt-4"><ErrorMessage message={error} /></div>}

        <div className="flex justify-end gap-3 mt-6">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-[var(--color-ink-secondary)] hover:bg-[var(--color-paper-warm)] rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !topic.trim() || !objective.trim()}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-[var(--color-accent)] rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting && <Loader2 size={15} className="animate-spin" />}
            {submitting ? 'Launching...' : 'Start Review'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function Dashboard() {
  const { data: reviews, loading, error } = useFetch(fetchReviews);
  const [showNewReview, setShowNewReview] = useState(false);
  const navigate = useNavigate();

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-[var(--color-border)] bg-[var(--color-paper-card)]">
        <div className="max-w-5xl mx-auto px-6 py-6 flex items-center justify-between">
          <div>
            <h1 className="font-serif text-2xl text-[var(--color-ink)]">research-os</h1>
            <p className="text-sm text-[var(--color-ink-muted)] mt-0.5">Literature Reviews</p>
          </div>
          <button
            onClick={() => setShowNewReview(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--color-accent)] text-sm font-medium text-white hover:opacity-90 transition-opacity"
          >
            <Plus size={16} />
            New Review
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        {loading ? (
          <Loading />
        ) : error ? (
          <ErrorMessage message={error} />
        ) : !reviews || reviews.length === 0 ? (
          <EmptyState
            icon={BookOpen}
            title="No reviews yet"
            description="Click 'New Review' to start your first literature review."
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {reviews.map((r) => (
              <ReviewCard key={r.id} review={r} />
            ))}
          </div>
        )}
      </main>

      {showNewReview && (
        <NewReviewModal
          onClose={() => setShowNewReview(false)}
          onCreated={(id) => {
            setShowNewReview(false);
            navigate(`/review/${id}`);
          }}
        />
      )}
    </div>
  );
}
