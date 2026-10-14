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
        (
            "orthopedic_trauma",
            "orthopedic_trauma_reduction_or_cast_splint_traction",
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


def test_expanded_category_rules_match_only_their_canonical_evidence(
    client,
):
    patient_id = register_patient(client)
    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "brain_trauma",
            "evidence": {
                "paediatric_head_injury_post_traumatic_seizure": "PRESENT",
                "adult_head_injury_post_traumatic_seizure": "PRESENT",
            },
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert {item["rule_id"] for item in body["inference_result"]["full_matches"]} == {
        "BT-05",
        "BT-P02",
    }
    adult_only = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "brain_trauma",
            "evidence": {
                "adult_head_injury_post_traumatic_seizure": "PRESENT",
            },
        },
    )
    assert adult_only.status_code == 201
    assert {
        item["rule_id"]
        for item in adult_only.get_json()["inference_result"]["full_matches"]
    } == {"BT-05"}


@pytest.mark.parametrize(
    ("category", "evidence", "rule_id"),
    [
        (
            "chest_trauma",
            {
                "chest_trauma_efast_specialist_team_immediately_available": "PRESENT",
                "chest_trauma_efast_onward_transfer_not_delayed": "PRESENT",
            },
            "CT-02",
        ),
        (
            "abdominal_trauma",
            {
                "abdominal_trauma_suspected_haemorrhage_with_unstable_nonresponsive_context": "PRESENT",
            },
            "AT-02",
        ),
        (
            "orthopedic_trauma",
            {
                "orthopedic_trauma_suspected_ankle_fracture_person_over_5": "PRESENT",
            },
            "OT-03",
        ),
    ],
)
def test_expanded_stage_6_rules_match(client, category, evidence, rule_id):
    patient_id = register_patient(client)
    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": category,
            "evidence": evidence,
        },
    )

    assert response.status_code == 201
    assert rule_id in {
        item["rule_id"]
        for item in response.get_json()["inference_result"]["full_matches"]
    }


def test_expanded_multicondition_rule_preserves_unknown_evidence(client):
    patient_id = register_patient(client)
    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "chest_trauma",
            "evidence": {
                "chest_trauma_efast_specialist_team_immediately_available": "PRESENT",
            },
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    ct02 = next(
        item
        for item in body["inference_result"]["evaluations"]
        if item["rule_id"] == "CT-02"
    )
    assert ct02["match_status"] == "PARTIAL_MATCH"
    assert ct02["unknown_conditions"] == [
        "chest_trauma_efast_onward_transfer_not_delayed"
    ]
    assert ct02["absent_conditions"] == []
    assert "CT-02" not in {
        item["rule_id"]
        for item in body["inference_result"]["full_matches"]
    }


def _create_partial_chest_assessment(client):
    patient_id = register_patient(client)
    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "chest_trauma",
            "evidence": {
                "chest_trauma_efast_specialist_team_immediately_available":
                    "PRESENT",
            },
        },
    )
    assert response.status_code == 201
    return patient_id, response.get_json()


def test_follow_up_questions_are_selected_from_partial_rules(client):
    _patient_id, body = _create_partial_chest_assessment(client)

    questions = body["inference_result"]["follow_up_questions"]
    assert [question["question_id"] for question in questions] == [
        "Q-CT-EFAST-TRANSFER"
    ]
    assert questions[0]["required_by_rule_ids"] == ["CT-02"]
    ct02 = next(
        item
        for item in body["inference_result"]["evaluations"]
        if item["rule_id"] == "CT-02"
    )
    assert ct02["follow_up_question_ids"] == ["Q-CT-EFAST-TRANSFER"]
    explanation = next(
        item
        for item in body["inference_result"]["explanations"]
        if item["rule_id"] == "CT-02"
    )
    assert "Q-CT-EFAST-TRANSFER" in explanation["text"]


@pytest.mark.parametrize(
    ("response_token", "expected_status", "expected_question_count"),
    [
        ("YES", "FULL_MATCH", 0),
        ("NO", "NO_MATCH", 0),
        ("UNKNOWN", "PARTIAL_MATCH", 1),
    ],
)
def test_follow_up_answer_reevaluates_and_persists(
    client,
    app,
    response_token,
    expected_status,
    expected_question_count,
):
    patient_id, initial = _create_partial_chest_assessment(client)
    answer = client.post(
        f"/api/patients/{patient_id}/assessments/"
        f"{initial['assessment_id']}/questions/Q-CT-EFAST-TRANSFER",
        json={"response": response_token},
    )

    assert answer.status_code == 200
    body = answer.get_json()
    ct02 = next(
        item
        for item in body["inference_result"]["evaluations"]
        if item["rule_id"] == "CT-02"
    )
    assert ct02["match_status"] == expected_status
    assert len(body["inference_result"]["follow_up_questions"]) == (
        expected_question_count
    )
    assert body["evidence"][
        "chest_trauma_efast_onward_transfer_not_delayed"
    ] == {
        "YES": "PRESENT",
        "NO": "ABSENT",
        "UNKNOWN": "UNKNOWN",
    }[response_token]

    with app.app_context():
        assessment = db.session.get(Assessment, initial["assessment_id"])
        assert json.loads(assessment.evidence_json) == body["evidence"]
        persisted = json.loads(assessment.inference_result_json)
        assert persisted["evaluations"]
        assert persisted["outcome"] == body["outcome"]


