import type {
  Review,
  Paper,
  PaperDetail,
  CoverageAssessment,
  ReviewNote,
  SearchRecord,
  ActivityEvent,
  CapabilityRequest,
  Resource,
  LogRun,
  ReviewReport,
  SotaSummary,
} from './types';

const BASE = '/api';

async function get<T>(path: string): Promise<T> {
  const resp = await fetch(`${BASE}${path}`);
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      if (body.detail) detail = body.detail;
    } catch { /* non-JSON error response */ }
    throw new Error(`${resp.status}: ${detail}`);
  }
  return await resp.json();
}

export async function fetchReviews(): Promise<Review[]> {
  return get('/reviews');
}

export async function fetchReview(id: string): Promise<Review> {
  return get(`/reviews/${id}`);
}

export async function fetchPapers(
  reviewId: string,
  params?: Record<string, string>
): Promise<{ total: number; papers: Paper[] }> {
  const qs = params ? '?' + new URLSearchParams(params).toString() : '';
  return get(`/reviews/${reviewId}/papers${qs}`);
}

export async function fetchPaperDetail(
  reviewId: string,
  paperId: string
): Promise<PaperDetail> {
  return get(`/reviews/${reviewId}/papers/${paperId}`);
}

export async function fetchReport(
  reviewId: string
): Promise<{ report: ReviewReport | null; sota_summary: SotaSummary | null }> {
  return get(`/reviews/${reviewId}/report`);
}

export async function fetchCoverage(reviewId: string): Promise<CoverageAssessment[]> {
  return get(`/reviews/${reviewId}/coverage`);
}

export async function fetchNotes(
  reviewId: string,
  kind?: string
): Promise<ReviewNote[]> {
  const qs = kind ? `?kind=${kind}` : '';
  return get(`/reviews/${reviewId}/notes${qs}`);
}

export async function fetchSearches(reviewId: string): Promise<SearchRecord[]> {
  return get(`/reviews/${reviewId}/searches`);
}

export async function fetchResources(
  reviewId: string
): Promise<Record<string, Resource[]>> {
  return get(`/reviews/${reviewId}/resources`);
}

export async function fetchActivity(reviewId: string): Promise<ActivityEvent[]> {
  return get(`/reviews/${reviewId}/activity`);
}

export async function fetchCapabilityRequests(
  reviewId: string
): Promise<CapabilityRequest[]> {
  return get(`/reviews/${reviewId}/capability-requests`);
}

export async function fetchLogs(
  reviewId: string
): Promise<{ runs: LogRun[] }> {
  return get(`/reviews/${reviewId}/logs`);
}

export async function fetchLogStdout(
  reviewId: string,
  runDir: string,
  tail = 500
): Promise<{ lines: string[]; total_lines: number }> {
  return get(`/reviews/${reviewId}/logs/${runDir}/stdout?tail=${tail}`);
}

export interface ParsedLogEvent {
  type: 'system' | 'text' | 'tool_call' | 'tool_result' | 'tool_error' | 'result';
  content?: string;
  tool?: string;
  description?: string;
  tool_id?: string;
}

export interface ParsedLogResponse {
  events: ParsedLogEvent[];
  stats: {
    total_events: number;
    tool_calls: number;
    errors: number;
    total_input_tokens: number;
    total_output_tokens: number;
  };
}

// ── Actions ──────────────────────────────────────────────────────

async function post<T>(path: string, body: unknown): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const b = await resp.json();
      if (b.detail) detail = b.detail;
    } catch { /* non-JSON */ }
    throw new Error(`${resp.status}: ${detail}`);
  }
  return await resp.json();
}

export async function createReview(
  topic: string,
  objective: string,
  seedUrls?: string[],
): Promise<{ review_id: string; status: string }> {
  return post('/reviews', { topic, objective, seed_urls: seedUrls || [] });
}

export async function continueReview(
  reviewId: string,
  instructions?: string,
): Promise<{ review_id: string; status: string }> {
  return post(`/reviews/${reviewId}/continue`, instructions ? { instructions } : {});
}

export async function stopReview(
  reviewId: string,
): Promise<{ review_id: string; status: string }> {
  return post(`/reviews/${reviewId}/stop`, {});
}

export async function steerReview(
  reviewId: string,
  message: string,
): Promise<{ review_id: string; status: string; timestamp: string }> {
  return post(`/reviews/${reviewId}/steer`, { message });
}

export async function fetchSteering(
  reviewId: string,
): Promise<{ pending: string | null }> {
  return get(`/reviews/${reviewId}/steering`);
}

export async function seedPaper(
  reviewId: string,
  urlOrId: string,
): Promise<{ paper_id: string; title: string }> {
  return post(`/reviews/${reviewId}/seed`, { url_or_id: urlOrId });
}

export async function fetchPaperFullText(
  reviewId: string,
  paperId: string,
): Promise<{ paper_id: string; title: string; source?: string; chars?: number }> {
  return post(`/reviews/${reviewId}/papers/${paperId}/fetch-text`, {});
}

// ── Logs ──────────────────────────────────────────────────────────

export async function fetchLogParsed(
  reviewId: string,
  runDir: string,
): Promise<ParsedLogResponse> {
  return get(`/reviews/${reviewId}/logs/${runDir}/parsed`);
}
