import json
from pathlib import Path

import pytest

from app import create_app
from inference_engine.modifier_matcher import run_modifier_evaluation
from inference_engine.rule_matcher import ABSENT, FULL_MATCH, NO_MATCH, UNKNOWN
from inference_engine.rule_validator import validate_modifier_files
from models.assessment import Assessment
from models.db import db
from routes.triage import MODIFIER_PATHS, SYMPTOMS_PATH


ROOT = Path(__file__).resolve().parents[1]
MODIFIER_CASES = (
    ("pregnancy_status_documented_pregnant", "PREG-01"),
    ("anticoagulant_treatment_documented", "AC-01"),
    ("opioid_intoxication_documented_or_suspected", "OPI-01"),
    ("anesthesia_allergy_documented", "ALG-01"),
)


@pytest.fixture()
def app():
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
        }
    )
    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def register_patient(client):
    response = client.post(
        "/api/patients",
        json={
            "name": "Modifier Patient",
            "age": 35,
            "gender": "unspecified",
            "incident_type": "trauma",
        },
    )
    assert response.status_code == 201
    return response.get_json()["id"]


def test_all_modifier_datasets_validate():
    modifiers = validate_modifier_files(SYMPTOMS_PATH, MODIFIER_PATHS)

    assert {modifier["modifier_id"] for modifier in modifiers} == {
        "PREG-01",
        "AC-01",
        "OPI-01",
        "ALG-01",
    }
    assert all(modifier["priority_override"] == "NONE" for modifier in modifiers)
    anticoagulant = next(
        modifier for modifier in modifiers if modifier["modifier_id"] == "AC-01"
    )
    assert "NICE NG232, recommendation 1.5.13:" in (
        anticoagulant["protocol_reference"]
    )


@pytest.mark.parametrize(("trigger", "modifier_id"), MODIFIER_CASES)
def test_each_modifier_fires_independently(trigger, modifier_id):
    modifiers = validate_modifier_files(SYMPTOMS_PATH, MODIFIER_PATHS)
    result = run_modifier_evaluation(
        modifiers,
        "brain_trauma",
        {trigger: "PRESENT"},
    )

    fired = {item["modifier_id"] for item in result["fired_modifiers"]}
    assert modifier_id in fired
    evaluation = next(
        item for item in result["evaluations"]
        if item["modifier_id"] == modifier_id
    )
    assert evaluation["match_status"] == FULL_MATCH
    assert evaluation["matched_conditions"] == [trigger]
    assert evaluation["protocol_reference"]
    assert evaluation["explanation"]


def test_unknown_and_absent_modifier_evidence_do_not_fire():
    modifiers = validate_modifier_files(SYMPTOMS_PATH, MODIFIER_PATHS)
    for state in (UNKNOWN, ABSENT):
        result = run_modifier_evaluation(
            modifiers,
            "brain_trauma",
            {trigger: state for trigger, _modifier_id in MODIFIER_CASES},
        )

        assert result["outcome"] == NO_MATCH
        assert result["fired_modifiers"] == []
        assert all(
            evaluation["match_status"] == NO_MATCH
            for evaluation in result["evaluations"]
        )


def test_modifier_combination_preserves_core_result_and_persistence(client, app):
    patient_id = register_patient(client)
    modifier_evidence = {
        trigger: "PRESENT"
        for trigger, _modifier_id in MODIFIER_CASES
    }
    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "brain_trauma",
            "evidence": {
                "adult_head_injury_post_traumatic_seizure": "PRESENT",
            },
            "modifier_evidence": modifier_evidence,
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["outcome"] == FULL_MATCH
    assert len(body["inference_result"]["evaluations"]) == 7
    assert {
        item["modifier_id"]
        for item in body["modifier_result"]["fired_modifiers"]
    } == {"PREG-01", "AC-01", "OPI-01", "ALG-01"}
    assert all(
        item["matched_conditions"]
        and item["protocol_reference"]
        and item["explanation"]
        for item in body["modifier_result"]["fired_modifiers"]
    )

    with app.app_context():
        assessment = db.session.get(Assessment, body["assessment_id"])
        persisted = json.loads(assessment.inference_result_json)
        assert {
            item["modifier_id"]
            for item in persisted["modifiers"]["fired_modifiers"]
        } == {"PREG-01", "AC-01", "OPI-01", "ALG-01"}
        assert persisted["modifiers"]["submitted_evidence"] == modifier_evidence


def test_modifier_scope_does_not_apply_brain_only_modifiers_to_chest(client):
    patient_id = register_patient(client)
    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "chest_trauma",
            "evidence": {},
            "modifier_evidence": {
                "pregnancy_status_documented_pregnant": "PRESENT",
                "anticoagulant_treatment_documented": "PRESENT",
                "opioid_intoxication_documented_or_suspected": "PRESENT",
                "anesthesia_allergy_documented": "PRESENT",
            },
        },
    )

    assert response.status_code == 201
    assert {
        item["modifier_id"]
        for item in response.get_json()["modifier_result"]["fired_modifiers"]
    } == {"PREG-01", "ALG-01"}


@pytest.mark.parametrize(
    "modifier_evidence",
    [
        [],
        {"unknown_modifier_key": "PRESENT"},
        {"pregnancy_status_documented_pregnant": "MAYBE"},
    ],
)
def test_invalid_modifier_evidence_is_rejected(client, modifier_evidence):
    patient_id = register_patient(client)
    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "brain_trauma",
            "evidence": {},
            "modifier_evidence": modifier_evidence,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["field"] == "modifier_evidence"


def test_no_modifier_match_is_explicit(client):
    patient_id = register_patient(client)
    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "brain_trauma",
            "evidence": {},
            "modifier_evidence": {},
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["modifier_result"]["outcome"] == NO_MATCH
    assert body["modifier_result"]["fired_modifiers"] == []
    assert body["modifier_result"]["no_matches"]
