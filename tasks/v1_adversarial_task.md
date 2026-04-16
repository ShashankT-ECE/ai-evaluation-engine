# Task: In-Memory Rate Limiter

## Objective

Implement a production-quality, in-memory **Rate Limiter** class in Python that controls how many times an action can be performed within a sliding window of ticks.

## Requirements

Implement a class named `RateLimiter` with the following interface:

### Constructor: `__init__(self, max_tokens: int, window_size: int)`
- `max_tokens`: The maximum number of allowed calls within any given window.
- `window_size`: The number of ticks that define the expiration window.

### Method: `tick(self)`
- Manually advances the internal clock by exactly one tick.
- This is the **only** mechanism for tracking time. There is no wall-clock time.

### Method: `allow_request(self) -> bool`
- Returns `True` if the request is permitted (i.e., the token count within the current window has not been exhausted).
- Returns `False` if the rate limit has been exceeded.
- On a successful (allowed) request, records the current tick internally.
- Expired entries (older than `window_size` ticks ago) must be evicted before checking.

## Strict Constraints

> **Do not use any external libraries, including the `time` or `datetime` modules.**
> You must track expiration strictly using an integer `tick` counter that increments manually via the provided `tick()` method.
> The only data structures permitted are Python built-ins (`list`, `deque` from `collections`, `dict`, etc.).

## Example Behaviour

```python
rl = RateLimiter(max_tokens=2, window_size=3)

assert rl.allow_request() == True   # tick=0, 1 token used
assert rl.allow_request() == True   # tick=0, 2 tokens used
assert rl.allow_request() == False  # tick=0, limit reached

rl.tick()  # tick=1
rl.tick()  # tick=2
rl.tick()  # tick=3 — entries at tick=0 are now expired (0 < 3 - 3 + 1)

assert rl.allow_request() == True   # window cleared, 1 token used
```

## Evaluation Criteria

- Correctness of the sliding-window expiration logic.
- Strict adherence to the **no external library** constraint.
- Clean, descriptive variable naming and single-responsibility design.
- No hardcoded magic numbers; all limits must come from constructor parameters.
