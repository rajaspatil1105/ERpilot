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
