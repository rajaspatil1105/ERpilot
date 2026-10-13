"""Deterministic matching of rules against recorded evidence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import re


PRESENT = "PRESENT"
ABSENT = "ABSENT"
UNKNOWN = "UNKNOWN"
EVIDENCE_STATES = {PRESENT, ABSENT, UNKNOWN}

FULL_MATCH = "FULL_MATCH"
PARTIAL_MATCH = "PARTIAL_MATCH"
NO_MATCH = "NO_MATCH"
MATCH_STATUSES = {FULL_MATCH, PARTIAL_MATCH, NO_MATCH}

_SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class InferenceValidationError(ValueError):
    """Raised when inference inputs are malformed."""


def match_rule(
    rule: Mapping[str, Any],
    evidence: Mapping[str, str],
) -> dict[str, Any]:
    """Evaluate one rule without mutating the rule or evidence inputs."""

    _require_mapping(rule, "rule")
    _require_mapping(evidence, "evidence")

    rule_id = rule.get("rule_id")
    category = rule.get("category")
    _require_non_empty_string(rule_id, "rule.rule_id")
    _require_non_empty_string(category, f"rule {rule_id!r}.category")

    conditions = rule.get("conditions")
    _validate_conditions(conditions, rule_id)
    _validate_evidence(evidence)

    observed_states = {
        condition: evidence.get(condition, UNKNOWN) for condition in conditions
    }
    present_conditions = [
        condition
        for condition, state in observed_states.items()
        if state == PRESENT
    ]
    absent_conditions = [
        condition
        for condition, state in observed_states.items()
        if state == ABSENT
    ]
    unknown_conditions = [
        condition
        for condition, state in observed_states.items()
        if state == UNKNOWN
    ]
    missing_conditions = [
        condition for condition in unknown_conditions if condition not in evidence
    ]

    if not present_conditions or absent_conditions:
        match_status = NO_MATCH
    elif unknown_conditions:
        match_status = PARTIAL_MATCH
    else:
        match_status = FULL_MATCH

    result = {
        "rule_id": rule_id,
        "category": category,
        "match_status": match_status,
        "observed_states": observed_states,
        "present_conditions": present_conditions,
        "absent_conditions": absent_conditions,
        "unknown_conditions": unknown_conditions,
        "missing_conditions": missing_conditions,
        "unmatched_evidence_keys": [
            key for key in evidence if key not in observed_states
        ],
    }
    for field in (
        "conclusion",
        "priority_flag",
        "suggested_department",
        "checklist_action",
        "protocol_reference",
    ):
        if field in rule:
            result[field] = rule[field]
    return result


def _validate_conditions(conditions: Any, rule_id: str) -> None:
    location = f"rule {rule_id!r}.conditions"
    if not isinstance(conditions, list) or not conditions:
        raise InferenceValidationError(
            f"{location}: expected a non-empty list"
        )
    seen: set[str] = set()
    for condition in conditions:
        if not isinstance(condition, str) or not condition:
            raise InferenceValidationError(
                f"{location}: every condition must be a non-empty string"
            )
        if not _SNAKE_CASE_PATTERN.fullmatch(condition):
            raise InferenceValidationError(
                f"{location}: invalid canonical condition key {condition!r}"
            )
        if condition in seen:
            raise InferenceValidationError(
                f"{location}: duplicate condition key {condition!r}"
            )
        seen.add(condition)


def _validate_evidence(evidence: Mapping[str, str]) -> None:
    for key, state in evidence.items():
        if not isinstance(key, str) or not _SNAKE_CASE_PATTERN.fullmatch(key):
            raise InferenceValidationError(
                f"evidence: invalid canonical condition key {key!r}"
            )
        if state not in EVIDENCE_STATES:
            raise InferenceValidationError(
                f"evidence[{key!r}]: invalid evidence state {state!r}; "
                f"expected one of {sorted(EVIDENCE_STATES)}"
            )


def _require_mapping(value: Any, name: str) -> None:
    if not isinstance(value, Mapping):
        raise InferenceValidationError(f"{name}: expected a mapping")


def _require_non_empty_string(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InferenceValidationError(f"{name}: expected a non-empty string")
