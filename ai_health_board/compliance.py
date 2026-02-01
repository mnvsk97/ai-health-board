from __future__ import annotations

import hashlib
import time

from .models import ComplianceStatus, Guideline, Scenario
from . import redis_store
from .scenario_pipeline import generate_scenario_from_guideline


def register_guideline(guideline: Guideline) -> None:
    redis_store.save_guideline(guideline)


def simulate_guideline_change(guideline_id: str, target_id: str) -> Scenario | None:
    guideline = redis_store.get_guideline(guideline_id)
    if not guideline:
        return None

    guideline.version = time.strftime("%Y-%m-%d")
    guideline.hash = hashlib.sha256(f"{guideline.source_url}{time.time()}".encode()).hexdigest()
    guideline.last_checked = time.time()
    redis_store.save_guideline(guideline)

    status = ComplianceStatus(
        target_id=target_id,
        status="outdated",
        reason=f"Guideline {guideline_id} updated",
        updated_at=time.time(),
    )
    redis_store.set_compliance_status(status)

    scenario = generate_scenario_from_guideline(guideline.model_dump())
    redis_store.save_scenario(scenario)
    return scenario
