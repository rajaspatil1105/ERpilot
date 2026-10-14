"""Patient registration and trauma triage API routes."""

from __future__ import annotations

import json
import math
from io import BytesIO
from pathlib import Path
from typing import Any

from flask import Blueprint, current_app, jsonify, request, send_file

from inference_engine.explainer import explain_match
from inference_engine.forward_chaining import run_forward_chaining
from inference_engine.modifier_matcher import run_modifier_evaluation
from inference_engine.question_workflow import run_question_workflow
from inference_engine.rule_matcher import (
    EVIDENCE_STATES,
    FULL_MATCH,
    NO_MATCH,
    PARTIAL_MATCH,
    InferenceValidationError,
)
from inference_engine.rule_validator import (
    ALLOWED_CATEGORIES,
    ValidationError,
    load_json_file,
    validate_core_rules,
    validate_departments,
    validate_modifier_files,
    validate_questions,
    validate_symptoms,
    SPECIAL_CONDITION_CATEGORY,
)
from models.assessment import Assessment
from models.db import db
from models.patient import Patient
from reporting import (
    ReportDataError,
    build_report_data,
    generate_docx_report,
    generate_pdf_report,
)


triage_bp = Blueprint("triage", __name__, url_prefix="/api")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SYMPTOMS_PATH = PROJECT_ROOT / "knowledge_base" / "symptoms.json"
QUESTIONS_PATH = PROJECT_ROOT / "knowledge_base" / "questions.json"
DEPARTMENTS_PATH = PROJECT_ROOT / "knowledge_base" / "departments.json"
RULES_PATHS = {
    "brain_trauma": PROJECT_ROOT / "rule_base" / "core" / "brain_trauma_rules.json",
    "chest_trauma": PROJECT_ROOT / "rule_base" / "core" / "chest_trauma_rules.json",
    "abdominal_trauma": PROJECT_ROOT / "rule_base" / "core" / "abdominal_trauma_rules.json",
    "orthopedic_trauma": PROJECT_ROOT / "rule_base" / "core" / "orthopedic_trauma_rules.json",
}
MODIFIER_PATHS = (
    PROJECT_ROOT
    / "rule_base"
    / "special_conditions"
    / "pregnancy_modifiers.json",
    PROJECT_ROOT
    / "rule_base"
    / "special_conditions"
    / "anticoagulant_modifiers.json",
    PROJECT_ROOT
    / "rule_base"
    / "special_conditions"
    / "opioid_intoxication_modifiers.json",
    PROJECT_ROOT
    / "rule_base"
    / "special_conditions"
    / "allergy_modifiers.json",
)
SUPPORTED_RULE_CATEGORIES = set(RULES_PATHS)
REPORT_FORMATS = {
    "pdf": (
        "application/pdf",
        "pdf",
        generate_pdf_report,
    ),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "docx",
        generate_docx_report,
    ),
}


@triage_bp.post("/patients")
def create_patient():
    """Register a patient after validating all required registration fields."""

    try:
        payload = _request_object()
    except RequestValidationError as error:
        return _error(error.message, 400, error.field)

    required_fields = ("name", "age", "gender", "incident_type")
    for field in required_fields:
        if field not in payload:
            return _error(f"Missing required field: {field}.", 400, field)

    text_values = {}
    for field in ("name", "gender", "incident_type"):
        value = payload[field]
        if not isinstance(value, str) or not value.strip():
            return _error(
                f"{field} must be a non-empty string.",
                400,
                field,
            )
        text_values[field] = value.strip()

    age = payload["age"]
    if isinstance(age, bool) or not isinstance(age, int) or age < 0:
        return _error(
            "age must be a non-negative integer.",
            400,
            "age",
        )

    patient = Patient(age=age, **text_values)
    try:
        db.session.add(patient)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Unable to persist patient registration")
        return _error("Unable to persist patient registration.", 500)

    return (
        jsonify(
            id=patient.id,
            name=patient.name,
            age=patient.age,
            gender=patient.gender,
            incident_type=patient.incident_type,
            disclaimer=_disclaimer(),
        ),
        201,
    )


