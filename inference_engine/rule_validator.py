"""Validation helpers for the Stage 2 knowledge base and core rules."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ALLOWED_CATEGORIES = {
    "brain_trauma",
    "chest_trauma",
    "abdominal_trauma",
    "orthopedic_trauma",
}
ALLOWED_PRIORITIES = {"RED", "ORANGE", "YELLOW", "GREEN"}
EXPECTED_BRAIN_RULE_IDS = {f"BT-{number:02d}" for number in range(1, 8)}
PROTOCOL_URL = (
    "https://www.nice.org.uk/guidance/NG232/chapter/recommendations"
)

SYMPTOM_FIELDS = {
    "key",
    "label",
    "category",
    "evidence_type",
    "description",
    "source_reference",
}
DEPARTMENT_FIELDS = {"department_id", "name", "description"}
RULE_FIELDS = {
    "rule_id",
    "category",
    "conditions",
    "conclusion",
    "priority_flag",
    "suggested_department",
    "checklist_action",
    "protocol_reference",
}
SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class ValidationError(ValueError):
    """Raised when a knowledge-base or rule dataset is invalid."""


def load_json_file(path: str | Path) -> Any:
    """Load a JSON file and report malformed input with its file location."""

    file_path = Path(path)
    try:
        with file_path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except FileNotFoundError as error:
        raise ValidationError(f"{file_path}: file does not exist") from error
    except json.JSONDecodeError as error:
        raise ValidationError(
            f"{file_path}: malformed JSON at line {error.lineno}, "
            f"column {error.colno}: {error.msg}"
        ) from error


def validate_symptoms(data: Any, source: str | Path = "symptoms.json") -> set[str]:
    """Validate the canonical symptom vocabulary and return its keys."""

    source_name = str(source)
    _require_mapping(data, source_name)
    _require_exact_fields(data, {"version", "symptoms"}, source_name)
    _require_non_empty_string(data["version"], f"{source_name}.version")
    symptoms = data["symptoms"]
    if not isinstance(symptoms, list):
        raise ValidationError(f"{source_name}.symptoms: expected a list")

    symptom_keys: set[str] = set()
    for index, symptom in enumerate(symptoms):
        location = f"{source_name}.symptoms[{index}]"
        _require_mapping(symptom, location)
        _require_exact_fields(symptom, SYMPTOM_FIELDS, location)
        for field in SYMPTOM_FIELDS:
            _require_non_empty_string(symptom[field], f"{location}.{field}")
        key = symptom["key"]
        _require_snake_case(key, f"{location}.key")
        if key in symptom_keys:
            raise ValidationError(f"{location}.key: duplicate symptom key {key!r}")
        symptom_keys.add(key)
        if symptom["category"] not in ALLOWED_CATEGORIES:
            raise ValidationError(
                f"{location}.category: invalid category "
                f"{symptom['category']!r}"
            )

    return symptom_keys


def validate_departments(
    data: Any,
    source: str | Path = "departments.json",
) -> dict[str, str]:
    """Validate departments and return display-name to ID mappings."""

    source_name = str(source)
    _require_mapping(data, source_name)
    _require_exact_fields(data, {"departments"}, source_name)
    departments = data["departments"]
    if not isinstance(departments, list):
        raise ValidationError(f"{source_name}.departments: expected a list")

    department_catalog: dict[str, str] = {}
    department_ids: set[str] = set()
    for index, department in enumerate(departments):
        location = f"{source_name}.departments[{index}]"
        _require_mapping(department, location)
        _require_exact_fields(department, DEPARTMENT_FIELDS, location)
        for field in DEPARTMENT_FIELDS:
            _require_non_empty_string(department[field], f"{location}.{field}")
        department_id = department["department_id"]
        if department_id in department_ids:
            raise ValidationError(
                f"{location}.department_id: duplicate department ID "
                f"{department_id!r}"
            )
        department_name = department["name"]
        if department_name in department_catalog:
            raise ValidationError(
                f"{location}.name: duplicate department name "
                f"{department_name!r}"
            )
        department_ids.add(department_id)
        department_catalog[department_name] = department_id

    return department_catalog


def validate_core_rules(
    data: Any,
    symptom_keys: set[str],
    department_catalog: Mapping[str, str],
    source: str | Path = "brain_trauma_rules.json",
) -> list[dict[str, Any]]:
    """Validate core rules against canonical symptoms and departments."""

    source_name = str(source)
    _require_mapping(data, source_name)
    _require_exact_fields(data, {"rules"}, source_name)
    rules = data["rules"]
    if not isinstance(rules, list):
        raise ValidationError(f"{source_name}.rules: expected a list")

    rule_ids: set[str] = set()
    validated_rules: list[dict[str, Any]] = []
    for index, rule in enumerate(rules):
        location = f"{source_name}.rules[{index}]"
        _require_mapping(rule, location)
        _require_exact_fields(rule, RULE_FIELDS, location)
        for field in (
            "rule_id",
            "category",
            "conclusion",
            "priority_flag",
            "suggested_department",
            "checklist_action",
            "protocol_reference",
        ):
            _require_non_empty_string(rule[field], f"{location}.{field}")

        rule_id = rule["rule_id"]
        if rule_id in rule_ids:
            raise ValidationError(
                f"{location}.rule_id: duplicate rule ID {rule_id!r}"
            )
        rule_ids.add(rule_id)

        if rule["category"] not in ALLOWED_CATEGORIES:
            raise ValidationError(
                f"{location} ({rule_id}).category: invalid category "
                f"{rule['category']!r}"
            )
        if rule["priority_flag"] not in ALLOWED_PRIORITIES:
            raise ValidationError(
                f"{location} ({rule_id}).priority_flag: invalid priority "
                f"{rule['priority_flag']!r}"
            )
        conditions = rule["conditions"]
        if not isinstance(conditions, list) or not conditions:
            raise ValidationError(
                f"{location} ({rule_id}).conditions: expected a non-empty list"
            )
        condition_keys: set[str] = set()
        for condition in conditions:
            condition_location = f"{location} ({rule_id}).conditions"
            if not isinstance(condition, str) or not condition:
                raise ValidationError(
                    f"{condition_location}: every condition must be a "
                    "non-empty string"
                )
            _require_snake_case(condition, condition_location)
            if condition in condition_keys:
                raise ValidationError(
                    f"{condition_location}: duplicate condition key {condition!r}"
                )
            if condition not in symptom_keys:
                raise ValidationError(
                    f"{condition_location}: unknown condition key {condition!r}"
                )
            condition_keys.add(condition)

        department_name = rule["suggested_department"]
        if not _department_name_exists(department_name, department_catalog):
            raise ValidationError(
                f"{location} ({rule_id}).suggested_department: unknown "
                f"department {department_name!r}"
            )
        _require_traceable_protocol_reference(
            rule["protocol_reference"],
            f"{location} ({rule_id}).protocol_reference",
        )
        validated_rules.append(rule)

    missing_expected = EXPECTED_BRAIN_RULE_IDS - rule_ids
    unexpected_brain_ids = rule_ids - EXPECTED_BRAIN_RULE_IDS
    if missing_expected:
        missing = ", ".join(sorted(missing_expected))
        raise ValidationError(
            f"{source_name}.rules: missing expected brain-trauma rule IDs: "
            f"{missing}"
        )
    if unexpected_brain_ids:
        unexpected = ", ".join(sorted(unexpected_brain_ids))
        raise ValidationError(
            f"{source_name}.rules: unexpected brain-trauma rule IDs: "
            f"{unexpected}"
        )

    return validated_rules


def validate_dataset_files(
    symptoms_path: str | Path,
    departments_path: str | Path,
    rules_path: str | Path,
) -> list[dict[str, Any]]:
    """Load and validate the Stage 2 datasets together."""

    symptom_data = load_json_file(symptoms_path)
    department_data = load_json_file(departments_path)
    rule_data = load_json_file(rules_path)
    symptom_keys = validate_symptoms(symptom_data, symptoms_path)
    department_catalog = validate_departments(department_data, departments_path)
    return validate_core_rules(
        rule_data,
        symptom_keys,
        department_catalog,
        rules_path,
    )


def _department_name_exists(
    name: str,
    department_catalog: Mapping[str, str],
) -> bool:
    """Resolve the schema's display-name department reference."""

    return name in department_catalog


def _require_mapping(value: Any, location: str) -> None:
    if not isinstance(value, dict):
        raise ValidationError(f"{location}: expected an object")


def _require_exact_fields(
    value: dict[str, Any],
    expected_fields: set[str],
    location: str,
) -> None:
    actual_fields = set(value)
    missing = expected_fields - actual_fields
    unexpected = actual_fields - expected_fields
    if missing:
        raise ValidationError(
            f"{location}: missing required field(s): {', '.join(sorted(missing))}"
        )
    if unexpected:
        raise ValidationError(
            f"{location}: unexpected field(s): {', '.join(sorted(unexpected))}"
        )


def _require_non_empty_string(value: Any, location: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{location}: expected a non-empty string")


def _require_snake_case(value: str, location: str) -> None:
    if not SNAKE_CASE_PATTERN.fullmatch(value):
        raise ValidationError(
            f"{location}: expected a snake_case condition key, got {value!r}"
        )


def _require_traceable_protocol_reference(
    value: str,
    location: str,
) -> None:
    if PROTOCOL_URL not in value or "recommendation " not in value.lower():
        raise ValidationError(
            f"{location}: must include a source locator and recommendation "
            f"reference ({PROTOCOL_URL})"
        )
