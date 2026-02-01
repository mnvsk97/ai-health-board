from __future__ import annotations

import json
import os
import struct
import time
from typing import Any

import redis
from loguru import logger
from redis.commands.search.field import NumericField, TagField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from .config import load_settings
from .embeddings import generate_embedding
from .models import (
    BatchRun,
    ComplianceStatus,
    Guideline,
    IntakeSession,
    PatientIdentity,
    Run,
    Scenario,
    TranscriptEntry,
)

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
    try:
        payload = json.dumps(value)
        client = _redis_client()
        if ttl:
            client.setex(key, ttl, payload)
        else:
            client.set(key, payload)
    except Exception:
        logger.exception("Redis write failed for key {}", key)


def _get_json(key: str) -> Any | None:
    if _use_memory():
        return _MEM_STORE.get(key)
    data = _redis_client().get(key)
    return json.loads(data) if data else None


def save_scenario(scenario: Scenario) -> None:
    _set_json(f"scenario:{scenario.scenario_id}", scenario.model_dump())


def update_scenario(scenario_id: str, updates: dict) -> Scenario | None:
    """Update a scenario with partial data."""
    scenario = get_scenario(scenario_id)
    if not scenario:
        return None
    # Apply updates
    data = scenario.model_dump()
    data.update(updates)
    updated_scenario = Scenario(**data)
    save_scenario(updated_scenario)
    return updated_scenario


def get_scenario(scenario_id: str) -> Scenario | None:
    key = f"scenario:{scenario_id}"
    if _use_memory():
        data = _MEM_STORE.get(key)
        return Scenario(**data) if data else None
    client = _redis_client()
    try:
        key_type = client.type(key)
        if key_type == "string":
            data = _get_json(key)
        elif key_type == "hash":
            data_str = client.hget(key, "data")
            data = json.loads(data_str) if data_str else None
        else:
            return None
        return Scenario(**data) if data else None
    except Exception as e:
        logger.warning(f"Failed to get scenario {scenario_id}: {e}")
        return None


def list_scenarios() -> list[Scenario]:
    if _use_memory():
        return [Scenario(**v) for k, v in _MEM_STORE.items() if k.startswith("scenario:")]
    client = _redis_client()
    keys = client.keys("scenario:*")
    if not keys:
        return []

    scenarios: list[Scenario] = []

    # Use pipeline to batch all type checks
    pipe = client.pipeline()
    for key in keys:
        pipe.type(key)
    types = pipe.execute()

    # Separate keys by type
    string_keys = []
    hash_keys = []
    for key, key_type in zip(keys, types):
        if key_type == "string":
            string_keys.append(key)
        elif key_type == "hash":
            hash_keys.append(key)

    # Batch fetch string keys with MGET
    if string_keys:
        values = client.mget(string_keys)
        for val in values:
            if val:
                try:
                    data = json.loads(val)
                    scenarios.append(Scenario(**data))
                except Exception as e:
                    logger.warning(f"Failed to parse scenario: {e}")

    # Batch fetch hash keys with pipeline
    if hash_keys:
        pipe = client.pipeline()
        for key in hash_keys:
            pipe.hget(key, "data")
        hash_values = pipe.execute()
        for val in hash_values:
            if val:
                try:
                    data = json.loads(val)
                    scenarios.append(Scenario(**data))
                except Exception as e:
                    logger.warning(f"Failed to parse scenario: {e}")

    return scenarios


def create_run(run: Run) -> None:
    _set_json(f"run:{run.run_id}", run.model_dump())


def update_run(run: Run) -> None:
    run.updated_at = time.time()
    _set_json(f"run:{run.run_id}", run.model_dump())


def get_run(run_id: str) -> Run | None:
    data = _get_json(f"run:{run_id}")
    return Run(**data) if data else None


def list_runs(status: str | None = None, limit: int = 50) -> list[Run]:
    """List all runs with optional status filtering.

    Args:
        status: Filter by run status (pending, running, completed, etc.)
        limit: Maximum number of runs to return

    Returns:
        List of Run objects sorted by started_at descending
    """
    if _use_memory():
        runs = [Run(**v) for k, v in _MEM_STORE.items() if k.startswith("run:")]
    else:
        client = _redis_client()
        keys = client.keys("run:*")
        runs = []
        if keys:
            values = client.mget(keys)
            for val in values:
                if val:
                    try:
                        data = json.loads(val)
                        runs.append(Run(**data))
                    except Exception:
                        continue
    if status:
        runs = [r for r in runs if r.status == status]
    runs.sort(key=lambda r: r.started_at or 0, reverse=True)
    return runs[:limit]


def append_transcript(run_id: str, entry: TranscriptEntry) -> None:
    key = f"transcript:{run_id}"
    if _use_memory():
        _MEM_STORE.setdefault(key, []).append(entry.model_dump())
        return
    try:
        _redis_client().rpush(key, json.dumps(entry.model_dump()))
    except Exception:
        logger.exception("Redis transcript write failed for {}", key)


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


