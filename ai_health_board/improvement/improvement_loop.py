"""Validated improvement loop with A/B testing.

This implements real self-improvement by:
1. Analyzing historical performance data
2. Generating prompt variants
3. A/B testing variants against baseline
4. Promoting winners based on real results
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from loguru import logger

from ..observability import trace_op
from ..wandb_inference import inference_chat_json
from .prompt_registry import PromptRegistry, PromptVersion, get_registry


@dataclass
class ImprovementResult:
    """Result of an improvement cycle."""

    prompts_analyzed: int
    variants_created: int
    variants_promoted: int
    improvements: list[dict[str, Any]]


PROMPT_IMPROVEMENT_TEMPLATE = """You are an expert at improving LLM prompts for healthcare AI evaluation.

Analyze this prompt's performance and suggest an improved version.

## Current Prompt
{current_prompt}

## Performance Data
- Usage count: {usage_count}
- Success rate: {success_rate:.1%}
- Average score: {avg_score:.2f}

## Common Issues (from feedback)
{feedback_summary}

## Task
Generate an improved version of this prompt that addresses the issues while maintaining its core purpose.

Respond with JSON:
{{
    "improved_prompt": "The full improved prompt text",
    "changes_made": ["change 1", "change 2"],
    "expected_improvement": "Why this should perform better"
}}
"""


@trace_op("improvement.analyze_prompt_performance")
def analyze_prompt_performance(
    prompt_id: str,
    registry: PromptRegistry,
) -> dict[str, Any]:
    """Analyze a prompt's historical performance.

    Args:
        prompt_id: The prompt to analyze
        registry: The prompt registry

    Returns:
        Performance analysis with recommendations
    """
    stats = registry.get_performance_stats(prompt_id)

    if not stats or stats.get("usage_count", 0) < 10:
        return {
            "prompt_id": prompt_id,
            "needs_improvement": False,
            "reason": "Insufficient data (need at least 10 usages)",
        }

    success_rate = stats.get("success_rate", 0)
    avg_score = stats.get("avg_score", 0)

    needs_improvement = success_rate < 0.7 or avg_score < 0.6

    return {
        "prompt_id": prompt_id,
        "usage_count": stats.get("usage_count"),
        "success_rate": success_rate,
        "avg_score": avg_score,
        "needs_improvement": needs_improvement,
        "reason": "Low performance metrics" if needs_improvement else "Performing well",
    }


@trace_op("improvement.generate_prompt_variant")
def generate_prompt_variant(
    prompt_id: str,
    current_content: str,
    stats: dict[str, Any],
    feedback_summary: str = "",
) -> dict[str, Any] | None:
    """Generate an improved prompt variant using LLM.

    Args:
        prompt_id: The prompt to improve
        current_content: Current prompt content
        stats: Performance statistics
        feedback_summary: Summary of feedback/issues

    Returns:
        Improved prompt with explanation, or None on failure
    """
    prompt = PROMPT_IMPROVEMENT_TEMPLATE.format(
        current_prompt=current_content,
        usage_count=stats.get("usage_count", 0),
        success_rate=stats.get("success_rate", 0),
        avg_score=stats.get("avg_score", 0),
        feedback_summary=feedback_summary or "No specific feedback available",
    )

    try:
        result = inference_chat_json(
            model=None,
            messages=[
                {"role": "system", "content": "You are a prompt engineering expert."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=1500,
        )

        if result and result.get("improved_prompt"):
            return {
                "prompt_id": prompt_id,
                "improved_prompt": result["improved_prompt"],
                "changes_made": result.get("changes_made", []),
                "expected_improvement": result.get("expected_improvement", ""),
            }
    except Exception as e:
        logger.error(f"Failed to generate prompt variant: {e}")

    return None


@trace_op("improvement.evaluate_variant")
def evaluate_variant(
    baseline: PromptVersion,
    variant: PromptVersion,
    min_samples: int = 20,
) -> dict[str, Any]:
    """Evaluate whether a variant outperforms the baseline.

    Args:
        baseline: The baseline prompt version
        variant: The variant to evaluate
        min_samples: Minimum samples needed for comparison

    Returns:
        Evaluation result with recommendation
    """
    if variant.usage_count < min_samples:
        return {
            "ready_for_evaluation": False,
            "reason": f"Need {min_samples - variant.usage_count} more samples",
            "recommendation": "continue_testing",
        }

    baseline_rate = baseline.success_rate()
    variant_rate = variant.success_rate()

    improvement = variant_rate - baseline_rate
    significant = abs(improvement) > 0.05  # 5% threshold

    if significant and improvement > 0:
        return {
            "ready_for_evaluation": True,
            "baseline_success_rate": baseline_rate,
            "variant_success_rate": variant_rate,
            "improvement": improvement,
            "recommendation": "promote",
            "reason": f"Variant improves success rate by {improvement:.1%}",
        }
    elif significant and improvement < 0:
        return {
            "ready_for_evaluation": True,
            "baseline_success_rate": baseline_rate,
            "variant_success_rate": variant_rate,
            "improvement": improvement,
            "recommendation": "discard",
            "reason": f"Variant degrades success rate by {abs(improvement):.1%}",
        }
    else:
        return {
            "ready_for_evaluation": True,
            "baseline_success_rate": baseline_rate,
            "variant_success_rate": variant_rate,
            "improvement": improvement,
            "recommendation": "continue_testing",
            "reason": "No significant difference yet",
        }


@trace_op("improvement.run_validated_improvement_cycle")
def run_validated_improvement_cycle(
    prompt_ids: list[str] | None = None,
    min_usage_for_improvement: int = 20,
    min_usage_for_promotion: int = 30,
) -> ImprovementResult:
    """Run a validated improvement cycle.

    This:
    1. Analyzes prompt performance
    2. Generates variants for underperforming prompts
    3. Evaluates existing variants
    4. Promotes winners

    Args:
        prompt_ids: Specific prompts to analyze (default: all)
        min_usage_for_improvement: Min samples before generating variant
        min_usage_for_promotion: Min samples before promoting variant

    Returns:
        Summary of improvements made
    """
    registry = get_registry()
    all_prompts = registry.list_prompts()

    if prompt_ids:
        all_prompts = [p for p in all_prompts if p.get("prompt_id") in prompt_ids]

    logger.info(f"Analyzing {len(all_prompts)} prompts for improvement")

    variants_created = []
    variants_promoted = []
    improvements = []

    for prompt_stats in all_prompts:
        prompt_id = prompt_stats.get("prompt_id")
        if not prompt_id:
            continue

        # Analyze performance
        analysis = analyze_prompt_performance(prompt_id, registry)

        if not analysis.get("needs_improvement"):
            continue

        if prompt_stats.get("usage_count", 0) < min_usage_for_improvement:
            logger.info(f"Skipping {prompt_id}: insufficient data")
            continue

        # Get current prompt content
        current_content = registry.get(prompt_id)
        if not current_content:
            continue

        # Generate improved variant
        logger.info(f"Generating variant for: {prompt_id}")
        variant_data = generate_prompt_variant(
            prompt_id=prompt_id,
            current_content=current_content,
            stats=prompt_stats,
        )

        if variant_data:
            # Create the variant in registry
            variant = registry.create_variant(
                prompt_id=prompt_id,
                new_content=variant_data["improved_prompt"],
            )
            variants_created.append({
                "prompt_id": prompt_id,
                "version": variant.version,
                "changes": variant_data.get("changes_made", []),
            })

            improvements.append({
                "prompt_id": prompt_id,
                "action": "variant_created",
                "version": variant.version,
                "expected_improvement": variant_data.get("expected_improvement"),
            })

    # TODO: Evaluate existing variants and promote winners
    # This would require tracking which variants are in testing
    # and comparing their performance to baseline

    result = ImprovementResult(
        prompts_analyzed=len(all_prompts),
        variants_created=len(variants_created),
        variants_promoted=len(variants_promoted),
        improvements=improvements,
    )

    logger.info(
        f"Improvement cycle complete: "
        f"{result.prompts_analyzed} analyzed, "
        f"{result.variants_created} variants created, "
        f"{result.variants_promoted} promoted"
    )

    return result


# ---------------------------------------------------------------------------
# Skill Improvement (adding new tools/capabilities)
# ---------------------------------------------------------------------------


SKILL_SUGGESTIONS_TEMPLATE = """You are an expert at designing AI agent capabilities.