@triage_bp.post("/triage")
def create_triage_assessment():
    """Evaluate and persist a trauma assessment."""

    try:
        payload = _request_object()
    except RequestValidationError as error:
        return _error(error.message, 400, error.field)

    required_fields = ("patient_id", "category", "evidence")
    for field in required_fields:
        if field not in payload:
            return _error(f"Missing required field: {field}.", 400, field)

    patient_id = payload["patient_id"]
    if (
        isinstance(patient_id, bool)
        or not isinstance(patient_id, int)
        or patient_id <= 0
    ):
        return _error(
            "patient_id must be a positive integer.",
            400,
            "patient_id",
        )
    patient = db.session.get(Patient, patient_id)
    if patient is None:
        return _error("Patient was not found.", 404, "patient_id")

    category = payload["category"]
    if not isinstance(category, str) or category not in ALLOWED_CATEGORIES:
        return _error(
            "category must be one of the canonical trauma categories.",
            400,
            "category",
        )
    if category not in SUPPORTED_RULE_CATEGORIES:
        return (
            jsonify(
                error=(
                    f"No rule set is implemented for category {category!r}; "
                    "the request was not evaluated."
                ),
                status="UNSUPPORTED_CATEGORY",
                category=category,
                disclaimer=_disclaimer(),
            ),
            422,
        )

    try:
        symptom_categories = _load_symptom_categories()
        evidence = _validate_evidence(
            payload["evidence"],
            symptom_categories,
            ALLOWED_CATEGORIES,
            "evidence",
        )
        modifier_evidence = _validate_evidence(
            payload.get("modifier_evidence", {}),
            symptom_categories,
            {SPECIAL_CONDITION_CATEGORY},
            "modifier_evidence",
        )
        vitals = _validate_vitals(payload.get("vitals", {}))
        rules = _load_rules(category)
        modifiers = _load_modifiers()
        questions = _load_questions()
        inference_result = _evaluate_rules(
            rules,
            evidence,
            category,
            questions,
        )
        modifier_result = _evaluate_modifiers(
            modifiers,
            category,
            modifier_evidence,
        )
        inference_result["modifiers"] = modifier_result
    except RequestValidationError as error:
        return _error(error.message, 400, error.field)
    except (ValidationError, InferenceValidationError, RuleDataError) as error:
        db.session.rollback()
        current_app.logger.error("Triage evaluation failed: %s", error)
        return _error("Triage evaluation could not be completed.", 500)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Unexpected triage evaluation failure")
        return _error("Triage evaluation could not be completed.", 500)

    assessment = Assessment(
        patient_id=patient.id,
        category=category,
        evidence_json=json.dumps(evidence, allow_nan=False),
        vitals_json=json.dumps(vitals, allow_nan=False),
        inference_result_json=json.dumps(
            inference_result,
            allow_nan=False,
        ),
    )
    try:
        db.session.add(assessment)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Unable to persist triage assessment")
        return _error("Unable to persist triage assessment.", 500)

    return _assessment_response(
        assessment,
        evidence,
        modifier_evidence,
        vitals,
        inference_result,
        201,
    )


