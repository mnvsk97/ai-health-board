from __future__ import annotations

import json
import os
import struct
import time
from typing import Any

import redis
from redis.commands.search.field import NumericField, TagField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from .config import load_settings
from .embeddings import generate_embedding
from .models import ComplianceStatus, Guideline, Run, Scenario, TranscriptEntry

SCENARIO_INDEX = "scenario_idx"
TRANSCRIPT_INDEX = "transcript_idx"

_MEM_STORE: dict[str, Any] = {}


def _use_memory() -> bool:
    return os.getenv("REDIS_FALLBACK", "0") == "1"


def _redis_client() -> redis.Redis:
    settings = load_settings()
    return redis.Redis(
        host=str(settings.get("redis_cloud_host") or ""),
        port=int(settings.get("redis_cloud_port") or 6379),
        username="default",
        password=str(settings.get("redis_cloud_password") or ""),
        decode_responses=True,
    )


def _redis_binary() -> redis.Redis:
    """Binary client for vector operations."""
    settings = load_settings()
    return redis.Redis(
        host=str(settings.get("redis_cloud_host") or ""),
        port=int(settings.get("redis_cloud_port") or 6379),
        username="default",
        password=str(settings.get("redis_cloud_password") or ""),
        decode_responses=False,
    )


def _set_json(key: str, value: Any, ttl: int | None = None) -> None:
    if _use_memory():
        _MEM_STORE[key] = value
        return
    payload = json.dumps(value)
    client = _redis_client()
    if ttl:
        client.setex(key, ttl, payload)
    else:
        client.set(key, payload)


def _get_json(key: str) -> Any | None:
    if _use_memory():
        return _MEM_STORE.get(key)
    data = _redis_client().get(key)
    return json.loads(data) if data else None


def save_scenario(scenario: Scenario) -> None:
    _set_json(f"scenario:{scenario.scenario_id}", scenario.model_dump())


def list_scenarios() -> list[Scenario]:
    if _use_memory():
        return [Scenario(**v) for k, v in _MEM_STORE.items() if k.startswith("scenario:")]
    keys = _redis_client().keys("scenario:*")
    scenarios: list[Scenario] = []
    for key in keys:
        data = _get_json(key)
        if data:
            scenarios.append(Scenario(**data))
    return scenarios


def create_run(run: Run) -> None:
    _set_json(f"run:{run.run_id}", run.model_dump())


def update_run(run: Run) -> None:
    run.updated_at = time.time()
    _set_json(f"run:{run.run_id}", run.model_dump())


def get_run(run_id: str) -> Run | None:
    data = _get_json(f"run:{run_id}")
    return Run(**data) if data else None


def append_transcript(run_id: str, entry: TranscriptEntry) -> None:
    key = f"transcript:{run_id}"
    if _use_memory():
        _MEM_STORE.setdefault(key, []).append(entry.model_dump())
        return
    _redis_client().rpush(key, json.dumps(entry.model_dump()))


def get_transcript(run_id: str) -> list[TranscriptEntry]:
    key = f"transcript:{run_id}"
    if _use_memory():
        return [TranscriptEntry(**e) for e in _MEM_STORE.get(key, [])]
    entries = _redis_client().lrange(key, 0, -1)
    return [TranscriptEntry(**json.loads(e)) for e in entries]


def save_grading(run_id: str, grading: dict[str, Any]) -> None:
    _set_json(f"grading:{run_id}", grading)


def get_grading(run_id: str) -> dict[str, Any] | None:
    return _get_json(f"grading:{run_id}")


def checkpoint(run_id: str, state: dict[str, Any], ttl: int = 3600) -> None:
    _set_json(f"checkpoint:{run_id}", state, ttl=ttl)


def restore_checkpoint(run_id: str) -> dict[str, Any] | None:
    return _get_json(f"checkpoint:{run_id}")


def get_attack_plan(scenario_id: str, rubric_hash: str) -> dict[str, Any] | None:
    return _get_json(f"attack_plan:{scenario_id}:{rubric_hash}")


