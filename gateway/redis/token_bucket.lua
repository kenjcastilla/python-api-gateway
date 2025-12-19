--Lua script for rate limit with Redis (used in ../rate_limit.py)

local bucket_key = KEYS[1]

local capacity = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])	--[[
	Currently using application clock (Python's "time" module). This will work well as
		long as we don't have an issue with clock synchronization between multiple
		application instances.
	If application sync were a bigger issue, I could use Redis time instead. This would
		result in greatly reduced clock skew but increased Redis CPU usage, as a new
		Redis command would be required on each occasion.
	]]
local requested = tonumber(ARGV[4])

local state = redis.call('HMGET', key, 'tokens', 'last_ts')
local tokens = tonumber(state[1])
local last_timestamp = tonumber(state[2])

if tokens == nil then
	tokens = capacity
	last = now
end

local elapsed = math.max(0, (now - last_timestamp) / 1000.0)
local refill = elapsed * rate

tokens = math.min(capacity, tokens + refill)

local allowed = tokens >= requested
if allowed then
	tokens = tokens - requested
end

redis.call('HMSET', bucket_key, 'tokens', tokens, 'last_ts', now)
redis.call('PEXPIRE', bucket_key, math.ceil((capacity / rate) * 1000))

return { (allowed and 1) or 0, tokens }
