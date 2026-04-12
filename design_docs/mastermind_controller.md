# Mastermind Controller

## Overview

The Mastermind is the strategic control layer of Research OS.

It is responsible for:
- deciding what to do next
- allocating effort across directions
- managing research branches
- interpreting results and adjusting strategy
- delegating execution to subsystems

> The mastermind **delegates, not executes**.

---

## Action flexibility

The mastermind is not restricted to predefined workflows or task types.

It may pursue any action that is expected to contribute to the research objective, including:

- direct experimentation
- subcomponent validation
- capability building
- literature refresh
- anomaly investigation
- branch creation or consolidation
- problem reframing

The system must support both direct and indirect contributions to progress.

### Direct actions
- test a hypothesis
- improve a metric
- beat a baseline

### Indirect actions (but essential)
- build tooling
- validate assumptions
- reproduce baselines
- construct benchmarks
- investigate anomalies
- compare internal representations
- refactor problem framing

### Meta-level actions
- refresh literature
- spawn parallel branches
- merge or kill branches
- escalate rigor
- request human input
- revisit earlier conclusions

> The system is not optimizing for "next experiment" —
> it is optimizing for **progress of the entire research process**.

---

## Structural discipline without strategic constraint

The mastermind has full freedom in what it does. It has no freedom in whether it records what it does.

Every action the mastermind takes goes through a tool interface that produces a structured record in the research state — a Decision, an Experiment, a Hypothesis, a Branch operation. The mastermind cannot skip record-keeping because it is embedded in the tool interface itself.

This is not a constraint on strategy. It is a constraint on record-keeping. The mastermind can pursue any direction, try any approach, reframe any problem — but every action leaves a structured, queryable trace. This is what makes the research process traceable by humans and navigable through the frontend.

---

## What would violate action flexibility

Anything that forces the mastermind into:

- rigid pipelines
- fixed step sequences
- only "hypothesis → experiment → result" loops
- only end-to-end evaluation
- only predefined task types

These constrain strategy and would cripple the system. Note: requiring structured records for every action is NOT a strategic constraint — it is a recording constraint. The mastermind is free to do anything; it is required to record everything.

---

## Human-in-the-loop

The mastermind does not operate in isolation. Human operators can inject guidance through the frontend:

- **suggestions** for directions to consider
- **priorities** that the mastermind must factor into planning
- **overrides** on specific decisions
- **concerns** about results or assumptions

Human inputs become structured records in the research state. The mastermind is required to acknowledge and consider them in its next planning cycle. It may decline a suggestion, but it must record why.

---
