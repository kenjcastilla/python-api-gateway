class FakeRateLimiter:
    def __init__(self, allow: bool=True):
        self.allow_next = allow
        self.calls = []

    async def load(self):
        pass

    async def allow(self, key:str, capacity:int, rate:float, tokens:int = 1):
        self.calls.append((key, capacity, rate, tokens))

        return self.allow_next, capacity
