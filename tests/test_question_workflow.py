import pytest

from inference_engine.question_workflow import run_question_workflow
from inference_engine.rule_matcher import (
    ABSENT,
    FULL_MATCH,
    NO_MATCH,
    PARTIAL_MATCH,
    PRESENT,
    UNKNOWN,
)


def rule(rule_id, conditions, conclusion="shared_conclusion"):
    return {
        "rule_id": rule_id,
        "category": "chest_trauma",
        "conditions": conditions,
        "conclusion": conclusion,
        "priority_flag": "YELLOW",
        "suggested_department": "Emergency Department",
        "checklist_action": "Review the recorded evidence.",
        "protocol_reference": "Test protocol",
    }


QUESTIONS = [
    {
        "question_id": "Q-SHARED",
        "evidence_key": "shared_unknown",
        "prompt": "Was the shared finding documented?",
        "response_mapping": {
            "YES": PRESENT,
            "NO": ABSENT,
            "UNKNOWN": UNKNOWN,
        },
        "applicable_categories": ["chest_trauma"],
        "rule_ids": ["R-01", "R-02"],
    },
    {
        "question_id": "Q-SECOND",
        "evidence_key": "second_unknown",
        "prompt": "Was the second finding documented?",
        "response_mapping": {
            "YES": PRESENT,
            "NO": ABSENT,
            "UNKNOWN": UNKNOWN,
        },
        "applicable_categories": ["chest_trauma"],
        "rule_ids": ["R-01"],
    },
]


def test_partial_rules_select_unique_shared_questions():
    result = run_question_workflow(
        [
            rule("R-01", ["present_finding", "shared_unknown", "second_unknown"]),
            rule("R-02", ["present_finding", "shared_unknown"]),
        ],
        {
            "present_finding": PRESENT,
            "shared_unknown": UNKNOWN,
        },
        QUESTIONS,
        "chest_trauma",
    )

    assert {
        question["question_id"]
        for question in result["follow_up_questions"]
    } == {"Q-SHARED", "Q-SECOND"}
    shared = next(
        question
        for question in result["follow_up_questions"]
        if question["question_id"] == "Q-SHARED"
    )
    assert shared["required_by_rule_ids"] == ["R-01", "R-02"]


@pytest.mark.parametrize(
    ("answer", "expected_status"),
    [
        (PRESENT, FULL_MATCH),
        (ABSENT, NO_MATCH),
        (UNKNOWN, PARTIAL_MATCH),
    ],
)
def test_question_response_states_drive_reevaluation(answer, expected_status):
    result = run_question_workflow(
        [rule("R-01", ["present_finding", "shared_unknown"])],
        {
            "present_finding": PRESENT,
            "shared_unknown": answer,
        },
        QUESTIONS,
        "chest_trauma",
    )

    evaluation = result["forward_result"]["evaluations"][0]
    assert evaluation["match_status"] == expected_status


def test_explicit_absence_is_not_selected_as_a_question():
    result = run_question_workflow(
        [rule("R-01", ["present_finding", "shared_unknown"])],
        {
            "present_finding": PRESENT,
            "shared_unknown": ABSENT,
        },
        QUESTIONS,
        "chest_trauma",
    )

    assert result["follow_up_questions"] == []
    assert result["forward_result"]["evaluations"][0]["match_status"] == NO_MATCH
