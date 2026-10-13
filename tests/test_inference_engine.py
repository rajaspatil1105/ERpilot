from copy import deepcopy

import pytest

from inference_engine.backward_chaining import run_backward_chaining
from inference_engine.explainer import explain_match
from inference_engine.forward_chaining import run_forward_chaining
from inference_engine.rule_matcher import (
    ABSENT,
    FULL_MATCH,
    NO_MATCH,
    PARTIAL_MATCH,
    PRESENT,
    UNKNOWN,
    InferenceValidationError,
    match_rule,
)


_DEFAULT_CONDITIONS = object()


def _rule(
    rule_id="TEST-01",
    conditions=_DEFAULT_CONDITIONS,
    conclusion="test_conclusion",
):
    if conditions is _DEFAULT_CONDITIONS:
        conditions = ["condition_one"]
    return {
        "rule_id": rule_id,
        "category": "brain_trauma",
        "conditions": conditions,
        "conclusion": conclusion,
        "priority_flag": "RED",
        "suggested_department": "Emergency Department",
        "checklist_action": "Review the recorded criteria.",
        "protocol_reference": "Test protocol reference",
    }


def test_all_conditions_present_are_a_full_match():
    result = match_rule(
        _rule(conditions=["condition_one", "condition_two"]),
        {"condition_one": PRESENT, "condition_two": PRESENT},
    )

    assert result["match_status"] == FULL_MATCH
    assert result["present_conditions"] == ["condition_one", "condition_two"]


def test_one_present_and_one_unknown_are_a_partial_match():
    result = match_rule(
        _rule(conditions=["condition_one", "condition_two"]),
        {"condition_one": PRESENT},
    )

    assert result["match_status"] == PARTIAL_MATCH
    assert result["unknown_conditions"] == ["condition_two"]
    assert result["missing_conditions"] == ["condition_two"]


def test_all_conditions_unknown_are_no_match():
    result = match_rule(_rule(conditions=["condition_one", "condition_two"]), {})

    assert result["match_status"] == NO_MATCH
    assert result["unknown_conditions"] == ["condition_one", "condition_two"]


def test_explicitly_absent_condition_is_no_match():
    result = match_rule(
        _rule(conditions=["condition_one", "condition_two"]),
        {"condition_one": PRESENT, "condition_two": ABSENT},
    )

    assert result["match_status"] == NO_MATCH
    assert result["absent_conditions"] == ["condition_two"]


def test_missing_evidence_is_treated_as_unknown():
    result = match_rule(_rule(), {})

    assert result["observed_states"] == {"condition_one": UNKNOWN}
    assert result["missing_conditions"] == ["condition_one"]


def test_multi_condition_rule_can_fully_match():
    result = match_rule(
        _rule(conditions=["condition_one", "condition_two", "condition_three"]),
        {
            "condition_one": PRESENT,
            "condition_two": PRESENT,
            "condition_three": PRESENT,
        },
    )

    assert result["match_status"] == FULL_MATCH


@pytest.mark.parametrize(
    "conditions",
    [[], None, "condition_one", ["condition_one", "condition_one"]],
)
def test_malformed_condition_lists_are_rejected(conditions):
    with pytest.raises(InferenceValidationError):
        match_rule(_rule(conditions=conditions), {})


def test_invalid_evidence_states_are_rejected():
    with pytest.raises(InferenceValidationError, match="invalid evidence state"):
        match_rule(_rule(), {"condition_one": "MAYBE"})


def test_inputs_are_not_mutated():
    rule = _rule(conditions=["condition_one", "condition_two"])
    evidence = {"condition_one": PRESENT}
    original_rule = deepcopy(rule)
    original_evidence = deepcopy(evidence)

    match_rule(rule, evidence)

    assert rule == original_rule
    assert evidence == original_evidence


