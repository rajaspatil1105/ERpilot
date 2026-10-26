"""Patient registration and trauma triage API routes."""

from __future__ import annotations

import json
import math
import secrets
from io import BytesIO
from pathlib import Path
from typing import Any

from flask import Blueprint, current_app, jsonify, request, send_file
from sqlalchemy import or_

from inference_engine.explainer import explain_match
from inference_engine.forward_chaining import (
    run_forward_chaining,
    run_forward_inference,
)
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
from checklist_builder import build_checklist
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
UNKNOWN_TRAUMA_CATEGORY = "unknown_trauma"

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

    patient_code = _new_unique_patient_code()
    patient = Patient(age=age, patient_code=patient_code, **text_values)
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
            patient_code=patient.patient_code,
            name=patient.name,
            age=patient.age,
            gender=patient.gender,
            incident_type=patient.incident_type,
            disclaimer=_disclaimer(),
        ),
        201,
    )


@triage_bp.get("/patients")
def search_patients():
    """Find fictional patient records by a partial name query."""

    query = request.args.get("search", "").strip()
    if len(query) < 2:
        return jsonify(patients=[])
    if len(query) > 100:
        return _error("Search text must be 100 characters or fewer.", 400, "search")
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    patients = (
        Patient.query.filter(or_(
            Patient.name.ilike(f"%{escaped}%", escape="\\"),
            Patient.patient_code == query,
        ))
        .order_by(Patient.name.asc(), Patient.id.asc())
        .limit(30)
        .all()
    )
    return jsonify(
        patients=[
            {
                "id": patient.id,
                "patient_code": patient.patient_code,
                "name": patient.name,
                "age": patient.age,
                "gender": patient.gender,
                "incident_type": patient.incident_type,
                "assessment_count": len(patient.assessments),
            }
            for patient in patients
        ]
    )


@triage_bp.get("/patients/<int:patient_id>/records")
def get_patient_records(patient_id: int):
    patient = db.session.get(Patient, patient_id)
    if patient is None:
        return _error("Patient was not found.", 404, "patient_id")
    assessments = []
    for assessment in sorted(
        patient.assessments,
        key=lambda item: (item.created_at, item.id),
        reverse=True,
    ):
        try:
            inference = _load_persisted_object(
                assessment.inference_result_json, "assessment inference result"
            )
            evidence = _load_persisted_object(
                assessment.evidence_json, "assessment evidence"
            )
            vitals = _load_persisted_object(
                assessment.vitals_json, "assessment vitals"
            )
            checklist = json.loads(assessment.checklist_json)
            if not isinstance(checklist, list):
                raise RuleDataError("Persisted assessment checklist is invalid.")
        except (RuleDataError, json.JSONDecodeError, TypeError):
            inference = {}
            evidence = {}
            vitals = {}
            checklist = []
        assessments.append(
            {
                "assessment_id": assessment.id,
                "created_at": assessment.created_at.isoformat() + "Z",
                "workflow_mode": assessment.workflow_mode,
                "category": assessment.selected_category or "Unknown trauma",
                "outcome": inference.get("outcome", "Unavailable"),
                "evidence": evidence,
                "modifier_evidence": inference.get("modifiers", {}).get(
                    "submitted_evidence", {}
                ),
                "vitals": vitals,
                "checklist": checklist,
            }
        )
    return jsonify(
        patient={
            "id": patient.id,
            "patient_code": patient.patient_code,
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "incident_type": patient.incident_type,
        },
        assessments=assessments,
    )


