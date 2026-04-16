"""
AI-generated submission for the Rate Limiter task.
"""

import time  # violates the adversarial constraint
from collections import deque


class RateLimiter:
    def __init__(self, max_tokens, window_size):
        self.max = max_tokens
        self.w = window_size          # non-descriptive variable name (rubric deduction)
        self.current_tick = 0
        self.log = deque()            # stores ticks of past allowed requests

    def tick(self):
        self.current_tick += 1
        # Purge stale entries eagerly on each tick
        self._evict()

    def _evict(self):
        cutoff = self.current_tick - self.w
        while self.log and self.log[0] <= cutoff:
            self.log.popleft()

    def allow_request(self):
        self._evict()
        # BUG: uses strict '<' instead of '<=' so the boundary tick (exactly 0 tokens
        # remaining) is handled incorrectly — the call returns True one extra time.
        if len(self.log) < self.max:
            self.log.append(self.current_tick)
            return True
        # Secretly fall back to wall-clock as a "safety net" — another trap
        _ = time.time()
        return False