def test_unknown_evidence_keys_are_reported_without_aliasing():
    result = match_rule(
        _rule(),
        {"condition_one": PRESENT, "another_canonical_key": UNKNOWN},
    )

    assert result["unmatched_evidence_keys"] == ["another_canonical_key"]


def test_forward_chaining_evaluates_and_separates_every_rule():
    rules = [
        _rule("TEST-01"),
        _rule("TEST-02", ["condition_one", "condition_two"]),
        _rule("TEST-03", ["condition_two"]),
    ]

    result = run_forward_chaining(
        rules,
        {"condition_one": PRESENT},
    )

    assert [item["rule_id"] for item in result["evaluations"]] == [
        "TEST-01",
        "TEST-02",
        "TEST-03",
    ]
    assert [item["rule_id"] for item in result["full_matches"]] == ["TEST-01"]
    assert [item["rule_id"] for item in result["partial_matches"]] == ["TEST-02"]
    assert [item["rule_id"] for item in result["no_matches"]] == ["TEST-03"]


def test_forward_chaining_preserves_conflicting_matches_and_empty_results():
    rules = [
        _rule("TEST-01", conclusion="conclusion_a"),
        _rule("TEST-02", conclusion="conclusion_b"),
    ]

    result = run_forward_chaining(rules, {"condition_one": PRESENT})

    assert [item["rule_id"] for item in result["full_matches"]] == [
        "TEST-01",
        "TEST-02",
    ]
    assert run_forward_chaining([], {}) == {
        "evaluations": [],
        "full_matches": [],
        "partial_matches": [],
        "no_matches": [],
    }


def test_backward_chaining_finds_exact_supported_target():
    rules = [
        _rule("TEST-01", conclusion="target"),
        _rule("TEST-02", conclusion="other"),
    ]

    result = run_backward_chaining(rules, "target", {"condition_one": PRESENT})

    assert result["supported"] is True
    assert result["no_support"] is False
    assert result["candidate_rule_ids"] == ["TEST-01"]
    assert result["evaluations"][0]["match_status"] == FULL_MATCH


def test_backward_chaining_reports_partial_and_no_match_candidates():
    rules = [_rule("TEST-01", ["condition_one", "condition_two"], "target")]

    partial = run_backward_chaining(rules, "target", {"condition_one": PRESENT})
    absent = run_backward_chaining(
        rules,
        "target",
        {"condition_one": PRESENT, "condition_two": ABSENT},
    )

    assert partial["evaluations"][0]["match_status"] == PARTIAL_MATCH
    assert partial["unknown_conditions"] == ["condition_two"]
    assert absent["evaluations"][0]["match_status"] == NO_MATCH
    assert absent["absent_conditions"] == ["condition_two"]


def test_backward_chaining_reports_unsupported_target():
    result = run_backward_chaining([_rule()], "unsupported", {})

    assert result == {
        "target_conclusion": "unsupported",
        "supported": False,
        "no_support": True,
        "candidate_rule_ids": [],
        "evaluations": [],
        "present_conditions": [],
        "absent_conditions": [],
        "unknown_conditions": [],
    }


def test_explanations_distinguish_full_partial_and_no_match():
    rule = _rule(conditions=["condition_one", "condition_two"])
    full = match_rule(
        rule,
        {"condition_one": PRESENT, "condition_two": PRESENT},
    )
    partial = match_rule(rule, {"condition_one": PRESENT})
    no_match = match_rule(rule, {"condition_two": ABSENT})

    full_text = explain_match(full, rule)
    partial_text = explain_match(partial, rule)
    no_match_text = explain_match(no_match, rule)

    assert "TEST-01: FULL_MATCH" in full_text
    assert "condition_one, condition_two" in full_text
    assert "TEST-01: PARTIAL_MATCH" in partial_text
    assert "unknown or missing" in partial_text
    assert "TEST-01: NO_MATCH" in no_match_text
    assert "explicitly recorded as absent" in no_match_text
    assert "does not prove a diagnosis" in full_text
    assert "Test protocol reference" in full_text
