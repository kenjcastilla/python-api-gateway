from gateway.routing import find_upstream
from gateway.config import RouteRule, settings


def setup_function():
    settings.routes = [
        RouteRule(prefix='/hello', upstream='http://a'),
        RouteRule(prefix='/api', upstream='http://b'),
    ]


def test_find_upstream_exact_match():
    upstream, suffix = find_upstream('/hello')
    assert upstream == 'http://a'
    assert suffix == '/'


def test_find_upstream_prefix_match():
    upstream, suffix = find_upstream('/api/users')
    assert upstream == 'http://b'
    assert suffix == '/users'

def test_find_upstream_not_found():
    upstream, suffix = find_upstream('/unknown')
    assert upstream is None
    assert suffix is None
