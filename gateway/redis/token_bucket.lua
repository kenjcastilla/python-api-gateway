--Lua script for rate limit with Redis (used in ../rate_limit.py)

local key = ARGV[1]
local capacity = tonumber(ARGV[2])
local rate = tonumber(ARGV[3])
local now = tonumber(ARGV[4])
local requested = tonumber(ARGV[5])

local state = redis.call('HMGET', key, 'tokens', 'last_ts')
local tokens = tonumber(state[1])
local last = tonumber(state[2])

if tokens == nil then
	tokens = capacity
	last = now
end

local elapsed = math.max(0, (now - last) / 1000.0)
local refill = elapsed * rate
tokens = math.min(capacity, tokens + refill)

if tokens < requested then
	redis.call('HMSET', key, 'tokens', tokens, 'last_ts', now)
	redis.call('PEXPIRE', key, 6e4)
	return {0, tokens}
else
	tokens = tokens - requested
	redis.call('HMSET', key, 'tokens', tokens, 'last_ts', now)
	redis.call('PEXPIRE', key, 6e4)
	return {1, tokens}
end
