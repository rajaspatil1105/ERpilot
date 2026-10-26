# ERPilot AI Demonstration Guide

## Safety boundary

Use fictional data only. ERPilot is an educational prototype, not clinically
validated, not intended for real-patient care, and not a substitute for
qualified clinical judgment. The demonstration shows software behavior and
traceability, not a clinical diagnosis or triage decision.

## MVP checklist and patient records

The assessment output is a short task checklist. Tasks generated from matched
configured rules are grouped by distinct action. The checklist also provides
places to record clinician-selected investigations, a page/consultation, and
a procedure decision. Tick completed tasks, enter remarks, and select **Save
checklist**. Open **Patient Records**, search by patient name, then select
**View record** to review saved checklist state and remarks.

Optional prompts are references for recording a clinician's decision, not
orders. The head-injury prompt links to [NICE NG232](https://www.nice.org.uk/guidance/ng232/chapter/recommendations),
which identifies CT as the primary initial investigation for acute clinically
important traumatic brain injury and says MRI is not the primary initial test.
The optional chest-decompression prompt states the specific condition in
[NICE NG39 recommendations 1.4.1–1.4.2](https://www.nice.org.uk/guidance/ng39/chapter/Recommendations):
clinician-suspected tension pneumothorax with haemodynamic instability or
severe respiratory compromise. It contains no procedural steps. The paging
prompt points to [NICE NG40 recommendation 1.3.3](https://www.nice.org.uk/guidance/ng40/chapter/recommendations),
which directs trauma response according to the site's written local guidance.

The MVP does not select a standard blood-test panel or order any test or
procedure. The responsible clinician records what was chosen and why. Use
fictional data only; the local prototype does not provide authentication or
clinical validation.

## Prerequisites

From the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
python -c "from app import app; from models.db import db; app.app_context().push(); db.create_all(); print('database initialized')"
python -m flask --app app run --debug
```

Open <http://127.0.0.1:5000/>. The equivalent macOS/Linux commands are in the
root [README](../README.md).

## Recommended demonstration sequence

### 0. Show the two reasoning directions

On `/assessment`, choose **Unknown Trauma** to enter findings without choosing
a category. The app submits the recorded evidence to all configured core rules
and shows category outcomes only when a rule fully matches. Choose **Known
Trauma Category** to select a goal category; the existing goal-directed rule
evaluation can then ask configured follow-up questions for unresolved partial
matches.

For a verified forward example, record:

```text
Adult head injury post-traumatic seizure: Yes
Chest trauma negative chest eFAST: Yes
All other core evidence: Unknown
```

The configured rules produce full matches BT-05 (`brain_trauma`,
`adult_head_injury_urgent_clinician_review`) and CT-01 (`chest_trauma`,
`chest_trauma_pneumothorax_not_excluded`). Both rule IDs and their recorded
supporting conditions appear in the results; no category is selected in this
workflow. Marking the seizure No and rerunning removes BT-05 while the chest
match remains.

For backward chaining, choose **Known Trauma Category**, select **Chest
Trauma**, and set `chest_trauma_efast_specialist_team_immediately_available`
to Yes while leaving
`chest_trauma_efast_onward_transfer_not_delayed` Unknown. This produces CT-02
as a partial match and asks the configured `Q-CT-EFAST-TRANSFER` question
about whether onward transfer would be delayed. Answer Yes to mark that
prerequisite present; CT-02 then becomes a full match. This demonstrates
reasoning from the selected category goal toward its prerequisites.

### 1. Register a fictional patient

Open `/register` and enter:

```text
Name: Demo Patient
Age: 35
Gender: unspecified
Incident type: fall
```

The registration response supplies a patient ID. The browser stores this
fictional identifier for the assessment page.

### 2. Submit a brain-trauma assessment

Open `/assessment`, keep `Brain trauma` selected, and set:

```text
Post-traumatic seizure: Present
All other core criteria: Unknown
Pregnancy: Unknown
Anticoagulant treatment: Present
Opioid intoxication: Unknown
Anaesthesia allergy: Unknown
```

Submit without adding vitals. The verified API behavior is:

- The core result is `FULL_MATCH` for BT-05 because the documented seizure
  criterion is present.
- Other core rules remain visible as partial or no-match evaluations.
- AC-01 is reported separately as a modifier review flag.
- The core outcome and priority are not replaced by the modifier.
- The stored response contains rule IDs, matched conditions, explanations,
  protocol references, submitted modifier evidence, and modifier results.

### 3. Review explainability and the RED alert

On `/results`, point out:

- The core software outcome.
- BT-05 and its matched condition.
- The protocol reference to NICE NG232 recommendation 1.5.8.
- The AC-01 modifier and its separate protocol reference.
- The accessible alert stating that RED is a provisional ERPilot
  software-display priority, not a clinically validated triage category.

The page keeps unknown conditions visible and does not convert them into
confirmed absence.

### 4. Demonstrate another category

Submit a second fictional assessment for `chest_trauma` with:

```json
{
  "chest_trauma_negative_chest_efast": "PRESENT"
}
```

The CT-01 evaluation preserves the NICE NG39 warning that a negative chest
eFAST does not exclude pneumothorax. The browser only submits evidence keys
for the selected core category; special-condition keys remain in the separate
modifier payload.

Equivalent core evidence keys for the other categories are:

```text
abdominal_trauma_negative_fast
orthopedic_trauma_suspected_knee_fracture_person_over_2
orthopedic_trauma_reduction_or_cast_splint_traction
```

These are software review flags, not diagnoses or imaging orders.

### 5. Download and inspect reports

Use the `Download PDF` and `Download DOCX` buttons on the results page. The
report includes:

- Patient and assessment identifiers.
- Category, timestamps, evidence, and vitals.
- Core outcome, triggered core rule IDs, evaluations, explanations, and
  protocol references.
- Recorded follow-up prompts, responses, normalized evidence states, and any
  currently unanswered questions.
- Modifier evidence, modifier outcome, triggered modifier IDs, and additive
  review flags.
- The provisional-priority and educational-prototype limitations.

The report route requires the matching patient ID and assessment ID. A
mismatched patient receives a non-disclosing 404 response.

## API-only demonstration

The same flow can be exercised without a browser:

```powershell
$patient = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:5000/api/patients `
  -ContentType "application/json" `
  -Body '{"name":"Demo Patient","age":35,"gender":"unspecified","incident_type":"fall"}'

$payload = @{
  patient_id = $patient.id
  category = "brain_trauma"
  evidence = @{
    adult_head_injury_post_traumatic_seizure = "PRESENT"
  }
  modifier_evidence = @{
    anticoagulant_treatment_documented = "PRESENT"
  }
  vitals = @{}
} | ConvertTo-Json -Depth 5

$assessment = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:5000/api/triage `
  -ContentType "application/json" `
  -Body $payload

$assessment | ConvertTo-Json -Depth 10
```

Replace the IDs in these report URLs with values from the response:

```text
http://127.0.0.1:5000/api/patients/<patient_id>/assessments/<assessment_id>/report/pdf
http://127.0.0.1:5000/api/patients/<patient_id>/assessments/<assessment_id>/report/docx
```

## Expected observable results

The automated suite verifies the category-specific rules, modifier
coexistence, persistence, report content and MIME types, wrong-patient
denial, malformed persisted data, frontend contracts, and RED-alert markup.
The five Playwright Chromium workflows exercise registration, assessment,
follow-up, result refresh, report downloads, and error recovery. The Stage 9
full run reported 147 passing tests. JavaScript syntax checks cover all four
frontend scripts. Browser screenshot verification is not part of the suite.

## Cleanup

Stop the Flask process with `Ctrl+C`. Remove only local demonstration data if
it was created:

```powershell
Remove-Item -LiteralPath .\instance\erpilot.db -ErrorAction SilentlyContinue
```

Do not commit the local database, real patient information, or generated
reports.
