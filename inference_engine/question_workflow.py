"""Backward-chaining follow-up questions for unresolved rule conditions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .backward_chaining import run_backward_chaining
from .forward_chaining import run_forward_chaining
from .rule_matcher import PARTIAL_MATCH


def run_question_workflow(
    rules: Iterable[Mapping[str, Any]],
    evidence: Mapping[str, str],
    questions: Iterable[Mapping[str, Any]],
    category: str,
    forward_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate rules backward from conclusions and select relevant questions."""

    supplied_rules = list(rules)
    supplied_questions = list(questions)
    if forward_result is None:
        forward_result = run_forward_chaining(supplied_rules, evidence)
    targets: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    partial_rule_ids: set[str] = set()

    for rule in supplied_rules:
        conclusion = rule["conclusion"]
        if conclusion in seen_targets:
            continue
        seen_targets.add(conclusion)
        backward_result = run_backward_chaining(
            supplied_rules,
            conclusion,
            evidence,
        )
        partial_rule_ids.update(
            evaluation["rule_id"]
            for evaluation in backward_result["evaluations"]
            if evaluation["match_status"] == PARTIAL_MATCH
        )
        targets.append(backward_result)

    question_by_key: dict[str, dict[str, Any]] = {}
    for question in supplied_questions:
        if category not in question["applicable_categories"]:
            continue
        question_by_key[question["evidence_key"]] = question

    selected_questions: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for evaluation in forward_result["evaluations"]:
        if evaluation["rule_id"] not in partial_rule_ids:
            evaluation["follow_up_question_ids"] = []
            continue
        question_ids: list[str] = []
        for condition in evaluation["unknown_conditions"]:
            question = question_by_key.get(condition)
            if question is None or evaluation["rule_id"] not in question["rule_ids"]:
                continue
            question_id = question["question_id"]
            question_ids.append(question_id)
            if question_id in selected_ids:
                continue
            selected_ids.add(question_id)
            selected_questions.append(
                {
                    **question,
                    "required_by_rule_ids": [evaluation["rule_id"]],
                    "target_conclusions": [evaluation["conclusion"]],
                }
            )
        evaluation["follow_up_question_ids"] = question_ids

    for question in selected_questions:
        required_by = set(question["required_by_rule_ids"])
        targets_for_question = set(question["target_conclusions"])
        for evaluation in forward_result["evaluations"]:
            if question["evidence_key"] not in evaluation["unknown_conditions"]:
                continue
            if evaluation["rule_id"] not in question["rule_ids"]:
                continue
            required_by.add(evaluation["rule_id"])
            targets_for_question.add(evaluation["conclusion"])
        question["required_by_rule_ids"] = [
            rule["rule_id"]
            for rule in supplied_rules
            if rule["rule_id"] in required_by
        ]
        question["target_conclusions"] = [
            rule["conclusion"]
            for rule in supplied_rules
            if rule["rule_id"] in required_by
            and rule["conclusion"] in targets_for_question
        ]

    return {
        "forward_result": forward_result,
        "backward_chaining": targets,
        "follow_up_questions": selected_questions,
    }
