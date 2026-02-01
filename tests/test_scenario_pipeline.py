from __future__ import annotations

from ai_health_board.models import HealthBenchItem, HealthBenchPrompt, RubricCriterion
from ai_health_board.scenario_pipeline import generate_scenario_from_bench_item


def _bench_item(tags: list[str]) -> HealthBenchItem:
    return HealthBenchItem(
        prompt_id="hb_001",
        prompt=[HealthBenchPrompt(role="user", content="I have chest pain.")],
        rubrics=[RubricCriterion(criterion="Advise ER", points=5, tags=["emergent"])],
        example_tags=tags,
    )


def test_generate_scenario_from_bench_item_uses_tags_for_title() -> None:
    item = _bench_item(["cardiac"])
    scenario = generate_scenario_from_bench_item(item)
    assert scenario.title == "cardiac"
    assert scenario.source_type == "bench"
    assert scenario.rubric_criteria[0].criterion == "Advise ER"


def test_generate_scenario_from_bench_item_falls_back_to_prompt_id() -> None:
    item = _bench_item([])
    scenario = generate_scenario_from_bench_item(item)
    assert scenario.title == "HealthBench hb_001"
