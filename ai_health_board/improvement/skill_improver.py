"""Skill improvement using Claude Agents SDK.

This module handles:
1. Detecting skill gaps from failure patterns
2. Designing new skills with Claude
3. Implementing skills as Python code
4. Validating and deploying new skills

Skills are stored in Redis and loaded dynamically by agents.
"""
from __future__ import annotations

import ast
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from .. import redis_store
from ..observability import trace_op


@dataclass
class SkillSpec:
    """Specification for a skill/tool."""

    skill_id: str
    name: str
    description: str
    parameters: list[dict[str, Any]]
    implementation: str  # Python code
    created_at: float = field(default_factory=time.time)
    version: str = "v1"
    is_active: bool = False
    usage_count: int = 0
    success_count: int = 0
    agent_type: str = "tester"  # "tester" or "grader"

    def success_rate(self) -> float:
        return self.success_count / self.usage_count if self.usage_count > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "implementation": self.implementation,
            "created_at": self.created_at,
            "version": self.version,
            "is_active": self.is_active,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "agent_type": self.agent_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillSpec:
        return cls(**data)


class SkillRegistry:
    """Registry for dynamic skills."""

    def __init__(self):
        self._cache: dict[str, SkillSpec] = {}

    def _redis_key(self, skill_id: str) -> str:
        return f"skill:{skill_id}"

    def _save(self, skill: SkillSpec) -> None:
        key = self._redis_key(skill.skill_id)
        redis_store._set_json(key, skill.to_dict())
        self._cache[skill.skill_id] = skill

    def _load(self, skill_id: str) -> SkillSpec | None:
        if skill_id in self._cache:
            return self._cache[skill_id]
        key = self._redis_key(skill_id)
        data = redis_store._get_json(key)
        if data:
            skill = SkillSpec.from_dict(data)
            self._cache[skill_id] = skill
            return skill
        return None

    def register_skill(self, skill: SkillSpec) -> None:
        """Register a new skill."""
        self._save(skill)
        logger.info(f"Registered skill: {skill.skill_id}")

    def get_skill(self, skill_id: str) -> SkillSpec | None:
        """Get a skill by ID."""
        return self._load(skill_id)

    def list_skills(self, agent_type: str | None = None, active_only: bool = True) -> list[SkillSpec]:
        """List all skills, optionally filtered."""
        # Scan Redis for skill keys
        skills = []
        try:
            client = redis_store._get_client()
            for key in client.scan_iter(match="skill:*"):
                data = redis_store._get_json(key.decode() if isinstance(key, bytes) else key)
                if data:
                    skill = SkillSpec.from_dict(data)
                    if agent_type and skill.agent_type != agent_type:
                        continue
                    if active_only and not skill.is_active:
                        continue
                    skills.append(skill)
        except Exception as e:
            logger.warning(f"Failed to list skills: {e}")
        return skills

    def record_usage(self, skill_id: str, success: bool) -> None:
        """Record skill usage."""
        skill = self._load(skill_id)
        if skill:
            skill.usage_count += 1
            if success:
                skill.success_count += 1
            self._save(skill)

    def activate_skill(self, skill_id: str) -> bool:
        """Activate a skill for use."""
        skill = self._load(skill_id)
        if skill:
            skill.is_active = True
            self._save(skill)
            return True
        return False

    def deactivate_skill(self, skill_id: str) -> bool:
        """Deactivate a skill."""
        skill = self._load(skill_id)
        if skill:
            skill.is_active = False
            self._save(skill)
            return True
        return False


# Global registry
_skill_registry: SkillRegistry | None = None


def get_skill_registry() -> SkillRegistry:
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry()
    return _skill_registry


# ---------------------------------------------------------------------------
# Skill Gap Detection
# ---------------------------------------------------------------------------

SKILL_GAP_ANALYSIS_PROMPT = """You are analyzing failure patterns in a healthcare AI testing system.

## Agent Type
{agent_type}

## Current Skills
{current_skills}

## Failure Patterns (from recent test runs)
{failure_patterns}

## Task
Identify skill gaps - capabilities the agent needs but doesn't have.

For each gap, explain:
1. What capability is missing
2. What failures it would prevent
3. How it would work

Respond with JSON:
{{
    "skill_gaps": [
        {{
            "name": "skill_name_snake_case",
            "description": "What this skill does",
            "addresses_failures": ["failure1", "failure2"],
            "priority": "high|medium|low",
            "implementation_complexity": "simple|moderate|complex"
        }}
    ]
}}
"""


