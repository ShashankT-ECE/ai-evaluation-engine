"""
Run 2 — Logic Error submission.
No forbidden imports, but contains an off-by-one bug: uses strict `<` instead
of `<=` in the eviction cutoff comparison, causing the boundary tick entry to
survive one tick longer than it should. This produces incorrect behaviour when
`allow_request` is called exactly `window_size` ticks after the window filled.
"""

from collections import deque


class RateLimiter:
    def __init__(self, max_tokens, window_size):
        self.max = max_tokens
        self.window = window_size
        self.current_tick = 0
        self.request_log = deque()

    def tick(self):
        self.current_tick += 1
        self._evict_expired()

    def _evict_expired(self):
        # BUG: strict `<` means entries at exactly the cutoff tick are NOT evicted.
        # Correct operator is `<=`.
        cutoff = self.current_tick - self.window
        while self.request_log and self.request_log[0] < cutoff:
            self.request_log.popleft()

    def allow_request(self):
        self._evict_expired()
        if len(self.request_log) < self.max:
            self.request_log.append(self.current_tick)
            return True
        return False
