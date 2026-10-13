"""Deterministic evaluation of additive special-condition modifiers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .rule_matcher import (
    ABSENT,
    FULL_MATCH,
    NO_MATCH,
    PRESENT,
    UNKNOWN,
    InferenceValidationError,
)


def run_modifier_evaluation(
    modifiers: Iterable[Mapping[str, Any]],
    category: str,
    evidence: Mapping[str, str],
) -> dict[str, Any]:
    """Evaluate applicable modifiers without changing core rule results."""

    if isinstance(modifiers, (str, bytes)) or not isinstance(modifiers, Iterable):
        raise InferenceValidationError(
            "modifiers: expected an iterable of mappings"
        )
    if not isinstance(category, str) or not category:
        raise InferenceValidationError(
            "category: expected a non-empty string"
        )
    if not isinstance(evidence, Mapping):
        raise InferenceValidationError("evidence: expected a mapping")

    evaluations: list[dict[str, Any]] = []
    for modifier in modifiers:
        if not isinstance(modifier, Mapping):
            raise InferenceValidationError(
                "each modifier must be a mapping"
            )
        applies_when_fired = modifier.get("applies_when_fired")
        if not isinstance(applies_when_fired, list):
            raise InferenceValidationError(
                f"modifier {modifier.get('modifier_id')!r}: "
                "applies_when_fired must be a list"
            )
        if category not in applies_when_fired:
            continue
        modifier_id = modifier.get("modifier_id")
        trigger = modifier.get("trigger")
        if not isinstance(modifier_id, str) or not modifier_id:
            raise InferenceValidationError(
                "modifier.modifier_id: expected a non-empty string"
            )
        if not isinstance(trigger, str) or not trigger:
            raise InferenceValidationError(
                f"modifier {modifier_id}: expected a trigger"
            )

        state = evidence.get(trigger, UNKNOWN)
        if state not in {ABSENT, PRESENT, UNKNOWN}:
            raise InferenceValidationError(
                f"invalid evidence state for modifier trigger {trigger!r}: "
                f"{state!r}"
            )
        is_fired = state == PRESENT
        evaluation = {
            "modifier_id": modifier_id,
            "match_status": FULL_MATCH if is_fired else NO_MATCH,
            "trigger": trigger,
            "matched_conditions": [trigger] if is_fired else [],
            "present_conditions": [trigger] if is_fired else [],
            "absent_conditions": [trigger] if state == ABSENT else [],
            "unknown_conditions": [trigger] if state == UNKNOWN else [],
            "action": modifier["action"],
            "priority_override": modifier["priority_override"],
            "applies_when_fired": list(applies_when_fired),
            "protocol_reference": modifier["protocol_reference"],
        }
        evaluation["explanation"] = _explain_modifier(evaluation)
        evaluations.append(evaluation)

    fired_modifiers = [
        evaluation
        for evaluation in evaluations
        if evaluation["match_status"] == FULL_MATCH
    ]
    return {
        "evaluations": evaluations,
        "submitted_evidence": dict(evidence),
        "fired_modifiers": fired_modifiers,
        "no_matches": [
            evaluation
            for evaluation in evaluations
            if evaluation["match_status"] == NO_MATCH
        ],
        "outcome": FULL_MATCH if fired_modifiers else NO_MATCH,
    }


def _explain_modifier(evaluation: Mapping[str, Any]) -> str:
    status = evaluation["match_status"]
    modifier_id = evaluation["modifier_id"]
    trigger = evaluation["trigger"]
    if status == FULL_MATCH:
        evidence_text = f"Recorded present condition: {trigger}."
    elif evaluation["absent_conditions"]:
        evidence_text = f"Recorded absent condition: {trigger}."
    else:
        evidence_text = f"Condition remains unknown or missing: {trigger}."
    return (
        f"Modifier {modifier_id}: {status}. {evidence_text} "
        f"Action: {evaluation['action']} "
        f"Protocol reference: {evaluation['protocol_reference']}. "
        "This modifier reflects recorded evidence only and does not prove a "
        "diagnosis or change the core trauma classification."
    )
