# ERPilot AI Final Report

## Abstract

ERPilot AI is an educational Flask prototype that records trauma-assessment
evidence, evaluates deterministic JSON rules, exposes explicit unknown and
absent states, and presents explainable results with source references. It
supports brain, chest, abdominal, and orthopedic trauma categories, plus
pregnancy, anticoagulant, opioid-intoxication, and allergy modifiers. It
persists assessment data and generates PDF and DOCX reports.

The project verifies software behavior only. It has no clinical validation,
does not diagnose patients, is not intended for real-patient care, and does
not replace qualified clinical judgment.

## Problem statement and objectives

The product requirements address the risk that structured trauma evidence,
incomplete observations, checklist actions, or protocol references may be
overlooked under time pressure. The implementation objectives are to:

- collect fictional patient and assessment data;
- evaluate explicit evidence using a deterministic inference engine;
- keep `PRESENT`, `ABSENT`, and `UNKNOWN` distinct;
- expose full, partial, and no-match behavior;
- explain rule IDs, matched conditions, actions, and protocol references;
- evaluate special conditions separately and additively;
- persist complete assessment results; and
- provide reviewable PDF and DOCX reports.

These are software workflow objectives, not authorization for diagnosis,
autonomous treatment, or clinical triage.

## Scope and requirements

The implemented scope is:

- four core categories: brain, chest, abdominal, and orthopedic trauma;
- four special-condition modifiers: pregnancy, anticoagulant treatment,
  opioid intoxication documented or suspected, and documented anaesthesia
  allergy;
- patient registration and SQLite persistence;
- Flask JSON APIs and a Bootstrap/vanilla-JavaScript interface;
- deterministic forward chaining, backward-chaining support, and explanations;
- PDF/DOCX report downloads; and
- an accessible RED-priority display alert.

The optional rule viewer is deferred. Authentication, historical assessment
search, EHR integration, live notifications, ML, LLMs, and external inference
APIs are not implemented.

## Architecture and technology

The browser sends validated evidence to Flask. The triage route validates
canonical keys, loads only the selected category's core JSON rules, loads the
modifier datasets, evaluates them separately, persists the result through
SQLAlchemy, and returns the complete response. The report routes retrieve an
assessment through its patient association, validate the stored JSON, and
render PDF or DOCX output.

The stack is Python 3.11.9 in the verified environment, Flask,
Flask-SQLAlchemy, SQLAlchemy, SQLite, JSON datasets, ReportLab,
`python-docx`, HTML/CSS/Bootstrap, vanilla JavaScript, and pytest.

## Knowledge acquisition and inference methodology

Core and modifier mappings are documented in
[knowledge_acquisition_and_rule_derivation.md](knowledge_acquisition_and_rule_derivation.md).
The underlying source notes are in
[knowledge_base/protocols.md](../knowledge_base/protocols.md).

The matcher uses explicit evidence states:

- `PRESENT` satisfies a required condition.
- `ABSENT` remains an explicit negative observation.
- `UNKNOWN` and missing keys remain unresolved.

For each rule, all-present conditions produce `FULL_MATCH`; a mix of present
and unresolved conditions produces `PARTIAL_MATCH`; and no present condition
produces `NO_MATCH`. Explanations are generated from the evaluation and
include rule ID, match status, conditions, and protocol reference.

Modifiers are evaluated separately. They can coexist with one another and
with core matches, but the current modifier data uses `priority_override:
"NONE"` so core outcomes and software priorities remain unchanged.

## Implemented clinical-source mappings

The implemented datasets record:

- BT-01 through BT-07 against NICE NG232 recommendation 1.5.8.
- CT-01 against NICE NG39 recommendation 1.3.3.
- AT-01 against NICE NG39 recommendation 1.5.30.
- OT-01 against NICE NG38 recommendation 1.2.1.
- OT-02 against NICE NG38 recommendation 1.5.7.
- PREG-01 against ACOG Committee Opinion 723.
- AC-01 against NICE NG232 recommendation 1.5.13.
- OPI-01 against NICE NG232 recommendation 1.4.2.
- ALG-01 against NICE CG183 recommendation 1.2.5.

These references are source-to-software mappings, not claims that the
configured priority, department, or checklist text is a validated clinical
decision. The sources and protocol notes must be checked again before any
real-world use.

## Explainability, persistence, and reports

Each triage response includes the assessment ID, patient ID, category,
submitted evidence, modifier evidence, vitals, core inference result,
modifier result, outcome, and educational disclaimer. The database stores
core evidence, vitals, and the complete inference result including modifier
evidence and results.

