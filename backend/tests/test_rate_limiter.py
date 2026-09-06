from app.services.rate_limiter import SlidingWindowRateLimiter


def test_rate_limiter_rejects_events_after_limit():
    limiter = SlidingWindowRateLimiter(max_events=2, window_seconds=60)

    assert limiter.accept("camera-a") == (True, 0)
    assert limiter.accept("camera-a") == (True, 0)

    accepted, retry_after = limiter.accept("camera-a")
    assert accepted is False
    assert retry_after > 0


def test_rate_limiter_tracks_clients_independently():
    limiter = SlidingWindowRateLimiter(max_events=1, window_seconds=60)

    assert limiter.accept("camera-a") == (True, 0)
    assert limiter.accept("camera-b") == (True, 0)
