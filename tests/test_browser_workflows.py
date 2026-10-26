"""Real Chromium workflows against an isolated Flask application."""

from __future__ import annotations

import threading
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile

import pytest
from werkzeug.serving import make_server

from app import create_app
from models.db import db
from models.assessment import Assessment
from models.patient import Patient


@pytest.fixture()
def browser_app(tmp_path: Path):
    database_path = (tmp_path / "browser-test.sqlite").as_posix()
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
        }
    )
    with application.app_context():
        db.create_all()

    server = make_server("127.0.0.1", 0, application, threaded=True)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        yield application, base_url
    finally:
        server.shutdown()
        server_thread.join(timeout=5)
        with application.app_context():
            db.session.remove()
            db.drop_all()


@pytest.fixture()
def page(browser_app):
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    application, base_url = browser_app
    playwright = sync_playwright().start()
    browser = None
    context = None
    try:
        try:
            browser = playwright.chromium.launch(headless=True)
        except PlaywrightError as error:
            pytest.skip(
                "Playwright Chromium is unavailable; run "
                "`python -m playwright install chromium`: "
                f"{error}"
            )
        context = browser.new_context()
        # The app uses Bootstrap only for presentation. Fulfill the CDN assets
        # locally so tests remain deterministic and check app requests cleanly.
        context.route(
            "https://cdn.jsdelivr.net/**",
            lambda route: route.fulfill(
                status=200,
                content_type=(
                    "text/css"
                    if route.request.url.endswith(".css")
                    else "text/javascript"
                ),
                body="",
            ),
        )
        current_page = context.new_page()
        current_page.set_default_timeout(8000)
        current_page.set_default_navigation_timeout(10000)
        current_page._browser_errors = []
        current_page._browser_console_errors = []
        current_page._unexpected_failed_requests = []
        current_page._expected_failed_requests = []
        current_page._expected_failed_urls = set()
        current_page._expected_browser_console_errors = []
        current_page._http_errors = []
        current_page._expected_http_errors = []
        current_page._expected_download_urls = set()
        current_page.on(
            "pageerror",
            lambda error: current_page._browser_errors.append(str(error)),
        )
        def record_failed_request(request):
            if not request.url.startswith(base_url):
                return
            if request.url in current_page._expected_download_urls:
                return
            if request.url in current_page._expected_failed_urls:
                current_page._expected_failed_requests.append(request.url)
                return
            current_page._unexpected_failed_requests.append(request.url)

        def record_response(response):
            if response.url.startswith(base_url) and response.status >= 400:
                current_page._http_errors.append(
                    (urlparse(response.url).path, response.status)
                )

        def record_console_error(message):
            if message.type != "error":
                return
            if (
                "net::ERR_FAILED" in message.text
                and current_page._expected_failed_urls
            ):
                current_page._expected_browser_console_errors.append(message.text)
                return
            # Chromium reports expected API 4xx responses as resource errors;
            # those are tracked separately with their exact paths and statuses.
            if "Failed to load resource: the server responded with a status" in message.text:
                return
            current_page._browser_console_errors.append(message.text)

        current_page.on("requestfailed", record_failed_request)
        current_page.on("response", record_response)
        current_page.on("console", record_console_error)
        current_page.base_url = base_url
        yield current_page
        assert current_page._browser_errors == []
        assert current_page._browser_console_errors == []
        assert current_page._unexpected_failed_requests == []
        assert current_page._expected_failed_urls == set(
            current_page._expected_failed_requests
        )
        assert len(current_page._expected_browser_console_errors) == len(
            current_page._expected_failed_requests
        )
        assert current_page._http_errors == current_page._expected_http_errors
    finally:
        if context is not None:
            context.close()
        if browser is not None:
            browser.close()
        playwright.stop()


