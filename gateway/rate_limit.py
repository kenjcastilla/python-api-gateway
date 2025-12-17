import time
from pathlib import Path
import redis.exceptions
from redis.asyncio import Redis

LUA_SCRIPT = Path(__file__).parent / 'redis/token/bucket.lua'
LUA = LUA_SCRIPT.read_text()

class RateLimiter:
    """
    Redis-backed token-bucket rate limiter.

    Utilizes Lua script to implement atomic check-and-decrement semantics across
    concurrent gateway instances.
    """
    def __init__(self, redis: Redis):
        self.redis = redis
        self.sha: str|None = None

    async def load(self) -> None:
        """
        Load LUA script into Redis and cache the SHA.
        :return:
        """
        self.sha = await self.redis.script_load(LUA)

    async def allow(self,
                    key: str,
                    capacity: int,
                    rate: float,
                    tokens: int=1) -> tuple[bool, float]:
        """
        Attempt to consume tokens from the Redis bucket.
        :return: (allowed, remaining_tokens)
        """

        if self.sha is None:
            raise RuntimeError("RateLimiter not initialized. Call load() first.")

        now_ms = int(time.time() * 1000)
        try:
            result = await self.redis.evalsha(self.sha,
                                              0, # num Redis keys passed in explicitly
                                          key,
                                          capacity,
                                          rate,
                                          now_ms,
                                          tokens)
        except redis.exceptions.NoScriptError:
            await self.load()
            result = await self.redis.evalsha(self.sha,
                                              0,  # num Redis keys passed in explicitly
                                              key,
                                              capacity,
                                              rate,
                                              now_ms,
                                              tokens)
        allowed = bool(result[0])
        remaining = float(result[1])

        return allowed, remaining
