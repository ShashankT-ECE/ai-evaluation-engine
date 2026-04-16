"""
Main evaluation pipeline orchestrator.

Usage:
    python evaluate_pipeline.py

Steps:
    1. Run the procedural pytest suite and capture results.
    2. Call the LLM grader and capture score + reasoning.
    3. Print a formatted Evaluation Report.
"""

import subprocess
import sys
import os

# Ensure project root is on the path so graders can be imported
sys.path.insert(0, os.path.dirname(__file__))

from graders.llm_grader import evaluate_code_with_llm

SUBMISSION_PATH = os.path.join("submissions", "dummy_ai_submission.py")
GRADER_PATH = os.path.join("graders", "procedural_grader.py")

SEPARATOR = "=" * 60


def run_procedural_tests() -> tuple[int, str]:
    """
    Execute the pytest suite as a subprocess.

    Returns:
        A tuple of (return_code, captured_output).
        return_code == 0 means all tests passed.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", GRADER_PATH, "-v", "--tb=short"],
        capture_output=True,
        text=True,
    )
    combined_output = result.stdout + result.stderr
    return result.returncode, combined_output


def run_llm_grader() -> dict | None:
    """
    Run the LLM rubric grader.

    Returns the evaluation dict on success, or None on failure (with the
    error printed to stderr so the pipeline continues).
    """
    try:
        return evaluate_code_with_llm(SUBMISSION_PATH)
    except EnvironmentError as env_err:
        print(f"[LLM Grader] Configuration error: {env_err}", file=sys.stderr)
    except ValueError as val_err:
        print(f"[LLM Grader] Response parsing error: {val_err}", file=sys.stderr)
    except Exception as unexpected_err:  # noqa: BLE001
        print(f"[LLM Grader] Unexpected error: {unexpected_err}", file=sys.stderr)
    return None


def print_report(
    pytest_returncode: int,
    pytest_output: str,
    llm_result: dict | None,
) -> None:
    """Render the final Evaluation Report to stdout."""
    procedural_status = "PASSED" if pytest_returncode == 0 else "FAILED"

    print()
    print(SEPARATOR)
    print("           EVALUATION REPORT")
    print(SEPARATOR)

    print()
    print("[ SECTION 1 — Procedural Test Results ]")
    print(f"  Overall status : {procedural_status}")
    print()
    print("  Pytest output:")
    for line in pytest_output.splitlines():
        print(f"    {line}")

    print()
    print("[ SECTION 2 — LLM Rubric Score ]")
    if llm_result is not None:
        score = llm_result["score"]
        reasoning = llm_result["reasoning"]
        bar_filled = round(score / 10 * 20)
        bar = "#" * bar_filled + "-" * (20 - bar_filled)
        print(f"  Score     : {score} / 10  [{bar}]")
        print(f"  Reasoning : {reasoning}")
    else:
        print("  LLM grading was skipped due to an error (see stderr above).")

    print()
    print(SEPARATOR)
    print()


def main() -> None:
    print(f"Running procedural tests against: {SUBMISSION_PATH}")
    pytest_returncode, pytest_output = run_procedural_tests()

    print("Running LLM rubric evaluation …")
    llm_result = run_llm_grader()

    print_report(pytest_returncode, pytest_output, llm_result)

    # Exit with a non-zero code if procedural tests failed
    sys.exit(pytest_returncode)


if __name__ == "__main__":
    main()