def register_patient(page, name="Browser Test Patient"):
    page.goto(f"{page.base_url}/")
    assert page.url.endswith("/register")
    page.get_by_role("button", name="Save and continue").click()
    assert "Correct the highlighted fields" in page.locator(
        "#registration-status"
    ).inner_text()
    assert page.locator("#patient-name").get_attribute("class").find(
        "is-invalid"
    ) >= 0

    page.locator("#patient-name").fill(name)
    page.locator("#patient-age").fill("35.5")
    page.locator("#patient-gender").select_option("Male")
    page.locator("#incident-type").fill("fall")
    page.get_by_role("button", name="Save and continue").click()
    assert "Correct the highlighted fields" in page.locator(
        "#registration-status"
    ).inner_text()
    assert "is-invalid" in page.locator("#patient-age").get_attribute("class")

    page.locator("#patient-age").fill("35")
    page.locator("#patient-gender").select_option("Female")
    page.locator("#incident-type").fill("fall")
    page.get_by_role("button", name="Save and continue").click()
    page.locator("#patient-code").wait_for(state="visible")
    code = page.locator("#patient-code").inner_text()
    assert len(code) == 5 and code.isdigit()
    page.get_by_role("link", name="Continue to assessment").wait_for(
        state="visible"
    )
    page.get_by_role("link", name="Continue to assessment").click()
    page.locator("#patient-context").wait_for(state="visible")


def select_state(page, evidence_key, label):
    card = page.locator(
        f'.symptom-card[data-symptom-key="{evidence_key}"]'
    )
    card.get_by_role("button", name=label, exact=True).click()
    assert f"Recorded state: {label}" in card.locator(
        ".evidence-status"
    ).inner_text()


def submit_assessment(page):
    page.get_by_role("button", name="Submit assessment").click()
    page.wait_for_url("**/results")
    page.locator("#checklist-content").wait_for(state="visible")


def test_registration_positive_multiple_rules_and_checklist(page, browser_app):
    application, _base_url = browser_app
    register_patient(page)

    present_keys = (
        "adult_head_injury_gcs_12_or_less_initial_ed",
        "adult_head_injury_post_traumatic_seizure",
        "adult_head_injury_focal_neurological_deficit",
    )
    for evidence_key in present_keys:
        select_state(page, evidence_key, "Yes")
    select_state(page, "adult_head_injury_gcs_below_15_at_2_hours", "No")
    select_state(page, "anesthesia_allergy_documented", "Yes")
    assert "Recorded state: Unknown" in page.locator(
        '[data-symptom-key="adult_head_injury_more_than_one_vomiting_episode"] '
        ".evidence-status"
    ).inner_text()

    submitted_payloads = []
    page.on(
        "request",
        lambda request: submitted_payloads.append(request.post_data_json)
        if request.url == f"{page.base_url}/api/triage"
        and request.method == "POST"
        else None,
    )
    submit_assessment(page)

    checklist_text = page.locator("#checklist-items").inner_text()
    assert "urgent CT head assessment" in checklist_text
    assert "BT-01" in checklist_text and "BT-05" in checklist_text
    assert page.locator(".checklist-task").count() == 4
    assert len(submitted_payloads) == 1
    evidence = submitted_payloads[0]["evidence"]
    assert evidence["adult_head_injury_gcs_12_or_less_initial_ed"] == "PRESENT"
    assert evidence["adult_head_injury_gcs_below_15_at_2_hours"] == "ABSENT"
    assert evidence[
        "adult_head_injury_more_than_one_vomiting_episode"
    ] == "UNKNOWN"

    with application.app_context():
        assert db.session.query(Patient).count() == 1
        assert db.session.query(Assessment).count() == 1

    page.reload()
    assert "Checklist for Browser Test Patient" in page.locator(
        "#checklist-patient"
    ).inner_text()
    page.get_by_role("link", name="Assessment", exact=True).evaluate(
        "link => link.click()"
    )
    page.wait_for_url("**/assessment")
    assert page.url.endswith("/assessment")
    assert "Patient Browser Test Patient" in page.locator(
        "#patient-context"
    ).inner_text()
    assert "Code" in page.locator("#patient-context").inner_text()
    select_state(page, "adult_head_injury_post_traumatic_seizure", "Yes")
    page.reload()
    assert "Recorded state: Unknown" in page.locator(
        '[data-symptom-key="adult_head_injury_post_traumatic_seizure"] '
        ".evidence-status"
    ).inner_text()
    assert "Patient Browser Test Patient" in page.locator(
        "#patient-context"
    ).inner_text()


