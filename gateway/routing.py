from .config import settings

# Basic prefix matching

def find_upstream(path: str) -> tuple[str | None, str | None]:
    for rule in settings.routes:
        if path.startswith(rule.prefix):
            suffix = path[len(rule.prefix):] or '/'
            return rule.upstream, suffix
    return None, None
