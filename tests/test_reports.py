import json
from io import BytesIO
from zipfile import ZipFile

import pytest
from sqlalchemy import text

from app import create_app
from models.assessment import Assessment
from models.db import db


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


def register_patient(client, name="Report Patient"):
    response = client.post(
        "/api/patients",
        json={
            "name": name,
            "age": 35,
            "gender": "unspecified",
            "incident_type": "fall",
        },
    )
    assert response.status_code == 201
    return response.get_json()["id"]


def create_assessment(client, patient_id):
    response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "brain_trauma",
            "evidence": {
                "adult_head_injury_post_traumatic_seizure": "PRESENT",
            },
            "modifier_evidence": {
                "anticoagulant_treatment_documented": "PRESENT",
            },
            "vitals": {"heart_rate": 88},
        },
    )
    assert response.status_code == 201
    return response.get_json()


def report_url(patient_id, assessment_id, report_format):
    return (
        f"/api/patients/{patient_id}/assessments/{assessment_id}/"
        f"report/{report_format}"
    )


def test_assessment_preserves_complete_report_data(client, app):
    patient_id = register_patient(client)
    body = create_assessment(client, patient_id)

    with app.app_context():
        assessment = db.session.get(Assessment, body["assessment_id"])
        persisted = json.loads(assessment.inference_result_json)
        assert persisted["evaluations"]
        assert persisted["explanations"]
        assert all(
            evaluation["protocol_reference"]
            for evaluation in persisted["evaluations"]
        )
        assert persisted["modifiers"]["submitted_evidence"] == {
            "anticoagulant_treatment_documented": "PRESENT"
        }
        assert persisted["modifiers"]["fired_modifiers"][0]["protocol_reference"]
        assert json.loads(assessment.evidence_json) == {
            "adult_head_injury_post_traumatic_seizure": "PRESENT"
        }
        assert json.loads(assessment.vitals_json) == {"heart_rate": 88}


def test_pdf_report_download_contains_assessment_and_safety_content(client):
    patient_id = register_patient(client)
    body = create_assessment(client, patient_id)

    response = client.get(
        report_url(patient_id, body["assessment_id"], "pdf")
    )

    assert response.status_code == 200
    assert response.content_type == "application/pdf"
    assert "erpilot-assessment-" in response.headers["Content-Disposition"]
    assert b"ERPilot AI Assessment Report" in response.data
    assert b"BT-05" in response.data
    assert b"AC-01" in response.data
    assert b"1.5.13" in response.data
    assert b"Not clinically validated" in response.data


def test_docx_report_download_contains_rule_and_modifier_content(client):
    patient_id = register_patient(client)
    body = create_assessment(client, patient_id)

    response = client.get(
        report_url(patient_id, body["assessment_id"], "docx")
    )

    assert response.status_code == 200
    assert (
        response.content_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "erpilot-assessment-" in response.headers["Content-Disposition"]
    with ZipFile(BytesIO(response.data)) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
    assert "ERPilot AI Assessment Report" in document_xml
    assert "BT-05" in document_xml
    assert "AC-01" in document_xml
    assert "1.5.13" in document_xml
    assert "not clinically validated" in document_xml


def test_report_does_not_expose_another_patient_assessment(client):
    first_patient_id = register_patient(client, "First Patient")
    second_patient_id = register_patient(client, "Second Patient")
    body = create_assessment(client, first_patient_id)

    response = client.get(
        report_url(second_patient_id, body["assessment_id"], "pdf")
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "Assessment was not found."


@pytest.mark.parametrize(
    "path_suffix",
    ["pdf", "docx"],
)
def test_missing_assessment_returns_not_found(client, path_suffix):
    patient_id = register_patient(client)

    response = client.get(report_url(patient_id, 99999, path_suffix))

    assert response.status_code == 404


def test_invalid_report_format_is_rejected(client):
    patient_id = register_patient(client)

    response = client.get(report_url(patient_id, 1, "html"))

    assert response.status_code == 400
    assert response.get_json()["field"] == "report_format"


def test_malformed_persisted_result_returns_consistent_error(client, app):
    patient_id = register_patient(client)
    body = create_assessment(client, patient_id)

    with app.app_context():
        db.session.execute(
            text(
                "UPDATE assessments "
                "SET inference_result_json = :value "
                "WHERE id = :assessment_id"
            ),
            {"value": "not-json", "assessment_id": body["assessment_id"]},
        )
        db.session.commit()

    response = client.get(
        report_url(patient_id, body["assessment_id"], "pdf")
    )

    assert response.status_code == 500
    assert response.get_json()["error"] == (
        "Assessment report could not be generated."
    )
