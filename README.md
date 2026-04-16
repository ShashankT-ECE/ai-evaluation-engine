# AI Evaluation Engine — Hybrid Grader & Adversarial Task

A complete, end-to-end evaluation pipeline for frontier coding models. This repository demonstrates the full task lifecycle — prompt engineering, adversarial constraint design, deterministic procedural grading, and LLM-based heuristic scoring — in a single, runnable system.

---

## Overview

Evaluating whether a language model can *actually* solve a problem is harder than it looks. Passing functional tests is necessary but not sufficient: a model may reach for forbidden APIs out of habit, ignore edge cases at exact boundaries, or produce technically correct code that violates every principle of clean software design.

This engine addresses all three failure modes simultaneously through a **hybrid grading architecture**:

- A **procedural grader** enforces hard, binary constraints via AST analysis and deterministic test cases.
- An **LLM heuristic grader** scores soft constraints — code quality, naming conventions, design principles — that no regex or unit test can reliably capture.

The two scores are combined into a unified **Evaluation Report**, giving a complete picture of model capability across both correctness and craftsmanship dimensions.

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

## Repository Structure

```
.
├── evaluate_pipeline.py          # Orchestrator: runs both graders, prints report
├── requirements.txt
├── .env.example
│
├── tasks/
│   └── v1_adversarial_task.md    # The prompt delivered to the model under test
│
├── submissions/
│   └── dummy_ai_submission.py    # Synthetic buggy submission for demonstration
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
