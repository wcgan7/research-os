# Literature Review System

## Overview

The Literature Review System is responsible for grounding the research process in existing knowledge.

It provides:
- discovery of relevant work  
- understanding of the current landscape  
- identification of baselines  
- extraction of useful insights  

It feeds into the Research State and supports all downstream systems.

> The goal is to **enable informed, grounded research decisions build upon current state of the art**.

---

## Design philosophy

The literature system follows the same core principle as the overall system:

> **Strong grounding, weak prescription**

It should:
- provide high-quality context  
- surface relevant knowledge  
- highlight important signals  

It should NOT:
- rigidly define the problem  
- force premature structure  
- constrain how the mastermind interprets information  

---

## Core responsibilities

### 1. Discovery

Find relevant sources related to the research problem.

Sources may include:
- papers  
- repositories  
- blog posts  
- benchmarks  
- documentation  

Discovery should be:
- broad initially  
- refined iteratively  

---

### 2. Field mapping

Build a high-level understanding of the space.

This includes identifying:
- major approaches  
- common techniques  
- recurring ideas  
- competing methods  
- benchmark standards  

This is not a fixed taxonomy — it evolves over time.

---

### 3. Baseline identification

Identify strong reference points.

Baselines should include:
- widely accepted methods  
- strong-performing approaches  
- commonly used implementations  
- benchmark leaders  

The goal is to answer:
> “What does the best currently look like?”

---

### 4. Insight extraction

Extract useful knowledge without over-structuring.

Examples:
- key ideas  
- assumptions  
- trade-offs  
- limitations  
- evaluation methods  

Extraction should support both:
- human understanding  
- system reasoning  

---

### 5. Relevance filtering

Not all literature is equally useful.

The system should:
- rank relevance  
- filter noise  
- surface high-impact sources  

This process is iterative and context-dependent.

---

### 6. Novelty awareness

Help detect overlap with existing work.

This includes:
- identifying similar approaches  
- highlighting potential duplication  
- surfacing prior attempts  

This does NOT require perfect novelty detection —  
it only needs to provide useful signals.

---

## Outputs to Research State

The literature system contributes to both layers of the Research State.

---

### Exploratory layer outputs

- notes  
- summaries  
- observations  
- questions  
- interpretations  

These help the mastermind build intuition.

---

### Structured layer outputs

- literature records  
- extracted claims  
- identified baselines  
- linked methods  
- benchmark references  

These support:
- comparison  
- grounding  
- traceability  

---

## Progressive structuring

Every literature finding produces a structured record with required fields (source, relevance, key claims, extracted insights). This is non-negotiable — it's how the system maintains queryable, traceable state.

But interpretation deepens over time:

- initial records capture what was found and why it's relevant
- as research evolves, records are updated with richer connections
- insights and interpretations are refined as understanding grows

The structure is on the record format, not on the interpretation. The agent must always create a properly typed record, but the content of that record — especially relevance and insights — evolves as the research progresses.

---

## Iterative refinement

Literature review is not a one-time step.

It should:
- evolve as the research evolves  
- revisit sources when needed  
- expand or narrow scope dynamically  

Examples:
- deeper dive into a promising method  
- re-evaluate assumptions  
- search for missing approaches  

---

## Interaction with other systems

### With Research State

- writes notes and records  
- links literature to hypotheses and experiments  
- updates relevance over time  

---

### With Mastermind

The mastermind:
- guides search direction  
- decides when to deepen or broaden  
- interprets literature signals  
- resolves ambiguity  

The literature system does NOT decide strategy.

---

### With Hypothesis system

Literature informs:
- idea generation  
- feasibility  
- expected outcomes  

---

### With Experiment system

Literature provides:
- benchmark definitions  
- evaluation methods  
- baseline expectations  

---

## Flexibility considerations

The literature system must allow:

- incomplete understanding  
- conflicting interpretations  
- multiple perspectives  
- evolving conclusions  

It should not assume:
- literature is always correct  
- claims are always valid  
- benchmarks are always meaningful  

---

## Anti-goals

The literature system should NOT:

- produce static summaries only  
- enforce rigid interpretation of findings (record format is enforced; interpretation is free)
- assume correctness of sources  
- block exploration due to “existing work”  
- over-optimize for citation completeness  

---

## Key challenges

- balancing breadth vs depth  
- avoiding shallow summarization  
- distinguishing signal from noise  
- handling conflicting sources  
- detecting true novelty vs variation  

---

## Summary

The Literature Review System provides the foundation for grounded research.

It:
- connects the system to existing knowledge  
- informs decisions without constraining them  
- evolves alongside the research process  

> It ensures the system builds on what is known —  
> to support exploration beyond it
