import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, FileText, BookOpen, Shield, StickyNote, Activity, Package, PlayCircle,
  Plus, X, Loader2,
} from 'lucide-react';
import { fetchReview, continueReview, seedPaper } from '../api/client';
import { useFetch, usePolling } from '../api/hooks';
import StatusBadge from '../components/StatusBadge';
import ConfidenceGauge from '../components/ConfidenceGauge';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import ReportTab from './tabs/ReportTab';
import PapersTab from './tabs/PapersTab';
import CoverageTab from './tabs/CoverageTab';
import NotesTab from './tabs/NotesTab';
import ActivityTab from './tabs/ActivityTab';
import ResourcesTab from './tabs/ResourcesTab';

const tabs = [
  { id: 'report', label: 'Report', icon: FileText },
  { id: 'papers', label: 'Papers', icon: BookOpen },
  { id: 'coverage', label: 'Coverage', icon: Shield },
  { id: 'notes', label: 'Notes', icon: StickyNote },
  { id: 'activity', label: 'Agent Activity', icon: Activity },
  { id: 'resources', label: 'Resources', icon: Package },
];

function SeedPaperModal({ reviewId, onClose, onSeeded }: { reviewId: string; onClose: () => void; onSeeded: () => void }) {
  const [urlOrId, setUrlOrId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await seedPaper(reviewId, urlOrId.trim());
      setSuccess(`Added: ${result.title}`);
      setUrlOrId('');
      onSeeded();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to seed paper');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <form
        onSubmit={handleSubmit}
        className="relative bg-[var(--color-paper-card)] rounded-xl border border-[var(--color-border)] shadow-xl w-full max-w-md mx-4 p-6"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-serif text-lg text-[var(--color-ink)]">Seed Paper</h2>
          <button type="button" onClick={onClose} className="p-1.5 rounded-md hover:bg-[var(--color-paper-warm)] text-[var(--color-ink-muted)]" aria-label="Close">
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        <p className="text-sm text-[var(--color-ink-muted)] mb-4">
          Add a paper to this review by arXiv URL, arXiv ID, DOI, or Semantic Scholar URL.
        </p>
        <input
          type="text"
          required
          value={urlOrId}
          onChange={(e) => setUrlOrId(e.target.value)}
          placeholder="e.g., https://arxiv.org/abs/2504.19874 or 2504.19874"
          className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-paper)] focus:outline-none focus:border-[var(--color-border-strong)] font-mono"
          aria-label="Paper URL or ID"
        />
        {error && <div className="mt-3"><ErrorMessage message={error} /></div>}
        {success && (
          <div className="mt-3 px-3 py-2 rounded-lg bg-[var(--color-relevant-bg)] text-sm text-[var(--color-relevant)]">
            {success}
          </div>
        )}
        <div className="flex justify-end gap-3 mt-5">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-[var(--color-ink-secondary)] hover:bg-[var(--color-paper-warm)] rounded-lg transition-colors"
          >
            Close
          </button>
          <button
            type="submit"
            disabled={submitting || !urlOrId.trim()}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-[var(--color-accent)] rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting && <Loader2 size={15} className="animate-spin" />}
            {submitting ? 'Adding...' : 'Add Paper'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function ReviewWorkspace() {
  const { reviewId } = useParams<{ reviewId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('report');
  const [showSeedModal, setShowSeedModal] = useState(false);
  const [continuing, setContinuing] = useState(false);
  const [continueError, setContinueError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // Initial fetch
  const { data: initialReview, loading, error } = useFetch(() => fetchReview(reviewId!), [reviewId, refreshKey]);

  // Poll when running
  const isRunning = initialReview?.is_running || continuing;
  const { data: polledReview } = usePolling(
    () => fetchReview(reviewId!),
    5000,
    isRunning,
    [reviewId],
  );

  const review = polledReview || initialReview;

  // Detect when agent finishes — refresh tab content
  const prevRunning = useRef(isRunning);
  useEffect(() => {
    if (prevRunning.current && !review?.is_running) {
      // Agent just finished — refresh everything
      setRefreshKey(k => k + 1);
    }
    prevRunning.current = review?.is_running || false;
  }, [review?.is_running]);

  // Bump refreshKey when stats change during polling
  const prevStats = useRef<string>('');
  useEffect(() => {
    if (!review?.stats) return;
    const statsKey = `${review.stats.paper_count}-${review.stats.assessment_count}-${review.stats.search_count}-${review.stats.note_count}`;
    if (prevStats.current && prevStats.current !== statsKey) {
      setRefreshKey(k => k + 1);
    }
    prevStats.current = statsKey;
  }, [review?.stats]);

  if (loading) return <Loading />;
  if (error) return <div className="p-8"><ErrorMessage message={error} /></div>;
  if (!review) return <div className="p-8 text-center text-[var(--color-ink-muted)]">Review not found</div>;

  const stats = review.stats;

  const handleContinue = async () => {
    setContinuing(true);
    setContinueError(null);
    try {
      await continueReview(review.id);
      // Reset after a short delay — polling will pick up is_running from the backend
      setTimeout(() => setContinuing(false), 10000);
    } catch (err) {
      setContinueError(err instanceof Error ? err.message : 'Failed to continue review');
      setContinuing(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-[var(--color-paper-card)] border-b border-[var(--color-border)] sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-6">
          {/* Top row */}
          <div className="flex items-center gap-3 pt-4 pb-2">
            <button
              onClick={() => navigate('/')}
              className="p-1.5 rounded-md hover:bg-[var(--color-paper-warm)] text-[var(--color-ink-muted)] transition-colors"
              aria-label="Back to dashboard"
            >
              <ArrowLeft size={18} aria-hidden="true" />
            </button>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3">
                <h1 className="font-serif text-xl text-[var(--color-ink)] truncate">{review.topic}</h1>
                <StatusBadge status={review.status} />
                {review.is_running && (
                  <span className="flex items-center gap-1.5 text-xs text-[var(--color-active)] font-medium">
                    <Loader2 size={13} className="animate-spin" />
                    Agent running
                  </span>
                )}
              </div>
              <p className="text-sm text-[var(--color-ink-secondary)] truncate mt-0.5">{review.objective}</p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setShowSeedModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-[var(--color-ink-secondary)] border border-[var(--color-border)] hover:bg-[var(--color-paper-warm)] transition-colors"
              >
                <Plus size={15} aria-hidden="true" />
                Seed Paper
              </button>
              <button
                onClick={handleContinue}
                disabled={continuing || review.is_running}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-white bg-[var(--color-accent)] hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {(continuing || review.is_running) ? <Loader2 size={15} className="animate-spin" /> : <PlayCircle size={15} aria-hidden="true" />}
                {review.is_running ? 'Running...' : continuing ? 'Launching...' : 'Continue'}
              </button>
            </div>
          </div>

          {continueError && (
            <div className="pb-2"><ErrorMessage message={continueError} /></div>
          )}

          {/* Stats row */}
          {stats && (
            <div className="flex items-center gap-5 pb-3 text-xs text-[var(--color-ink-muted)] overflow-x-auto">
              <span><strong className="text-[var(--color-ink)]">{stats.paper_count}</strong> papers</span>
              <span><strong className="text-[var(--color-ink)]">{stats.assessment_count}</strong> assessed</span>
              <span className="text-[var(--color-relevant)]">
                <strong>{stats.relevance_counts?.relevant || 0}</strong> relevant
              </span>
              <span className="text-[var(--color-essential)]">
                <strong>{stats.relevance_counts?.essential || 0}</strong> essential
              </span>
              {stats.has_report && (
                <span className="text-[var(--color-completed)]">Report ready</span>
              )}
              {stats.latest_confidence != null && (
                <span className="flex items-center gap-2 min-w-[140px]">
                  Coverage
                  <span className="w-20 inline-block">
                    <ConfidenceGauge confidence={stats.latest_confidence} />
                  </span>
                </span>
              )}
            </div>
          )}

          {/* Tabs */}
          <nav role="tablist" className="flex gap-0 -mb-px overflow-x-auto" aria-label="Review sections">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                role="tab"
                aria-selected={activeTab === id}
                aria-controls={`tabpanel-${id}`}
                onClick={() => setActiveTab(id)}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === id
                    ? 'border-[var(--color-accent)] text-[var(--color-accent)]'
                    : 'border-transparent text-[var(--color-ink-muted)] hover:text-[var(--color-ink-secondary)] hover:border-[var(--color-border)]'
                }`}
              >
                <Icon size={15} aria-hidden="true" />
                {label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Tab Content */}
      <main className="flex-1 max-w-6xl mx-auto px-6 py-6 w-full" role="tabpanel" id={`tabpanel-${activeTab}`}>
        {activeTab === 'report' && <ReportTab reviewId={reviewId!} key={refreshKey} />}
        {activeTab === 'papers' && <PapersTab reviewId={reviewId!} key={refreshKey} />}
        {activeTab === 'coverage' && <CoverageTab reviewId={reviewId!} key={refreshKey} />}
        {activeTab === 'notes' && <NotesTab reviewId={reviewId!} key={refreshKey} />}
        {activeTab === 'activity' && <ActivityTab reviewId={reviewId!} isRunning={review.is_running || false} />}
        {activeTab === 'resources' && <ResourcesTab reviewId={reviewId!} key={refreshKey} />}
      </main>

      {showSeedModal && (
        <SeedPaperModal
          reviewId={review.id}
          onClose={() => setShowSeedModal(false)}
          onSeeded={() => setRefreshKey(k => k + 1)}
        />
      )}
    </div>
  );
}