def list_guidelines() -> list[Guideline]:
    """List all registered guidelines."""
    if _use_memory():
        return [
            Guideline(**v) for k, v in _MEM_STORE.items() if k.startswith("compliance:guideline:")
        ]
    keys = _redis_client().keys("compliance:guideline:*")
    guidelines: list[Guideline] = []
    for key in keys:
        data = _get_json(key.decode() if isinstance(key, bytes) else key)
        if data:
            guidelines.append(Guideline(**data))
    return guidelines


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


def get_extracted_guideline_by_url(url: str) -> dict | None:
    key = f"guideline:extracted:{_url_to_key(url)}"
    return _get_json(key)


def list_extracted_guidelines() -> list[dict]:
    if _use_memory():
        return [v for k, v in _MEM_STORE.items() if k.startswith("guideline:extracted:")]
    keys = _redis_client().keys("guideline:extracted:*")
    guidelines: list[dict] = []
    for key in keys:
        data = _get_json(key)
        if data:
            guidelines.append(data)
    return guidelines


def append_pipeline_memory(entry: dict[str, Any]) -> None:
    key = "memory:scenario_pipeline"
    if _use_memory():
        _MEM_STORE.setdefault(key, []).append(entry)
        return
    _redis_client().rpush(key, json.dumps(entry))


def list_pipeline_memory() -> list[dict[str, Any]]:
    key = "memory:scenario_pipeline"
    if _use_memory():
        return _MEM_STORE.get(key, [])
    entries = _redis_client().lrange(key, 0, -1)
    return [json.loads(e) for e in entries]


def save_attack_vector(attack_id: str, payload: dict[str, Any]) -> None:
    _set_json(f"attack:global:{attack_id}", payload)


def get_attack_vector(attack_id: str) -> dict[str, Any] | None:
    return _get_json(f"attack:global:{attack_id}")


def list_attack_vectors() -> list[dict[str, Any]]:
    """List all attack vectors with their stats."""
    if _use_memory():
        vectors = []
        for key, payload in _MEM_STORE.items():
            if key.startswith("attack:global:"):
                attack_id = key.replace("attack:global:", "")
                stats = _get_attack_stats(attack_id)
                attempts = int(stats.get("attempts") or 0)
                successes = int(stats.get("successes") or 0)
                severity_avg = (
                    float(stats.get("severity_total") or 0.0) / attempts
                    if attempts
                    else 0.0
                )
                vectors.append({
                    "attack_id": attack_id,
                    "prompt": payload.get("prompt"),
                    "category": payload.get("category"),
                    "tags": payload.get("tags", []),
                    "attempts": attempts,
                    "success_rate": successes / attempts if attempts else 0.0,
                    "severity_avg": severity_avg,
                    "last_used": payload.get("last_used"),
                })
        return vectors

    client = _redis_client()
    keys = client.keys("attack:global:*")
    if not keys:
        return []

    # Convert keys to strings
    key_strs = [k.decode() if isinstance(k, bytes) else k for k in keys]

    # Batch fetch all attack payloads with MGET
    values = client.mget(key_strs)

    vectors = []
    for key_str, val in zip(key_strs, values):
        if not val:
            continue
        try:
            payload = json.loads(val)
            attack_id = key_str.replace("attack:global:", "")
            vectors.append({
                "attack_id": attack_id,
                "prompt": payload.get("prompt"),
                "category": payload.get("category"),
                "tags": payload.get("tags", []),
                "attempts": 0,
                "success_rate": 0.0,
                "severity_avg": 0.0,
                "last_used": payload.get("last_used"),
            })
        except Exception:
            continue
    return vectors


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


# =============================================================================
# Intake Session Operations
# =============================================================================


def save_intake_session(session: IntakeSession) -> None:
    """Save an intake session to Redis.

    Args:
        session: IntakeSession model to save.
    """
    session.updated_at = time.time()
    _set_json(f"intake_session:{session.session_id}", session.model_dump())


def get_intake_session(session_id: str) -> IntakeSession | None:
    """Retrieve an intake session by ID.

    Args:
        session_id: Session identifier.

    Returns:
        IntakeSession if found, None otherwise.
    """
    data = _get_json(f"intake_session:{session_id}")
    return IntakeSession(**data) if data else None


def list_intake_sessions(
    status: str | None = None,
    limit: int = 50,
) -> list[IntakeSession]:
    """List intake sessions with optional filtering.

    Args:
        status: Filter by current_stage if provided.
        limit: Maximum number of sessions to return.

    Returns:
        List of IntakeSession objects sorted by updated_at descending.
    """
    if _use_memory():
        sessions = [
            IntakeSession(**v)
            for k, v in _MEM_STORE.items()
            if k.startswith("intake_session:")
        ]
    else:
        keys = _redis_client().keys("intake_session:*")
        sessions = []
        for key in keys:
            data = _get_json(key)
            if data:
                sessions.append(IntakeSession(**data))

    if status:
        sessions = [s for s in sessions if s.current_stage == status]

    sessions.sort(key=lambda s: s.updated_at, reverse=True)
    return sessions[:limit]


