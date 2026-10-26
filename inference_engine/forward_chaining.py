"""Forward evaluation of all supplied rules."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .rule_matcher import (
    FULL_MATCH,
    NO_MATCH,
    PARTIAL_MATCH,
    InferenceValidationError,
    match_rule,
)


def run_forward_chaining(
    rules: Iterable[Mapping[str, Any]],
    evidence: Mapping[str, str],
) -> dict[str, Any]:
    """Evaluate every rule in input order and preserve every outcome."""

    if isinstance(rules, (str, bytes)) or not isinstance(rules, Iterable):
        raise InferenceValidationError("rules: expected an iterable of mappings")

    evaluations = [match_rule(rule, evidence) for rule in rules]
    return {
        "evaluations": evaluations,
        "full_matches": [
            result
            for result in evaluations
            if result["match_status"] == FULL_MATCH
        ],
        "partial_matches": [
            result
            for result in evaluations
            if result["match_status"] == PARTIAL_MATCH
        ],
        "no_matches": [
            result
            for result in evaluations
            if result["match_status"] == NO_MATCH
        ],
    }


def run_forward_inference(
    rules: Iterable[Mapping[str, Any]],
    evidence: Mapping[str, str],
) -> dict[str, Any]:
    """Fire configured rules from evidence across categories.

    Current core rules map directly from evidence prerequisites to a
    category-tagged conclusion; they do not define prerequisite facts that
    enable other rules. This therefore performs one rule-firing pass while
    preserving an explicit working-memory trace and category aggregation.
    """

    evaluations = run_forward_chaining(rules, evidence)
    fired = [item for item in evaluations["full_matches"]]
    category_results: dict[str, dict[str, Any]] = {}
    derived: list[dict[str, Any]] = []
    for evaluation in fired:
        category = evaluation["category"]
        category_result = category_results.setdefault(
            category,
            {"category": category, "conclusions": [], "rule_ids": []},
        )
        conclusion = evaluation.get("conclusion")
        if conclusion and conclusion not in category_result["conclusions"]:
            category_result["conclusions"].append(conclusion)
            derived.append({"category": category, "conclusion": conclusion})
        category_result["rule_ids"].append(evaluation["rule_id"])
        evaluation["satisfied_prerequisites"] = list(
            evaluation["present_conditions"]
        )
        evaluation["supporting_facts"] = {
            key: evidence[key]
            for key in evaluation["present_conditions"]
        }
        evaluation["unresolved_prerequisites"] = list(
            evaluation["unknown_conditions"]
        )
        evaluation["contradicted_prerequisites"] = list(
            evaluation["absent_conditions"]
        )

    return {
        **evaluations,
        "working_memory": dict(evidence),
        "fired_rules": fired,
        "derived_conclusions": derived,
        "category_results": list(category_results.values()),
        "unresolved_rules": [
            item for item in evaluations["evaluations"]
            if item["unknown_conditions"]
        ],
        "trace": [
            {
                "rule_id": item["rule_id"],
                "category": item["category"],
                "match_status": item["match_status"],
                "satisfied_prerequisites": item["present_conditions"],
                "unresolved_prerequisites": item["unknown_conditions"],
                "contradicted_prerequisites": item["absent_conditions"],
                "conclusion": item.get("conclusion"),
            }
            for item in evaluations["evaluations"]
        ],
    }
