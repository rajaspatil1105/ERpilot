import copy
import json
from pathlib import Path

import pytest

from inference_engine.rule_validator import (
    ValidationError,
    load_json_file,
    validate_core_rules,
    validate_dataset_files,
    validate_departments,
    validate_symptoms,
    validate_questions,
)


ROOT = Path(__file__).resolve().parents[1]
SYMPTOMS_PATH = ROOT / "knowledge_base" / "symptoms.json"
DEPARTMENTS_PATH = ROOT / "knowledge_base" / "departments.json"
RULES_PATH = ROOT / "rule_base" / "core" / "brain_trauma_rules.json"
STAGE_6_RULE_PATHS = (
    ROOT / "rule_base" / "core" / "chest_trauma_rules.json",
    ROOT / "rule_base" / "core" / "abdominal_trauma_rules.json",
    ROOT / "rule_base" / "core" / "orthopedic_trauma_rules.json",
)
PROTOCOL_REFERENCE = (
    "NICE NG232, recommendation 1.5.8: "
    "https://www.nice.org.uk/guidance/NG232/chapter/recommendations"
)


def _valid_symptoms():
    return {
        "version": "1.0",
        "symptoms": [
            {
                "key": "adult_head_injury_test_criterion",
                "label": "Test criterion",
                "category": "brain_trauma",
                "evidence_type": "derived_criterion",
                "description": "Test criterion description.",
                "source_reference": "NICE NG232, recommendation 1.5.8",
            }
        ],
    }


def _valid_departments():
    return {
        "departments": [
            {
                "department_id": "emergency_department",
                "name": "Emergency Department",
                "description": "Test department.",
            }
        ]
    }


def _valid_rules():
    return {
        "rules": [
            {
                "rule_id": f"BT-{number:02d}",
                "category": "brain_trauma",
                "conditions": ["adult_head_injury_test_criterion"],
                "conclusion": "adult_head_injury_urgent_clinician_review",
                "priority_flag": "RED",
                "suggested_department": "Emergency Department",
                "checklist_action": "Flag the criterion for clinician review.",
                "protocol_reference": PROTOCOL_REFERENCE,
            }
            for number in range(1, 8)
        ]
        + [
            {
                "rule_id": f"BT-P{number:02d}",
                "category": "brain_trauma",
                "conditions": ["adult_head_injury_test_criterion"],
                "conclusion": "adult_head_injury_urgent_clinician_review",
                "priority_flag": "RED",
                "suggested_department": "Emergency Department",
                "checklist_action": "Flag the criterion for clinician review.",
                "protocol_reference": PROTOCOL_REFERENCE,
            }
            for number in range(1, 11)
        ]
    }


def _validate_fixture(symptoms=None, departments=None, rules=None):
    symptoms = symptoms or _valid_symptoms()
    departments = departments or _valid_departments()
    rules = rules or _valid_rules()
    symptom_keys = validate_symptoms(symptoms)
    department_catalog = validate_departments(departments)
    return validate_core_rules(rules, symptom_keys, department_catalog)


def test_valid_project_datasets_pass_validation():
    rules = validate_dataset_files(SYMPTOMS_PATH, DEPARTMENTS_PATH, RULES_PATH)

    assert len(rules) == 17
    assert {rule["rule_id"] for rule in rules} == {
        *{f"BT-{number:02d}" for number in range(1, 8)},
        *{f"BT-P{number:02d}" for number in range(1, 11)},
    }


def test_question_metadata_is_valid_and_links_to_real_rules():
    symptoms = load_json_file(SYMPTOMS_PATH)
    rules_by_id = {}
    for rules_path in (RULES_PATH, *STAGE_6_RULE_PATHS):
        for rule in validate_dataset_files(
            SYMPTOMS_PATH,
            DEPARTMENTS_PATH,
            rules_path,
        ):
            rules_by_id[rule["rule_id"]] = rule["category"]

    questions = load_json_file(ROOT / "knowledge_base" / "questions.json")
    validated = validate_questions(
        questions,
        validate_symptoms(symptoms),
        rules_by_id,
    )

    assert {question["question_id"] for question in validated} == {
        "Q-CT-EFAST-TEAM",
        "Q-CT-EFAST-TRANSFER",
    }


@pytest.mark.parametrize("rules_path", STAGE_6_RULE_PATHS)
def test_stage_6_rule_files_pass_validation(rules_path):
    category = rules_path.stem.removesuffix("_trauma_rules") + "_trauma"
    rules = validate_dataset_files(
        SYMPTOMS_PATH,
        DEPARTMENTS_PATH,
        rules_path,
        expected_category=category,
    )

    assert rules
    assert all(rule["category"] == category for rule in rules)
    assert all("recommendation " in rule["protocol_reference"] for rule in rules)


def test_orthopedic_rules_preserve_ng38_scope():
    rules = validate_dataset_files(
        SYMPTOMS_PATH,
        DEPARTMENTS_PATH,
        STAGE_6_RULE_PATHS[2],
        expected_category="orthopedic_trauma",
    )
    rules_by_id = {rule["rule_id"]: rule for rule in rules}

    assert rules_by_id["OT-01"]["conditions"] == [
        "orthopedic_trauma_suspected_knee_fracture_person_over_2"
    ]
    assert rules_by_id["OT-02"]["conditions"] == [
        "orthopedic_trauma_reduction_or_cast_splint_traction"
    ]
    assert "Ottawa knee rules" in rules_by_id["OT-01"]["checklist_action"]
    assert "before and after the intervention" in rules_by_id["OT-02"][
        "checklist_action"
    ]


