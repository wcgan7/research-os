# Research State

## Overview

The Research State is the spine of Research OS.

It is the persistent, structured record of everything the system has learned, tried, decided, and failed at. Every other system reads from it and writes to it through defined tool interfaces.

> The goal is to ensure the system **never loses what it has learned** — and that what it has learned is **queryable, traceable, and structured**.

---

## Why structured state matters

An agent told to "keep notes" will produce freeform text that drifts in format, buries important signals, and becomes unqueryable as the research grows. You can't ask "show me all failed approaches related to attention mechanisms" if failures are scattered across markdown paragraphs.

Research state solves this by making every piece of research activity a **typed record with required fields and relationships to other records**. The agent writes through defined tool interfaces — it cannot skip fields, drift the format, or choose what's worth recording. The system decides what gets tracked, not the agent.

This is also what makes the frontend possible. Because research state is structured, the UI can render a research graph, experiment dashboard, decision log, and full traceability — not a wall of text.

---

## Core record types

### Hypothesis

A proposed idea, approach, or conjecture to be tested.

Required fields:
- statement (what is being proposed)
- motivation (why this might work)
- grounding (literature or prior results that inform this)
- status (proposed | active | validated | rejected | paused)
- parent branch (which research direction this belongs to)

---

### Experiment

A concrete test of an idea against reality.

Required fields:
- target hypothesis (what this tests)
- method (what is being done)
- configuration (parameters, environment, code version)
- status (planned | running | completed | failed)
- rigor level (exploratory | medium | high)

---

### Result

The outcome of an experiment.

Required fields:
- source experiment (which experiment produced this)
- metrics (measured values)
- validity (passed sanity checks or not)
- interpretation (what this means — written by the mastermind, but the record itself is enforced by the system)

---

### Decision

A strategic choice made by the mastermind.

Required fields:
- decision type (promote | reject | branch | merge | pause | pivot | escalate)
- rationale (why this decision was made)
- evidence links (which results or findings support this)
- affected entities (which hypotheses, branches, or experiments this impacts)

---

### Literature record

A finding from the literature system.

Required fields:
- source (paper, repo, blog, benchmark)
- relevance (how this relates to the current research)
- key claims (what the source asserts)
- extracted insights (what is useful for the research)

---

### Branch

A research direction being explored.

Required fields:
- objective (what this branch is trying to achieve)
- status (active | paused | merged | abandoned)
- parent branch (if this was spawned from another direction)
- rationale (why this direction was created)

---

### Human input

A suggestion, priority, or override from a human operator.

Required fields:
- input type (suggestion | priority | override | concern)
- content (what the human is communicating)
- target (which branch, hypothesis, or decision this relates to)
- status (pending | incorporated | acknowledged | declined with rationale)

---

## Relationships

Records are not isolated — they form a graph.

- Hypotheses belong to branches
- Experiments test hypotheses
- Results come from experiments
- Decisions reference results and hypotheses
- Literature records link to hypotheses they inform
- Human inputs target specific branches, hypotheses, or decisions

These relationships are what make the state queryable and the frontend renderable. The mastermind can ask "what experiments have been run for hypothesis X" or "what is the best result on branch Y" and get structured answers.

---

## Write interfaces

Records are created through defined tool interfaces, not freeform text. When the mastermind takes an action, the corresponding tool creates a record with all required fields. If a required field is missing, the write fails.

This is the core enforcement mechanism. The agent cannot opt out of record-keeping because record-keeping is embedded in the tool interface — you can't run an experiment without creating an Experiment record, and you can't record a result without linking it to the experiment that produced it.

---

## Queryability

The research state must be efficiently queryable. Key query patterns:

- all experiments for a given hypothesis
- all failed approaches in a branch
- current best result for a given metric
- full history of a research direction
- all decisions with their evidence
- all human inputs and their status

These queries power both the mastermind's planning and the frontend's rendering.

---

## Intermediate work

Not all research activity directly improves the main objective.

The system must support intermediate work such as:
- component validation
- tooling and infrastructure
- benchmark construction
- assumption testing

This work produces records like any other activity. The research state does not distinguish "real" work from "supporting" work — all of it is first-class research activity with structured records and traceability.

> Indirect contributions are first-class research activity, not overhead.
