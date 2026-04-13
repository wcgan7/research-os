import { useState, useEffect, useRef } from 'react';
import {
  Search, CheckCircle, Shield, StickyNote, FileText, ChevronDown, ChevronRight, Terminal, Lightbulb,
  Wrench, MessageSquare, AlertCircle, Play, Cpu, ArrowRight,
} from 'lucide-react';
import { fetchActivity, fetchSearches, fetchCapabilityRequests, fetchLogs, fetchLogStdout, fetchLogParsed } from '../../api/client';
import type { ParsedLogEvent, ParsedLogResponse } from '../../api/client';
import { useFetch, usePolling } from '../../api/hooks';
import StatCard from '../../components/StatCard';
import PaperChip from '../../components/PaperChip';
import SourceIcon from '../../components/SourceIcon';
import EmptyState from '../../components/EmptyState';
import ErrorMessage from '../../components/ErrorMessage';
import Loading from '../../components/Loading';
import type { ActivityEvent, SearchRecord } from '../../api/types';

const EVENT_ICONS: Record<string, typeof Search> = {
  search: Search,
  assessment: CheckCircle,
  coverage: Shield,
  note: StickyNote,
  report: FileText,
};

function SearchHistoryTable({ reviewId, isRunning }: { reviewId: string; isRunning: boolean }) {
  const { data: initialData, loading, error } = useFetch(() => fetchSearches(reviewId), [reviewId]);
  const { data: polledData } = usePolling(() => fetchSearches(reviewId), 5000, isRunning, [reviewId]);
  const data = polledData || initialData;
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (loading) return <Loading />;
  if (error) return <ErrorMessage message={error} />;
  if (!data || data.length === 0) return null;

  return (
    <div className="bg-[var(--color-paper-card)] rounded-xl border border-[var(--color-border)] overflow-hidden">
      <div className="px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-paper-warm)]">
        <h4 className="text-sm font-medium text-[var(--color-ink)]">Search History ({data.length})</h4>
      </div>
      {data.map((s: SearchRecord) => (
        <div key={s.id} className="border-b border-[var(--color-border)] last:border-b-0">
          <button
            onClick={() => setExpandedId(expandedId === s.id ? null : s.id)}
            className="w-full text-left px-4 py-2.5 flex items-center gap-3 hover:bg-[var(--color-paper-warm)] transition-colors text-sm"
          >
            <span className="text-[var(--color-ink-muted)]">
              {expandedId === s.id ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
            </span>
            <SourceIcon source={s.source} />
            <span className="flex-1 text-[var(--color-ink)] truncate">"{s.query}"</span>
            <span className="text-xs text-[var(--color-ink-muted)] tabular-nums">{s.result_count} results</span>
            <span className="text-xs text-[var(--color-ink-muted)]">
              {new Date(s.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
            </span>
          </button>
          {expandedId === s.id && (
            <div className="px-4 pb-3 pl-10 space-y-2 bg-[var(--color-paper-warm)]">
              {s.rationale && (
                <div>
                  <span className="text-xs font-medium text-[var(--color-ink-muted)] uppercase tracking-wide">Rationale</span>
                  <p className="text-sm text-[var(--color-ink-secondary)] mt-0.5">{s.rationale}</p>
                </div>
              )}
              {s.paper_ids?.length > 0 && (
                <div>
                  <span className="text-xs font-medium text-[var(--color-ink-muted)] uppercase tracking-wide">Papers Found</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {s.paper_ids.slice(0, 10).map((pid) => <PaperChip key={pid} paperId={pid} />)}
                    {s.paper_ids.length > 10 && (
                      <span className="text-xs text-[var(--color-ink-muted)] self-center">+{s.paper_ids.length - 10} more</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

const LOG_EVENT_ICONS: Record<string, typeof Search> = {
  system: Cpu,
  text: MessageSquare,
  tool_call: Wrench,
  tool_result: ArrowRight,
  tool_error: AlertCircle,
  result: Play,
};

const LOG_EVENT_COLORS: Record<string, string> = {
  system: 'text-blue-400',
  text: 'text-gray-300',
  tool_call: 'text-amber-400',
  tool_result: 'text-gray-500',
  tool_error: 'text-red-400',
  result: 'text-emerald-400',
};

function ParsedLogView({ events, stats, scrollRef }: ParsedLogResponse & { scrollRef?: React.RefObject<HTMLDivElement | null> }) {
  return (
    <div className="border-t border-[var(--color-border)]">
      {/* Stats bar */}
      <div className="px-4 py-2 bg-[#1e1e1e] border-b border-[#333] flex items-center gap-4 text-xs text-gray-400">
        <span>{stats.tool_calls} tool calls</span>
        {stats.errors > 0 && <span className="text-red-400">{stats.errors} errors</span>}
        {stats.total_input_tokens > 0 && (
          <span>~{Math.round((stats.total_input_tokens + stats.total_output_tokens) / 1000)}k tokens</span>
        )}
      </div>
      {/* Event list */}
      <div ref={scrollRef} className="bg-[#1a1a1a] max-h-[500px] overflow-auto">
        {events.map((event: ParsedLogEvent, i: number) => {
          const Icon = LOG_EVENT_ICONS[event.type] || MessageSquare;
          const color = LOG_EVENT_COLORS[event.type] || 'text-gray-400';

          if (event.type === 'tool_call') {
            return (
              <div key={i} className="px-4 py-1.5 flex items-start gap-2.5 hover:bg-[#222] border-b border-[#2a2a2a]">
                <Wrench size={13} className={`mt-0.5 shrink-0 ${color}`} aria-hidden="true" />
                <div className="min-w-0">
                  <span className="text-xs font-mono font-medium text-amber-300">{event.tool}</span>
                  {event.description && (
                    <span className="text-xs text-gray-400 ml-2 truncate">{event.description}</span>
                  )}
                </div>
              </div>
            );
          }

          if (event.type === 'tool_result') {
            return (
              <div key={i} className="px-4 py-1 pl-9 border-b border-[#2a2a2a]">
                <span className="text-xs text-gray-500 font-mono">{event.content}</span>
              </div>
            );
          }

          if (event.type === 'tool_error') {
            return (
              <div key={i} className="px-4 py-1.5 flex items-start gap-2.5 bg-red-950/30 border-b border-[#2a2a2a]">
                <AlertCircle size={13} className="mt-0.5 shrink-0 text-red-400" aria-hidden="true" />
                <span className="text-xs text-red-300 font-mono">{event.content}</span>
              </div>
            );
          }

          if (event.type === 'text') {
            return (
              <div key={i} className="px-4 py-2 flex items-start gap-2.5 border-b border-[#2a2a2a]">
                <MessageSquare size={13} className="mt-0.5 shrink-0 text-gray-400" aria-hidden="true" />
                <span className="text-sm text-gray-200">{event.content}</span>
              </div>
            );
          }

          return (
            <div key={i} className="px-4 py-1.5 flex items-start gap-2.5 border-b border-[#2a2a2a]">
              <Icon size={13} className={`mt-0.5 shrink-0 ${color}`} aria-hidden="true" />
              <span className="text-xs text-gray-300">{event.content}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function RawLogView({ lines, scrollRef }: { lines: string[]; scrollRef?: React.RefObject<HTMLDivElement | null> }) {
  return (
    <div ref={scrollRef} className="border-t border-[var(--color-border)] bg-[#1a1a1a] text-[#e5e5e5] p-4 max-h-[500px] overflow-auto">
      <pre className="text-xs font-mono leading-relaxed whitespace-pre-wrap">
        {lines.join('\n')}
      </pre>
    </div>
  );
}

function LogViewer({ reviewId, isRunning }: { reviewId: string; isRunning: boolean }) {
  const { data: initialLogs, error: logsError } = useFetch(() => fetchLogs(reviewId), [reviewId]);
  const { data: polledLogs } = usePolling(() => fetchLogs(reviewId), 5000, isRunning, [reviewId]);
  const data = polledLogs || initialLogs;
  const [expanded, setExpanded] = useState(false);
  const [mode, setMode] = useState<'parsed' | 'raw'>('parsed');
  const [parsedData, setParsedData] = useState<ParsedLogResponse | null>(null);
  const [rawLines, setRawLines] = useState<string[] | null>(null);
  const [loadingLog, setLoadingLog] = useState(false);
  const [logError, setLogError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const latestRun = data?.runs?.[0];

  const fetchLogs_ = async () => {
    if (!latestRun) return;
    const [parsedResult, rawResult] = await Promise.allSettled([
      fetchLogParsed(reviewId, latestRun.dir),
      fetchLogStdout(reviewId, latestRun.dir, 500),
    ]);

    let nextError: string | null = null;

    if (parsedResult.status === 'fulfilled') {
      setParsedData(parsedResult.value);
    } else if (!parsedData) {
      nextError = parsedResult.reason instanceof Error ? parsedResult.reason.message : 'Failed to load parsed log';
    }

    if (rawResult.status === 'fulfilled') {
      setRawLines(rawResult.value.lines);
    } else if (!rawLines) {
      nextError = rawResult.reason instanceof Error ? rawResult.reason.message : 'Failed to load raw log';
    }

    if (parsedResult.status === 'rejected' && rawResult.status === 'rejected') {
      nextError = parsedResult.reason instanceof Error ? parsedResult.reason.message : 'Failed to load log';
    }

    setLogError(nextError);
  };

  const loadLog = async () => {
    if (!latestRun) return;
    if (parsedData || rawLines) { setExpanded(!expanded); return; }
    setLoadingLog(true);
    setLogError(null);
    await fetchLogs_();
    setExpanded(true);
    setLoadingLog(false);
  };

  // Poll logs when running and expanded
  useEffect(() => {
    if (!isRunning || !expanded || !latestRun) return;
    const id = setInterval(async () => {
      await fetchLogs_();
      // Auto-scroll to bottom
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    }, 3000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isRunning, expanded, reviewId, latestRun?.dir]);

  // Auto-expand when agent starts running
  useEffect(() => {
    if (isRunning && !expanded && !parsedData && latestRun) {
      setLoadingLog(true);
      setLogError(null);
      fetchLogs_().then(() => {
        setExpanded(true);
        setLoadingLog(false);
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isRunning]);

  if (logsError) return <ErrorMessage message={logsError} />;
  if (!latestRun) return null;

  return (
    <div className="bg-[var(--color-paper-card)] rounded-xl border border-[var(--color-border)] overflow-hidden">
      <div className="flex items-center">
        <button
          onClick={loadLog}
          className="flex-1 text-left px-4 py-3 flex items-center gap-2 hover:bg-[var(--color-paper-warm)] transition-colors"
        >
          <Terminal size={15} className="text-[var(--color-ink-muted)]" aria-hidden="true" />
          <span className="text-sm font-medium text-[var(--color-ink)]">Agent Log</span>
          {isRunning && (
            <span className="flex items-center gap-1 text-xs text-[var(--color-active)] font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-active)] animate-pulse" />
              Live
            </span>
          )}
          <span className="text-xs text-[var(--color-ink-muted)] ml-auto">
            {latestRun.meta?.completed_at ? 'Completed' : isRunning ? '' : 'Stopped'}
            {latestRun.stdout_size > 0 && ` (${Math.round(latestRun.stdout_size / 1024)}KB)`}
          </span>
          {expanded ? <ChevronDown size={14} aria-hidden="true" /> : <ChevronRight size={14} aria-hidden="true" />}
        </button>
        {expanded && (
          <div className="flex items-center gap-1 pr-3">
            <button
              onClick={() => setMode('parsed')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                mode === 'parsed'
                  ? 'bg-[var(--color-ink)] text-white'
                  : 'text-[var(--color-ink-muted)] hover:bg-[var(--color-paper-warm)]'
              }`}
            >
              Parsed
            </button>
            <button
              onClick={() => setMode('raw')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                mode === 'raw'
                  ? 'bg-[var(--color-ink)] text-white'
                  : 'text-[var(--color-ink-muted)] hover:bg-[var(--color-paper-warm)]'
              }`}
            >
              Raw
            </button>
          </div>
        )}
      </div>
      {loadingLog && <Loading />}
      {logError && <div className="px-4 pb-3"><ErrorMessage message={logError} /></div>}
      {expanded && mode === 'parsed' && parsedData && (
        <ParsedLogView events={parsedData.events} stats={parsedData.stats} scrollRef={scrollRef} />
      )}
      {expanded && mode === 'raw' && rawLines && (
        <RawLogView lines={rawLines} scrollRef={scrollRef} />
      )}
    </div>
  );
}

function CapabilityRequestsList({ reviewId, isRunning }: { reviewId: string; isRunning: boolean }) {
  const { data: initialData, error } = useFetch(() => fetchCapabilityRequests(reviewId), [reviewId]);
  const { data: polledData } = usePolling(() => fetchCapabilityRequests(reviewId), 5000, isRunning, [reviewId]);
  const data = polledData || initialData;
  if (error) return <ErrorMessage message={error} />;
  if (!data?.length) return null;

  return (
    <div className="bg-[var(--color-paper-card)] rounded-xl border border-[var(--color-border)] p-5">
      <h4 className="text-sm font-medium text-[var(--color-ink)] mb-3 flex items-center gap-2">
        <Lightbulb size={15} /> Capability Requests
      </h4>
      <div className="space-y-3">
        {data.map((req) => (
          <div key={req.id} className="text-sm">
            <div className="font-medium text-[var(--color-ink)]">{req.name}</div>
            <p className="text-[var(--color-ink-secondary)] mt-0.5">{req.rationale}</p>
            {req.example_usage && (
              <p className="text-xs text-[var(--color-ink-muted)] mt-1 font-mono bg-[var(--color-paper-warm)] px-2 py-1 rounded">
                {req.example_usage}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ActivityTab({ reviewId, isRunning = false }: { reviewId: string; isRunning?: boolean }) {
  const { data: initialEvents, loading, error } = useFetch(() => fetchActivity(reviewId), [reviewId]);
  const { data: polledEvents } = usePolling(() => fetchActivity(reviewId), 5000, isRunning, [reviewId]);
  const events = polledEvents || initialEvents;

  if (loading) return <Loading />;
  if (error) return <ErrorMessage message={error} />;

  const counts = {
    search: 0,
    assessment: 0,
    coverage: 0,
    note: 0,
    report: 0,
  };
  events?.forEach((e: ActivityEvent) => {
    if (e.type in counts) counts[e.type as keyof typeof counts]++;
  });

  const hasEvents = events && events.length > 0;

  return (
    <div className="space-y-6">
      {/* Stats — only show when there's data */}
      {hasEvents && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard label="Searches" value={counts.search} icon={Search} />
          <StatCard label="Assessments" value={counts.assessment} icon={CheckCircle} />
          <StatCard label="Notes" value={counts.note} icon={StickyNote} />
          <StatCard label="Reports" value={counts.report} icon={FileText} />
        </div>
      )}

      {/* Search History */}
      <SearchHistoryTable reviewId={reviewId} isRunning={isRunning} />

      {/* Activity Timeline */}
      {events && events.length > 0 && (
        <div className="bg-[var(--color-paper-card)] rounded-xl border border-[var(--color-border)] p-5">
          <h4 className="text-sm font-medium text-[var(--color-ink)] mb-4">Activity Timeline</h4>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {events.map((e: ActivityEvent, i: number) => {
              const Icon = EVENT_ICONS[e.type] || Search;
              return (
                <div key={i} className="flex items-start gap-3 text-sm">
                  <Icon size={14} className="mt-0.5 text-[var(--color-ink-muted)] shrink-0" />
                  <span className="flex-1 text-[var(--color-ink-secondary)]">{e.summary}</span>
                  <span className="text-xs text-[var(--color-ink-muted)] shrink-0 tabular-nums">
                    {new Date(e.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Log Viewer */}
      <LogViewer reviewId={reviewId} isRunning={isRunning} />

      {/* Capability Requests */}
      <CapabilityRequestsList reviewId={reviewId} isRunning={isRunning} />

      {!hasEvents && (
        <EmptyState title="No activity" description="No agent activity recorded yet." />
      )}
    </div>
  );
}
