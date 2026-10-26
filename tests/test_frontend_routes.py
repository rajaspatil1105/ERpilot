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


def test_frontend_pages_render_without_the_removed_disclaimer(client):
    for path in ("/register", "/assessment", "/results", "/records"):
        response = client.get(path)

        assert response.status_code == 200
        page = response.get_data(as_text=True)
        assert "ERPilot AI is an educational prototype" not in page
        assert "not clinically validated" not in page.lower()


def test_frontend_pages_reference_local_favicon(client):
    page = client.get("/register").get_data(as_text=True)

    assert 'rel="icon"' in page
    assert 'href="/static/favicon.svg"' in page
    favicon = client.get("/static/favicon.svg")

    assert favicon.status_code == 200
    assert favicon.content_type.startswith("image/svg+xml")


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
    assert page.count('data-state="PRESENT"') >= len(canonical_keys)
    assert page.count('data-state="ABSENT"') >= len(canonical_keys)
    assert 'data-state="UNKNOWN"' in page
    assert ">Yes<" in page
    assert ">No<" in page
    assert ">Unknown<" in page
    assert 'id="evidence-count"' in page
    assert 'class="symptom-category-panel"' in page
    assert "evidence: Object.fromEntries" in script
    assert "Object.entries(states).filter" in script
    assert "symptomCategories.get(key) === categorySelect.value" in script
    assert "isSubmitting" in script
    assert '"/api/triage/forward"' in script
    assert 'value="unknown_trauma"' in page
    assert 'value="known_category"' in page


def test_assessment_page_exposes_separate_modifier_evidence(client):
    page = client.get("/assessment").get_data(as_text=True)
    script = client.get("/static/js/assessment.js").get_data(as_text=True)

    for key in (
        "pregnancy_status_documented_pregnant",
        "anticoagulant_treatment_documented",
        "opioid_intoxication_documented_or_suspected",
        "anesthesia_allergy_documented",
    ):
        assert key in page
    assert "modifier_evidence" in script
    assert '=== "special_condition"' in script
    assert 'id="modifier-list"' in page
    assert 'data-state="UNKNOWN"' in page


def test_supported_categories_are_enabled_by_assessment_script(client):
    page = client.get("/assessment").get_data(as_text=True)
    script = client.get("/static/js/assessment.js").get_data(as_text=True)

    assert 'value="brain_trauma"' in page
    assert re.search(
        r'value="chest_trauma"[^>]*>\s*Chest Trauma\s+\(supported\)',
        page,
    )
    assert "(supported)" in page
    assert re.search(r'value="abdominal_trauma"[^>]*>\s*Abdominal Trauma\s+\(supported\)', page)
    assert re.search(r'value="orthopedic_trauma"[^>]*>\s*Orthopedic Trauma\s+\(supported\)', page)
    for category in (
        "chest_trauma",
        "abdominal_trauma",
        "orthopedic_trauma",
    ):
        assert f'data-category="{category}"' in page


def test_results_page_preserves_api_result_fields_and_limitation(client):
    page = client.get("/results").get_data(as_text=True)
    script = client.get("/static/js/results.js").get_data(as_text=True)

    assert "Checklist and remarks" in page
    assert 'id="checklist-items"' in page
    assert 'id="save-checklist"' in page
    assert "Save checklist" in page
    assert "patient_name" in script
    assert "item.remark" in script
    assert "item.completed" in script
    assert "checklist" in script
    assert "/checklist" in script
    assert "outcome-summary" not in page
    assert 'id="report-downloads"' not in page
    assert "assessment checklist" in page.lower()


def test_patient_records_page_exposes_name_search_and_record_button(client):
    page = client.get("/records").get_data(as_text=True)
    script = client.get("/static/js/patient_records.js").get_data(as_text=True)
    assert 'id="patient-search"' in page
    assert "View record" in script
    assert "/api/patients?search=" in script
    assert 'href="/records"' in page


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

    assert "No saved assessment checklist is available." in script
    assert "Open it from Patient Records" in script