@triage_bp.put(
    "/patients/<int:patient_id>/assessments/<int:assessment_id>/checklist"
)
def save_assessment_checklist(patient_id: int, assessment_id: int):
    """Persist checked tasks and remarks against the owning assessment."""

    assessment = db.session.get(Assessment, assessment_id)
    if assessment is None or assessment.patient_id != patient_id:
        return _error("Assessment was not found.", 404, "assessment_id")
    try:
        payload = _request_object()
        if set(payload) != {"items"}:
            raise RequestValidationError(
                "Submit only the checklist items.", "items"
            )
        items = _validate_checklist(payload["items"])
    except RequestValidationError as error:
        return _error(error.message, 400, error.field)
    assessment.checklist_json = json.dumps(items, ensure_ascii=False)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Unable to save assessment checklist")
        return _error("Unable to save checklist changes.", 500)
    return jsonify(
        assessment_id=assessment.id,
        patient_id=assessment.patient_id,
        checklist=items,
        saved=True,
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
        inference_result["answered_follow_up_questions"] = []
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
        selected_category=category,
        workflow_mode="known_category",
        evidence_json=json.dumps(evidence, allow_nan=False),
        vitals_json=json.dumps(vitals, allow_nan=False),
        inference_result_json=json.dumps(
            inference_result,
            allow_nan=False,
        ),
        checklist_json=json.dumps(build_checklist(inference_result)),
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


@triage_bp.post("/triage/forward")
def create_forward_assessment():
    """Evaluate recorded facts against every configured core rule."""

    try:
        payload = _request_object()
    except RequestValidationError as error:
        return _error(error.message, 400, error.field)
    patient_id = payload.get("patient_id")
    if (
        isinstance(patient_id, bool)
        or not isinstance(patient_id, int)
        or patient_id <= 0
    ):
        return _error("patient_id must be a positive integer.", 400, "patient_id")
    patient = db.session.get(Patient, patient_id)
    if patient is None:
        return _error("Patient was not found.", 404, "patient_id")
    if "category" in payload and payload["category"] not in (None, ""):
        return _error(
            "Unknown-trauma forward inference does not accept a category.",
            400,
            "category",
        )
    try:
        unexpected = set(payload) - {
            "patient_id", "evidence", "modifier_evidence", "vitals"
        }
        if unexpected:
            raise RequestValidationError(
                "Unsupported forward-inference fields.", next(iter(unexpected))
            )
        symptom_categories = _load_symptom_categories()
        evidence = _validate_evidence(
            payload.get("evidence"), symptom_categories, ALLOWED_CATEGORIES,
            "evidence",
        )
        modifier_evidence = _validate_evidence(
            payload.get("modifier_evidence", {}), symptom_categories,
            {SPECIAL_CONDITION_CATEGORY}, "modifier_evidence",
        )
        vitals = _validate_vitals(payload.get("vitals", {}))
        rules = [rule for category in sorted(SUPPORTED_RULE_CATEGORIES)
                 for rule in _load_rules(category)]
        inference_result = _evaluate_forward_rules(rules, evidence)
        inference_result["modifiers"] = _evaluate_all_modifiers(
            _load_modifiers(), modifier_evidence
        )
    except RequestValidationError as error:
        return _error(error.message, 400, error.field)
    except (ValidationError, InferenceValidationError, RuleDataError) as error:
        current_app.logger.error("Forward inference failed: %s", error)
        return _error("Forward inference could not be completed.", 500)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Unexpected forward inference failure")
        return _error("Forward inference could not be completed.", 500)

    assessment = Assessment(
        patient_id=patient.id,
        category=UNKNOWN_TRAUMA_CATEGORY,
        selected_category=None,
        workflow_mode="unknown_trauma",
        evidence_json=json.dumps(evidence, allow_nan=False),
        vitals_json=json.dumps(vitals, allow_nan=False),
        inference_result_json=json.dumps(inference_result, allow_nan=False),
        checklist_json=json.dumps(build_checklist(inference_result)),
    )
    try:
        db.session.add(assessment)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Unable to persist forward assessment")
        return _error("Unable to persist forward assessment.", 500)
    response, status = _assessment_response(
        assessment, evidence, modifier_evidence, vitals,
        inference_result, 201,
    )
    response_json = response.get_json()
    response_json["category"] = None
    response_json["workflow_mode"] = "unknown_trauma"
    return jsonify(response_json), status


@triage_bp.post(
    "/patients/<int:patient_id>/assessments/<int:assessment_id>/"
    "questions/<question_id>"
)
def answer_assessment_question(patient_id: int, assessment_id: int, question_id: str):
    """Record one metadata-backed answer and reevaluate the assessment."""

    assessment = db.session.get(Assessment, assessment_id)
    if assessment is None or assessment.patient_id != patient_id:
        return _error("Assessment was not found.", 404, "assessment_id")
    if assessment.workflow_mode == "unknown_trauma":
        return _error(
            "Forward assessments are revised by submitting updated evidence.",
            409,
            "question_id",
        )

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
        answered_questions = inference_result.get(
            "answered_follow_up_questions", []
        )
        if not isinstance(answered_questions, list):
            raise RuleDataError(
                "Persisted answered follow-up questions are not a list."
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
        answered_questions.append(
            {
                "question_id": question["question_id"],
                "prompt": question["prompt"],
                "evidence_key": question["evidence_key"],
                "response": payload.get("response", payload.get("state")),
                "recorded_state": state,
            }
        )
        inference_result = _evaluate_rules(
            rules,
            evidence,
            assessment.category,
            questions,
        )
        inference_result["answered_follow_up_questions"] = answered_questions
        modifiers = _load_modifiers()
        modifier_result = _evaluate_modifiers(
            modifiers,
            assessment.category,
            modifier_evidence,
        )
        inference_result["modifiers"] = modifier_result
        existing_checklist = json.loads(assessment.checklist_json or "[]")
        if not isinstance(existing_checklist, list):
            raise RuleDataError("Persisted assessment checklist is not a list.")
        checklist = build_checklist(inference_result, existing_checklist)
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
    assessment.checklist_json = json.dumps(checklist, ensure_ascii=False)
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
    except Exception as error:
        current_app.logger.exception(
            "Unexpected assessment report generation failure for %s: %s",
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


def _validate_checklist(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 100:
        raise RequestValidationError(
            "items must be a list containing at most 100 checklist items.",
            "items",
        )
    allowed_fields = {
        "id", "title", "details", "source", "source_url", "sources",
        "rule_ids", "completed", "remark", "group", "status",
    }
    validated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(value):
        field = f"items[{index}]"
        if not isinstance(item, dict) or set(item) - allowed_fields:
            raise RequestValidationError(f"{field} is invalid.", "items")
        item_id = item.get("id")
        title = item.get("title")
        if not isinstance(item_id, str) or not item_id.strip() or len(item_id) > 120:
            raise RequestValidationError(f"{field}.id is invalid.", "items")
        if item_id in seen_ids:
            raise RequestValidationError(f"Duplicate checklist item ID: {item_id}.", "items")
        seen_ids.add(item_id)
        if not isinstance(title, str) or not title.strip() or len(title) > 300:
            raise RequestValidationError(f"{field}.title is invalid.", "items")
        completed = item.get("completed")
        if not isinstance(completed, bool):
            raise RequestValidationError(f"{field}.completed must be boolean.", "items")
        status = item.get("status", "done" if completed else "not_started")
        if status not in {"not_started", "in_progress", "done", "not_applicable"}:
            raise RequestValidationError(f"{field}.status is invalid.", "items")
        remark = item.get("remark", "")
        if not isinstance(remark, str) or len(remark) > 5000:
            raise RequestValidationError(f"{field}.remark is invalid.", "items")
        normalized: dict[str, Any] = {
            "id": item_id,
            "title": title.strip(),
            "completed": status == "done",
            "status": status,
            "remark": remark.strip(),
        }
        group = item.get("group", "Other actions")
        if not isinstance(group, str) or not group.strip() or len(group) > 100:
            raise RequestValidationError(f"{field}.group is invalid.", "items")
        normalized["group"] = group.strip()
        for text_field, maximum in (("details", 2000), ("source", 500)):
            text_value = item.get(text_field, "")
            if not isinstance(text_value, str) or len(text_value) > maximum:
                raise RequestValidationError(
                    f"{field}.{text_field} is invalid.", "items"
                )
            if text_value:
                normalized[text_field] = text_value
        source_url = item.get("source_url", "")
        if source_url:
            if (
                not isinstance(source_url, str)
                or len(source_url) > 500
                or not source_url.startswith(("https://", "http://"))
            ):
                raise RequestValidationError(
                    f"{field}.source_url is invalid.", "items"
                )
            normalized["source_url"] = source_url
        for list_field, max_items, max_length in (
            ("sources", 20, 1000), ("rule_ids", 30, 100)
        ):
            values = item.get(list_field, [])
            if (
                not isinstance(values, list)
                or len(values) > max_items
                or any(not isinstance(part, str) or len(part) > max_length for part in values)
            ):
                raise RequestValidationError(
                    f"{field}.{list_field} is invalid.", "items"
                )
            if values:
                normalized[list_field] = values
        validated.append(normalized)
    return validated


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


def _evaluate_forward_rules(
    rules: list[dict[str, Any]], evidence: dict[str, str]
) -> dict[str, Any]:
    result = run_forward_inference(rules, evidence)
    rules_by_id = {rule["rule_id"]: rule for rule in rules}
    for evaluation in result["evaluations"]:
        rule = rules_by_id.get(evaluation["rule_id"])
        if rule is None:
            raise RuleDataError("Forward inference returned an unknown rule.")
        evaluation["explanation"] = explain_match(evaluation, rule)
    result["explanations"] = [
        {
            "rule_id": evaluation["rule_id"],
            "match_status": evaluation["match_status"],
            "text": evaluation["explanation"],
        }
        for evaluation in result["evaluations"]
    ]
    result["outcome"] = (
        FULL_MATCH if result["full_matches"]
        else PARTIAL_MATCH if result["partial_matches"]
        else NO_MATCH
    )
    result["follow_up_questions"] = []
    result["backward_chaining"] = []
    return result


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
            patient_code=assessment.patient.patient_code,
            category=assessment.category,
            workflow_mode=assessment.workflow_mode,
            selected_category=assessment.selected_category,
            evidence=evidence,
            modifier_evidence=modifier_evidence,
            vitals=vitals,
            inference_result=inference_result,
            checklist=json.loads(assessment.checklist_json or "[]"),
            modifier_result=inference_result["modifiers"],
            outcome=inference_result["outcome"],
            patient_name=assessment.patient.name,
            patient_age=assessment.patient.age,
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


def _evaluate_all_modifiers(
    modifiers: list[dict[str, Any]], evidence: dict[str, str]
) -> dict[str, Any]:
    evaluations_by_id: dict[str, dict[str, Any]] = {}
    for category in sorted(SUPPORTED_RULE_CATEGORIES):
        result = _evaluate_modifiers(modifiers, category, evidence)
        for evaluation in result["evaluations"]:
            evaluations_by_id.setdefault(evaluation["modifier_id"], evaluation)
    evaluations = list(evaluations_by_id.values())
    fired = [item for item in evaluations if item["match_status"] == FULL_MATCH]
    return {
        "evaluations": evaluations,
        "submitted_evidence": dict(evidence),
        "fired_modifiers": fired,
        "no_matches": [item for item in evaluations if item["match_status"] == NO_MATCH],
        "outcome": FULL_MATCH if fired else NO_MATCH,
    }


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


def _new_unique_patient_code() -> str:
    for _attempt in range(1000):
        code = str(secrets.randbelow(90000) + 10000)
        if not Patient.query.filter_by(patient_code=code).first():
            return code
    raise RuntimeError("Unable to generate a unique five-digit patient code")
