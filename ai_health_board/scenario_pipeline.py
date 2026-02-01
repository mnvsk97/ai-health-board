from __future__ import annotations

import hashlib
import time
from typing import Any

from .models import HealthBenchItem, RubricCriterion, Scenario, ScenarioRequest
from .observability import trace_op
from .wandb_inference import inference_chat_json


@trace_op("scenario.generate_from_guideline")
def generate_scenario_from_guideline(guideline: dict[str, Any]) -> Scenario:
    prompt = [
        {"role": "system", "content": "You are a medical scenario generator."},
        {
            "role": "user",
            "content": (
                "Create one healthcare AI test scenario and rubric criteria from this guideline. "
                "Return JSON with fields: title, description, state, specialty, rubric_criteria[] with criterion/points/tags. "
                f"Guideline: {guideline}"
            ),
        },
    ]
    result = inference_chat_json(None, prompt)
    rubric = [RubricCriterion(**c) for c in result.get("rubric_criteria", [])]
    scenario_id = hashlib.sha256(f"{result.get('title','')}{time.time()}".encode()).hexdigest()[:12]
    return Scenario(
        scenario_id=f"sc_{scenario_id}",
        title=result.get("title", "Untitled"),
        description=result.get("description", ""),
        source_type="web",
        source_url=guideline.get("source_url"),
        state=result.get("state"),
        specialty=result.get("specialty"),
        rubric_criteria=rubric,
        clinician_approved=True,
    )


def hash_rubric(criteria: list[RubricCriterion]) -> str:
    payload = "|".join([c.criterion for c in criteria])
    return hashlib.sha256(payload.encode()).hexdigest()


def generate_scenario_from_bench_item(item: HealthBenchItem) -> Scenario:
    content_lines = [f"{m.role}: {m.content}" for m in item.prompt]
    description = "\n".join(content_lines)
    title = item.example_tags[0] if item.example_tags else f"HealthBench {item.prompt_id}"
    scenario_id = hashlib.sha256(f"{item.prompt_id}{time.time()}".encode()).hexdigest()[:12]
    return Scenario(
        scenario_id=f"sc_{scenario_id}",
        title=title,
        description=description,
        source_type="bench",
        source_url="healthbench:oss_eval",
        state=None,
        specialty=None,
        rubric_criteria=item.rubrics,
        clinician_approved=True,
    )


def generate_scenario_from_request(request: ScenarioRequest) -> Scenario:
    if request.source_type == "web" and request.guideline:
        return generate_scenario_from_guideline(request.guideline)
    if request.source_type == "bench" and request.bench_item:
        return generate_scenario_from_bench_item(request.bench_item)
    raise ValueError("ScenarioRequest missing source payload")
