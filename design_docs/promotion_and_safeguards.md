# Promotion and Safeguards

## Overview

The Promotion and Safeguards system ensures that the Research OS does not fool itself.

It provides:
- lightweight checks before committing to conclusions  
- safeguards against false progress  
- consistency in how results are interpreted  

> The goal is not to control research —  
> it is to ensure that **progress is real when it is recognized as such**.

---

## Design philosophy

The system follows a core principle:

> **Constrain commitment, not exploration**

It should:
- allow free exploration  
- allow speculative ideas  
- allow low-rigor experiments  

It should only intervene when:
- results are being promoted  
- decisions are being committed  
- conclusions are being treated as meaningful progress  

---

## Scope

The system applies only to:
- promotion of results  
- prioritization decisions  
- pruning of branches  
- recognition of progress  

It does NOT apply to:
- idea generation  
- early exploration  
- brainstorming  
- low-rigor experiments  

---

## Core responsibilities

### 1. Promotion checks

Before a result is treated as progress, verify:

- does it outperform baseline (if applicable)?
- is the improvement consistent?
- is the result meaningful or just noise?

---

### 2. Evidence validation

Ensure that claims are supported by:

- experiment results  
- reproducible configurations  
- reasonable evaluation conditions  

Avoid:
- single-run conclusions  
- unverified assumptions  

---

### 3. Rigor escalation triggers

Increase validation requirements when:

- results appear promising  
- decisions are impactful  
- contradictions arise  

Examples:
- require repeated runs  
- require ablation  
- require independent verification  

---

### 4. Noise and false positive detection

Guard against:

- overfitting to benchmark  
- random fluctuations  
- accidental improvements  

---

### 5. Failure recognition

Ensure the system acknowledges:

- repeated failures  
- unproductive directions  
- diminishing returns  

Prevent:
- infinite retry loops  
- disguised repetition  

---

### 6. Human interaction

Human involvement is bidirectional.

**System → Human (escalation):**
Trigger human attention when:
- evidence is insufficient but stakes are high  
- results are conflicting  
- system confidence is low  
- decisions are ambiguous  

**Human → System (guidance):**
Humans can proactively inject:
- suggestions for directions to consider
- priorities the mastermind must weigh
- overrides on specific decisions
- concerns about results or assumptions

Human inputs are structured records in the research state. The mastermind must acknowledge them in its next planning cycle — it may decline, but must record why.

---

## Decision outcomes

The system does not enforce what the mastermind decides, but validates that decisions are justified and records them as structured Decision records.

Every decision produces a record with required fields:
- decision type
- rationale
- evidence links (which results or findings support this)
- affected entities (which hypotheses, branches, or experiments this impacts)

Typical decision types:

- **promote** → result accepted as progress  
- **revise** → more evidence required  
- **reject** → insufficient or invalid  
- **branch** → explore further  
- **pause** → insufficient clarity  

---

## Rigor levels

Validation strength should scale with importance.

### Low rigor
- exploratory  
- directional signals  
- minimal checks  

---

### Medium rigor
- consistent metrics  
- baseline comparison  
- partial reproducibility  

---

### High rigor
- reproducible  
- controlled conditions  
- ablation  
- independent verification  

---

## Recognizing multiple forms of progress

The system recognizes multiple forms of progress, including:

- end-to-end improvements
- component-level validation
- capability-building work
- benchmark and tooling validation

Not all progress looks like a metric going up. Building reliable infrastructure, validating assumptions, and establishing benchmarks are all legitimate forms of progress that the safeguards system should recognize and support.

---

## Interaction with mastermind

The mastermind:
- proposes actions and decisions  

Promotion and Safeguards:
- validates whether they are justified  

---

## Key principle

> The mastermind proposes  
> The safeguards validate  

---

## Flexibility considerations

The system should:
- allow different evaluation strategies  
- adapt to different problem domains  
- avoid rigid rules  

It should not:
- enforce fixed workflows  
- require identical validation for all cases  

---

## Anti-goals

The system should NOT:

- block exploration  
- over-constrain the system  
- require excessive validation  
- slow down iteration unnecessarily  

---

## Summary

Promotion and Safeguards ensures that:

- progress is not declared prematurely  
- evidence supports conclusions  
- the system remains honest  

> It does not control what the system explores —  
> it ensures that what it accepts is **real**
