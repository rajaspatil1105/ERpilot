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
)


ROOT = Path(__file__).resolve().parents[1]
SYMPTOMS_PATH = ROOT / "knowledge_base" / "symptoms.json"
DEPARTMENTS_PATH = ROOT / "knowledge_base" / "departments.json"
RULES_PATH = ROOT / "rule_base" / "core" / "brain_trauma_rules.json"
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

    assert len(rules) == 7
    assert {rule["rule_id"] for rule in rules} == {
        f"BT-{number:02d}" for number in range(1, 8)
    }


def test_valid_in_memory_data_passes_validation():
    assert len(_validate_fixture()) == 7


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
    assert rule_ids == [f"BT-{number:02d}" for number in range(1, 8)]


def test_valid_json_file_is_loadable(tmp_path):
    path = tmp_path / "valid.json"
    path.write_text(json.dumps({"valid": True}), encoding="utf-8")

    assert load_json_file(path) == {"valid": True}


def test_malformed_json_has_a_clear_error(tmp_path):
    path = tmp_path / "malformed.json"
    path.write_text('{"valid": ', encoding="utf-8")

    with pytest.raises(ValidationError, match=r"malformed\.json.*line"):
        load_json_file(path)