@trace_op("improvement.detect_skill_gaps")
def detect_skill_gaps(
    agent_type: str,
    failure_patterns: list[str],
    current_skills: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Detect skill gaps from failure patterns.

    Args:
        agent_type: "tester" or "grader"
        failure_patterns: List of failure descriptions
        current_skills: List of current skill names

    Returns:
        List of skill gap specifications
    """
    from ..wandb_inference import inference_chat_json

    if not failure_patterns:
        return []

    prompt = SKILL_GAP_ANALYSIS_PROMPT.format(
        agent_type=agent_type,
        current_skills="\n".join(f"- {s}" for s in (current_skills or [])) or "None",
        failure_patterns="\n".join(f"- {f}" for f in failure_patterns),
    )

    try:
        result = inference_chat_json(
            model=None,
            messages=[
                {"role": "system", "content": "You are an AI agent architect."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        return result.get("skill_gaps", [])
    except Exception as e:
        logger.error(f"Failed to detect skill gaps: {e}")
        return []


# ---------------------------------------------------------------------------
# Skill Design with Claude
# ---------------------------------------------------------------------------

SKILL_DESIGN_PROMPT = """You are designing a new tool/skill for a healthcare AI agent.

## Agent Type
{agent_type}

## Skill Requirement
Name: {skill_name}
Description: {skill_description}
Should address: {addresses_failures}

## Existing Skills (for reference)
{existing_skills}

## Task
Design the skill as a Python function that can be used as an agent tool.

Requirements:
1. Must be a standalone function with type hints
2. Must have a clear docstring
3. Must handle errors gracefully
4. Must return a dict with results
5. Can use these imports: json, re, time, datetime, httpx, loguru.logger

Respond with JSON:
{{
    "name": "function_name",
    "description": "One-line description for tool",
    "parameters": [
        {{"name": "param1", "type": "str", "description": "What it is", "required": true}}
    ],
    "implementation": "def function_name(param1: str) -> dict:\\n    ..."
}}
"""


@trace_op("improvement.design_skill")
def design_skill(
    agent_type: str,
    skill_name: str,
    skill_description: str,
    addresses_failures: list[str],
    existing_skills: list[str] | None = None,
) -> dict[str, Any] | None:
    """Design a new skill using Claude.

    Args:
        agent_type: "tester" or "grader"
        skill_name: Name of the skill to design
        skill_description: What the skill should do
        addresses_failures: What failures it should prevent
        existing_skills: Current skill names for context

    Returns:
        Skill design specification
    """
    from ..wandb_inference import inference_chat_json

    prompt = SKILL_DESIGN_PROMPT.format(
        agent_type=agent_type,
        skill_name=skill_name,
        skill_description=skill_description,
        addresses_failures=", ".join(addresses_failures),
        existing_skills="\n".join(f"- {s}" for s in (existing_skills or [])) or "None",
    )

    try:
        result = inference_chat_json(
            model=None,
            messages=[
                {"role": "system", "content": "You are an expert Python developer."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=2000,
        )

        if result and result.get("implementation"):
            return result
    except Exception as e:
        logger.error(f"Failed to design skill: {e}")

    return None


# ---------------------------------------------------------------------------
# Skill Validation
# ---------------------------------------------------------------------------


def validate_skill_code(implementation: str) -> tuple[bool, str]:
    """Validate that skill code is safe and syntactically correct.

    Args:
        implementation: Python code string

    Returns:
        (is_valid, error_message)
    """
    # Check syntax
    try:
        ast.parse(implementation)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    # Check for dangerous patterns
    dangerous_patterns = [
        "import os",
        "import subprocess",
        "import sys",
        "__import__",
        "eval(",
        "exec(",
        "open(",
        "file(",
        "input(",
        "breakpoint(",
    ]

    for pattern in dangerous_patterns:
        if pattern in implementation:
            return False, f"Dangerous pattern detected: {pattern}"

    # Must be a function definition
    if not implementation.strip().startswith("def "):
        return False, "Implementation must be a function definition"

    return True, ""


def test_skill_execution(skill: SkillSpec, test_input: dict[str, Any]) -> tuple[bool, Any]:
    """Test that a skill can execute.

    Args:
        skill: The skill to test
        test_input: Test input parameters

    Returns:
        (success, result_or_error)
    """
    try:
        # Create a restricted namespace
        namespace = {
            "json": __import__("json"),
            "re": __import__("re"),
            "time": __import__("time"),
            "datetime": __import__("datetime"),
            "logger": logger,
        }

        # Execute the function definition
        exec(skill.implementation, namespace)

        # Get the function
        func_name = skill.name
        if func_name not in namespace:
            return False, f"Function {func_name} not found after execution"

        func = namespace[func_name]

        # Call with test input
        result = func(**test_input)
        return True, result

    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Full Skill Improvement Cycle
# ---------------------------------------------------------------------------


@trace_op("improvement.run_skill_improvement_cycle")
def run_skill_improvement_cycle(
    agent_type: str,
    failure_patterns: list[str],
    current_skills: list[str] | None = None,
    auto_activate: bool = False,
) -> dict[str, Any]:
    """Run a full skill improvement cycle.

    1. Detect skill gaps from failures
    2. Design new skills
    3. Validate implementations
    4. Register (optionally activate)

    Args:
        agent_type: "tester" or "grader"
        failure_patterns: Recent failure patterns
        current_skills: Current skill names
        auto_activate: Whether to auto-activate valid skills

    Returns:
        Summary of improvements made
    """
    registry = get_skill_registry()

    result = {
        "gaps_detected": 0,
        "skills_designed": 0,
        "skills_validated": 0,
        "skills_registered": 0,
        "skills_activated": 0,
        "errors": [],
        "new_skills": [],
    }

    # 1. Detect gaps
    logger.info(f"Detecting skill gaps for {agent_type}...")
    gaps = detect_skill_gaps(agent_type, failure_patterns, current_skills)
    result["gaps_detected"] = len(gaps)

    if not gaps:
        logger.info("No skill gaps detected")
        return result

    # 2. Design and validate each skill
    for gap in gaps:
        skill_name = gap.get("name", "unknown")
        logger.info(f"Designing skill: {skill_name}")

        # Design
        design = design_skill(
            agent_type=agent_type,
            skill_name=skill_name,
            skill_description=gap.get("description", ""),
            addresses_failures=gap.get("addresses_failures", []),
            existing_skills=current_skills,
        )

        if not design:
            result["errors"].append(f"Failed to design {skill_name}")
            continue

        result["skills_designed"] += 1

        # Validate
        implementation = design.get("implementation", "")
        is_valid, error = validate_skill_code(implementation)

        if not is_valid:
            result["errors"].append(f"{skill_name}: {error}")
            continue

        result["skills_validated"] += 1

        # Create skill spec
        skill_id = f"{agent_type}.{skill_name}.{hashlib.md5(implementation.encode()).hexdigest()[:8]}"
        skill = SkillSpec(
            skill_id=skill_id,
            name=design.get("name", skill_name),
            description=design.get("description", ""),
            parameters=design.get("parameters", []),
            implementation=implementation,
            agent_type=agent_type,
            is_active=False,
        )

        # Register
        registry.register_skill(skill)
        result["skills_registered"] += 1
        result["new_skills"].append({
            "skill_id": skill_id,
            "name": skill.name,
            "description": skill.description,
        })

        # Optionally activate
        if auto_activate:
            registry.activate_skill(skill_id)
            result["skills_activated"] += 1
            logger.info(f"Activated skill: {skill_id}")

    logger.info(
        f"Skill improvement complete: {result['skills_registered']} registered, "
        f"{result['skills_activated']} activated"
    )

    return result


# ---------------------------------------------------------------------------
# Get Skills for Agent Use
# ---------------------------------------------------------------------------


def get_active_skills_for_agent(agent_type: str) -> list[dict[str, Any]]:
    """Get active skills formatted for agent tool use.

    Args:
        agent_type: "tester" or "grader"

    Returns:
        List of skill definitions ready for agent tools
    """
    registry = get_skill_registry()
    skills = registry.list_skills(agent_type=agent_type, active_only=True)

    tool_definitions = []
    for skill in skills:
        tool_definitions.append({
            "name": skill.name,
            "description": skill.description,
            "parameters": skill.parameters,
            "skill_id": skill.skill_id,  # For tracking usage
        })

    return tool_definitions


def execute_skill(skill_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Execute a skill and record usage.

    Args:
        skill_id: The skill to execute
        params: Parameters to pass

    Returns:
        Skill execution result
    """
    registry = get_skill_registry()
    skill = registry.get_skill(skill_id)

    if not skill:
        return {"error": f"Skill not found: {skill_id}"}

    if not skill.is_active:
        return {"error": f"Skill not active: {skill_id}"}

    success, result = test_skill_execution(skill, params)
    registry.record_usage(skill_id, success=success)

    if success:
        return {"success": True, "result": result}
    else:
        return {"success": False, "error": result}