@triage_bp.post(
    "/patients/<int:patient_id>/assessments/<int:assessment_id>/"
    "questions/<question_id>"
)
def answer_assessment_question(patient_id: int, assessment_id: int, question_id: str):
    """Record one metadata-backed answer and reevaluate the assessment."""

    assessment = db.session.get(Assessment, assessment_id)
    if assessment is None or assessment.patient_id != patient_id:
        return _error("Assessment was not found.", 404, "assessment_id")

    try:
        payload = _request_object()
        questions = _load_questions()
        question = next(
            (item for item in questions if item["question_id"] == question_id),
            None,
        )
        if question is None:
            raise RequestValidationError(
                f"Unknown question ID: {question_id}.",
                "question_id",
            )
        if assessment.category not in question["applicable_categories"]:
            raise RequestValidationError(
                "The question does not apply to this assessment category.",
                "question_id",
            )

        evidence = _load_persisted_object(
            assessment.evidence_json,
            "assessment evidence",
        )
        inference_result = _load_persisted_object(
            assessment.inference_result_json,
            "assessment inference result",
        )
        symptom_categories = _load_symptom_categories()
        evidence = _validate_evidence(
            evidence,
            symptom_categories,
            {assessment.category},
            "evidence",
        )
        modifier_data = inference_result.get("modifiers", {})
        if not isinstance(modifier_data, dict):
            raise RuleDataError("Persisted modifier result is not an object.")
        modifier_evidence = _validate_evidence(
            modifier_data.get("submitted_evidence", {}),
            symptom_categories,
            {SPECIAL_CONDITION_CATEGORY},
            "modifier_evidence",
        )
        rules = _load_rules(assessment.category)
        if question["evidence_key"] not in {
            condition
            for rule in rules
            if rule["rule_id"] in question["rule_ids"]
            for condition in rule["conditions"]
        }:
            raise RequestValidationError(
                "The question does not belong to this assessment.",
                "question_id",
            )

        current_result = _evaluate_rules(
            rules,
            evidence,
            assessment.category,
            questions,
        )
        active_question_ids = {
            item["question_id"]
            for item in current_result["follow_up_questions"]
        }
        if question_id not in active_question_ids:
            return _error(
                "This question is no longer relevant to the current evidence.",
                409,
                "question_id",
            )

        state = _question_response_state(payload, question)
        evidence[question["evidence_key"]] = state
        inference_result = _evaluate_rules(
            rules,
            evidence,
            assessment.category,
            questions,
        )
        modifiers = _load_modifiers()
        modifier_result = _evaluate_modifiers(
            modifiers,
            assessment.category,
            modifier_evidence,
        )
        inference_result["modifiers"] = modifier_result
        vitals = _load_persisted_object(
            assessment.vitals_json,
            "assessment vitals",
        )
        vitals = _validate_vitals(vitals)
    except RequestValidationError as error:
        return _error(error.message, 400, error.field)
    except (ValidationError, InferenceValidationError, RuleDataError) as error:
        current_app.logger.error(
            "Assessment question evaluation failed: %s",
            error,
        )
        return _error("Assessment question could not be processed.", 500)
    except Exception:
        current_app.logger.exception(
            "Unexpected assessment question evaluation failure"
        )
        return _error("Assessment question could not be processed.", 500)

    assessment.evidence_json = json.dumps(evidence, allow_nan=False)
    assessment.inference_result_json = json.dumps(
        inference_result,
        allow_nan=False,
    )
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Unable to persist assessment question response"
        )
        return _error("Assessment question could not be saved.", 500)

    return _assessment_response(
        assessment,
        evidence,
        modifier_evidence,
        vitals,
        inference_result,
        200,
    )


@triage_bp.get(
    "/patients/<int:patient_id>/assessments/<int:assessment_id>/report/<report_format>"
)
def download_assessment_report(patient_id: int, assessment_id: int, report_format: str):
    """Download a report only when the assessment belongs to the path patient."""

    format_details = REPORT_FORMATS.get(report_format.lower())
    if format_details is None:
        return _error(
            "report format must be either pdf or docx.",
            400,
            "report_format",
        )

    assessment = db.session.get(Assessment, assessment_id)
    if assessment is None or assessment.patient_id != patient_id:
        return _error("Assessment was not found.", 404, "assessment_id")

    try:
        report_data = build_report_data(assessment)
        content_type, extension, generator = format_details
        report_content = generator(report_data)
    except ReportDataError as error:
        current_app.logger.error(
            "Assessment report data is invalid for %s: %s",
            assessment_id,
            error,
        )
        return _error("Assessment report could not be generated.", 500)
    except (OSError, TypeError, ValueError) as error:
        current_app.logger.exception(
            "Assessment report generation failed for %s: %s",
            assessment_id,
            error,
        )
        return _error("Assessment report could not be generated.", 500)

    return send_file(
        BytesIO(report_content),
        mimetype=content_type,
        as_attachment=True,
        download_name=f"erpilot-assessment-{assessment_id}.{extension}",
    )


