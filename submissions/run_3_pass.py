"""
Run 3 — Passing submission.
No forbidden imports, correct boundary logic, descriptive variable names,
single-responsibility methods, and no hardcoded magic numbers.
"""

from collections import deque


class RateLimiter:
    def __init__(self, max_tokens: int, window_size: int) -> None:
        self.max_tokens = max_tokens
        self.window_size = window_size
        self.current_tick = 0
        self.allowed_request_ticks: deque[int] = deque()

    def tick(self) -> None:
        """Advance the internal clock by one tick and evict stale entries."""
        self.current_tick += 1
        self._evict_expired_entries()

    def _evict_expired_entries(self) -> None:
        """Remove all recorded ticks that have fallen outside the current window."""
        expiry_cutoff = self.current_tick - self.window_size
        while self.allowed_request_ticks and self.allowed_request_ticks[0] <= expiry_cutoff:
            self.allowed_request_ticks.popleft()

    def allow_request(self) -> bool:
        """
        Approve or deny an incoming request based on the current token budget.

        Returns True and records the tick if the request is within the limit.
        Returns False if the token budget for the current window is exhausted.
        """
        self._evict_expired_entries()
        tokens_used_in_window = len(self.allowed_request_ticks)
        if tokens_used_in_window < self.max_tokens:
            self.allowed_request_ticks.append(self.current_tick)
            return True
        return False