def delete_intake_session(session_id: str) -> bool:
    """Delete an intake session.

    Args:
        session_id: Session identifier.

    Returns:
        True if deleted, False if not found.
    """
    key = f"intake_session:{session_id}"
    if _use_memory():
        if key in _MEM_STORE:
            del _MEM_STORE[key]
            return True
        return False
    try:
        return _redis_client().delete(key) > 0
    except Exception:
        logger.exception("Failed to delete intake session {}", session_id)
        return False


# =============================================================================
# Patient Operations
# =============================================================================


def save_patient(patient_id: str, patient_data: dict[str, Any]) -> None:
    """Save patient data to Redis.

    Args:
        patient_id: Patient identifier.
        patient_data: Patient data dictionary.
    """
    patient_data["updated_at"] = time.time()
    _set_json(f"patient:{patient_id}", patient_data)


def get_patient(patient_id: str) -> dict[str, Any] | None:
    """Retrieve patient data by ID.

    Args:
        patient_id: Patient identifier.

    Returns:
        Patient data dictionary if found, None otherwise.
    """
    return _get_json(f"patient:{patient_id}")


def lookup_patient_by_phone(phone: str) -> dict[str, Any] | None:
    """Look up a patient by phone number.

    Args:
        phone: Phone number (digits only, normalized).

    Returns:
        Patient data if found, None otherwise.
    """
    # Normalize phone to digits
    import re
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    # Use phone index
    index_data = _get_json(f"patient:phone_index:{digits}")
    if index_data and index_data.get("patient_id"):
        return get_patient(index_data["patient_id"])
    return None


def index_patient_phone(patient_id: str, phone: str) -> None:
    """Index a patient by phone number for lookups.

    Args:
        patient_id: Patient identifier.
        phone: Phone number.
    """
    import re
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    _set_json(f"patient:phone_index:{digits}", {"patient_id": patient_id})


def save_patient_identity(session_id: str, identity: PatientIdentity) -> None:
    """Save patient identity verification result to session.

    Args:
        session_id: Intake session ID.
        identity: Verified patient identity.
    """
    session = get_intake_session(session_id)
    if session:
        session.patient_identity = identity
        session.current_stage = "insurance"  # Move to next stage
        save_intake_session(session)


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


# =============================================================================
# Batch Run Operations
# =============================================================================


def create_batch_run(batch: BatchRun) -> None:
    """Create a new batch run.

    Args:
        batch: BatchRun model to save.
    """
    batch.created_at = batch.created_at or time.time()
    _set_json(f"batch:{batch.batch_id}", batch.model_dump())


def get_batch_run(batch_id: str) -> BatchRun | None:
    """Retrieve a batch run by ID.

    Args:
        batch_id: Batch identifier.

    Returns:
        BatchRun if found, None otherwise.
    """
    data = _get_json(f"batch:{batch_id}")
    return BatchRun(**data) if data else None


def update_batch_run(batch: BatchRun) -> None:
    """Update a batch run.

    Args:
        batch: BatchRun model to update.
    """
    _set_json(f"batch:{batch.batch_id}", batch.model_dump())


def list_batch_runs(status: str | None = None, limit: int = 20) -> list[BatchRun]:
    """List batch runs with optional status filtering.

    Args:
        status: Filter by batch status if provided.
        limit: Maximum number of batches to return.

    Returns:
        List of BatchRun objects sorted by created_at descending.
    """
    if _use_memory():
        batches = [
            BatchRun(**v)
            for k, v in _MEM_STORE.items()
            if k.startswith("batch:")
        ]
    else:
        client = _redis_client()
        keys = client.keys("batch:*")
        # Filter out cancel flag keys
        keys = [k for k in keys if ":cancel:" not in (k.decode() if isinstance(k, bytes) else k)]
        batches = []
        if keys:
            values = client.mget(keys)
            for val in values:
                if val:
                    try:
                        data = json.loads(val)
                        batches.append(BatchRun(**data))
                    except Exception:
                        continue

    if status:
        batches = [b for b in batches if b.status == status]

    batches.sort(key=lambda b: b.created_at or 0, reverse=True)
    return batches[:limit]


def set_batch_cancel_flag(batch_id: str) -> None:
    """Set a cancel flag for a batch run.

    Args:
        batch_id: Batch identifier.
    """
    key = f"batch:cancel:{batch_id}"
    if _use_memory():
        _MEM_STORE[key] = True
        return
    _redis_client().set(key, "1", ex=3600)  # 1 hour TTL


def is_batch_canceled(batch_id: str) -> bool:
    """Check if a batch run has been canceled.

    Args:
        batch_id: Batch identifier.

    Returns:
        True if the batch has been canceled.
    """
    key = f"batch:cancel:{batch_id}"
    if _use_memory():
        return _MEM_STORE.get(key, False)
    return bool(_redis_client().get(key))


def clear_batch_cancel_flag(batch_id: str) -> None:
    """Clear the cancel flag for a batch run.

    Args:
        batch_id: Batch identifier.
    """
    key = f"batch:cancel:{batch_id}"
    if _use_memory():
        _MEM_STORE.pop(key, None)
        return
    _redis_client().delete(key)
