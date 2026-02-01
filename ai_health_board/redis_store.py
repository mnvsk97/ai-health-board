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


def save_attack_vector(attack_id: str, payload: dict[str, Any]) -> None:
    _set_json(f"attack:global:{attack_id}", payload)


def get_attack_vector(attack_id: str) -> dict[str, Any] | None:
    return _get_json(f"attack:global:{attack_id}")


def _get_attack_stats(attack_id: str) -> dict[str, Any]:
    key = f"attack:stats:{attack_id}"
    if _use_memory():
        return _MEM_STORE.get(key, {"attempts": 0, "successes": 0, "severity_total": 0.0})
    stats = _redis_client().hgetall(key)
    return {
        "attempts": int(stats.get("attempts") or 0),
        "successes": int(stats.get("successes") or 0),
        "severity_total": float(stats.get("severity_total") or 0.0),
    }


def update_attack_stats(
    attack_id: str,
    success: bool,
    severity: float,
    tags: list[str],
) -> dict[str, Any]:
    key = f"attack:stats:{attack_id}"
    if _use_memory():
        stats = _MEM_STORE.setdefault(key, {"attempts": 0, "successes": 0, "severity_total": 0.0})
        stats["attempts"] += 1
        if success:
            stats["successes"] += 1
        stats["severity_total"] += float(severity)
    else:
        client = _redis_client()
        pipe = client.pipeline()
        pipe.hincrby(key, "attempts", 1)
        if success:
            pipe.hincrby(key, "successes", 1)
        pipe.hincrbyfloat(key, "severity_total", float(severity))
        pipe.execute()

    stats = _get_attack_stats(attack_id)
    attempts = max(int(stats.get("attempts") or 0), 1)
    successes = int(stats.get("successes") or 0)
    severity_avg = float(stats.get("severity_total") or 0.0) / attempts
    success_rate = successes / attempts
    confidence = success_rate * (0.5 + 0.5 * severity_avg)

    all_tags = list({*(tags or []), "global"})
    if _use_memory():
        for tag in all_tags:
            tag_key = f"attack:tag:{tag}"
            ranking = _MEM_STORE.setdefault(tag_key, {})
            ranking[attack_id] = confidence
    else:
        client = _redis_client()
        for tag in all_tags:
            client.zadd(f"attack:tag:{tag}", {attack_id: confidence})

    return {
        "attempts": attempts,
        "successes": successes,
        "success_rate": success_rate,
        "severity_avg": severity_avg,
        "confidence": confidence,
    }


def get_attack_candidates(
    tags: list[str] | None = None,
    limit: int = 3,
    min_confidence: float = 0.0,
) -> list[dict[str, Any]]:
    tag_list = tags or ["global"]
    candidates: dict[str, float] = {}

    if _use_memory():
        for tag in tag_list:
            tag_key = f"attack:tag:{tag}"
            ranking = _MEM_STORE.get(tag_key, {})
            for attack_id, score in sorted(ranking.items(), key=lambda item: item[1], reverse=True)[:limit]:
                candidates[attack_id] = max(candidates.get(attack_id, 0.0), float(score))
    else:
        client = _redis_client()
        for tag in tag_list:
            tag_key = f"attack:tag:{tag}"
            results = client.zrevrangebyscore(
                tag_key,
                "+inf",
                min_confidence,
                start=0,
                num=limit,
                withscores=True,
            )
            for attack_id, score in results:
                candidates[str(attack_id)] = max(candidates.get(str(attack_id), 0.0), float(score))

    ordered = sorted(candidates.items(), key=lambda item: item[1], reverse=True)[:limit]
    payloads: list[dict[str, Any]] = []
    for attack_id, score in ordered:
        payload = get_attack_vector(attack_id) or {"attack_id": attack_id}
        stats = _get_attack_stats(attack_id)
        attempts = int(stats.get("attempts") or 0)
        successes = int(stats.get("successes") or 0)
        severity_avg = (
            float(stats.get("severity_total") or 0.0) / attempts
            if attempts
            else 0.0
        )
        payloads.append(
            {
                "attack_id": attack_id,
                "prompt": payload.get("prompt"),
                "category": payload.get("category"),
                "tags": payload.get("tags", []),
                "confidence": score,
                "attempts": attempts,
                "success_rate": successes / attempts if attempts else 0.0,
                "severity_avg": severity_avg,
            }
        )
    return payloads


def save_prompt_overlay(
    tags: list[str],
    strategy_text: str,
    confidence: float,
    ttl_seconds: int,
) -> None:
    payload = {
        "tags": tags,
        "strategy": strategy_text,
        "confidence": confidence,
    }
    key = f"prompt:overlay:{':'.join(tags) if tags else 'global'}"
    _set_json(key, payload, ttl=ttl_seconds)


def get_prompt_overlay(tags: list[str]) -> dict[str, Any] | None:
    key = f"prompt:overlay:{':'.join(tags) if tags else 'global'}"
    return _get_json(key)

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
