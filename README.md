# AI Evaluation Engine — Hybrid Grader & Adversarial Task

A complete, end-to-end evaluation pipeline for frontier coding models. This repository demonstrates the full task lifecycle — prompt engineering, adversarial constraint design, deterministic procedural grading, and LLM-based heuristic scoring — across **multi-run simulation with automatic failure categorization**.

---

## Overview

Evaluating whether a language model can *actually* solve a problem is harder than it looks. Passing functional tests is necessary but not sufficient: a model may reach for forbidden APIs out of habit, ignore edge cases at exact boundaries, or produce technically correct code that violates every principle of clean software design.

This engine addresses all three failure modes simultaneously through a **hybrid grading architecture**:

- A **procedural grader** enforces hard, binary constraints via AST analysis and deterministic test cases.
- An **LLM heuristic grader** scores soft constraints — code quality, naming conventions, design principles — that no regex or unit test can reliably capture.

The pipeline runs **multiple submissions in sequence**, automatically classifies each failure as either a **Rule Violation** (forbidden import detected) or a **Logic Error** (incorrect boundary behaviour), and renders a consolidated Rich dashboard with per-run scores and an overall pass rate.

```
┌─────────────────────────────────────────────────────────┐
│                  evaluate_pipeline.py                   │
│                                                         │
│  ┌─────────────────────┐   ┌─────────────────────────┐  │
│  │  Procedural Grader  │   │    LLM Heuristic Grader │  │
│  │  (pytest + AST)     │   │    (Gemini 2.5 Flash)   │  │
│  │                     │   │                         │  │
│  │  PASS / FAIL        │   │    Score: 0–10          │  │
│  └─────────────────────┘   └─────────────────────────┘  │
│                  ↓                   ↓                  │
│            ╔══════════════════════════════╗             │
│            ║      EVALUATION REPORT       ║             │
│            ╚══════════════════════════════╝             │
└─────────────────────────────────────────────────────────┘
```

---

## Business Value & Financial Impact

This pipeline is not an academic exercise — it is the kind of automated QA infrastructure that makes the difference between an AI feature that ships and one that stalls indefinitely in review.

**Solving the AI Trust Bottleneck**
Organisations routinely delay or abandon AI-powered features because they lack a repeatable, auditable process for verifying model behaviour before deployment. Without that process, every release carries undefined risk — and business stakeholders will not sign off on undefined risk. This pipeline provides the automated quality-assurance layer that converts model outputs from *untrusted artefacts* into *verified, policy-compliant code*, enabling teams to ship AI features with the same confidence they apply to human-authored code.

**R&D Cost Reduction**
Traditional AI QA relies on senior engineers manually reviewing model outputs run by run — a process that does not scale as model usage grows. By automating multi-run evaluation, adversarial constraint checking, and heuristic rubric scoring end-to-end, this engine eliminates the bottleneck. Engineering hours previously spent on repetitive manual review are reallocated to higher-leverage work, reducing the effective cost per evaluated submission by an order of magnitude.

**Mitigating Financial and Security Risk**
The adversarial constraint system — specifically the AST-level detection of forbidden module imports — demonstrates a concrete approach to preventing AI from introducing unauthorized dependencies or security vulnerabilities into a production codebase. An AI model that reaches for `time`, `subprocess`, or `os` when explicitly prohibited is a liability. Catching that at evaluation time, before the code reaches a repository, is the difference between a guardrail and a post-incident review.

**Optimizing Compute Costs**
LLM API calls are not free. Running a rubric grader against every submission regardless of quality wastes token budget on models that have already failed basic correctness checks. The Failure Categorization Dashboard addresses this directly: by classifying failures as **Rule Violations** or **Logic Errors** before invoking the LLM grader, the pipeline gates expensive heuristic scoring behind cheap deterministic tests. Teams get actionable signal — which failure class is most prevalent, and where to focus fine-tuning or prompt engineering effort — without burning budget on fundamentally incapable submissions.

---

## The Adversarial Task

**Task file:** `tasks/v1_adversarial_task.md`

The model under evaluation is asked to implement an in-memory **sliding-window Rate Limiter** in Python. The interface is straightforward:

```python
class RateLimiter:
    def __init__(self, max_tokens: int, window_size: int): ...
    def tick(self) -> None: ...          # advances the internal clock
    def allow_request(self) -> bool: ... # returns True if within limit
```

### The Hidden Constraint

The prompt contains a deliberately adversarial restriction buried in the requirements:

> **"Do not use any external libraries, including the `time` or `datetime` modules. You must track expiration strictly using an integer `tick` counter that increments manually via the provided `tick()` method."**

This constraint is adversarial for two precise reasons:

1. **It exploits trained reflexes.** A model that has seen thousands of rate-limiter implementations will reach for `time.time()` or `datetime.now()` automatically. Complying with the constraint requires the model to suppress a deeply reinforced pattern — a reliable signal of whether the model is *reasoning about the prompt* or *pattern-matching against its training distribution*.

2. **It tests determinism under a controlled clock.** The tick-based design forces the model to implement a pure, side-effect-free sliding window that can be tested precisely at its expiration boundary. A model that uses wall-clock time produces code that is correct in production but *untestable* in this evaluation harness — which is itself a design failure.

The dummy submission in `submissions/dummy_ai_submission.py` illustrates exactly this failure: it imports `time`, uses single-character variable names, and contains an off-by-one error at the `max_tokens` boundary — three distinct, independently-detectable problems.

---

## The Hybrid Grading System

### Procedural Grader — `graders/procedural_grader.py`

The procedural grader is a `pytest` suite with three tests targeting different failure dimensions:

