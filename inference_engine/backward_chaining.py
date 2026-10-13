"""Backward evaluation of rules supporting an exact target conclusion."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .rule_matcher import (
    InferenceValidationError,
    match_rule,
)


def run_backward_chaining(
    rules: Iterable[Mapping[str, Any]],
    target_conclusion: str,
    evidence: Mapping[str, str],
) -> dict[str, Any]:
    """Evaluate candidate rules whose conclusion exactly matches the target."""

    if not isinstance(target_conclusion, str) or not target_conclusion.strip():
        raise InferenceValidationError(
            "target_conclusion: expected a non-empty string"
        )
    if isinstance(rules, (str, bytes)) or not isinstance(rules, Iterable):
        raise InferenceValidationError("rules: expected an iterable of mappings")

    supplied_rules = list(rules)
    for index, rule in enumerate(supplied_rules):
        if not isinstance(rule, Mapping):
            raise InferenceValidationError(
                f"rules[{index}]: expected a mapping"
            )
    candidates = [
        rule
        for rule in supplied_rules
        if rule.get("conclusion") == target_conclusion
    ]
    evaluations = [match_rule(rule, evidence) for rule in candidates]
    return {
        "target_conclusion": target_conclusion,
        "supported": bool(candidates),
        "no_support": not candidates,
        "candidate_rule_ids": [result["rule_id"] for result in evaluations],
        "evaluations": evaluations,
        "present_conditions": _unique_conditions(
            evaluations, "present_conditions"
        ),
        "absent_conditions": _unique_conditions(
            evaluations, "absent_conditions"
        ),
        "unknown_conditions": _unique_conditions(
            evaluations, "unknown_conditions"
        ),
    }


def _unique_conditions(
    evaluations: list[dict[str, Any]],
    field: str,
) -> list[str]:
    conditions: list[str] = []
    seen: set[str] = set()
    for evaluation in evaluations:
        for condition in evaluation[field]:
            if condition not in seen:
                seen.add(condition)
                conditions.append(condition)
    return conditions
