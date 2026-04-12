# Research OS

A literature-aware, experiment-driven research operating system.

---

## Overview

Research OS is a system for orchestrating AI agents, tools, experiments, and memory into a disciplined research workflow.

It is designed to help tackle research problems by combining:
- literature grounding  
- structured experimentation  
- persistent memory  
- strategic control  

Instead of relying on a single “smart agent”, Research OS provides:

- a research substrate for execution and validation  
- a strategic control layer (“mastermind”)  
- a persistent research state  
- a frontend interface for interaction and control  

> The goal is to produce validated research progress.

## Why this exists

You can give a capable AI agent a research problem and tell it to keep going until it finds a solution. You can even prompt it to take notes, track failures, and be rigorous. And it will get surprisingly far.

But it will eventually:
- **forget** what it tried as context grows and degrades
- **not ground** its ideas in what actually exists — reinventing worse versions of known methods
- **not know if it's making progress** — declaring success on noisy or unvalidated results
- **repeat itself** — circling back to failed ideas without realizing it
- **follow one path linearly** — unable to branch, backtrack, or manage parallel directions

Prompting the agent to be disciplined doesn't fix this. The agent decides what's worth documenting, and it's bad at that. It over-documents the obvious, under-documents the subtle. Its notes drift in format and become unqueryable. There's no separation between the thinker and the record-keeper — the same agent that rationalizes a direction also decides whether to track its failure.

Research OS is based on a different premise:

> Research quality comes from **structural discipline** — the system forces rigor through defined interfaces, not by asking the agent to be disciplined.

The agent writes to structured, typed records through tool interfaces with required fields. It cannot skip record-keeping. It cannot drift the format. The system enforces what gets tracked, not the agent.

---

## Core design principles

### Baseline-first
Start from existing knowledge before proposing novelty.

---

### Literature as a system
Literature is continuously integrated, not treated as a one-off step.

---

### Research is stateful
The system tracks:
- hypotheses  
- failures  
- decisions  
- artifacts  
- confidence  

---

### Truth before polish
All claims are tied to evidence and tracked explicitly.

---

### Strategic flexibility
The system supports:
- branching  
- backtracking  
- reframing  
- consolidation  

---

### Reality is the final judge
All ideas must be validated through:
- tests  
- experiments  
- benchmarks  

---

## System architecture

Research OS consists of three layers.

### Research state (the spine)

The persistent, structured record of everything the system has learned and done.

Every entity — hypothesis, experiment, result, decision, literature finding — is a typed record with required fields, relationships to other records, and provenance. The research state is **queryable**: the mastermind can ask "what have I tried for X" and get a structured answer, not grep through freeform notes.

This is the foundation that makes everything else possible. Because the state is structured, the frontend can render it. Because it's queryable, the mastermind can reason over it. Because it's enforced through tool interfaces, it stays consistent.

---

### Capabilities (tools the mastermind calls)

The concrete actions the mastermind can take:

- search and retrieve literature
- run experiments and collect results
- measure against benchmarks
- record hypotheses, observations, decisions
- branch and merge research directions

Each capability is a tool interface that does something in the world **and writes structured records back to the research state**. The agent cannot take an action without creating the corresponding record. This is how structural discipline is enforced — not by prompting, but by interface design.

---

### Strategic control layer (Mastermind)

A top-level controller that:
- decides what to do next  
- allocates effort  
- avoids dead ends  
- manages branches  
- receives and incorporates human guidance

The mastermind has full strategic flexibility — it can pursue any action it believes will advance the research. But every action it takes goes through a defined tool interface that enforces record-keeping. The mastermind is free in what it does, constrained in how it records what it does.

---

### Safeguards (gates on state transitions)

Validation that fires when certain state transitions occur — promoting a result, pruning a branch, recording a conclusion. The mastermind proposes; the safeguards check. This is not a system the mastermind calls — it's a constraint the system enforces.

---

## Primary interface: Frontend UI

The **frontend is the main interface** for interacting with Research OS.

It serves as the control plane for the entire system.

### Why frontend-first?

Because the research state is structured and queryable, the frontend can render a complete, navigable view of the research process — not a log of agent outputs, but a real-time map of hypotheses, experiments, results, decisions, and their relationships.

This is not possible with a freeform-notes approach. If the agent just writes markdown files, you get a pile of text. Because Research OS enforces typed records with relationships, the frontend gets structured data it can actually render.

A CLI alone is insufficient for research that is long-running, stateful, multi-branch, and complex.

---

### Key frontend capabilities

#### Research graph
Hypotheses, branches, dependencies — rendered from the structured relationships in research state.

#### Experiment dashboard
Metrics, comparisons, trends — queryable from typed experiment and result records.

#### Literature map
Papers, methods, relationships — built from structured literature records.

#### Decision log
Promotions, rejections, rationale — every decision is a typed record with evidence links.

#### State inspector
System status, confidence levels, active directions — direct views into research state.

#### Human-in-the-loop control
The frontend is not just for observation — it is the primary channel for human guidance.

Humans can:
- **suggest directions** the mastermind should consider next
- **inject priorities** that the mastermind must factor into its planning
- **override decisions** when the system's judgment is insufficient
- **flag concerns** about specific results, directions, or assumptions

Human suggestions become structured records in the research state — they are first-class inputs to the mastermind's planning cycle, not side-channel comments.

---

## Secondary interfaces

### CLI

Used for:
- automation  
- scripting  
- power users  

```bash
research-os run
research-os status
research-os review
````

---

### Python API

```python
from research_os import Director

director = Director()
director.run("improve kv cache compression")
```

---

## How it works (conceptually)

1. User provides a research problem (natural language)
2. Mastermind interprets and decomposes it — creates structured Branch and Hypothesis records
3. Literature is gathered — creates Literature records with required fields
4. Baselines are identified — creates Experiment records for baseline reproduction
5. Hypotheses are generated and recorded — each a typed record linked to its grounding
6. Experiments are executed — Experiment and Result records created through tool interfaces
7. Results are evaluated — safeguards validate before promotion
8. Decisions are made — each a structured Decision record with evidence links and rationale
9. Strategy is updated — mastermind plans next actions based on queryable research state
10. Humans observe progress through the frontend and inject guidance as structured records

This loop continues iteratively. At every step, the system produces structured records — this is what makes the process traceable, queryable, and renderable in the frontend.

---

## Repository structure

```text
.
├── README.md
├── design_docs/
│   ├── research_state.md
│   ├── mastermind_controller.md
│   ├── literature_review.md
│   ├── experiment_engine.md
│   └── promotion_and_safeguards.md
├── src/
├── tests/
└── examples/
```

---

## Design docs

Detailed designs live in [`design_docs/`](./design_docs).

These documents define the system in depth and serve as the source of truth for implementation.

---

## Core capabilities

Research OS is built around several core systems:

- Problem understanding
- Literature and knowledge
- Hypothesis and planning
- Experimentation
- Evaluation and decision-making
- Research memory
- Strategic control (mastermind)

These systems work together to form a continuous research loop.
