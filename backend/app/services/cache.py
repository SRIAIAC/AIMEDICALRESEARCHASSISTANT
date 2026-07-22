import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

_store: dict[str, tuple[float, Any]] = {}


def _make_key(namespace: str, payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"{namespace}:{digest}"


async def cached(
    namespace: str, payload: dict[str, Any], ttl_seconds: int, fn: Callable[[], Awaitable[Any]]
) -> Any:
    """Runs `fn()` and caches the result in-process, keyed by namespace + a hash
    of `payload`. A repeat request with the same inputs within `ttl_seconds`
    returns the cached result instead of re-running expensive agent calls
    (external API round-trips + a local LLM synthesis step that can take
    30s-2min). Cache is process-memory only — it resets on server restart,
    same tradeoff already accepted for the news feed's cache.
    """
    key = _make_key(namespace, payload)
    now = time.monotonic()
    entry = _store.get(key)
    if entry is not None and now - entry[0] < ttl_seconds:
        return entry[1]
    result = await fn()
    _store[key] = (now, result)
    return result