| Test | What it checks | Failure signal |
|---|---|---|
| `test_basic_allowance` | Requests within the token budget are accepted | Broken core logic |
| `test_adversarial_trap` | Submission source is parsed with `ast.walk` to detect any `import time` or `import datetime` node | Model ignored the constraint |
| `test_edge_case_expiration` | At exactly `max_tokens` requests the limiter returns `False`; after exactly `window_size` ticks entries expire and new requests are permitted | Off-by-one logic errors |

The `test_adversarial_trap` test deliberately uses **AST parsing** rather than a string search. This prevents a model from evading detection via `from time import sleep` or `import time as t` — aliases and `from` imports all resolve to the same module name in the AST.

### LLM Heuristic Grader — `graders/llm_grader.py`

Soft quality properties — whether a function has a single responsibility, whether variable names are self-documenting, whether numeric constants are hardcoded — do not map cleanly onto deterministic tests. For these, the grader submits the full submission source to **Gemini 2.5 Flash** with a structured rubric prompt:

| Criterion | What is penalized |
|---|---|
| Single Responsibility Principle | Methods that mix eviction logic, token counting, and side-effects |
| Descriptive Variable Names | Single-letter names (`w`, `log`, `_`) that obscure intent |
| No Magic Numbers | Inline numeric literals instead of constructor-injected parameters |

The model is instructed to return **only** a strict JSON object:

```json
{"score": 4, "reasoning": "Variable names are terse and the allow_request method violates SRP by calling time.time() as a side-effect."}
```

The grader strips accidental markdown fences, validates the schema, and surfaces the score and reasoning directly in the final report.

---

## Multi-Run Evaluation & Failure Categorization

The pipeline evaluates a manifest of submissions in sequence, staging each one as `submissions/active_run.py` before grading and cleaning up afterward. Three synthetic submissions ship with the repo to demonstrate the three distinct outcome classes:

| File | Expected outcome | Failure category |
|---|---|---|
| `run_1_trap.py` | Procedural FAIL | Rule Violation — illegal `import time` detected via AST |
| `run_2_logic.py` | Procedural FAIL | Logic Error — off-by-one in eviction cutoff (`<` vs `<=`) |
| `run_3_pass.py` | Procedural PASS | — (LLM rubric score reported) |

After all runs complete, a **Rich terminal dashboard** renders the consolidated results:

```
╭──────────────────────┬──────────────┬──────────────────────┬────────────┬──────────────────────╮
│ Run                  │ Procedural   │ Failure Category     │ LLM Score  │ LLM Reasoning        │
├──────────────────────┼──────────────┼──────────────────────┼────────────┼──────────────────────┤
│ run_1_trap.py        │    FAIL      │   Rule Violation     │  Skipped   │ Skipped              │
│ run_2_logic.py       │    FAIL      │   Logic Error        │  Skipped   │ Skipped              │
│ run_3_pass.py        │    PASS      │       —              │   8 / 10   │ Clean design…        │
╰──────────────────────┴──────────────┴──────────────────────┴────────────┴──────────────────────╯

Overall Pass Rate: 1/3  (33%)
```

![AI Evaluation Dashboard](dashboard.jpg)

---

## Repository Structure

```
.
├── evaluate_pipeline.py          # Orchestrator: multi-run loop, Rich dashboard
├── requirements.txt
├── .env.example
│
├── tasks/
│   └── v1_adversarial_task.md    # The prompt delivered to the model under test
│
├── submissions/
│   ├── run_1_trap.py             # Rule Violation: illegal import time
│   ├── run_2_logic.py            # Logic Error: off-by-one eviction cutoff
│   └── run_3_pass.py             # Passing: correct logic, clean code
│   └── active_run.py             # Ephemeral — created and deleted per run
│
└── graders/
    ├── procedural_grader.py      # pytest suite: AST checks + boundary tests
    └── llm_grader.py             # Gemini rubric scorer
```

---

## Setup & Execution

**1. Create and activate a virtual environment**

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Configure your API key**

```bash
cp .env.example .env
# Open .env and replace the placeholder with your Gemini API key
```

**4. Run the full evaluation pipeline**

```bash
python evaluate_pipeline.py
```

**Sample output**

```
Running procedural tests against: submissions/dummy_ai_submission.py
Running LLM rubric evaluation …

============================================================
           EVALUATION REPORT
============================================================

[ SECTION 1 — Procedural Test Results ]
  Overall status : FAILED

  Pytest output:
    FAILED graders/procedural_grader.py::test_adversarial_trap
    FAILED graders/procedural_grader.py::test_edge_case_expiration
    PASSED graders/procedural_grader.py::test_basic_allowance

[ SECTION 2 — LLM Rubric Score ]
  Score     : 4 / 10  [########------------]
  Reasoning : Variable names are terse and non-descriptive; allow_request
              violates SRP by invoking time.time() as a hidden side-effect.

============================================================
```

---

## Design Principles

**Separation of grading concerns.** Deterministic properties (import violations, off-by-one logic) belong in code. Qualitative properties (naming, design patterns) belong with an LLM. Conflating the two produces graders that are either too brittle or too vague.

**AST over string matching.** Import detection uses `ast.walk` rather than `"import time" in source`. This closes the aliasing bypass and reflects how the Python runtime actually resolves modules.

**Graceful degradation.** If the Gemini API is unavailable or returns malformed JSON, the pipeline logs the error to stderr and still prints a complete procedural report. LLM grading failure does not mask test failures.

**Tick-based determinism.** Replacing wall-clock time with a manually-advanced counter makes every test case fully deterministic, hermetic, and reproducible — a prerequisite for rigorous model evaluation.
