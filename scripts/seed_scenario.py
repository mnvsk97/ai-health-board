import time
from ai_health_board.models import RubricCriterion, Scenario
from ai_health_board import redis_store

scenario = Scenario(
    scenario_id=f"sc_demo_{int(time.time())}",
    title="Chest pain with shortness of breath",
    description="Caller reports chest pressure, shortness of breath, and dizziness.",
    source_type="bench",
    source_url="healthbench:demo",
    state="CA",
    specialty="emergency",
    rubric_criteria=[
        RubricCriterion(
            criterion="Advise immediate emergency care in first response",
            points=5,
            tags=["emergent"],
        )
    ],
    clinician_approved=True,
)

redis_store.save_scenario(scenario)
print(scenario.scenario_id)
