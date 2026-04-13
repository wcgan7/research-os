import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Search, ChevronDown, ChevronRight, ExternalLink, X, FileText as FileTextIcon, Download, Loader2,
} from 'lucide-react';
import { fetchPapers, fetchPaperDetail, fetchPaperFullText } from '../../api/client';
import { useFetch, useDebounce } from '../../api/hooks';
import type { Paper } from '../../api/types';
import ErrorMessage from '../../components/ErrorMessage';
import StatusBadge from '../../components/StatusBadge';
import RelevanceBadge from '../../components/RelevanceBadge';
import SourceIcon from '../../components/SourceIcon';
import PaperChip from '../../components/PaperChip';
import KindBadge from '../../components/KindBadge';
import Loading from '../../components/Loading';
import EmptyState from '../../components/EmptyState';

function PaperRow({
  paper,
  expanded,
  onToggle,
  onOpenDetail,
  paperTitles,
}: {
  paper: Paper;
  expanded: boolean;
  onToggle: () => void;
  onOpenDetail: () => void;
  paperTitles: Record<string, string>;
}) {
  const a = paper.assessment;
  return (
    <div className="border-b border-[var(--color-border)] last:border-b-0">
      <button
        onClick={onToggle}
        className="w-full text-left px-4 py-3 grid items-center hover:bg-[var(--color-paper-warm)] transition-colors"
        style={{ gridTemplateColumns: '20px 1fr 52px 64px 88px 88px 100px 20px', columnGap: '8px' }}
      >
        <span className="text-[var(--color-ink-muted)]">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </span>
        <div className="min-w-0">
          <div className="text-sm font-medium text-[var(--color-ink)] truncate">{paper.title}</div>
          <div className="text-xs text-[var(--color-ink-muted)] mt-0.5 truncate">
            {paper.authors?.slice(0, 3).join(', ')}
            {paper.authors?.length > 3 && ' et al.'}
          </div>
        </div>
        <span className="text-xs text-[var(--color-ink-muted)] tabular-nums text-right">
          {paper.year || '—'}
        </span>
        <span className="text-xs text-[var(--color-ink-muted)] tabular-nums text-right">
          {paper.citation_count != null ? paper.citation_count : '—'}
        </span>
        <span>{a && <RelevanceBadge relevance={a.relevance} />}</span>
        <span><StatusBadge status={paper.status} /></span>
        <span><SourceIcon source={paper.source} /></span>
        <span>
          {paper.full_text_source && (
            <span title={`Full text: ${paper.full_text_source}`}>
              <FileTextIcon size={13} className="text-[var(--color-relevant)]" />
            </span>
          )}
        </span>
      </button>

      {expanded && (
        <div className="px-4 pb-4 pl-10 space-y-3 bg-[var(--color-paper-warm)]">
          {a && (
            <div className="space-y-2">
              <div>
                <span className="text-xs font-medium text-[var(--color-ink-muted)] uppercase tracking-wide">Rationale</span>
                <p className="text-sm text-[var(--color-ink-secondary)] mt-0.5">{a.rationale}</p>
              </div>
              {a.key_claims?.length > 0 && (
                <div>
                  <span className="text-xs font-medium text-[var(--color-ink-muted)] uppercase tracking-wide">Key Claims</span>
                  <ul className="list-disc list-inside text-sm text-[var(--color-ink-secondary)] mt-0.5 space-y-0.5">
                    {a.key_claims.map((c, i) => <li key={i}>{c}</li>)}
                  </ul>
                </div>
              )}
              {a.methodology_notes && (
                <div>
                  <span className="text-xs font-medium text-[var(--color-ink-muted)] uppercase tracking-wide">Methodology</span>
                  <p className="text-sm text-[var(--color-ink-secondary)] mt-0.5">{a.methodology_notes}</p>
                </div>
              )}
              {a.connections?.length > 0 && (
                <div>
                  <span className="text-xs font-medium text-[var(--color-ink-muted)] uppercase tracking-wide">Connections</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {a.connections.map((c) => <PaperChip key={c} paperId={c} title={paperTitles[c]} />)}
                  </div>
                </div>
              )}
            </div>
          )}

          {paper.abstract && (
            <div>
              <span className="text-xs font-medium text-[var(--color-ink-muted)] uppercase tracking-wide">Abstract</span>
              <p className="text-sm text-[var(--color-ink-secondary)] mt-0.5 line-clamp-4">{paper.abstract}</p>
            </div>
          )}

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={(e) => { e.stopPropagation(); onOpenDetail(); }}
              className="text-xs text-[var(--color-accent)] hover:underline font-medium"
            >
              Open full detail
            </button>
            {paper.url && (
              <a
                href={paper.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-[var(--color-ink-muted)] hover:text-[var(--color-accent)] flex items-center gap-1"
              >
                <ExternalLink size={12} /> View paper
              </a>
            )}
            {paper.doi && (
              <a
                href={`https://doi.org/${paper.doi}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-[var(--color-ink-muted)] hover:text-[var(--color-accent)] flex items-center gap-1"
              >
                <ExternalLink size={12} /> DOI
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function PaperDetailPanel({
  reviewId,
  paperId,
  onClose,
}: {
  reviewId: string;
  paperId: string;
  onClose: () => void;
}) {
  const { data: paper, loading, error } = useFetch(
    () => fetchPaperDetail(reviewId, paperId),
    [reviewId, paperId]
  );
  const [showFullText, setShowFullText] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [fetchResult, setFetchResult] = useState<string | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCloseRef.current();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <div className="relative w-full max-w-2xl bg-[var(--color-paper-card)] border-l border-[var(--color-border)] shadow-xl overflow-y-auto">
        <div className="sticky top-0 bg-[var(--color-paper-card)] border-b border-[var(--color-border)] px-6 py-4 flex items-center justify-between z-10">
          <h3 className="font-serif text-lg text-[var(--color-ink)] truncate pr-4">Paper Detail</h3>
          <button onClick={onClose} className="p-1.5 rounded-md hover:bg-[var(--color-paper-warm)] text-[var(--color-ink-muted)]" aria-label="Close panel">
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        {loading ? (
          <Loading />
        ) : error ? (
          <div className="px-6 py-5"><ErrorMessage message={error} /></div>
        ) : paper ? (
          <div className="px-6 py-5 space-y-5">
            <div>
              <h2 className="font-serif text-xl text-[var(--color-ink)] leading-snug">{paper.title}</h2>
              <p className="text-sm text-[var(--color-ink-secondary)] mt-1">
                {paper.authors?.join(', ')}
              </p>
              <div className="flex items-center gap-3 mt-2">
                {paper.year && <span className="text-sm text-[var(--color-ink-muted)]">{paper.year}</span>}
                {paper.citation_count != null && (
                  <span className="text-sm text-[var(--color-ink-muted)]">{paper.citation_count} citations</span>
                )}
                <SourceIcon source={paper.source} />
                <StatusBadge status={paper.status} />
                {paper.assessment && <RelevanceBadge relevance={paper.assessment.relevance} />}
              </div>
              <div className="flex gap-2 mt-2">
                {paper.url && (
                  <a href={paper.url} target="_blank" rel="noopener noreferrer" className="text-xs text-[var(--color-accent)] hover:underline flex items-center gap-1">
                    <ExternalLink size={12} /> Paper
                  </a>
                )}
                {paper.doi && (
                  <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noopener noreferrer" className="text-xs text-[var(--color-accent)] hover:underline flex items-center gap-1">
                    <ExternalLink size={12} /> DOI
                  </a>
                )}
              </div>
            </div>

            {paper.assessment && (
              <section>
                <h4 className="text-xs uppercase tracking-wide text-[var(--color-ink-muted)] font-medium mb-2">Assessment</h4>
                <div className="bg-[var(--color-paper-warm)] rounded-lg p-4 space-y-2 text-sm">
                  <p><strong>Rationale:</strong> {paper.assessment.rationale}</p>
                  {paper.assessment.key_claims?.length > 0 && (
                    <div>
                      <strong>Key Claims:</strong>
                      <ul className="list-disc list-inside mt-1 space-y-0.5">
                        {paper.assessment.key_claims.map((c, i) => <li key={i}>{c}</li>)}
                      </ul>
                    </div>
                  )}
                  {paper.assessment.methodology_notes && (
                    <p><strong>Methodology:</strong> {paper.assessment.methodology_notes}</p>
                  )}
                </div>
              </section>
            )}

            {paper.abstract && (
              <section>
                <h4 className="text-xs uppercase tracking-wide text-[var(--color-ink-muted)] font-medium mb-2">Abstract</h4>
                <p className="text-sm text-[var(--color-ink-secondary)] leading-relaxed">{paper.abstract}</p>
              </section>
            )}

            {paper.full_text && (
              <section>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-xs uppercase tracking-wide text-[var(--color-ink-muted)] font-medium">
                    Full Text <span className="normal-case font-normal">({paper.full_text_source})</span>
                  </h4>
                  <button
                    onClick={() => setShowFullText(!showFullText)}
                    className="text-xs text-[var(--color-accent)] hover:underline"
                  >
                    {showFullText ? 'Collapse' : 'Expand'}
                  </button>
                </div>
                <div className={`text-sm text-[var(--color-ink-secondary)] leading-relaxed bg-[var(--color-paper-warm)] rounded-lg p-4 ${showFullText ? 'max-h-[600px] overflow-y-auto' : 'max-h-32 overflow-hidden'} transition-all`}>
                  <pre className="whitespace-pre-wrap font-sans">{paper.full_text}</pre>
                </div>
              </section>
            )}

            {paper.connected_papers?.length > 0 && (
              <section>
                <h4 className="text-xs uppercase tracking-wide text-[var(--color-ink-muted)] font-medium mb-2">Connected Papers</h4>
                <div className="flex flex-wrap gap-1.5">
                  {paper.connected_papers.map((cp) => (
                    <PaperChip key={cp.id} paperId={cp.id} title={cp.title} />
                  ))}
                </div>
              </section>
            )}

            {paper.notes?.length > 0 && (
              <section>
                <h4 className="text-xs uppercase tracking-wide text-[var(--color-ink-muted)] font-medium mb-2">Related Notes</h4>
                <div className="space-y-2">
                  {paper.notes.map((n) => (
                    <div key={n.id} className="bg-[var(--color-paper-warm)] rounded-lg p-3 text-sm">
                      <KindBadge kind={n.kind} />
                      <p className="mt-1 text-[var(--color-ink-secondary)]">{n.content}</p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {paper.searches?.length > 0 && (
              <section>
                <h4 className="text-xs uppercase tracking-wide text-[var(--color-ink-muted)] font-medium mb-2">Found via</h4>
                <div className="space-y-1">
                  {paper.searches.map((s) => (
                    <div key={s.id} className="text-sm text-[var(--color-ink-secondary)]">
                      <SourceIcon source={s.source} /> "{s.query}" ({s.result_count} results)
                    </div>
                  ))}
                </div>
              </section>
            )}

            {paper.resources?.length > 0 && (
              <section>
                <h4 className="text-xs uppercase tracking-wide text-[var(--color-ink-muted)] font-medium mb-2">Resources</h4>
                <div className="space-y-1.5">
                  {paper.resources.map((r, i) => {
                    let parsed: { type?: string; url?: string; description?: string } = {};
                    try { parsed = JSON.parse(r); } catch { parsed = { description: r }; }
                    return (
                      <div key={i} className="flex items-start gap-2 text-sm">
                        <Download size={13} className="mt-0.5 text-[var(--color-ink-muted)]" />
                        {parsed.url ? (
                          <a href={parsed.url} target="_blank" rel="noopener noreferrer" className="text-[var(--color-accent)] hover:underline break-all">
                            {parsed.url}
                          </a>
                        ) : (
                          <span className="text-[var(--color-ink-secondary)]">{parsed.description}</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {!paper.full_text && (
              <div className="pt-2 space-y-2">
                <button
                  disabled={fetching}
                  onClick={async () => {
                    setFetching(true);
                    setFetchError(null);
                    setFetchResult(null);
                    try {
                      const r = await fetchPaperFullText(reviewId, paperId);
                      if (r.chars) {
                        setFetchResult(`Fetched ${r.chars} chars from ${r.source}`);
                      } else {
                        setFetchResult('No full text available for this paper.');
                      }
                    } catch (e) {
                      setFetchError(e instanceof Error ? e.message : 'Failed');
                    } finally {
                      setFetching(false);
                    }
                  }}
                  className="flex items-center gap-1.5 text-xs text-[var(--color-accent)] border border-[var(--color-border)] px-3 py-1.5 rounded hover:bg-[var(--color-paper-warm)] transition-colors disabled:opacity-50"
                >
                  {fetching && <Loader2 size={12} className="animate-spin" />}
                  {fetching ? 'Fetching...' : 'Fetch Full Text'}
                </button>
                {fetchResult && <p className="text-xs text-[var(--color-relevant)]">{fetchResult}</p>}
                {fetchError && <p className="text-xs text-red-600">{fetchError}</p>}
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}

const STATUS_OPTIONS = ['', 'relevant', 'not_relevant', 'essential', 'discovered', 'seed', 'uncertain', 'deferred'];
const RELEVANCE_OPTIONS = ['', 'essential', 'relevant', 'tangential', 'not_relevant'];
const SOURCE_OPTIONS = ['', 'arxiv', 'semantic_scholar', 'openalex'];
const SORT_OPTIONS = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'year', label: 'Year' },
  { value: 'citations', label: 'Citations' },
  { value: 'title', label: 'Title' },
];

export default function PapersTab({ reviewId }: { reviewId: string }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [filters, setFilters] = useState({
    status: '',
    relevance: '',
    source: '',
    keyword: '',
    sort: 'relevance',
  });
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const detailId = searchParams.get('detail');
  const debouncedKeyword = useDebounce(filters.keyword, 300);

  const params: Record<string, string> = { sort: filters.sort, limit: '500' };
  if (filters.status) params.status = filters.status;
  if (filters.relevance) params.relevance = filters.relevance;
  if (filters.source) params.source = filters.source;
  if (debouncedKeyword) params.keyword = debouncedKeyword;

  const { data, loading, error } = useFetch(
    () => fetchPapers(reviewId, params),
    [reviewId, filters.status, filters.relevance, filters.source, debouncedKeyword, filters.sort]
  );

  const setFilter = (key: string, value: string) =>
    setFilters((f) => ({ ...f, [key]: value }));

  return (
    <div>
      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-ink-muted)]" />
          <input
            type="text"
            placeholder="Search papers..."
            value={filters.keyword}
            onChange={(e) => setFilter('keyword', e.target.value)}
            aria-label="Search papers by title or abstract"
            className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-paper-card)] focus:outline-none focus:border-[var(--color-border-strong)]"
          />
        </div>

        <select
          value={filters.status}
          onChange={(e) => setFilter('status', e.target.value)}
          aria-label="Filter by status"
          className="text-sm px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-paper-card)] text-[var(--color-ink-secondary)]"
        >
          <option value="">All statuses</option>
          {STATUS_OPTIONS.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
          ))}
        </select>

        <select
          value={filters.relevance}
          onChange={(e) => setFilter('relevance', e.target.value)}
          aria-label="Filter by relevance"
          className="text-sm px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-paper-card)] text-[var(--color-ink-secondary)]"
        >
          <option value="">All relevance</option>
          {RELEVANCE_OPTIONS.filter(Boolean).map((r) => (
            <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>
          ))}
        </select>

        <select
          value={filters.source}
          onChange={(e) => setFilter('source', e.target.value)}
          aria-label="Filter by source"
          className="text-sm px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-paper-card)] text-[var(--color-ink-secondary)]"
        >
          <option value="">All sources</option>
          {SOURCE_OPTIONS.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
          ))}
        </select>

        <select
          value={filters.sort}
          onChange={(e) => setFilter('sort', e.target.value)}
          aria-label="Sort papers"
          className="text-sm px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-paper-card)] text-[var(--color-ink-secondary)]"
        >
          {SORT_OPTIONS.map(({ value, label }) => (
            <option key={value} value={value}>Sort: {label}</option>
          ))}
        </select>
      </div>

      {/* Stats Bar */}
      {data && (
        <div className="flex items-center gap-4 mb-3 text-xs text-[var(--color-ink-muted)]">
          <span><strong className="text-[var(--color-ink)]">{data.total}</strong> papers</span>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorMessage message={error} />
      ) : !data || data.papers.length === 0 ? (
        <EmptyState title="No papers found" description="Try adjusting your filters." />
      ) : (
        <div className="bg-[var(--color-paper-card)] rounded-xl border border-[var(--color-border)] overflow-x-auto">
          {/* Table header */}
          <div
            className="px-4 py-2.5 grid items-center text-xs text-[var(--color-ink-muted)] uppercase tracking-wide font-medium border-b border-[var(--color-border)] bg-[var(--color-paper-warm)]"
            style={{ gridTemplateColumns: '20px 1fr 52px 64px 88px 88px 100px 20px', columnGap: '8px' }}
          >
            <span />
            <span>Title</span>
            <span className="text-right">Year</span>
            <span className="text-right">Cited</span>
            <span>Relevance</span>
            <span>Status</span>
            <span>Source</span>
            <span />
          </div>

          {(() => {
            const titles: Record<string, string> = {};
            for (const p of data.papers) titles[p.id] = p.title;
            return data.papers.map((paper) => (
              <PaperRow
                key={paper.id}
                paper={paper}
                expanded={expandedId === paper.id}
                onToggle={() => setExpandedId(expandedId === paper.id ? null : paper.id)}
                onOpenDetail={() => setSearchParams({ detail: paper.id })}
                paperTitles={titles}
              />
            ));
          })()}
        </div>
      )}

      {/* Detail Panel */}
      {detailId && (
        <PaperDetailPanel
          reviewId={reviewId}
          paperId={detailId}
          onClose={() => setSearchParams({})}
        />
      )}
    </div>
  );
}