def test_unknown_trauma_forward_matches_multiple_categories_and_revises(page, browser_app):
    application, _base_url = browser_app
    register_patient(page)
    page.get_by_label("Unknown Trauma").check()
    assert page.locator("#category").is_disabled()
    select_state(page, "adult_head_injury_post_traumatic_seizure", "Yes")
    select_state(page, "chest_trauma_negative_chest_efast", "Yes")
    page.get_by_role("button", name="Run forward inference").click()
    page.wait_for_url("**/results")

    checklist_text = page.locator("#checklist-items").inner_text()
    assert "BT-05" in checklist_text and "CT-01" in checklist_text
    assert "post-traumatic seizure" not in checklist_text.lower()
    assert "Applicable rule evaluations" not in page.locator("body").inner_text()

    page.get_by_role("link", name="Edit assessment").click()
    page.wait_for_url("**/assessment")
    assert page.locator("#category").is_disabled()
    assert "Recorded state: Yes" in page.locator(
        '[data-symptom-key="adult_head_injury_post_traumatic_seizure"] .evidence-status'
    ).inner_text()
    select_state(page, "adult_head_injury_post_traumatic_seizure", "No")
    page.get_by_role("button", name="Run forward inference").click()
    page.wait_for_url("**/results")
    assert "BT-05" not in page.locator("#checklist-items").inner_text()
    assert "CT-01" in page.locator("#checklist-items").inner_text()
    page.reload()
    assert "CT-01" in page.locator("#checklist-items").inner_text()

    with application.app_context():
        forward_assessments = db.session.query(Assessment).filter_by(
            workflow_mode="unknown_trauma"
        ).count()
        assert forward_assessments == 2


def test_unknown_no_match_refresh_and_missing_result_state(page):
    register_patient(page)
    assert page.locator(
        '[data-symptom-key="adult_head_injury_post_traumatic_seizure"] '
        '[data-state="UNKNOWN"]'
    ).get_attribute("aria-pressed") == "true"
    submit_assessment(page)

    assert page.locator(".checklist-task").count() == 3
    assert "Clinician-selected tests" in page.locator("#checklist-items").inner_text()

    page.reload()
    assert page.locator(".checklist-task").count() == 3
    page.evaluate("sessionStorage.removeItem('erpilotLastAssessment')")
    page.goto(f"{page.base_url}/results")
    assert "open it from patient records" in page.locator(
        "#checklist-error"
    ).inner_text().lower()
    assert "d-none" in page.locator("#checklist-content").get_attribute("class")


def test_checklist_completion_and_remarks_save_to_patient_record(page, browser_app):
    register_patient(page, "MVP Record Patient")
    select_state(page, "adult_head_injury_post_traumatic_seizure", "Yes")
    submit_assessment(page)
    task = page.locator(".checklist-task").filter(has_text="CT head")
    task.locator("select.checklist-status").select_option("done")
    task.locator("textarea").fill("Requested by clinician; completed and reviewed.")
    page.get_by_role("button", name="Save checklist").click()
    page.get_by_text("Saved to the patient record.").wait_for(state="visible")
    page.reload()
    task = page.locator(".checklist-task").filter(has_text="CT head")
    assert task.locator("select.checklist-status").input_value() == "done"
    assert "completed and reviewed" in task.locator("textarea").input_value()

    page.get_by_role("link", name="Patient records", exact=True).click()
    page.wait_for_url("**/records")
    page.locator("#patient-search").fill("MVP Record")
    page.get_by_role("button", name="View record").wait_for(state="visible")
    page.get_by_role("button", name="View record").click()
    record = page.locator("#patient-record")
    record.get_by_role("heading", name="MVP Record Patient").wait_for(state="visible")
    assert "MVP Record Patient" in record.inner_text()
    assert "completed and reviewed" in record.inner_text()
    assert "Done" in record.inner_text()


