"""
Procedural pytest suite for dummy_ai_submission.py.
"""

import ast
import sys
import os
import pytest

# Make the submissions package importable regardless of working directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from submissions.active_run import RateLimiter

SUBMISSION_PATH = os.path.join(
    os.path.dirname(__file__), "..", "submissions", "active_run.py"
)


# ---------------------------------------------------------------------------
# Test 1 — Basic allowance within a window
# ---------------------------------------------------------------------------
def test_basic_allowance():
    """Requests up to max_tokens within the same tick must all be allowed."""
    rate_limiter = RateLimiter(max_tokens=3, window_size=5)

    first_request = rate_limiter.allow_request()
    second_request = rate_limiter.allow_request()
    third_request = rate_limiter.allow_request()

    assert first_request is True, "First request should be allowed"
    assert second_request is True, "Second request should be allowed"
    assert third_request is True, "Third request (at the limit) should be allowed"


# ---------------------------------------------------------------------------
# Test 2 — Adversarial trap: forbidden imports must not be present
# ---------------------------------------------------------------------------
def test_adversarial_trap():
    """
    The task explicitly forbids the 'time' and 'datetime' modules.
    Parse the submission's AST to detect any such import.
    """
    with open(SUBMISSION_PATH, "r", encoding="utf-8") as source_file:
        source_code = source_file.read()

    tree = ast.parse(source_code)
    forbidden_modules = {"time", "datetime"}
    imported_modules = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(node.module.split(".")[0])

    violations = forbidden_modules & imported_modules

    assert not violations, (
        f"Submission illegally imports forbidden module(s): {violations}. "
        "The task prohibits use of 'time' or 'datetime'."
    )


# ---------------------------------------------------------------------------
# Test 3 — Edge case: exact boundary tick expiration
# ---------------------------------------------------------------------------
def test_edge_case_expiration():
    """
    After exactly window_size ticks the oldest entries should be expired,
    freeing tokens so new requests are accepted.

    Also validates the boundary: the (max_tokens + 1)-th request in the same
    window must be denied, and exactly 0 tokens remaining means the next call
    returns False (not True).
    """
    max_tokens = 2
    window_size = 3
    rate_limiter = RateLimiter(max_tokens=max_tokens, window_size=window_size)

    # Fill the window completely
    assert rate_limiter.allow_request() is True, "1st request should be allowed"
    assert rate_limiter.allow_request() is True, "2nd request should be allowed"

    # Exactly 0 tokens left — must be denied
    assert rate_limiter.allow_request() is False, (
        "When exactly 0 tokens remain the request must be denied (boundary condition)"
    )

    # Advance exactly window_size ticks to expire all prior entries
    for _ in range(window_size):
        rate_limiter.tick()

    # Window is now clear — requests should be allowed again
    assert rate_limiter.allow_request() is True, (
        "After window_size ticks all old entries should be expired; "
        "new request must be allowed"
    )
