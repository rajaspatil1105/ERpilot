"""Real Chromium workflows against an isolated Flask application."""

from __future__ import annotations

import threading
from pathlib import Path
from urllib.parse import urlparse

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
        current_page.on(
            "pageerror",
            lambda error: current_page._browser_errors.append(str(error)),
        )
        def record_failed_request(request):
            if not request.url.startswith(base_url):
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
        context.close()
        browser.close()
    finally:
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
    page.locator("#patient-gender").fill("unspecified")
    page.locator("#incident-type").fill("fall")
    page.get_by_role("button", name="Save and continue").click()
    assert "Correct the highlighted fields" in page.locator(
        "#registration-status"
    ).inner_text()
    assert "is-invalid" in page.locator("#patient-age").get_attribute("class")

    page.locator("#patient-age").fill("35")
    page.locator("#patient-gender").fill("unspecified")
    page.locator("#incident-type").fill("fall")
    page.get_by_role("button", name="Save and continue").click()
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
    page.locator("#outcome-summary h2").wait_for(state="visible")


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

    assert page.locator("#outcome-summary h2").inner_text() == (
        "Software outcome: FULL_MATCH"
    )
    assert page.locator("#matched-rules .rule-card").count() == 3
    for rule_id in ("BT-01", "BT-05", "BT-06"):
        assert page.locator("#matched-rules").get_by_text(
            rule_id, exact=True
        ).count() == 1
    assert page.locator("#review-checklist .review-checklist-item").count() == 4
    assert "modifier ALG-01" in page.locator("#review-checklist").inner_text()
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
    assert page.locator("#outcome-summary h2").inner_text() == (
        "Software outcome: FULL_MATCH"
    )
    page.get_by_role("link", name="Assessment", exact=True).evaluate(
        "link => link.click()"
    )
    page.wait_for_url("**/assessment")
    assert page.url.endswith("/assessment")
    assert "Assessment for patient ID" in page.locator(
        "#patient-context"
    ).inner_text()
    select_state(page, "adult_head_injury_post_traumatic_seizure", "Yes")
    page.reload()
    assert "Recorded state: Unknown" in page.locator(
        '[data-symptom-key="adult_head_injury_post_traumatic_seizure"] '
        ".evidence-status"
    ).inner_text()
    assert "Assessment for patient ID" in page.locator(
        "#patient-context"
    ).inner_text()


def test_unknown_no_match_refresh_and_missing_result_state(page):
    register_patient(page)
    assert page.locator(
        '[data-symptom-key="adult_head_injury_post_traumatic_seizure"] '
        '[data-state="UNKNOWN"]'
    ).get_attribute("aria-pressed") == "true"
    submit_assessment(page)

    assert page.locator("#outcome-summary h2").inner_text() == (
        "Software outcome: NO_MATCH"
    )
    assert "No rule matched the recorded evidence" in page.locator(
        "#outcome-summary"
    ).inner_text()
    assert page.locator("#matched-rules .rule-card").count() == 0
    assert page.locator("#unmatched-rules .rule-card").count() == 17

    page.reload()
    assert page.locator("#outcome-summary h2").inner_text() == (
        "Software outcome: NO_MATCH"
    )
    page.evaluate("sessionStorage.removeItem('erpilotLastAssessment')")
    page.goto(f"{page.base_url}/results")
    assert "stored assessment response is incomplete" in page.locator(
        "#results-error"
    ).inner_text().lower()
    assert "d-none" in page.locator("#results-content").get_attribute("class")


