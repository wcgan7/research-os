# Execution Workspace Plan

## Goal

Build a workspace-centric research system where:

- each research direction gets one workspace
- the workspace is self-contained: database, code, artifacts, logs all live together
- inside the workspace, the agent may clone repos, create projects, patch code, run experiments
- structured records capture what matters and are queryable
- lit review, baseline reproduction, and experimentation are phases within one workspace

This extends the same philosophy as the literature review module:

- a main agent drives the work
- the system stores typed records so the work is queryable
- the frontend and API read structured state, not just logs

---

## Core Design

- The research-os repo is the control plane (code, tools, API, UI)
- Each research direction gets one workspace with its own database
- A lightweight global index tracks which workspaces exist
- Lit review is a phase within a workspace, not a separate entity
- The workspace root is not itself a git repo; repos inside it may have their own git history
- The agent decides what is worth tracking, but must record important states

---

## Workspace Model

One research direction = one workspace = one database.

```text
~/.research-os/
  index.sqlite3                         # global: workspace list, names, status
  workspaces/{workspace_id}/
    db.sqlite3                          # all records for this research direction
    logs/                               # agent run logs
    repos/                              # cloned upstream repos
      baseline-self-rag/
      baseline-graphrag/
    projects/                           # agent-created code
      prototype-a/
    artifacts/                          # outputs, checkpoints, plots
```

Important distinctions:

- the workspace root is the bounded filesystem sandbox for the agent
- the workspace root is not a single code repo
- each meaningful code project inside it may have its own `.git`

This allows:

- cloning upstream repos
- creating new repos from scratch
- deriving prototypes from reproduced baselines
- keeping large outputs and transient files outside code repos

---

## Workspace Lifecycle

1. **Provision** -- user creates a workspace through the UI with a name, topic, and objective
2. **Literature review** -- agent surveys the field, stores papers/assessments/notes/reports in workspace db
3. **Baseline reproduction** -- agent clones repos, patches code, reproduces key results
4. **Experimentation** -- agent (or mastermind) forms hypotheses, runs experiments against baselines
5. **Archive** -- workspace is self-contained, can be moved/archived/deleted as a unit

The mastermind, when it exists, operates within a workspace context. It reads the workspace's database to understand what's been done and decides what to do next.

---

## Relationship Between Workspace and Lit Review

The current `LiteratureReview` record (topic, objective, status) becomes workspace metadata. There is no separate `LiteratureReview` entity -- the workspace *is* the research direction, and lit review is one of the things that happens in it.

What this means in practice:

- `review_id` foreign keys on Paper, Assessment, etc. become `workspace_id`
- The workspace record carries the topic and objective
- Papers, assessments, notes, coverage, reports all belong directly to the workspace
- Lit review agent runs are logged under `{workspace}/logs/`

This is a refactor of the current storage model but not a rewrite -- the Store class and record models stay the same, only the database path changes from one global file to per-workspace.

---

## Git Provenance Policy

Git tracks specific repos/projects inside the workspace, not the whole workspace as one giant repo.

Default policy:

- cloned repo: preserve existing git repo and record upstream + commit
- scratch project: initialize a local git repo if the agent starts editing code meaningfully
- artifacts/logs/checkpoints: remain outside git

Minimum provenance fields to record:

- repo URL, if any
- base commit
- current commit
- dirty/clean status
- modification summary

---

## Data Model

### Global Index (`~/.research-os/index.sqlite3`)

#### Workspace (global)

- `id`
- `name`
- `topic`
- `objective`
- `root_path`
- `status` (active, paused, completed, archived)
- `created_at`
- `updated_at`

Lightweight. Just enough to list workspaces and find their paths.

### Per-Workspace Database (`{workspace}/db.sqlite3`)

#### Literature review records (already exist, migrated)

- `Paper` -- discovered papers with metadata + extracted text
- `Assessment` -- relevance analysis per paper
- `SearchRecord` -- what searches were performed and why
- `CoverageAssessment` -- gap analysis and next actions
- `ReviewNote` -- structured notes
- `ReviewReport` -- synthesized report
- `CapabilityRequest` -- feature requests from agent

These keep their current schema. `review_id` becomes `workspace_id`.

#### Baseline and execution records (new)

##### Baseline

