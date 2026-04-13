# Execution Workspace Plan

## Goal

Build a baseline / implementation / execution module where:

- the agent gets one bounded workspace root
- inside it, the agent may clone repos, create repos, patch code, and run experiments
- structured records capture what matters
- git is used opportunistically by the agent for provenance, not forced everywhere

This should extend the same philosophy as the literature review module:

- a main agent drives the work
- the system stores typed records so the work is queryable
- the frontend and API read structured state, not just logs

---

## Core Design

- The Research OS repo remains the control plane
- execution happens in per-task workspaces
- the workspace root is not itself required to be a git repo
- repos/projects inside the workspace may each have their own git history
- the agent decides what is worth tracking, but must record important states

---

## Workspace Model

Default assumption:

- one research direction / task gets one workspace root
- inside that workspace, the agent may manage multiple repos or projects

Example:

```text
~/.research-os/workspaces/task-017/
├── repos/
│   ├── baseline-self-rag/
│   └── baseline-graphrag/
├── projects/
│   └── prototype-a/
├── artifacts/
└── logs/
```

Important distinction:

- the workspace root is the bounded filesystem sandbox for the agent
- the workspace root is not necessarily a single code repo
- each meaningful code project inside it may have its own `.git`

This allows:

- cloning upstream repos
- creating new repos from scratch
- deriving prototypes from reproduced baselines
- keeping large outputs and transient files outside code repos

---

## Git Provenance Policy

Git should usually track specific repos/projects inside the workspace, not the whole workspace as one giant repo.

Default policy:

- cloned repo: preserve existing git repo and record upstream + commit
- scratch project: initialize a local git repo if the agent starts editing code meaningfully
- artifacts/logs/checkpoints: usually remain outside git

The agent is allowed to decide what is worth tracking, but the system should record enough provenance to understand what code state was used for a run.

Minimum provenance fields to record:

- repo URL, if any
- base commit
- current commit
- dirty/clean status
- modification summary

---

## Data Model

Add these record types in `src/research_os/store/models.py`.

### Baseline

- `name`
- `description`
- `paper_ids`
- `source_urls`
- `status`
- `notes`

Represents prior work or an existing system/method worth reproducing, validating, or comparing against.

### Workspace

- `name`
- `root_path`
- `purpose`
- `baseline_id`
- `hypothesis_id`
- `status`

Represents the bounded execution root assigned to one research direction.

### Implementation

- `workspace_id`
- `name`
- `path`
- `source_type` (`repo|local|scratch`)
- `repo_url`
- `base_commit`
- `current_commit`
- `is_dirty`
- `modification_summary`
- `status`

Represents a specific codebase inside a workspace. This is the key provenance bridge between “paper/baseline” and “what code the agent actually ran”.

### Run

- `workspace_id`
- `implementation_id`
- `kind` (`reproduction|baseline_eval|prototype|ablation|benchmark`)
- `command`
- `cwd`
- `status`
- `pid`
- `started_at`
- `completed_at`
- `exit_code`
- `stdout_path`
- `stderr_path`

Represents one concrete execution attempt.

### Artifact

- `run_id`
- `kind`
- `path`
- `description`
- `metadata_json`

Represents outputs such as plots, result files, checkpoints, tables, patches, or reports.

### Result

- `run_id`
- `summary`
- `metrics_json`
- `success`
- `notes`

Represents the interpreted outcome of a run.

### Decision

- `subject_type`
- `subject_id`
- `decision`
- `rationale`
- `evidence_ids`

Represents a durable conclusion, such as “baseline reproduced”, “repo unusable”, or “prototype worth extending”.

---

## Workspace Management

Add a managed workspace root in config, for example:

- `RESEARCH_OS_WORKSPACES=~/.research-os/workspaces`

Implement helpers to:

- create workspace directories
- register workspace records
- create safe subpaths within a workspace
- validate that execution stays under the workspace root

Suggested default layout inside each workspace:

- `repos/`
- `projects/`
- `artifacts/`
- `logs/`

---

## Agent Tools

Expose smaller primitives rather than one giant `run_experiment` tool.

### Workspace / baseline tools

- `create_baseline`
- `create_workspace`
- `register_implementation`
- `update_implementation_state`

### Execution tools

- `start_run`
- `stop_run`
- `get_run_status`
- `record_result`
- `attach_artifact`
- `record_decision`

### Optional provenance tools

- `snapshot_implementation`
- `query_execution_state`

The agent should be free to decide whether to clone a repo, create one, patch code, or create helper scripts. The system should only require that the important states are recorded.

---

## Runner

Implement a minimal execution runner that can:

- start a subprocess in a selected `cwd`
- capture stdout/stderr to files
- record pid and lifecycle metadata
- finalize run metadata in `finally`
- support explicit stop/termination

This should follow the same hardening lessons learned from the literature review launcher.

Likely module:

- `src/research_os/execution/runner.py`

---

## Frontend v0

Add a minimal execution workspace UI.

Views:

- baselines list/detail
- workspace detail
- implementations in workspace
- runs table
- run log viewer
- results and decisions

Do not build yet:

- graph view
- mastermind UI
- full branch orchestration

The goal is state inspection, not full strategic control.

---

## Agent Workflow

After the primitives exist, add one execution-oriented agent prompt.

Expected flow:

1. create or select baseline
2. create workspace
3. clone or create implementations inside workspace
4. inspect and set up code
5. run commands
6. record outputs, results, and decisions
7. optionally branch into a derived prototype inside the same workspace

This gives the agent real operational freedom while preserving traceability.

---

## Relationship To Lit Review

This design suggests a broader system rule:

- one research direction should generally have one workspace root
- literature review can be treated as one such research direction

That means `1 research = 1 workspace` is a reasonable default, including literature review.

However, the meaning of “workspace” differs by module:

- lit review workspace may be light and mostly contain logs, notes, fetched artifacts, and maybe temporary scripts
- execution workspace may contain multiple repos, projects, and artifacts

So the answer is:

- yes, one research direction can map to one workspace
- yes, that can include lit review
- but lit review does not need to use the workspace as heavily as execution does

For execution modules:

- the workspace is where reproduction and experimentation actually happen

For lit review:

- the workspace is mostly a bounded place for process outputs and optional helper work

The important thing is consistency of the abstraction, not identical usage patterns.

---

## Recommended First Milestone

Implement only this first slice:

1. `Baseline`, `Workspace`, `Implementation`, `Run`, `Result`
2. workspace root creation
3. start/stop run APIs
4. run log viewer frontend
5. minimal baseline + execution agent tools
6. smoke tests

This is enough to support:

- clone repo
- patch code
- run baseline
- record outcome

without taking on full orchestration or mastermind logic.
