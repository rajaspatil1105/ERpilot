import json

import pytest

from app import create_app
from models.assessment import Assessment
from models.db import db
from models.patient import Patient
from routes import triage as triage_module


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
            "name": "Test Patient",
            "age": 35,
            "gender": "unspecified",
            "incident_type": "trauma",
        },
    )
    assert response.status_code == 201
    return response.get_json()["id"]


def valid_evidence():
    return {
        "adult_head_injury_post_traumatic_seizure": "PRESENT",
    }


def test_create_app_and_database_relationships_initialize(app):
    with app.app_context():
        assert db.engine is not None
        patient = Patient(
            name="Relationship Patient",
            age=20,
            gender="unspecified",
            incident_type="trauma",
        )
        db.session.add(patient)
        db.session.commit()
        assessment = Assessment(
            patient_id=patient.id,
            category="brain_trauma",
            evidence_json="{}",
            vitals_json="{}",
            inference_result_json="{}",
        )
        db.session.add(assessment)
        db.session.commit()
        assert patient.assessments == [assessment]
        assert assessment.patient.id == patient.id


def test_valid_patient_registration_returns_201_and_persists(client, app):
    response = client.post(
        "/api/patients",
        json={
            "name": "A Patient",
            "age": 42,
            "gender": "female",
            "incident_type": "fall",
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["id"]
    assert body["name"] == "A Patient"
    with app.app_context():
        patient = db.session.get(Patient, body["id"])
        assert patient.name == "A Patient"
        assert patient.age == 42


@pytest.mark.parametrize(
    "payload",
    [
        {"age": 42, "gender": "female", "incident_type": "fall"},
        {"name": "A", "gender": "female", "incident_type": "fall"},
        {"name": "A", "age": 42, "incident_type": "fall"},
        {"name": "A", "age": 42, "gender": "female"},
        {
            "name": "",
            "age": 42,
            "gender": "female",
            "incident_type": "fall",
        },
    ],
)
def test_patient_required_fields_and_empty_strings_are_rejected(client, payload):
    response = client.post("/api/patients", json=payload)

    assert response.status_code == 400
    assert response.get_json()["field"]


@pytest.mark.parametrize("age", [-1, True, False, 42.5, "42", None])
def test_invalid_patient_age_is_rejected(client, age):
    response = client.post(
        "/api/patients",
        json={
            "name": "A Patient",
            "age": age,
            "gender": "female",
            "incident_type": "fall",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["field"] == "age"


def test_malformed_patient_json_is_rejected(client):
    response = client.post(
        "/api/patients",
        data='{"name":',
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["error"]


@pytest.mark.parametrize(
    ("endpoint", "data", "content_type"),
    [
        ("/api/patients", '{"name":', "application/json"),
        ("/api/patients", "not json", "text/plain"),
        ("/api/triage", '{"patient_id":', "application/json"),
        ("/api/triage", "not json", "text/plain"),
    ],
)
def test_malformed_and_non_json_requests_return_consistent_errors(
    client,
    app,
    endpoint,
    data,
    content_type,
):
    response = client.post(
        endpoint,
        data=data,
        content_type=content_type,
    )

    assert response.status_code == 400
    assert response.is_json
    body = response.get_json()
    assert body["error"]
    assert body["disclaimer"] == app.config["EDUCATIONAL_DISCLAIMER"]


def test_unknown_patient_returns_404(client):
    response = client.post(
        "/api/triage",
        json={
            "patient_id": 99999,
            "category": "brain_trauma",
            "evidence": {},
        },
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"patient_id": 1, "category": "brain_trauma"},
        {"patient_id": 1, "category": "brain_trauma", "evidence": []},
    ],
)
def test_triage_missing_or_malformed_fields_are_rejected(client, payload):
    response = client.post("/api/triage", json=payload)

    assert response.status_code in {400, 404}
    assert response.get_json()["error"]


def test_invalid_categories_are_rejected_and_stage_6_categories_work(client):
    patient_id = register_patient(client)

    invalid = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "unsupported_category",
            "evidence": {},
        },
    )
    unsupported = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "chest_trauma",
            "evidence": {},
        },
    )

    assert invalid.status_code == 400
    assert unsupported.status_code == 201
    assert unsupported.get_json()["category"] == "chest_trauma"
    assert unsupported.get_json()["outcome"] == "NO_MATCH"


@pytest.mark.parametrize(
    ("category", "condition", "protocol"),
    [
        (
            "chest_trauma",
            "chest_trauma_negative_chest_efast",
            "NICE NG39",
        ),
        (
            "abdominal_trauma",
            "abdominal_trauma_negative_fast",
            "NICE NG39",
        ),
        (
            "orthopedic_trauma",
            "orthopedic_trauma_suspected_knee_fracture_person_over_2",
            "NICE NG38",
        ),
    ],
)
def test_stage_6_categories_load_their_own_rules(
    client,
    app,
    category,
    condition,
    protocol,
):
    patient_id = register_patient(client)
    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": category,
            "evidence": {condition: "PRESENT"},
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["category"] == category
    assert body["outcome"] == "FULL_MATCH"
    assert len(body["inference_result"]["evaluations"]) >= 1
    assert all(
        protocol in evaluation["protocol_reference"]
        for evaluation in body["inference_result"]["evaluations"]
    )
    with app.app_context():
        assessment = db.session.get(Assessment, body["assessment_id"])
        assert assessment.category == category