def set_attack_plan(scenario_id: str, rubric_hash: str, plan: dict[str, Any]) -> None:
    _set_json(f"attack_plan:{scenario_id}:{rubric_hash}", plan)


def record_vector_attempt(vector: str, effective: bool) -> None:
    key = f"vector_stats:{vector}"
    if _use_memory():
        stats = _MEM_STORE.setdefault(key, {"attempted": 0, "effective": 0})
        stats["attempted"] += 1
        if effective:
            stats["effective"] += 1
        return
    client = _redis_client()
    client.hincrby(key, "attempted", 1)
    if effective:
        client.hincrby(key, "effective", 1)


def get_vector_rate(vector: str) -> float:
    key = f"vector_stats:{vector}"
    if _use_memory():
        stats = _MEM_STORE.get(key, {"attempted": 0, "effective": 0})
        attempted = int(stats.get("attempted") or 0)
        effective = int(stats.get("effective") or 0)
        return effective / attempted if attempted else 0.5
    client = _redis_client()
    attempted = int(client.hget(key, "attempted") or 0)
    effective = int(client.hget(key, "effective") or 0)
    return effective / attempted if attempted else 0.5


def save_guideline(guideline: Guideline) -> None:
    _set_json(f"compliance:guideline:{guideline.guideline_id}", guideline.model_dump())


def get_guideline(guideline_id: str) -> Guideline | None:
    data = _get_json(f"compliance:guideline:{guideline_id}")
    return Guideline(**data) if data else None


def set_compliance_status(status: ComplianceStatus) -> None:
    _set_json(f"compliance:status:{status.target_id}", status.model_dump())


def get_compliance_status(target_id: str) -> ComplianceStatus | None:
    data = _get_json(f"compliance:status:{target_id}")
    return ComplianceStatus(**data) if data else None


def _url_to_key(url: str) -> str:
    """Convert a URL to a safe Redis key component."""
    import hashlib

    return hashlib.sha256(url.encode()).hexdigest()[:16]


def save_extracted_guideline(guideline: dict) -> None:
    """Save an extracted guideline to Redis.

    Args:
        guideline: Dictionary containing guideline data with source_url.
    """
    source_url = guideline.get("source_url", "")
    key = f"guideline:extracted:{_url_to_key(source_url)}"
    _set_json(key, guideline)

    # Also maintain a URL index for lookups
    index_key = f"guideline:url_index:{_url_to_key(source_url)}"
    _set_json(index_key, {"url": source_url, "key": key})


def get_extracted_guideline_by_url(url: str) -> dict | None:
    """Retrieve an extracted guideline by its source URL.

    Args:
        url: Source URL of the guideline.

    Returns:
        Guideline dictionary if found, None otherwise.
    """
    key = f"guideline:extracted:{_url_to_key(url)}"
    return _get_json(key)


def list_extracted_guidelines() -> list[dict]:
    """List all extracted guidelines.

    Returns:
        List of guideline dictionaries.
    """
    if _use_memory():
        return [
            v for k, v in _MEM_STORE.items() if k.startswith("guideline:extracted:")
        ]
    keys = _redis_client().keys("guideline:extracted:*")
    guidelines: list[dict] = []
    for key in keys:
        data = _get_json(key)
        if data:
            guidelines.append(data)
    return guidelines


# =============================================================================
# Vector Search Operations
# =============================================================================


def _vec_dim() -> int:
    return int(load_settings().get("embedding_dimensions") or 3072)


def _vec_bytes(v: list[float]) -> bytes:
    return struct.pack(f"{len(v)}f", *v)


