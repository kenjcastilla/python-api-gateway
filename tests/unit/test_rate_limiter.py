from gateway.testing.fake_limiter import FakeRateLimiter


async def test_rate_limiter_allows_by_default():
    limiter = FakeRateLimiter(allow=True)

    allowed, remaining = await limiter.allow(
        key="test",
        capacity=10,
        rate=1.0,
    )

    assert allowed is True
    assert remaining == 10


async def test_rate_limiter_blocks_when_configured():
    limiter = FakeRateLimiter(allow=False)

    allowed, _ = await limiter.allow(
        key="test",
        capacity=10,
        rate=1.0,
    )

    assert allowed is False