@pytest.mark.parametrize(
    "evidence",
    [
        {"unknown_key": "PRESENT"},
        {"adult_head_injury_post_traumatic_seizure": "MAYBE"},
    ],
)
def test_unknown_symptoms_and_invalid_evidence_are_rejected(client, evidence):
    patient_id = register_patient(client)
    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "brain_trauma",
            "evidence": evidence,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["field"] == "evidence"


def test_missing_evidence_remains_unknown_and_is_persisted(client, app):
    patient_id = register_patient(client)
    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "brain_trauma",
            "evidence": {},
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["outcome"] == "NO_MATCH"
    evaluation = body["inference_result"]["evaluations"][0]
    assert evaluation["match_status"] == "NO_MATCH"
    assert evaluation["unknown_conditions"] == [
        "adult_head_injury_gcs_12_or_less_initial_ed"
    ]
    assert evaluation["absent_conditions"] == []
    with app.app_context():
        assessment = db.session.get(Assessment, body["assessment_id"])
        assert json.loads(assessment.evidence_json) == {}


@pytest.mark.parametrize(
    "vitals",
    [
        {"heart_rate": True},
        {"heart_rate": float("nan")},
        {"heart_rate": float("inf")},
        {"heart_rate": "120"},
        {"": 120},
    ],
)
def test_invalid_vitals_are_rejected(client, vitals):
    patient_id = register_patient(client)
    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "brain_trauma",
            "evidence": {},
            "vitals": vitals,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["field"] == "vitals"


def test_valid_brain_triage_persists_full_engine_result(client, app):
    patient_id = register_patient(client)
    evidence = {
        "adult_head_injury_post_traumatic_seizure": "PRESENT",
        "adult_head_injury_focal_neurological_deficit": "PRESENT",
    }
    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "brain_trauma",
            "evidence": evidence,
            "vitals": {"heart_rate": 88},
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["assessment_id"]
    assert body["patient_id"] == patient_id
    assert body["category"] == "brain_trauma"
    assert body["outcome"] == "FULL_MATCH"
    assert body["disclaimer"]
    evaluations = body["inference_result"]["evaluations"]
    assert len(evaluations) == 7
    assert {item["rule_id"] for item in evaluations} == {
        f"BT-{number:02d}" for number in range(1, 8)
    }
    assert all(
        "NICE NG232" in item["protocol_reference"]
        for item in evaluations
    )
    with app.app_context():
        assessment = db.session.get(Assessment, body["assessment_id"])
        assert json.loads(assessment.inference_result_json)["evaluations"]
        assert json.loads(assessment.vitals_json) == {"heart_rate": 88}


def test_multiple_full_matches_remain_visible(client):
    patient_id = register_patient(client)
    evidence = {
        key: "PRESENT"
        for key in (
            "adult_head_injury_gcs_12_or_less_initial_ed",
            "adult_head_injury_gcs_below_15_at_2_hours",
            "adult_head_injury_suspected_open_or_depressed_skull_fracture",
            "adult_head_injury_sign_of_basal_skull_fracture",
            "adult_head_injury_post_traumatic_seizure",
            "adult_head_injury_focal_neurological_deficit",
            "adult_head_injury_more_than_one_vomiting_episode",
        )
    }

    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "brain_trauma",
            "evidence": evidence,
        },
    )

    body = response.get_json()
    assert response.status_code == 201
    assert len(body["inference_result"]["full_matches"]) == 7
    assert len(body["inference_result"]["evaluations"]) == 7


def test_rule_loading_failure_does_not_persist_assessment(client, app, monkeypatch):
    patient_id = register_patient(client)
    monkeypatch.setattr(
        triage_module,
        "_load_rules",
        lambda: (_ for _ in ()).throw(
            triage_module.RuleDataError("broken rules")
        ),
    )

    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "brain_trauma",
            "evidence": valid_evidence(),
        },
    )

    assert response.status_code == 500
    with app.app_context():
        assert db.session.query(Assessment).count() == 0


def test_inference_failure_does_not_persist_assessment(client, app, monkeypatch):
    patient_id = register_patient(client)
    monkeypatch.setattr(
        triage_module,
        "run_forward_chaining",
        lambda rules, evidence: (_ for _ in ()).throw(
            triage_module.InferenceValidationError("broken inference")
        ),
    )

    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "brain_trauma",
            "evidence": valid_evidence(),
        },
    )

    assert response.status_code == 500
    with app.app_context():
        assert db.session.query(Assessment).count() == 0