def create_vector_indexes() -> None:
    """Create vector indexes for semantic search."""
    if _use_memory():
        return
    c = _redis_binary()
    # Scenario index
    try:
        c.ft(SCENARIO_INDEX).dropindex(delete_documents=False)
    except redis.ResponseError:
        pass
    c.ft(SCENARIO_INDEX).create_index(
        (
            VectorField("embedding", "HNSW", {"TYPE": "FLOAT32", "DIM": _vec_dim(), "DISTANCE_METRIC": "COSINE"}),
            TagField("scenario_id"),
            TagField("source_type"),
            NumericField("created_at"),
        ),
        definition=IndexDefinition(prefix=["scenario:"], index_type=IndexType.HASH),
    )
    # Transcript index
    try:
        c.ft(TRANSCRIPT_INDEX).dropindex(delete_documents=False)
    except redis.ResponseError:
        pass
    c.ft(TRANSCRIPT_INDEX).create_index(
        (
            VectorField("embedding", "HNSW", {"TYPE": "FLOAT32", "DIM": _vec_dim(), "DISTANCE_METRIC": "COSINE"}),
            TagField("run_id"),
            TagField("role"),
            NumericField("timestamp"),
        ),
        definition=IndexDefinition(prefix=["transcript_entry:"], index_type=IndexType.HASH),
    )


def save_scenario_with_embedding(scenario: Scenario) -> None:
    """Save a scenario with its embedding for vector search."""
    if _use_memory():
        save_scenario(scenario)
        return
    emb = generate_embedding(f"{scenario.title}\n{scenario.description}")
    _redis_binary().hset(f"scenario:{scenario.scenario_id}", mapping={
        "data": json.dumps(scenario.model_dump()),
        "embedding": _vec_bytes(emb),
        "scenario_id": scenario.scenario_id,
        "source_type": scenario.source_type,
        "created_at": time.time(),
    })


def save_transcript_with_embedding(run_id: str, entry: TranscriptEntry, idx: int) -> None:
    """Save a transcript entry with its embedding."""
    if _use_memory():
        append_transcript(run_id, entry)
        return
    emb = generate_embedding(entry.content)
    _redis_binary().hset(f"transcript_entry:{run_id}:{idx}", mapping={
        "data": json.dumps(entry.model_dump()),
        "embedding": _vec_bytes(emb),
        "run_id": run_id,
        "role": entry.role,
        "timestamp": entry.timestamp,
    })


def search_similar_scenarios(query: str, k: int = 5) -> list[tuple[Scenario, float]]:
    """Find scenarios similar to the query text."""
    if _use_memory():
        return [(s, 0.0) for s in list_scenarios()[:k]]
    vec = _vec_bytes(generate_embedding(query))
    q = Query(f"(*)=>[KNN {k} @embedding $vec AS score]").sort_by("score").return_fields("data", "score").dialect(2)
    res = _redis_binary().ft(SCENARIO_INDEX).search(q, {"vec": vec})
    out = []
    for doc in res.docs:
        data = json.loads(doc.data.decode() if isinstance(doc.data, bytes) else doc.data)
        out.append((Scenario(**data), float(doc.score)))
    return out


def search_similar_transcripts(query: str, k: int = 10) -> list[tuple[TranscriptEntry, str, float]]:
    """Find transcript entries similar to the query."""
    if _use_memory():
        return []
    vec = _vec_bytes(generate_embedding(query))
    q = Query(f"(*)=>[KNN {k} @embedding $vec AS score]").sort_by("score").return_fields("data", "run_id", "score").dialect(2)
    res = _redis_binary().ft(TRANSCRIPT_INDEX).search(q, {"vec": vec})
    out = []
    for doc in res.docs:
        data = json.loads(doc.data.decode() if isinstance(doc.data, bytes) else doc.data)
        rid = doc.run_id.decode() if isinstance(doc.run_id, bytes) else doc.run_id
        out.append((TranscriptEntry(**data), rid, float(doc.score)))
    return out


# =============================================================================
# Pub/Sub & Audit
# =============================================================================


def publish_run_event(run_id: str, event: dict[str, Any]) -> int:
    """Publish a run event."""
    if _use_memory():
        return 0
    return _redis_client().publish(f"run_events:{run_id}", json.dumps(event))


def add_audit_log(run_id: str, event_type: str, data: dict[str, Any]) -> str:
    """Add an audit log entry."""
    if _use_memory():
        return "mem-0"
    return _redis_client().xadd(f"audit:{run_id}", {
        "event_type": event_type,
        "ts": str(time.time()),
        "data": json.dumps(data),
    })