class RequestValidationError(ValueError):
    """A client-provided request value failed validation."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field


class RuleDataError(ValueError):
    """The configured rule dataset cannot be evaluated safely."""


def _request_object() -> dict[str, Any]:
    if not request.is_json:
        raise RequestValidationError("Request body must be a JSON object.")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise RequestValidationError(
            "Request body must be a valid JSON object."
        )
    return payload


def _load_symptom_categories() -> dict[str, str]:
    data = load_json_file(SYMPTOMS_PATH)
    validate_symptoms(data, SYMPTOMS_PATH)
    return {
        symptom["key"]: symptom["category"]
        for symptom in data["symptoms"]
    }


def _load_questions() -> list[dict[str, Any]]:
    symptom_data = load_json_file(SYMPTOMS_PATH)
    symptom_keys = validate_symptoms(symptom_data, SYMPTOMS_PATH)
    rule_catalog: dict[str, str] = {}
    for category in SUPPORTED_RULE_CATEGORIES:
        for rule in _load_rules(category):
            rule_catalog[rule["rule_id"]] = category
    question_data = load_json_file(QUESTIONS_PATH)
    try:
        return validate_questions(
            question_data,
            symptom_keys,
            rule_catalog,
            source=QUESTIONS_PATH,
        )
    except ValidationError as error:
        raise RuleDataError(str(error)) from error


def _load_rules(category: str = "brain_trauma") -> list[dict[str, Any]]:
    rules_path = RULES_PATHS.get(category)
    if rules_path is None:
        raise RuleDataError(f"No rule file is configured for {category!r}.")
    rule_data = load_json_file(rules_path)
    symptom_data = load_json_file(SYMPTOMS_PATH)
    department_data = load_json_file(DEPARTMENTS_PATH)
    symptom_keys = validate_symptoms(symptom_data, SYMPTOMS_PATH)
    department_catalog = validate_departments(
        department_data,
        DEPARTMENTS_PATH,
    )
    try:
        return validate_core_rules(
            rule_data,
            symptom_keys,
            department_catalog,
            rules_path,
            expected_category=category,
        )
    except ValidationError as error:
        raise RuleDataError(str(error)) from error


def _load_modifiers() -> list[dict[str, Any]]:
    try:
        return validate_modifier_files(SYMPTOMS_PATH, MODIFIER_PATHS)
    except ValidationError as error:
        raise RuleDataError(str(error)) from error


def _validate_evidence(
    value: Any,
    symptom_categories: dict[str, str],
    allowed_categories: set[str],
    field_name: str,
) -> dict[str, str]:
    if not isinstance(value, dict):
        raise RequestValidationError(
            f"{field_name} must be a JSON object.",
            field_name,
        )
    for key, state in value.items():
        if (
            key not in symptom_categories
            or symptom_categories[key] not in allowed_categories
        ):
            raise RequestValidationError(
                f"Unknown {field_name.replace('_', ' ')} key: {key}.",
                field_name,
            )
        if not isinstance(state, str) or state not in EVIDENCE_STATES:
            raise RequestValidationError(
                f"Invalid evidence state for {key}: {state!r}.",
                field_name,
            )
    return dict(value)


def _validate_vitals(value: Any) -> dict[str, int | float]:
    if value is None:
        raise RequestValidationError("vitals must be a JSON object.", "vitals")
    if not isinstance(value, dict):
        raise RequestValidationError(
            "vitals must be a JSON object.",
            "vitals",
        )
    for name, reading in value.items():
        if not isinstance(name, str) or not name.strip():
            raise RequestValidationError(
                "Vital-sign names must be non-empty strings.",
                "vitals",
            )
        if (
            isinstance(reading, bool)
            or not isinstance(reading, (int, float))
            or not math.isfinite(float(reading))
        ):
            raise RequestValidationError(
                f"Vital sign {name!r} must be a finite numeric value.",
                "vitals",
            )
    return dict(value)


def _evaluate_rules(
    rules: list[dict[str, Any]],
    evidence: dict[str, str],
    category: str,
    questions: list[dict[str, Any]],
) -> dict[str, Any]:
    forward_result = run_forward_chaining(rules, evidence)
    workflow = run_question_workflow(
        rules,
        evidence,
        questions,
        category,
        forward_result=forward_result,
    )
    result = workflow["forward_result"]
    rules_by_id = {}
    for rule in rules:
        if not isinstance(rule, dict) or "rule_id" not in rule:
            raise RuleDataError("Every rule must contain a rule_id.")
        rules_by_id[rule["rule_id"]] = rule

    explanations = []
    for evaluation in result["evaluations"]:
        rule = rules_by_id.get(evaluation["rule_id"])
        if rule is None:
            raise RuleDataError(
                f"Evaluation returned unknown rule ID "
                f"{evaluation['rule_id']!r}."
            )
        explanations.append(
            {
                "rule_id": evaluation["rule_id"],
                "match_status": evaluation["match_status"],
                "text": explain_match(evaluation, rule),
            }
        )

    if result["full_matches"]:
        outcome = FULL_MATCH
    elif result["partial_matches"]:
        outcome = PARTIAL_MATCH
    else:
        outcome = NO_MATCH
    return {
        **result,
        "outcome": outcome,
        "explanations": explanations,
        "backward_chaining": workflow["backward_chaining"],
        "follow_up_questions": workflow["follow_up_questions"],
    }


def _question_response_state(
    payload: dict[str, Any],
    question: dict[str, Any],
) -> str:
    unexpected_fields = set(payload) - {"response", "state"}
    if unexpected_fields:
        raise RequestValidationError(
            "Only response or state may be submitted.",
            next(iter(unexpected_fields)),
        )
    if "response" in payload and "state" in payload:
        raise RequestValidationError(
            "Submit either response or state, not both.",
            "response",
        )
    if "response" in payload:
        response = payload["response"]
        mapping = question["response_mapping"]
        if not isinstance(response, str) or response not in mapping:
            raise RequestValidationError(
                "response must be one of YES, NO, or UNKNOWN.",
                "response",
            )
        return mapping[response]
    state = payload.get("state")
    if state not in EVIDENCE_STATES:
        raise RequestValidationError(
            "state must be PRESENT, ABSENT, or UNKNOWN.",
            "state",
        )
    return state


def _load_persisted_object(value: str, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError) as error:
        raise RuleDataError(f"{label} is malformed.") from error
    if not isinstance(parsed, dict):
        raise RuleDataError(f"{label} must be a JSON object.")
    return parsed


def _assessment_response(
    assessment: Assessment,
    evidence: dict[str, str],
    modifier_evidence: dict[str, str],
    vitals: dict[str, int | float],
    inference_result: dict[str, Any],
    status: int,
):
    return (
        jsonify(
            assessment_id=assessment.id,
            patient_id=assessment.patient_id,
            category=assessment.category,
            evidence=evidence,
            modifier_evidence=modifier_evidence,
            vitals=vitals,
            inference_result=inference_result,
            modifier_result=inference_result["modifiers"],
            outcome=inference_result["outcome"],
            disclaimer=_disclaimer(),
        ),
        status,
    )


def _evaluate_modifiers(
    modifiers: list[dict[str, Any]],
    category: str,
    evidence: dict[str, str],
) -> dict[str, Any]:
    return run_modifier_evaluation(modifiers, category, evidence)


def _error(message: str, status: int, field: str | None = None):
    body = {
        "error": message,
        "status": status,
        "disclaimer": _disclaimer(),
    }
    if field is not None:
        body["field"] = field
    return jsonify(body), status


def _disclaimer() -> str:
    return current_app.config["EDUCATIONAL_DISCLAIMER"]
