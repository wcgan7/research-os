"""Record types for all structured data in Research OS."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import ClassVar


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


@dataclass
class BaseRecord:
    """Base for all persisted records."""

    __table_name__: ClassVar[str] = ""

    id: str = field(default_factory=_uuid)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)


@dataclass
class LiteratureReview(BaseRecord):
    __table_name__: ClassVar[str] = "literature_reviews"

    topic: str = ""
    objective: str = ""
    status: str = "active"  # active | paused | completed
    seed_papers: list[str] = field(default_factory=list)


@dataclass
class Paper(BaseRecord):
    __table_name__: ClassVar[str] = "papers"

    review_id: str = ""
    source: str = ""  # semantic_scholar | arxiv | openalex | web_search | manual
    external_id: str = ""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    abstract: str | None = None
    url: str | None = None
    doi: str | None = None
    citation_count: int | None = None
    # discovered | seed | reviewed | relevant | not_relevant | uncertain | deferred
    status: str = "discovered"
    code_url: str | None = None  # URL to open-source implementation
    datasets: list[str] = field(default_factory=list)  # benchmark datasets used


@dataclass
class Assessment(BaseRecord):
    __table_name__: ClassVar[str] = "assessments"

    review_id: str = ""
    paper_id: str = ""
    relevance_score: int = 0  # 1-5
    rationale: str = ""
    key_claims: list[str] = field(default_factory=list)
    methodology_notes: str | None = None
    connections: list[str] = field(default_factory=list)


@dataclass
class SearchRecord(BaseRecord):
    __table_name__: ClassVar[str] = "search_records"

    review_id: str = ""
    query: str = ""
    source: str = ""
    rationale: str = ""
    result_count: int = 0
    paper_ids: list[str] = field(default_factory=list)


@dataclass
class CoverageAssessment(BaseRecord):
    __table_name__: ClassVar[str] = "coverage_assessments"

    review_id: str = ""
    areas_covered: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    confidence: float = 0.0
    next_actions: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class ReviewNote(BaseRecord):
    __table_name__: ClassVar[str] = "review_notes"

    review_id: str = ""
    # question | gap | contradiction | baseline_candidate | tool_wish |
    # strategy_note | observation | assumption | next_step
    kind: str = ""
    content: str = ""
    paper_ids: list[str] = field(default_factory=list)
    priority: int | None = None


@dataclass
class CapabilityRequest(BaseRecord):
    __table_name__: ClassVar[str] = "capability_requests"

    review_id: str = ""
    name: str = ""
    rationale: str = ""
    example_usage: str = ""


@dataclass
class SotaSummary(BaseRecord):
    """State-of-the-art summary produced at the end of a literature review."""
    __table_name__: ClassVar[str] = "sota_summaries"

    review_id: str = ""
    # Structured SOTA findings
    best_methods: list[str] = field(default_factory=list)  # ranked methods with metrics
    key_benchmarks: list[str] = field(default_factory=list)  # datasets/benchmarks used in the field
    open_source_implementations: list[str] = field(default_factory=list)  # available code repos
    open_problems: list[str] = field(default_factory=list)  # unsolved challenges
    trends: list[str] = field(default_factory=list)  # recent trends/directions
    summary: str = ""  # prose summary of the state of the art
    paper_ids: list[str] = field(default_factory=list)  # papers supporting this summary


# Registry of all record types for schema init
ALL_RECORD_TYPES: list[type[BaseRecord]] = [
    LiteratureReview,
    Paper,
    Assessment,
    SearchRecord,
    CoverageAssessment,
    ReviewNote,
    CapabilityRequest,
    SotaSummary,
]