def test_follow_up_answer_rejects_invalid_or_stale_questions(client):
    patient_id, initial = _create_partial_chest_assessment(client)
    base_url = (
        f"/api/patients/{patient_id}/assessments/{initial['assessment_id']}"
    )

    unknown = client.post(
        f"{base_url}/questions/Q-NOT-REAL",
        json={"response": "YES"},
    )
    invalid_response = client.post(
        f"{base_url}/questions/Q-CT-EFAST-TRANSFER",
        json={"response": "MAYBE"},
    )
    unrelated_evidence = client.post(
        f"{base_url}/questions/Q-CT-EFAST-TRANSFER",
        json={
            "response": "YES",
            "evidence_key": "adult_head_injury_post_traumatic_seizure",
        },
    )
    assert unknown.status_code == 400
    assert invalid_response.status_code == 400
    assert unrelated_evidence.status_code == 400

    answered = client.post(
        f"{base_url}/questions/Q-CT-EFAST-TRANSFER",
        json={"state": "PRESENT"},
    )
    stale = client.post(
        f"{base_url}/questions/Q-CT-EFAST-TRANSFER",
        json={"response": "YES"},
    )
    assert answered.status_code == 200
    assert stale.status_code == 409


def test_follow_up_response_is_idempotent_and_does_not_duplicate_evidence(client, app):
    patient_id, initial = _create_partial_chest_assessment(client)
    endpoint = (
        f"/api/patients/{patient_id}/assessments/"
        f"{initial['assessment_id']}/questions/Q-CT-EFAST-TRANSFER"
    )
    first = client.post(endpoint, json={"response": "YES"})
    repeated = client.post(endpoint, json={"response": "YES"})

    assert first.status_code == 200
    assert repeated.status_code == 409
    with app.app_context():
        assessment = db.session.get(Assessment, initial["assessment_id"])
        evidence = json.loads(assessment.evidence_json)
        assert evidence == {
            "chest_trauma_efast_specialist_team_immediately_available": "PRESENT",
            "chest_trauma_efast_onward_transfer_not_delayed": "PRESENT",
        }


def test_follow_up_request_for_missing_assessment_returns_not_found(client):
    patient_id = register_patient(client)
    response = client.post(
        f"/api/patients/{patient_id}/assessments/99999/questions/Q-CT-EFAST-TRANSFER",
        json={"response": "YES"},
    )

    assert response.status_code == 404
    assert response.get_json()["field"] == "assessment_id"


def test_unrelated_canonical_evidence_does_not_activate_a_rule(client):
    patient_id = register_patient(client)
    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "brain_trauma",
            "evidence": {"chest_trauma_negative_chest_efast": "PRESENT"},
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["outcome"] == "NO_MATCH"
    assert all(
        "chest_trauma_negative_chest_efast" in item["unmatched_evidence_keys"]
        for item in body["inference_result"]["evaluations"]
    )


def test_no_match_api_response_contains_no_fabricated_conclusion(client, app):
    patient_id = register_patient(client)
    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "brain_trauma",
            "evidence": {
                "adult_head_injury_post_traumatic_seizure": "ABSENT",
            },
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["outcome"] == "NO_MATCH"
    assert body["inference_result"]["full_matches"] == []
    assert body["inference_result"]["partial_matches"] == []
    assert body["inference_result"]["follow_up_questions"] == []
    assert all(
        item["match_status"] == "NO_MATCH"
        and item["conclusion"]
        and item["rule_id"]
        for item in body["inference_result"]["no_matches"]
    )
    with app.app_context():
        persisted = db.session.get(Assessment, body["assessment_id"])
        assert json.loads(persisted.inference_result_json)["outcome"] == body["outcome"]


def test_follow_up_answer_enforces_assessment_patient_ownership(client):
    owner_id, initial = _create_partial_chest_assessment(client)
    other_patient_id = register_patient(client)

    response = client.post(
        f"/api/patients/{other_patient_id}/assessments/"
        f"{initial['assessment_id']}/questions/Q-CT-EFAST-TRANSFER",
        json={"response": "YES"},
    )

    assert response.status_code == 404
    assert response.get_json()["field"] == "assessment_id"
    assert owner_id != other_patient_id


def test_follow_up_answer_preserves_modifier_results(client):
    patient_id = register_patient(client)
    initial = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "chest_trauma",
            "evidence": {
                "chest_trauma_efast_specialist_team_immediately_available":
                    "PRESENT",
            },
            "modifier_evidence": {
                "pregnancy_status_documented_pregnant": "PRESENT",
                "anesthesia_allergy_documented": "PRESENT",
            },
        },
    )
    assert initial.status_code == 201
    initial_body = initial.get_json()

    answer = client.post(
        f"/api/patients/{patient_id}/assessments/"
        f"{initial_body['assessment_id']}/questions/Q-CT-EFAST-TRANSFER",
        json={"response": "YES"},
    )

    assert answer.status_code == 200
    assert {
        item["modifier_id"]
        for item in answer.get_json()["modifier_result"]["fired_modifiers"]
    } == {"PREG-01", "ALG-01"}


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
    assert len(evaluations) == 17
    assert {item["rule_id"] for item in evaluations} == {
        *{f"BT-{number:02d}" for number in range(1, 8)},
        *{f"BT-P{number:02d}" for number in range(1, 11)},
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
    assert len(body["inference_result"]["evaluations"]) == 17


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