def test_expanded_rules_preserve_source_specific_conditions():
    brain_rules = validate_dataset_files(
        SYMPTOMS_PATH,
        DEPARTMENTS_PATH,
        RULES_PATH,
        expected_category="brain_trauma",
    )
    chest_rules = validate_dataset_files(
        SYMPTOMS_PATH,
        DEPARTMENTS_PATH,
        STAGE_6_RULE_PATHS[0],
        expected_category="chest_trauma",
    )
    abdominal_rules = validate_dataset_files(
        SYMPTOMS_PATH,
        DEPARTMENTS_PATH,
        STAGE_6_RULE_PATHS[1],
        expected_category="abdominal_trauma",
    )
    orthopedic_rules = validate_dataset_files(
        SYMPTOMS_PATH,
        DEPARTMENTS_PATH,
        STAGE_6_RULE_PATHS[2],
        expected_category="orthopedic_trauma",
    )

    assert len(brain_rules) == 17
    assert all(
        rule["conditions"][0].startswith("paediatric_")
        for rule in brain_rules
        if rule["rule_id"].startswith("BT-P")
    )
    assert {rule["rule_id"] for rule in chest_rules} == {"CT-01", "CT-02"}
    assert {rule["rule_id"] for rule in abdominal_rules} == {"AT-01", "AT-02"}
    assert {rule["rule_id"] for rule in orthopedic_rules} == {
        "OT-01",
        "OT-02",
        "OT-03",
    }


def test_valid_in_memory_data_passes_validation():
    assert len(_validate_fixture()) == 17


def test_duplicate_symptom_keys_are_rejected():
    symptoms = _valid_symptoms()
    symptoms["symptoms"].append(copy.deepcopy(symptoms["symptoms"][0]))

    with pytest.raises(ValidationError, match="duplicate symptom key"):
        validate_symptoms(symptoms)


def test_duplicate_rule_ids_are_rejected():
    rules = _valid_rules()
    rules["rules"][1]["rule_id"] = rules["rules"][0]["rule_id"]

    with pytest.raises(ValidationError, match="duplicate rule ID"):
        _validate_fixture(rules=rules)


def test_unknown_condition_key_is_rejected():
    rules = _valid_rules()
    rules["rules"][0]["conditions"] = ["unknown_condition"]

    with pytest.raises(ValidationError, match="unknown condition key"):
        _validate_fixture(rules=rules)


def test_missing_required_field_is_rejected():
    symptoms = _valid_symptoms()
    del symptoms["symptoms"][0]["label"]

    with pytest.raises(ValidationError, match="missing required field"):
        validate_symptoms(symptoms)


def test_unexpected_field_is_rejected():
    departments = _valid_departments()
    departments["departments"][0]["extra"] = "not allowed"

    with pytest.raises(ValidationError, match="unexpected field"):
        validate_departments(departments)


def test_invalid_category_is_rejected():
    symptoms = _valid_symptoms()
    symptoms["symptoms"][0]["category"] = "unsupported_category"

    with pytest.raises(ValidationError, match="invalid category"):
        validate_symptoms(symptoms)


def test_invalid_priority_is_rejected():
    rules = _valid_rules()
    rules["rules"][0]["priority_flag"] = "URGENT"

    with pytest.raises(ValidationError, match="invalid priority"):
        _validate_fixture(rules=rules)


def test_unknown_department_is_rejected():
    rules = _valid_rules()
    rules["rules"][0]["suggested_department"] = "Unknown Department"

    with pytest.raises(ValidationError, match="unknown department"):
        _validate_fixture(rules=rules)


def test_empty_protocol_reference_is_rejected():
    rules = _valid_rules()
    rules["rules"][0]["protocol_reference"] = ""

    with pytest.raises(ValidationError, match="non-empty string"):
        _validate_fixture(rules=rules)


def test_malformed_condition_list_is_rejected():
    rules = _valid_rules()
    rules["rules"][0]["conditions"] = "not-a-list"

    with pytest.raises(ValidationError, match="non-empty list"):
        _validate_fixture(rules=rules)


def test_all_expected_rules_are_present_exactly_once():
    rules = _valid_rules()

    validated = _validate_fixture(rules=rules)

    rule_ids = [rule["rule_id"] for rule in validated]
    assert rule_ids == [
        *[f"BT-{number:02d}" for number in range(1, 8)],
        *[f"BT-P{number:02d}" for number in range(1, 11)],
    ]


def test_valid_json_file_is_loadable(tmp_path):
    path = tmp_path / "valid.json"
    path.write_text(json.dumps({"valid": True}), encoding="utf-8")

    assert load_json_file(path) == {"valid": True}


def test_malformed_json_has_a_clear_error(tmp_path):
    path = tmp_path / "malformed.json"
    path.write_text('{"valid": ', encoding="utf-8")

    with pytest.raises(ValidationError, match=r"malformed\.json.*line"):
        load_json_file(path)
