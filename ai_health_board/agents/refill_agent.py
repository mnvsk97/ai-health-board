from __future__ import annotations

from .base_agent import build_agent

REFILL_PROMPT = """You are a prescription refill agent.
- Verify patient identity and medication details.
- Check refill eligibility and explain next steps.
- Do not provide medical advice or alter prescriptions.
- Escalate emergencies to ER/911.
- Maintain HIPAA-compliant tone and confirm consent.
"""


def make_refill_agent() -> dict[str, str]:
    return build_agent(agent_name="refill-agent", system_prompt=REFILL_PROMPT)
