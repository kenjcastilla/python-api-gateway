from pydantic import BaseModel, Field

class RouteRule(BaseModel):
    prefix: str
    upstream: str

class Settings(BaseModel):
    routes: list[RouteRule] = Field(default_factory=list)

# default in-memory config
settings = Settings(
    routes=[
        RouteRule(prefix="/api/users", upstream="http://users-service:8000"),
        RouteRule(prefix="/api/orders", upstream="http://user-service:8000"),
    ]
)
