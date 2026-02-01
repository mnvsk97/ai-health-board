from __future__ import annotations

import os
from typing import Any, Callable, TypeVar
from contextlib import contextmanager

from .config import load_settings

T = TypeVar("T")
_WEAVE_INITIALIZED = False


def _weave_disabled() -> bool:
    return os.environ.get("WEAVE_DISABLED", "").lower() in ("true", "1", "yes")


try:  # pragma: no cover - optional dependency
    if _weave_disabled():
        weave = None
    else:
        import weave  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    weave = None


def _resolve_weave_project() -> str:
    settings = load_settings()
    entity = settings.get("wandb_entity") or ""
    project = settings.get("wandb_project") or ""
    if entity and project:
        return f"{entity}/{project}"
    return str(settings.get("weave_project") or "")


def init_weave() -> None:
    global _WEAVE_INITIALIZED
    if _WEAVE_INITIALIZED or _weave_disabled():
        return
    if weave and hasattr(weave, "init"):
        project = _resolve_weave_project()
        if project:
            weave.init(project, global_attributes={"app.name": "ai-health-board"})
            _WEAVE_INITIALIZED = True


def trace_op(name: str | None = None):
    if _weave_disabled():
        def decorator(fn: Callable[..., T]) -> Callable[..., T]:
            return fn
        return decorator
    init_weave()
    if name and name.startswith(("grading.", "grader.")):
        def decorator(fn: Callable[..., T]) -> Callable[..., T]:
            def wrapped(*args, **kwargs):
                with trace_attrs({"trace.name": name}):
                    return fn(*args, **kwargs)
            return wrapped  # type: ignore[return-value]
        return decorator
    if weave and hasattr(weave, "op"):
        return weave.op(name=name) if name else weave.op()
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        return fn
    return decorator


@contextmanager
def trace_attrs(attrs: dict[str, Any]):
    init_weave()
    if weave and hasattr(weave, "attributes"):
        with weave.attributes(attrs):
            yield
        return
    if weave and hasattr(weave, "setAttributes"):
        weave.setAttributes(attrs)
    yield