def test_demo_patient_code_and_copy_controls(page):
    page.goto(f"{page.base_url}/register")
    page.get_by_role("button", name="Fill demo details").click()
    assert page.locator("#patient-name").input_value() == "Alex Demo"
    assert page.locator("#incident-type").input_value() == "Demo collision"
    assert "Fictional demo details" in page.locator("#registration-status").inner_text()
    page.get_by_role("button", name="Save and continue").click()
    page.locator("#patient-code-panel").wait_for(state="visible")
    code = page.locator("#patient-code").inner_text()
    assert len(code) == 5 and code.isdigit()
    assert page.locator("#copy-patient-code").get_attribute("data-copy-text") == code
    page.get_by_role("link", name="Continue to assessment").click()
    assert code in page.locator("#patient-context").inner_text()


def test_unsaved_checklist_warns_and_recovers_after_refresh(page):
    register_patient(page)
    submit_assessment(page)
    task = page.locator(".checklist-task").filter(has_text="Clinician-selected tests")
    task.locator("select.checklist-status").select_option("in_progress")
    task.locator("textarea").fill("Demo draft remark")

    dialogs = []
    page.once("dialog", lambda dialog: (dialogs.append(dialog.type), dialog.dismiss()))
    page.get_by_role("link", name="Patient records", exact=True).click()
    assert dialogs == ["beforeunload"]
    assert page.url.endswith("/results")

    page.once("dialog", lambda dialog: dialog.accept())
    page.reload()
    recovered = page.locator(".checklist-task").filter(has_text="Clinician-selected tests")
    assert recovered.locator("select.checklist-status").input_value() == "in_progress"
    assert recovered.locator("textarea").input_value() == "Demo draft remark"
    assert "Recovered unsaved checklist edits" in page.locator("#save-status").inner_text()

    page.get_by_role("button", name="Save checklist").click()
    page.get_by_text("Saved to the patient record.").wait_for(state="visible")


def test_conditional_chest_drain_prompt_is_opt_in_and_persisted(page):
    register_patient(page)
    submit_assessment(page)
    assert "chest drain" not in page.locator("#checklist-items").inner_text().lower()
    page.locator("#task-template").select_option("chest-drain")
    page.get_by_role("button", name="Add prompt").click()
    task = page.locator(".checklist-task").filter(has_text="Chest decompression")
    assert "haemodynamic instability" in task.inner_text()
    assert "not a procedure instruction" in task.inner_text()
    task.locator("select.checklist-status").select_option("done")
    task.locator("textarea").fill("Clinician decision documented.")
    page.get_by_role("button", name="Save checklist").click()
    page.get_by_text("Saved to the patient record.").wait_for(state="visible")


def test_triage_network_failure_shows_error_and_recovers(page, browser_app):
    application, _base_url = browser_app
    register_patient(page)
    failing_url = f"{page.base_url}/api/triage"
    triage_requests = []
    triage_statuses = []
    page.on(
        "request",
        lambda request: triage_requests.append(request.url)
        if request.url == failing_url and request.method == "POST"
        else None,
    )
    page.on(
        "response",
        lambda response: triage_statuses.append(response.status)
        if response.url == failing_url and response.request.method == "POST"
        else None,
    )
    page._expected_failed_urls.add(failing_url)
    page.route("**/api/triage", lambda route: route.abort())
    page.get_by_role("button", name="Submit assessment").click()
    page.locator("#assessment-status").get_by_text(
        "Failed to fetch", exact=False
    ).wait_for(state="visible")
    assert "Failed to fetch" in page.locator("#assessment-status").inner_text()
    assert page.get_by_role("button", name="Submit assessment").is_enabled()
    page.unroute("**/api/triage")

    page.locator("#submit-assessment").evaluate(
        "button => { button.click(); button.click(); }"
    )
    page.wait_for_url("**/results")
    assert page.locator(".checklist-task").count() == 3
    assert triage_requests == [failing_url, failing_url]
    assert triage_statuses == [201]
    with application.app_context():
        assert db.session.query(Assessment).count() == 1