Analyze the performance data and suggest new skills/tools that could improve the agent.

## Agent Type
{agent_type}

## Current Skills
{current_skills}

## Performance Issues
{performance_issues}

## Common Failure Patterns
{failure_patterns}

## Task
Suggest 1-3 new skills/tools that could address these issues.

Respond with JSON:
{{
    "suggested_skills": [
        {{
            "name": "skill_name",
            "description": "What this skill does",
            "parameters": ["param1", "param2"],
            "addresses_issue": "Which failure pattern this addresses",
            "implementation_hint": "How to implement this"
        }}
    ]
}}
"""


@trace_op("improvement.suggest_new_skills")
def suggest_new_skills(
    agent_type: str,
    current_skills: list[str],
    performance_issues: list[str],
    failure_patterns: list[str],
) -> list[dict[str, Any]]:
    """Suggest new skills/tools for an agent.

    This doesn't implement the skills, but suggests what could help.

    Args:
        agent_type: "tester" or "grader"
        current_skills: List of current skill names
        performance_issues: Identified performance issues
        failure_patterns: Common failure patterns

    Returns:
        List of suggested skills with implementation hints
    """
    prompt = SKILL_SUGGESTIONS_TEMPLATE.format(
        agent_type=agent_type,
        current_skills="\n".join(f"- {s}" for s in current_skills) or "None defined",
        performance_issues="\n".join(f"- {i}" for i in performance_issues) or "None identified",
        failure_patterns="\n".join(f"- {f}" for f in failure_patterns) or "None identified",
    )

    try:
        result = inference_chat_json(
            model=None,
            messages=[
                {"role": "system", "content": "You are an AI agent architect."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=800,
        )

        return result.get("suggested_skills", [])
    except Exception as e:
        logger.error(f"Failed to suggest skills: {e}")
        return []
