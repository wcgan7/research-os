export interface Review {
  id: string;
  topic: string;
  objective: string;
  status: string;
  seed_papers: string[];
  created_at: string;
  updated_at: string;
  paper_count?: number;
  assessment_count?: number;
  has_report?: boolean;
  paper_status_counts?: Record<string, number>;
  is_running?: boolean;
  stats?: ReviewStats;
}

export interface ReviewStats {
  paper_count: number;
  assessment_count: number;
  search_count: number;
  note_count: number;
  coverage_count: number;
  has_report: boolean;
  papers_with_full_text: number;
  papers_with_resources: number;
  paper_status_counts: Record<string, number>;
  relevance_counts: Record<string, number>;
  latest_confidence: number | null;
}

export interface Paper {
  id: string;
  title: string;
  authors: string[];
  year: number | null;
  abstract: string | null;
  full_text: string | null;
  full_text_source: string | null;
  url: string | null;
  doi: string | null;
  citation_count: number | null;
  source: string;
  external_id: string;
  status: string;
  resources: string[];
  review_id: string;
  created_at: string;
  assessment?: Assessment | null;
}

export interface Assessment {
  id: string;
  paper_id: string;
  relevance: string;
  rationale: string;
  key_claims: string[];
  methodology_notes: string | null;
  connections: string[];
  created_at: string;
}

export interface SearchRecord {
  id: string;
  query: string;
  source: string;
  rationale: string;
  result_count: number;
  paper_ids: string[];
  created_at: string;
}

export interface CoverageAssessment {
  id: string;
  areas_covered: string[];
  gaps: string[];
  confidence: number;
  next_actions: string[];
  summary: string;
  created_at: string;
}

export interface ReviewNote {
  id: string;
  kind: string;
  content: string;
  paper_ids: string[];
  priority: number | null;
  created_at: string;
}

export interface ReviewReport {
  id: string;
  landscape: string;
  methods: string;
  sota: string;
  resources: string;
  gaps: string;
  trends: string;
  conclusions: string;
  paper_ids: string[];
  created_at: string;
}

export interface SotaSummary {
  id: string;
  best_methods: string[];
  key_benchmarks: string[];
  open_source_implementations: string[];
  open_problems: string[];
  trends: string[];
  summary: string;
  paper_ids: string[];
  created_at: string;
}

export interface CapabilityRequest {
  id: string;
  name: string;
  rationale: string;
  example_usage: string;
  created_at: string;
}

export interface Resource {
  type: string;
  url: string;
  description?: string;
  paper_id: string;
  paper_title: string;
  paper_year: number | null;
}

export interface ActivityEvent {
  type: string;
  timestamp: string;
  summary: string;
  data: Record<string, unknown>;
}

export interface PaperDetail extends Paper {
  notes: ReviewNote[];
  searches: SearchRecord[];
  connected_papers: { id: string; title: string }[];
}

export interface LogRun {
  dir: string;
  meta: Record<string, unknown> | null;
  stdout_size: number;
  stdout_path: string | null;
}
