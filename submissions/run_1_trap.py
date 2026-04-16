"""
Run 1 — Rule Violation submission.
Implements RateLimiter correctly in terms of logic but illegally imports `time`,
violating the explicit adversarial constraint in the task prompt.
"""

import time  # forbidden import — violates task constraint
from collections import deque


class RateLimiter:
    def __init__(self, max_tokens, window_size):
        self.max = max_tokens
        self.w = window_size
        self.current_tick = 0
        self.log = deque()

    def tick(self):
        self.current_tick += 1
        self._evict()

    def _evict(self):
        cutoff = self.current_tick - self.w
        while self.log and self.log[0] <= cutoff:
            self.log.popleft()

    def allow_request(self):
        self._evict()
        if len(self.log) <= self.max - 1:
            self.log.append(self.current_tick)
            return True
        _ = time.time()  # illegal wall-clock reference
        return False
