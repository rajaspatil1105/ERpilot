"""Human-readable explanations for deterministic rule evaluations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .rule_matcher import (
    FULL_MATCH,
    NO_MATCH,
    PARTIAL_MATCH,
    InferenceValidationError,
)


def explain_match(
    match_result: Mapping[str, Any],
    rule: Mapping[str, Any],
) -> str:
    """Create a deterministic explanation from an evaluation and its rule."""

    if not isinstance(match_result, Mapping):
        raise InferenceValidationError("match_result: expected a mapping")
    if not isinstance(rule, Mapping):
        raise InferenceValidationError("rule: expected a mapping")

    rule_id = match_result.get("rule_id", rule.get("rule_id"))
    status = match_result.get("match_status")
    if not isinstance(rule_id, str) or not rule_id:
        raise InferenceValidationError(
            "match_result.rule_id: expected a non-empty string"
        )
    if status not in {FULL_MATCH, PARTIAL_MATCH, NO_MATCH}:
        raise InferenceValidationError(
            f"match_result.match_status: invalid status {status!r}"
        )

    present = _condition_list(match_result, "present_conditions")
    absent = _condition_list(match_result, "absent_conditions")
    unknown = _condition_list(match_result, "unknown_conditions")
    parts = [f"Rule {rule_id}: {status}."]

    if status == FULL_MATCH:
        parts.append(
            "Recorded present conditions: "
            f"{_format_conditions(present)}."
        )
    elif status == PARTIAL_MATCH:
        parts.append(
            "Recorded present conditions: "
            f"{_format_conditions(present)}."
        )
        parts.append(
            "Conditions still unknown or missing: "
            f"{_format_conditions(unknown)}."
        )
    elif absent:
        parts.append(
            "The following conditions were explicitly recorded as absent: "
            f"{_format_conditions(absent)}."
        )
    else:
        parts.append(
            "No required condition was recorded as present; this does not "
            "establish that an injury is absent."
        )

    if status == NO_MATCH and unknown:
        parts.append(
            "Other required conditions remain unknown or missing: "
            f"{_format_conditions(unknown)}."
        )

    protocol_reference = match_result.get(
        "protocol_reference",
        rule.get("protocol_reference"),
    )
    if protocol_reference:
        parts.append(f"Protocol reference: {protocol_reference}.")
    parts.append(
        "This explanation reflects recorded evidence only and does not prove "
        "a diagnosis or guarantee a clinical outcome."
    )
    return " ".join(parts)


def _condition_list(result: Mapping[str, Any], field: str) -> list[str]:
    value = result.get(field, [])
    if not isinstance(value, list) or not all(
        isinstance(condition, str) for condition in value
    ):
        raise InferenceValidationError(
            f"match_result.{field}: expected a list of strings"
        )
    return value


def _format_conditions(conditions: list[str]) -> str:
    return ", ".join(conditions) if conditions else "none"
