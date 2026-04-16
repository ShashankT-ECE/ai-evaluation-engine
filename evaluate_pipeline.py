"""
Multi-Run Evaluation Pipeline Orchestrator.

For each submission in the run manifest:
  1. Copy it to submissions/active_run.py.
  2. Run the procedural pytest suite and capture results.
  3. Categorize any failure as "Rule Violation" or "Logic Error".
  4. If all procedural tests pass, invoke the LLM heuristic grader.
  5. Clean up active_run.py.

Renders a final Rich dashboard table with per-run results and overall pass rate.
"""

import importlib
import os
import shutil
import subprocess
import sys

from rich.console import Console
from rich.table import Table
from rich import box

sys.path.insert(0, os.path.dirname(__file__))

from graders.llm_grader import evaluate_code_with_llm

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUBMISSIONS_DIR = os.path.join(os.path.dirname(__file__), "submissions")
ACTIVE_RUN_PATH = os.path.join(SUBMISSIONS_DIR, "active_run.py")
GRADER_PATH = os.path.join("graders", "procedural_grader.py")

RUN_MANIFEST = [
    "run_1_trap.py",
    "run_2_logic.py",
    "run_3_pass.py",
]

STATUS_PASS = "[bold green]PASS[/bold green]"
STATUS_FAIL = "[bold red]FAIL[/bold red]"
CATEGORY_RULE = "[yellow]Rule Violation[/yellow]"
CATEGORY_LOGIC = "[orange3]Logic Error[/orange3]"
CATEGORY_NONE = "[dim]—[/dim]"

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stage_submission(run_filename: str) -> None:
    source = os.path.join(SUBMISSIONS_DIR, run_filename)
    shutil.copy(source, ACTIVE_RUN_PATH)

    # Invalidate any cached import of active_run so pytest picks up the new file
    for mod_name in list(sys.modules):
        if "active_run" in mod_name:
            del sys.modules[mod_name]


def _cleanup_active_run() -> None:
    if os.path.exists(ACTIVE_RUN_PATH):
        os.remove(ACTIVE_RUN_PATH)
    for mod_name in list(sys.modules):
        if "active_run" in mod_name:
            del sys.modules[mod_name]


def run_procedural_tests() -> tuple[bool, str]:
    """
    Execute the pytest suite in a subprocess.

    Returns:
        (passed: bool, output: str)
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", GRADER_PATH, "-v", "--tb=short"],
        capture_output=True,
        text=True,
    )
    combined = result.stdout + result.stderr
    return result.returncode == 0, combined


def categorize_failure(pytest_output: str) -> str:
    """
    Classify the nature of a procedural test failure.

    - "Rule Violation" when the adversarial import trap fired.
    - "Logic Error"    for all other failures.

    Checks per-line so that a passing test_adversarial_trap line alongside a
    failing test_edge_case_expiration line is not misclassified as a Rule Violation.
    """
    for line in pytest_output.splitlines():
        if "FAILED" in line and "test_adversarial_trap" in line:
            return CATEGORY_RULE
    return CATEGORY_LOGIC


def run_llm_grader() -> tuple[str, str]:
    """
    Invoke the LLM heuristic grader on the current active_run.

    Returns:
        (score_display: str, reasoning: str)
    """
    try:
        result = evaluate_code_with_llm(ACTIVE_RUN_PATH)
        score = result["score"]
        color = "green" if score >= 7 else "yellow" if score >= 4 else "red"
        return f"[{color}]{score} / 10[/{color}]", result["reasoning"]
    except EnvironmentError as err:
        return "[dim]N/A[/dim]", f"[dim]Config error: {err}[/dim]"
    except Exception as err:  # noqa: BLE001
        return "[dim]N/A[/dim]", f"[dim]Grader error: {err}[/dim]"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    results: list[dict] = []

    for run_filename in RUN_MANIFEST:
        console.print(f"\n[bold cyan]► Evaluating {run_filename}[/bold cyan]")

        _stage_submission(run_filename)

        passed, pytest_output = run_procedural_tests()

        if passed:
            status = STATUS_PASS
            category = CATEGORY_NONE
            console.print("  [green]Procedural tests passed — running LLM grader…[/green]")
            llm_score, llm_reasoning = run_llm_grader()
        else:
            status = STATUS_FAIL
            category = categorize_failure(pytest_output)
            llm_score = "[dim]Skipped[/dim]"
            llm_reasoning = "[dim]Skipped — procedural tests failed[/dim]"
            console.print(f"  [red]Procedural tests failed[/red] — category: {category}")

        _cleanup_active_run()

        results.append(
            {
                "run": run_filename,
                "status": status,
                "category": category,
                "llm_score": llm_score,
                "llm_reasoning": llm_reasoning,
            }
        )

    # -----------------------------------------------------------------------
    # Dashboard
    # -----------------------------------------------------------------------
    pass_count = sum(1 for r in results if "PASS" in r["status"])
    pass_rate = pass_count / len(results) * 100

    table = Table(
        title="\n[bold white]AI Model Evaluation Dashboard[/bold white]",
        box=box.ROUNDED,
        show_lines=True,
        title_style="bold",
        header_style="bold magenta",
    )

    table.add_column("Run", style="cyan", no_wrap=True, min_width=18)
    table.add_column("Procedural", justify="center", min_width=12)
    table.add_column("Failure Category", justify="center", min_width=18)
    table.add_column("LLM Score", justify="center", min_width=10)
    table.add_column("LLM Reasoning", min_width=42)

    for row in results:
        table.add_row(
            row["run"],
            row["status"],
            row["category"],
            row["llm_score"],
            row["llm_reasoning"],
        )

    console.print()
    console.print(table)
    console.print(
        f"\n[bold]Overall Pass Rate:[/bold] "
        f"[{'green' if pass_rate == 100 else 'yellow' if pass_rate >= 50 else 'red'}]"
        f"{pass_count}/{len(results)}  ({pass_rate:.0f}%)[/]"
    )
    console.print()

    sys.exit(0 if pass_count == len(results) else 1)


if __name__ == "__main__":
    main()
