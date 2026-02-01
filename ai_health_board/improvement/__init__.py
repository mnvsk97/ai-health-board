"""Self-improvement system for tester and grader agents.

This module provides:
1. Prompt Registry - Dynamic prompt management with versioning
2. Grader Scorer - Evaluate grader accuracy against ground truth
3. Real Improvement Loop - A/B testing and validated updates
4. Skill Improvement - Dynamic skill/tool generation with Claude
"""

from .prompt_registry import PromptRegistry, PromptVersion, get_registry
from .grader_scorer import GraderAccuracyScorer, GraderConsistencyScorer, score_grader_output
from .improvement_loop import (
    run_validated_improvement_cycle,
    analyze_prompt_performance,
    generate_prompt_variant,
    suggest_new_skills,
)
from .skill_improver import (
    SkillSpec,
    SkillRegistry,
    get_skill_registry,
    detect_skill_gaps,
    design_skill,
    validate_skill_code,
    run_skill_improvement_cycle,
    get_active_skills_for_agent,
    execute_skill,
)

__all__ = [
    # Prompt improvement
    "PromptRegistry",
    "PromptVersion",
    "get_registry",
    # Grader scoring
    "GraderAccuracyScorer",
    "GraderConsistencyScorer",
    "score_grader_output",
    # Prompt improvement loop
    "run_validated_improvement_cycle",
    "analyze_prompt_performance",
    "generate_prompt_variant",
    "suggest_new_skills",
    # Skill improvement
    "SkillSpec",
    "SkillRegistry",
    "get_skill_registry",
    "detect_skill_gaps",
    "design_skill",
    "validate_skill_code",
    "run_skill_improvement_cycle",
    "get_active_skills_for_agent",
    "execute_skill",
]
