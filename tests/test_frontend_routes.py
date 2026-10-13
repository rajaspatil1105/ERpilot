import re

import pytest

from app import create_app
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


def test_frontend_pages_render_with_disclaimer(client, app):
    for path in ("/register", "/assessment", "/results"):
        response = client.get(path)

        assert response.status_code == 200
        page = response.get_data(as_text=True)
        assert "ERPilot AI is an educational prototype" in page
        assert app.config["EDUCATIONAL_DISCLAIMER"] in page


def test_home_page_redirects_to_registration(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/register")


def test_registration_page_uses_patient_api_fields_and_endpoint(client):
    page = client.get("/register").get_data(as_text=True)

    assert 'id="patient-name"' in page
    assert 'id="patient-age"' in page
    assert 'id="patient-gender"' in page
    assert 'id="incident-type"' in page
    assert 'fetch("/api/patients"' in client.get(
        "/static/js/registration.js"
    ).get_data(as_text=True)


def test_assessment_page_uses_canonical_keys_and_preserves_unknown_state(client):
    page = client.get("/assessment").get_data(as_text=True)
    script = client.get("/static/js/assessment.js").get_data(as_text=True)

    canonical_keys = (
        "adult_head_injury_gcs_12_or_less_initial_ed",
        "adult_head_injury_gcs_below_15_at_2_hours",
        "adult_head_injury_suspected_open_or_depressed_skull_fracture",
        "adult_head_injury_sign_of_basal_skull_fracture",
        "adult_head_injury_post_traumatic_seizure",
        "adult_head_injury_focal_neurological_deficit",
        "adult_head_injury_more_than_one_vomiting_episode",
    )
    for key in canonical_keys:
        assert key in page
    assert 'data-state="UNKNOWN"' in page
    assert "evidence: Object.fromEntries" in script
    assert "Object.entries(states).filter" in script
    assert "symptomCategories.get(key) === categorySelect.value" in script
    assert 'fetch("/api/triage"' in script


def test_stage_6_categories_are_enabled_by_assessment_script(client):
    page = client.get("/assessment").get_data(as_text=True)
    script = client.get("/static/js/assessment.js").get_data(as_text=True)

    assert 'value="brain_trauma"' in page
    assert re.search(r'value="chest_trauma"\s+disabled', page)
    assert re.search(r'value="abdominal_trauma"\s+disabled', page)
    assert re.search(r'value="orthopedic_trauma"\s+disabled', page)
    assert "(unavailable)" in page
    for category in (
        "chest_trauma",
        "abdominal_trauma",
        "orthopedic_trauma",
    ):
        assert f'"{category}"' in script


def test_results_page_preserves_api_result_fields_and_limitation(client):
    page = client.get("/results").get_data(as_text=True)
    script = client.get("/static/js/results.js").get_data(as_text=True)

    assert "Applicable rule evaluations" in page
    assert "Backward-chaining limitation" in page
    for field in (
        "assessment_id",
        "patient_id",
        "match_status",
        "priority_flag",
        "suggested_department",
        "checklist_action",
        "protocol_reference",
    ):
        assert field in script
    assert "No rule matched the recorded evidence" in script


def test_existing_patient_and_triage_api_endpoints_remain_available(client):
    patient_response = client.post(
        "/api/patients",
        json={
            "name": "Frontend Test Patient",
            "age": 30,
            "gender": "unspecified",
            "incident_type": "trauma",
        },
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.get_json()["id"]

    triage_response = client.post(
        "/api/triage",
        json={
            "patient_id": patient_id,
            "category": "brain_trauma",
            "evidence": {
                "adult_head_injury_post_traumatic_seizure": "PRESENT",
            },
        },
    )

    assert triage_response.status_code == 201
    assert triage_response.get_json()["patient_id"] == patient_id


def test_results_page_has_graceful_missing_result_message(client):
    page = client.get("/results").get_data(as_text=True)
    script = client.get("/static/js/results.js").get_data(as_text=True)

    assert "Submit an assessment to view its results." in page
    assert "No valid assessment result is available." in script