def test_chest_partial_follow_up_re_evaluation_and_duplicate_answer(page):
    register_patient(page)
    page.locator("#category").select_option("chest_trauma")
    select_state(
        page,
        "chest_trauma_efast_specialist_team_immediately_available",
        "Yes",
    )
    submit_assessment(page)

    assert page.locator("#outcome-summary h2").inner_text() == (
        "Software outcome: PARTIAL_MATCH"
    )
    assert page.locator("#matched-rules").get_by_text(
        "CT-02", exact=True
    ).count() == 1
    question = page.locator(".question-card")
    assert "Q-CT-EFAST-TRANSFER" in question.inner_text()
    assert "CT-02" in question.inner_text()

    result_ids = page.evaluate(
        """() => {
            const result = JSON.parse(sessionStorage.getItem('erpilotLastAssessment'));
            return {patient: result.patient_id, assessment: result.assessment_id};
        }"""
    )
    question_path = (
        f"/api/patients/{result_ids['patient']}/assessments/"
        f"{result_ids['assessment']}/questions/Q-CT-EFAST-TRANSFER"
    )

    page.evaluate(
        """async () => {
            const result = JSON.parse(sessionStorage.getItem('erpilotLastAssessment'));
            const response = await fetch(
                `/api/patients/${result.patient_id}/assessments/`
                    + `${result.assessment_id}/questions/Q-CT-EFAST-TRANSFER`,
                { method: 'POST', headers: {'Content-Type': 'application/json'},
                  body: JSON.stringify({response: 'MAYBE'}) },
            );
            window.invalidFollowupStatus = response.status;
        }"""
    )
    assert page.evaluate("window.invalidFollowupStatus") == 400
    page._expected_http_errors.append((question_path, 400))
    question_url = (
        f"{page.base_url}{question_path}"
    )
    page.route(
        question_url,
        lambda route: route.fulfill(
            status=400,
            content_type="application/json",
            body='{"error":"response must be one of YES, NO, or UNKNOWN."}',
        ),
    )
    question.get_by_role("button", name="Yes", exact=True).click()
    question.locator(".question-error").wait_for(state="visible")
    page._expected_http_errors.append((urlparse(question_url).path, 400))
    assert "response must be one of YES, NO, or UNKNOWN" in question.inner_text()
    assert question.get_by_role("button", name="Yes", exact=True).is_enabled()
    page.unroute(question_url)

    question = page.locator(".question-card")
    followup_requests = []
    page.on(
        "request",
        lambda request: followup_requests.append(request.url)
        if request.url == question_url and request.method == "POST"
        else None,
    )
    question.get_by_role("button", name="Yes", exact=True).evaluate(
        "button => { button.click(); button.click(); }"
    )
    page.locator("#outcome-summary h2").wait_for(state="visible")
    page.wait_for_function(
        "document.querySelector('#outcome-summary h2')?.textContent "
        "=== 'Software outcome: FULL_MATCH'"
    )
    assert page.locator("#follow-up-questions").inner_text().find(
        "No additional relevant questions remain"
    ) >= 0
    assert page.locator("#matched-rules").get_by_text(
        "CT-02", exact=True
    ).count() == 1
    assert followup_requests == [question_url]

    duplicate_status = page.evaluate(
        """async () => {
            const result = JSON.parse(sessionStorage.getItem('erpilotLastAssessment'));
            const response = await fetch(
                `/api/patients/${result.patient_id}/assessments/`
                    + `${result.assessment_id}/questions/Q-CT-EFAST-TRANSFER`,
                { method: 'POST', headers: {'Content-Type': 'application/json'},
                  body: JSON.stringify({response: 'YES'}) },
            );
            return response.status;
        }"""
    )
    assert duplicate_status == 409
    page._expected_http_errors.append((urlparse(question_url).path, 409))
    missing_status = page.evaluate(
        """async () => {
            const response = await fetch(
                '/api/patients/99999/assessments/99999/questions/Q-CT-EFAST-TRANSFER',
                { method: 'POST', headers: {'Content-Type': 'application/json'},
                  body: JSON.stringify({response: 'YES'}) },
            );
            return response.status;
        }"""
    )
    assert missing_status == 404
    page._expected_http_errors.append(
        ("/api/patients/99999/assessments/99999/questions/Q-CT-EFAST-TRANSFER", 404)
    )


def test_modifier_results_and_checklist_survive_browser_follow_up(page):
    register_patient(page)
    page.locator("#category").select_option("chest_trauma")
    select_state(page, "pregnancy_status_documented_pregnant", "Yes")
    select_state(page, "anesthesia_allergy_documented", "Yes")
    select_state(
        page,
        "chest_trauma_efast_specialist_team_immediately_available",
        "Yes",
    )
    submit_assessment(page)

    assert page.locator("#outcome-summary h2").inner_text() == (
        "Software outcome: PARTIAL_MATCH"
    )
    assert page.locator("#modifier-rules .rule-card").count() == 2
    for modifier_id in ("PREG-01", "ALG-01"):
        card = page.locator("#modifier-rules").get_by_text(
            modifier_id, exact=True
        )
        assert card.count() == 1
        assert modifier_id in page.locator("#review-checklist").inner_text()
    assert page.locator("#review-checklist .review-checklist-item").count() == 3

    question = page.locator(".question-card")
    question.get_by_role("button", name="Yes", exact=True).click()
    page.wait_for_function(
        "document.querySelector('#outcome-summary h2')?.textContent "
        "=== 'Software outcome: FULL_MATCH'"
    )
    assert page.locator("#matched-rules").get_by_text(
        "CT-02", exact=True
    ).count() == 1
    assert page.locator("#modifier-rules .rule-card").count() == 2
    assert page.locator("#review-checklist .review-checklist-item").count() == 3
    for modifier_id in ("PREG-01", "ALG-01"):
        assert modifier_id in page.locator("#modifier-rules").inner_text()
        assert modifier_id in page.locator("#review-checklist").inner_text()

    page.reload()
    assert page.locator("#outcome-summary h2").inner_text() == (
        "Software outcome: FULL_MATCH"
    )
    assert page.locator("#modifier-rules .rule-card").count() == 2


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
    assert page.locator("#outcome-summary h2").inner_text() == (
        "Software outcome: NO_MATCH"
    )
    assert triage_requests == [failing_url, failing_url]
    assert triage_statuses == [201]
    with application.app_context():
        assert db.session.query(Assessment).count() == 1
