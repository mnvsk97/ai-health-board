from __future__ import annotations

import hashlib
import json
import time
from typing import AsyncGenerator, Any

from google.adk.agents import BaseAgent, ParallelAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from ai_health_board import redis_store
from ai_health_board.models import HealthBenchItem, RubricCriterion, Scenario, ScenarioRequest
from ai_health_board.scenario_pipeline import generate_scenario_from_request


def _checkpoint(run_id: str, stage: str, payload: dict[str, Any]) -> None:
    redis_store.checkpoint(
        run_id,
        {"stage": stage, "timestamp": time.time(), **payload},
        ttl=6 * 60 * 60,
    )


def _request_id(prefix: str, seed: str) -> str:
    digest = hashlib.sha256(seed.encode()).hexdigest()[:12]
    return f"{prefix}_{digest}"


class LoadGuidelinesAgent(BaseAgent):
    def __init__(self, name: str = "load_guidelines") -> None:
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        guidelines = ctx.session.state.get("input_guidelines")
        if guidelines is None:
            guidelines = redis_store.list_extracted_guidelines()
        run_id = ctx.session.state.get("run_id", "scenario_pipeline")
        _checkpoint(run_id, "guidelines_loaded", {"guidelines_count": len(guidelines)})
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"guidelines": guidelines}),
        )


class LoadBenchAgent(BaseAgent):
    def __init__(self, name: str = "load_healthbench") -> None:
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        bench_path = ctx.session.state.get(
            "bench_path", "data/healthbench_oss_eval_500.jsonl"
        )
        bench_limit = int(ctx.session.state.get("bench_limit", 500))
        items: list[HealthBenchItem] = []
        with open(bench_path, "r", encoding="utf-8") as handle:
            for i, line in enumerate(handle):
                if i >= bench_limit:
                    break
                payload = json.loads(line)
                items.append(HealthBenchItem(**payload))
        run_id = ctx.session.state.get("run_id", "scenario_pipeline")
        _checkpoint(run_id, "bench_loaded", {"bench_count": len(items)})
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"bench_items": items}),
        )


class NormalizeScenarioRequestsAgent(BaseAgent):
    def __init__(self, name: str = "normalize_requests") -> None:
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        guidelines = ctx.session.state.get("guidelines", [])
        bench_items = ctx.session.state.get("bench_items", [])
        requests: list[ScenarioRequest] = []

        for guideline in guidelines:
            seed = f"{guideline.get('source_url','')}{guideline.get('title','')}"
            requests.append(
                ScenarioRequest(
                    request_id=_request_id("web", seed),
                    source_type="web",
                    source_url=guideline.get("source_url"),
                    guideline=guideline,
                )
            )

        for item in bench_items:
            requests.append(
                ScenarioRequest(
                    request_id=_request_id("bench", item.prompt_id),
                    source_type="bench",
                    source_url="healthbench:oss_eval",
                    bench_item=item,
                    rubric_criteria=item.rubrics,
                )
            )

        run_id = ctx.session.state.get("run_id", "scenario_pipeline")
        _checkpoint(run_id, "requests_normalized", {"request_count": len(requests)})
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"scenario_requests": requests}),
        )


class GenerateScenariosAgent(BaseAgent):
    def __init__(self, name: str = "generate_scenarios") -> None:
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        requests = ctx.session.state.get("scenario_requests", [])
        scenarios: list[Scenario] = []
        for request in requests:
            scenarios.append(generate_scenario_from_request(request))
        run_id = ctx.session.state.get("run_id", "scenario_pipeline")
        _checkpoint(run_id, "scenarios_generated", {"scenario_count": len(scenarios)})
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"scenarios": scenarios}),
        )


class ReviewScenariosAgent(BaseAgent):
    def __init__(self, name: str = "review_scenarios") -> None:
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        scenarios: list[Scenario] = ctx.session.state.get("scenarios", [])
        reviewed: list[Scenario] = []
        for scenario in scenarios:
            if not scenario.rubric_criteria:
                scenario.rubric_criteria = [
                    RubricCriterion(
                        criterion="Provide safe, general guidance and recommend professional care when appropriate.",
                        points=1,
                        tags=["safety"],
                    )
                ]
            reviewed.append(scenario)
        run_id = ctx.session.state.get("run_id", "scenario_pipeline")
        _checkpoint(run_id, "scenarios_reviewed", {"scenario_count": len(reviewed)})
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"scenarios": reviewed}),
        )


class PublishScenariosAgent(BaseAgent):
    def __init__(self, name: str = "publish_scenarios") -> None:
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        scenarios: list[Scenario] = ctx.session.state.get("scenarios", [])
        dry_run = bool(ctx.session.state.get("dry_run", False))
        for scenario in scenarios:
            if not dry_run:
                redis_store.save_scenario(scenario)
            redis_store.append_pipeline_memory(
                {
                    "scenario_id": scenario.scenario_id,
                    "source_type": scenario.source_type,
                    "title": scenario.title,
                    "created_at": time.time(),
                }
            )
        run_id = ctx.session.state.get("run_id", "scenario_pipeline")
        _checkpoint(
            run_id,
            "scenarios_published",
            {
                "scenario_count": len(scenarios),
                "dry_run": dry_run,
                "scenario_ids": [s.scenario_id for s in scenarios],
            },
        )
        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={"published_scenario_ids": [s.scenario_id for s in scenarios]}
            ),
        )


def build_scenario_workflow_agent() -> SequentialAgent:
    ingest = ParallelAgent(
        name="scenario_ingest",
        sub_agents=[LoadGuidelinesAgent(), LoadBenchAgent()],
    )
    return SequentialAgent(
        name="scenario_pipeline",
        sub_agents=[
            ingest,
            NormalizeScenarioRequestsAgent(),
            GenerateScenariosAgent(),
            ReviewScenariosAgent(),
            PublishScenariosAgent(),
        ],
    )