- `name`
- `description`
- `paper_ids` (list -- links to papers from lit review)
- `source_urls`
- `status`
- `notes`

Represents prior work or an existing method worth reproducing or comparing against.

##### Implementation

- `baseline_id` (optional -- null for scratch projects)
- `name`
- `path` (relative to workspace root)
- `source_type` (repo | local | scratch)
- `repo_url`
- `base_commit`
- `current_commit`
- `is_dirty`
- `modification_summary`
- `status`

The key provenance bridge between "paper/baseline" and "what code the agent actually ran."

##### Run

- `implementation_id`
- `kind` (reproduction | baseline_eval | prototype | ablation | benchmark)
- `command`
- `cwd`
- `status`
- `pid`
- `started_at`
- `completed_at`
- `exit_code`
- `stdout_path`
- `stderr_path`

One concrete execution attempt.

##### Artifact

- `run_id`
- `kind`
- `path` (relative to workspace root)
- `description`
- `metadata_json`

Outputs: plots, result files, checkpoints, tables, patches, reports.

##### Result

- `run_id`
- `summary`
- `metrics_json`
- `success`
- `notes`

Interpreted outcome of a run.

##### Decision

- `subject_type`
- `subject_id`
- `decision`
- `rationale`
- `evidence_ids`

Durable conclusions: "baseline reproduced", "repo unusable", "prototype worth extending."

---

## Workspace Management

Config:

- `RESEARCH_OS_WORKSPACES=~/.research-os/workspaces` (default)

Helpers:

- create workspace directory + subdirectories + db
- register in global index
- open workspace database by ID
- validate paths stay under workspace root

---

## Agent Tools

Expose smaller primitives rather than one giant `run_experiment` tool.

### Workspace tools

- `create_baseline`
- `register_implementation`
- `update_implementation_state`
- `snapshot_implementation` (record git state)

### Execution tools

- `start_run`
- `stop_run`
- `get_run_status`
- `record_result`
- `attach_artifact`
- `record_decision`

### Query tools

- `query_store` (already exists, works across all record types)

The agent has full operational freedom in the workspace -- clone repos, patch code, write scripts, install deps, adapt broken baselines. The system only requires that important states are recorded through the tools above.

---

## Runner

Implement a minimal execution runner that can:

- start a subprocess in a selected cwd
- capture stdout/stderr to files
- record pid and lifecycle metadata
- finalize run metadata in finally
- support explicit stop/termination

Follow the same hardening lessons from the lit review launcher (PID tracking, finally blocks, completion metadata).

Module: `src/research_os/execution/runner.py`

---

## Agent Prompt

Draft a baseline agent system prompt covering:

- strategy: inspect lit review results, pick high-value papers with code, reproduce systematically
- when to give up on a broken repo vs. adapt it
- how to decide a reproduction is "good enough"
- recording discipline: every run gets a result, every significant finding gets a decision

This is as important as the record types -- the lit review module's success comes largely from its well-crafted prompt.

---

## Frontend v0

Minimal execution workspace UI for state inspection:

- workspace list/detail (extends current dashboard)
- baselines list/detail
- implementations in workspace
- runs table with log viewer
- results and decisions

Do not build yet:

- graph view
- mastermind UI
- full branch orchestration

---

## Migration Path

To move from current global-database lit review to per-workspace model:

1. Build workspace provisioning (create workspace, create per-workspace db)
2. Update Store/API to accept a workspace path instead of global db path
3. Migrate existing reviews: create a workspace per review, copy records, update paths
4. Update frontend to navigate workspaces first, then into review/baseline/experiment views
5. Deprecate global db

This can be done incrementally. The lit review module continues working on the global db while the new workspace model is built alongside it.

---

## First Milestone

Implement only this first slice:

1. Workspace provisioning (directory + db + global index)
2. `Baseline`, `Implementation`, `Run`, `Result`, `Decision` record types
3. Workspace management helpers
4. Agent tools for baseline/execution recording
5. Runner (subprocess lifecycle management)
6. Baseline agent prompt
7. Minimal frontend: workspace detail, runs, results
8. Smoke tests

This is enough to support:

- create workspace
- clone repo
- patch code
- run baseline
- record outcome

Without taking on mastermind logic or lit review migration.

Lit review migration happens as a follow-up milestone once the workspace model is proven.
