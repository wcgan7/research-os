# Experiment Engine

## Overview

The Experiment Engine is responsible for testing ideas against reality.

It provides:
- execution of experiments  
- validation of results  
- comparison across approaches  
- grounding of claims in evidence  

> The goal is to **produce reliable, reproducible evidence**.

---

## Design philosophy

The Experiment Engine follows the core principle:

> **Reality is the final judge**

It should:
- enforce rigor where needed  
- ensure reproducibility  
- validate claims  

It should NOT:
- constrain what ideas are tested  
- impose rigid workflows on experimental strategy  
- assume correctness of implementations  

It MUST:
- create structured Experiment records before execution
- create structured Result records after execution
- enforce required fields through tool interfaces — the agent cannot run an experiment without recording it

---

## Core responsibilities

### 1. Execute experiments

Run concrete implementations of:
- baselines  
- hypotheses  
- variations  

Execution may involve:
- running code  
- calling external tools  
- orchestrating pipelines  

---

### 2. Validate correctness

Before trusting results, ensure:
- code runs as expected  
- outputs are valid  
- no silent failures  

Validation may include:
- sanity checks  
- invariants  
- unit tests  
- data integrity checks  

---

### 3. Measure performance

Collect metrics such as:
- primary objective metrics  
- secondary metrics  
- resource usage  
- latency / memory  

Metrics must be:
- consistent  
- comparable  
- well-defined  

---

### 4. Compare results

Evaluate performance relative to:
- baselines  
- prior experiments  
- alternative approaches  

Comparison should support:
- fair evaluation  
- normalized conditions  

---

### 5. Support reproducibility

Every experiment should be:
- reproducible  
- traceable  

This requires tracking:
- code version  
- configuration  
- dataset  
- environment  
- random seeds (where applicable)  

---

## Experiment scope

Experiments are not limited to end-to-end evaluation.

They may target:
- subcomponents
- assumptions
- benchmarks
- supporting capabilities

This ensures that indirect but essential work — such as validating a single module or building a benchmark — is treated as legitimate experimentation.

---

## Types of experiments

The Experiment Engine supports multiple types of experiments.

---

### 1. Baseline reproduction

Reproduce results from existing work.

#### Purpose
- validate literature claims  
- establish reference points  
- detect discrepancies  

#### Workflow
1. obtain official implementation (if available)  
2. configure environment  
3. run baseline  
4. compare results to reported metrics  
5. record deviations  

#### Key principle

> Prefer official implementations whenever possible, but never assume correctness.

---

### 2. Benchmark evaluation

Evaluate a method under defined conditions.

#### Purpose
- measure performance  
- enable comparison  

---

### 3. Ablation studies

Isolate the effect of changes.

#### Purpose
- understand causality  
- validate improvements  

---

### 4. Comparative experiments

Compare multiple approaches directly.

#### Purpose
- determine relative performance  
- identify trade-offs  

---

### 5. Exploratory experiments

Quick, low-rigor tests.

#### Purpose
- probe ideas  
- gather signals  

These may:
- be incomplete  
- have weaker guarantees  

---

## Progressive rigor

Not all experiments require the same level of rigor.

The system should support increasing levels of rigor:

---

### Low rigor (exploration)
- quick tests  
- incomplete validation  
- directional signals  

---

### Medium rigor
- consistent metrics  
- partial reproducibility  
- baseline comparison  

---

### High rigor
- full reproducibility  
- controlled conditions  
- ablation  
- statistical validation  

---

> Rigor should increase as ideas become more important.

---

## Outputs to Research State

The Experiment Engine writes structured records through defined tool interfaces. These records are mandatory — the engine cannot execute without creating them.

### Experiment record (created before execution)
- target hypothesis
- method and configuration
- environment and code version
- rigor level
- status

### Result record (created after execution)
- source experiment
- metrics collected
- validity (sanity checks passed or not)
- anomalies detected

### Derived outputs
- comparisons across experiments
- performance summaries
- failure patterns

### Relationships
- hypothesis → experiment (what this tests)
- experiment → result (what this produced)
- result → decision (what was concluded)

These structured relationships are what make research state queryable and the frontend renderable.

---

## Handling uncertainty

Results are not always definitive.

The system should track:
- variance  
- instability  
- sensitivity to configuration  
- anomalies  

It should avoid:
- over-interpreting single runs  
- treating noisy improvements as real  

---

## Failure handling

Failures are valuable signals.

The system should record:
- execution failures  
- invalid outputs  
- regressions  
- unexpected behavior  

Failures should:
- inform future decisions  
- contribute to failure pattern tracking  

---

## Environment considerations

Experiments depend on environment.

The system should account for:
- hardware differences  
- software versions  
- dependencies  
- resource constraints  

Perfect reproducibility may not always be possible, but it should be approximated.

---

## Interaction with other systems

### With Literature Review
- receives baseline definitions  
- receives benchmark references  

---

### With Research State
- records experiments and results  
- links to hypotheses and claims  

---

### With Mastermind
The mastermind:
- selects what to test  
- determines required rigor  
- interprets results  
- decides next actions  

The Experiment Engine does NOT:
- decide strategy  
- interpret significance  

---

## Flexibility considerations

The Experiment Engine must allow:

- partial implementations  
- iterative refinement  
- multiple competing approaches  
- different evaluation strategies  

It should not assume:
- a single benchmark is sufficient  
- all problems are comparable  
- all experiments are equally important  

---

## Anti-goals

The Experiment Engine should NOT:

- blindly trust outputs  
- constrain what experiments the mastermind can run (strategic flexibility is sacred)
- treat all experiments as equal  
- optimize prematurely  
- block exploratory work  

Note: requiring structured records for every experiment is not "rigidity" — it is the recording discipline that makes the system valuable. The engine is flexible in what it runs, strict in what it records.

---

## Key challenges

- ensuring fair comparisons  
- handling noisy results  
- balancing speed vs rigor  
- managing environment differences  
- avoiding false positives  

---

## Summary

The Experiment Engine is where ideas meet reality.

It:
- executes hypotheses  
- validates claims  
- produces evidence  

> It ensures that progress is **measured, tested, and real**s