Reports include patient and assessment metadata, evidence, vitals, core
outcome, triggered IDs, evaluations, explanations, protocol references,
modifier details, timestamps, and safety limitations. Report access verifies
that the path patient ID matches the assessment's associated patient ID.
There is no authentication system, so this association check is not a
complete access-control mechanism.

The results page shows a textual RED alert only when a matched or partial
core evaluation has a RED software priority. The alert explicitly says that
RED is provisional and not a clinically validated triage category.

## Testing methodology and verified results

Tests use isolated Flask applications and in-memory SQLite databases. Coverage
includes:

- schema, JSON, canonical vocabulary, priority, category, and protocol
  validation;
- matching, forward chaining, backward chaining, explanations, partial
  matches, no-match behavior, and unknown-versus-absent evidence;
- all four core categories and category-specific rule loading;
- independent and combined special-condition modifiers;
- invalid request and evidence handling;
- patient and assessment persistence;
- PDF/DOCX generation and content markers;
- wrong-patient, missing-assessment, invalid-format, and malformed-storage
  handling; and
- frontend route and RED-alert/report-link contracts.

Final verification commands and actual results:

```text
python -m pytest -q
147 passed in 15.75s

python -m pytest -q tests/test_browser_workflows.py
5 passed in 10.28s

Fresh temporary Python 3.11.9 virtual environment:
python -m pip install -r requirements.txt
passed

Fresh temporary Playwright Chromium installation and launch:
python -m playwright install chromium
passed

python -m compileall -q .
passed

node --check static/js/assessment.js
passed

node --check static/js/results.js
passed

node --check static/js/questions.js
passed

node --check static/js/registration.js
passed

git diff --check
passed
```

The full suite was also rerun in the fresh virtual environment using its
isolated Chromium installation: `147 passed in 12.32s`. No tests were skipped
or failed. The documented SQLite initialization created a temporary database;
the Flask debug server started and `/register`, `/assessment`, and `/results`
returned HTTP 200. The Playwright flows also exercised report downloads. No
clinical performance metric was measured. The test fixtures are synthetic and
must not be treated as clinical data.

## Results analysis

The verified results demonstrate functional behavior: the application can
register a fictional patient, evaluate category-specific evidence, preserve
unknown states, report additive modifiers, persist results, produce reports,
and reject malformed or mismatched report requests. The tests also demonstrate
that multiple rules and modifiers remain visible rather than being silently
collapsed.

These results do not demonstrate accuracy, sensitivity, specificity,
precision, recall, clinical utility, response-time performance, safety in
clinical practice, or equivalence to hospital workflows. No real-patient,
expert-review, or prospective evaluation has been performed.

## Limitations, assumptions, and threats to validity

- There is no authentication or authorization.
- Dependency versions in `requirements.txt` are unpinned; the clean install
  succeeded during this verification, but future installs may resolve newer
  releases.
- The local Flask configuration uses `DEBUG = True` and a development-only
  fallback secret key. The documented debug server is only for local
  demonstrations and must not be exposed to an untrusted network.
- The local SQLite database is not a production data store.
- Source notes contain paraphrases and require current guideline verification.
- PREG-01 does not identify a numbered ACOG recommendation in the current
  project notes.
- Population restrictions and source update metadata are incomplete for some
  NG39/NG38 notes.
- The interface records documented evidence; it does not independently verify
  a clinical observation, medication, allergy, procedure, or diagnosis.
- RED/ORANGE/YELLOW values are provisional software mappings and are not
  validated triage classifications.
- The optional rule viewer and general assessment-history retrieval are not
  implemented.

## Future improvements

Future work should be separately approved and clinically reviewed. Potential
items include re-verifying every source against current official guidance,
adding authentication and privacy
controls, adding a controlled assessment retrieval workflow, expanding tests
for any new source-backed rules, and deciding whether a safe read-only rule
viewer is warranted. None of these are claimed as implemented here.

## Conclusion

ERPilot is a reproducible educational demonstration of source-referenced,
deterministic trauma-assessment software behavior. Its verified functionality
is limited to the documented implementation and automated tests. It is not a
clinically validated decision-support system and must not be used for
real-patient care.

## References

- [Project requirements](requirement_analysis.md)
- [Protocol research notes](../knowledge_base/protocols.md)
- [Knowledge acquisition and rule derivation](knowledge_acquisition_and_rule_derivation.md)
- [Rule schema](../rule_base/rule_schema.md)
- NICE NG232, NG39, and NG38 official URLs recorded in
  [protocols.md](../knowledge_base/protocols.md).
- ACOG Committee Opinion 723 and NICE CG183 official URLs recorded in
  [protocols.md](../knowledge_base/protocols.md).
