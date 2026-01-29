from asyncio import sleep
from gateway.rate_limit import RateLimiter


async def test_redis_connection(redis_client):
    result = await redis_client.ping()

    assert result is True


async def test_rate_limiter_allows_within_capacity(rate_limiter):
    """Test that rate limiter allows requests when tokens are within capacity"""
    key = 'test:user:123'
    capacity = 10
    rate = 1.0  # 1 token/sec

    # First request should be allowed
    allowed, remaining_tokens = await rate_limiter.allow(key, capacity, rate)

    assert allowed is True
    assert remaining_tokens <= capacity


async def test_rate_limiter_blocks_over_capacity(rate_limiter):
    """Test that rate limiter blocks request when tokens are over capacity"""
    key = 'test:user:123'
    capacity = 3
    rate = 1.0

    # Use up all the tokens
    for _ in range(capacity):
        allowed, _ = await rate_limiter.allow(key, capacity, rate, tokens=1)
        assert allowed is True

    # The next request shouldn't be allowed
    allowed, remaining_tokens = await rate_limiter.allow(key, capacity, rate, tokens=1)

    assert allowed is False
    assert remaining_tokens == 0


async def test_rate_limiter_refills_over_time(rate_limiter):
    """Test that rate limiter refills over time at the specified rate"""
    key = 'test:user:123'
    capacity = 10
    rate = 10.0

    for _ in range(capacity):
        await rate_limiter.allow(key, capacity, rate, tokens=1)

    allowed, remaining_tokens = await rate_limiter.allow(key, capacity, rate, tokens=1)
    assert allowed is False

    # Wait for limiter refill
    await sleep(0.5) # 5 tokens should be generated in 0.5 seconds (10 tokens/sec)

    # Next request should be allowed
    allowed, remaining_tokens = await rate_limiter.allow(key, capacity, rate, tokens=1)
    assert allowed is True
    assert 0 < remaining_tokens <= capacity


async def test_rate_limiter_independent_buckets(rate_limiter):
    """Test that different keys yield independent buckets"""
    key1 = 'test:user:111'
    key2 = 'test:user:222'
    capacity = 5
    rate = 1.0

    # Drain user1 bucket
    for _ in range(capacity):
        await rate_limiter.allow(key1, capacity, rate, tokens=1)

    # User1 request should not be allowed
    allowed, _ = await rate_limiter.allow(key1, capacity, rate, tokens=1)
    assert allowed is False

    # User2 request should be allowed
    allowed, _ = await rate_limiter.allow(key2, capacity, rate, tokens=1)
    assert allowed is True


async def test_rate_limiter_state_persistence(redis_client):
    """Test that rate limit state persists in Redis"""
    key = 'test:user:123'
    capacity = 10
    rate = 1.0

    # Create first limiter; use some tokens
    limiter1 = RateLimiter(redis_client)
    await limiter1.load()
    await limiter1.allow(key, capacity, rate, tokens=5)

    # Create another limiter; this simulates app restart
    limiter2 = RateLimiter(redis_client)
    await limiter2.load()

    allowed, remaining_tokens = await limiter2.allow(key, capacity, rate, tokens=1)
    assert allowed is True
    assert remaining_tokens <= capacity
