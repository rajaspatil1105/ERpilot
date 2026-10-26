# Stage 5 Workflow Coverage Matrix

This matrix records the implementation and executable coverage reviewed for
Stage 5. Tests use isolated in-memory SQLite databases where they exercise
Flask persistence. The browser automation packages and browser binaries were
not installed in the inspected environment, so browser-only behavior is
identified separately from Flask/client coverage.

This is a historical Stage 5 snapshot. Its browser-availability statements
describe the environment at that stage; later Chromium execution is recorded
in [the final report](final_report.md) and `tests/test_browser_workflows.py`.

| Workflow | Existing implementation | Coverage reviewed or added | Gap / limitation |
| --- | --- | --- | --- |
| Patient registration and validation | `POST /api/patients`; SQLAlchemy patient model; registration page and JS | `test_triage_routes.py` validates required fields, types, malformed JSON, and persistence; `test_frontend_routes.py` verifies page/API wiring | No browser execution available |
| Assessment creation and persistence | `POST /api/triage` persists category, evidence, vitals, and inference JSON | Route tests verify create, failure rollback, and persisted response; multi-rule tests verify all configured IDs | No retrieval endpoint exists by design |
| Symptom evidence submission | Canonical keys across supported categories are validated; unrelated category keys are retained as unmatched evidence and cannot trigger current-category rules | Route tests cover valid, unsupported key/state, and unrelated canonical evidence; added no-activation assertion | API only; UI submission not browser-executed |
| PRESENT / ABSENT / UNKNOWN | Explicit matcher states; omitted conditions default to UNKNOWN | Inference tests cover all states; added per-configured-rule test and distinction between missing, explicit unknown, and absent | No gap found in matcher semantics |
| Forward chaining | Evaluates every configured rule | Existing synthetic and route tests; added every core rule positive/negative and multi-condition partial evaluation | Yes cases are derived from configured conditions, not clinical content |
| Full / partial / no match | `_evaluate_rules` returns aggregate outcome; matcher returns per-rule status | Unit/API tests cover outcomes; added no-match API/persistence consistency and no fabricated conclusion assertion | No gap found |
| Backward chaining | Exact conclusion target evaluation and unresolved condition aggregation | Unit and question workflow tests; API follow-up tests | No user-selectable arbitrary target endpoint |
| Follow-up generation/deduplication | Rule-linked JSON questions selected for partial rules | Question tests cover unique shared questions, relevance, and no repeat after resolved answer | Multiple follow-up question paths exercised by unit tests |
| Follow-up answer validation/persistence/re-evaluation | POST question endpoint validates ownership/current relevance and stores evidence/result | Route tests cover Yes/No/Unknown, invalid/stale, association, modifier retention; added repeat-answer conflict and persisted evidence stability | No answer-history table; current assessment JSON is authoritative |
| Multiple conclusions | Each evaluation retains its own conclusion; no automatic conflict resolution | Route test confirms simultaneous full matches remain visible | Not a clinical conflict-resolution system |
| Modifiers | Four JSON modifier sets, independently matched and combined additively | `test_modifiers.py` covers each trigger, absent/unknown, combinations, category applicability, persistence | PRD examples are covered where configured; no unconfigured pregnancy/trauma-specific rule is invented |
| Core + modifier combinations | Modifier payload stored within inference result; core outcome preserved | Modifier combination API test asserts core result and all fired modifiers | Browser rendering not executed |
| Explanations and rule trace | Rule IDs, matched/absent/unknown evidence, source reference, follow-up IDs | Matcher, explainer, question workflow, route, and report tests; added per-rule trace/reference checks | No gap found |
| Results page | Results JS renders API result from `sessionStorage` | Flask route/template contract tests and missing-result state test | Refresh survival depends on sessionStorage in the same browser tab; browser automation unavailable |
| Clinician-review checklist | Derived only from returned rule/modifier metadata | Frontend contract checks; results JS rendering logic inspected | DOM execution unavailable without browser/DOM tooling |
| PDF/DOCX reports | Report routes build output from persisted assessment with ownership association check | `test_reports.py` covers content, formats, missing/mismatched IDs, malformed persisted data | Covered at Flask route level |
| Malformed payloads/IDs/categories | Route validation returns 400/404/422 as configured | `test_triage_routes.py` validation cases; added missing assessment and cross-category cases | No fabricated auth/ownership semantics: app has no auth |
| Patient/assessment association | Follow-up and report endpoints check assessment's patient ID | Follow-up/report association tests | No authentication or authorization system, documented scope exclusion |
| Network failures/duplicate browser submissions | Assessment JS guards duplicate submit with `isSubmitting`, restores controls on failure; question JS restores button after error | Static JS contracts inspected | No browser network interception possible in current environment |
| Navigation, refresh, restart persistence | DB persists assessments; page results are sessionStorage-backed | API persistence across requests and template empty-state covered | Full browser refresh/restart behavior not exercised; no assessment GET route and new browser session cannot restore result |

## Configured rules and modifiers

Core rule data currently contains 24 rules: 17 brain, 2 chest, 2 abdominal,
and 3 orthopedic. The new data-driven unit coverage evaluates each configured
rule with all conditions PRESENT and all conditions ABSENT, and exercises a
partial state for every multi-condition rule (currently CT-02). Modifier
tests independently activate each of the four configured modifiers and verify
that ABSENT and UNKNOWN do not fire them.

## Browser verification status

No Playwright, Selenium, pytest browser plugin, Puppeteer, jsdom, Chromium,
Chrome, or Edge binary was present in the checked environment. Therefore no
browser-level scenario is claimed as executed. Flask test-client coverage
exercises the real routes, database persistence, and inference workflow; the
minimum additional setup for browser verification is an installed browser
automation tool with a browser binary. No dependency was installed for this
stage.
