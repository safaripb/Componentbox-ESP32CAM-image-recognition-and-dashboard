from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field


DEFAULT_IMAGE_UPLOADS_PER_MINUTE = int(os.getenv("RESISTOR_IMAGE_RATE_LIMIT", "12"))


@dataclass
class SlidingWindowRateLimiter:
    max_events: int = DEFAULT_IMAGE_UPLOADS_PER_MINUTE
    window_seconds: int = 60
    _events: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))

    def accept(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        bucket = self._events[key]

        while bucket and now - bucket[0] >= self.window_seconds:
            bucket.popleft()

        if len(bucket) >= self.max_events:
            retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
            return False, retry_after

        bucket.append(now)
        return True, 0
