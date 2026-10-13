# ERPilot AI - Requirement Analysis

## 1. Project description

ERPilot AI is a rule-based trauma center decision support system and
educational checklist assistant. It accepts staff-entered patient information,
evaluates explicit IF-THEN rules, identifies incomplete matches, asks targeted
follow-up questions, and explains the rules behind its suggestions.

**Mandatory disclaimer:** ERPilot AI is an educational prototype. It is not
clinically validated, is not intended for use on real patients, does not
diagnose patients, and does not replace qualified clinical judgment.

## 2. Problem statement

Trauma staff working under time pressure may overlook symptoms, miss checklist
steps, or delay contacting an appropriate department. ERPilot AI is intended to
support a structured checklist workflow by making the entered evidence,
incomplete matches, applicable rules, and protocol references visible.

## 3. Project goals

- Collect staff-entered patient details, symptoms, and vital signs.
- Classify supported trauma-related concerns using a rule-based engine.
- Use forward chaining to evaluate the collected evidence.
- Use backward chaining to identify missing conditions and ask targeted
  questions.
- Explain every fired rule with its rule ID, matched conditions, and protocol
  reference.
- Apply separate special-condition modifiers.
- Store patient assessments and generate downloadable reports.

These goals describe software behavior and educational workflow support. They
do not authorize diagnosis, autonomous treatment decisions, or clinical use.

## 4. Users

- **Emergency nurses and first responders:** enter observations.
- **Junior and on-call doctors:** review and verify suggestions.
- **Faculty/admin reviewers:** optionally view rules in a read-only interface
  after the core system is complete.

Patients are not direct users.

## 5. Scope

### 5.1 Core trauma categories

- Brain trauma
- Chest trauma
- Abdominal trauma
- Orthopedic trauma

### 5.2 Special conditions

- Pregnancy
- Anticoagulant use
- Narcotic/opioid intoxication
- Documented allergies, initially including anesthesia allergy as specified by
  the product requirements

Special conditions are handled as separate modifiers. They do not create new
trauma categories.

### 5.3 Required features

- Patient registration: name, age, gender, and incident type.
- Symptom selection and numeric vital-sign entry.
- Forward chaining, backward chaining, and explanations.
- An explicit no-match state.
- Special-condition modifiers.
- SQLite assessment storage.
- Assessment report generation.
- A visible RED-priority alert.

The initial implementation must use the following architecture:

- Python 3 and Flask
- HTML, CSS, Bootstrap, and vanilla JavaScript
- SQLite and SQLAlchemy
- JSON files as the source of truth for rules
- A custom Python inference engine using forward and backward chaining
- pytest for testing
- ReportLab or DOCX for later report generation

The system must not use LLMs, machine learning, React, Vue, external
inference APIs, or unnecessary frameworks.

## 6. Explicit exclusions

The initial implementation excludes:

- Clinical diagnosis or autonomous treatment decisions.
- Clinical validation claims or real-patient use.
- LLMs and machine learning.
- EHR integration, voice input, and live doctor notifications.
- Full drug-interaction checking.
- A rule-editing CRUD interface.
- Historical assessment search.

## 7. System behavior

### 7.1 Evidence states

The system must distinguish among:

- **Present:** the user has supplied evidence that a condition is present.
- **Absent:** the user has explicitly supplied evidence that a condition is
  absent.
- **Unknown:** the condition has not been answered or is otherwise unresolved.

An unanswered condition is not automatically false. In particular, missing
information must not be treated as confirmed absence.

### 7.2 Matching outcomes

For each rule, the software must define one of these outcomes:

- **FULL_MATCH:** all required conditions are present.
- **PARTIAL_MATCH:** at least one required condition is present and at least
  one required condition remains missing or unknown.
- **NO_MATCH:** no required condition is present.

These outcomes describe software behavior, not clinical certainty.

### 7.3 Rule evaluation and follow-up

- A rule may fire only when all of its required conditions are satisfied.
- For a `PARTIAL_MATCH`, identify the missing conditions and ask about a
  genuinely missing item.
- When new evidence is supplied, re-evaluate the affected rule.
- Display all applicable fired rules.
- Do not automatically resolve conflicts between competing recommendations.
- If no rule fires, show an explicit no-match message and advise the user to
  rely on qualified clinical judgment.

### 7.4 Explanations and modifiers

Every fired rule must display:

- Its stable rule ID.
- The conditions that matched.
- Its conclusion, priority flag, suggested department, and checklist action as
  defined by the rule data.
- Its protocol reference.

Special-condition modifiers must be evaluated separately and their effect on
applicable core-rule output must be visible. Modifiers must not be broader than
their independently researched supporting evidence.

### 7.5 Safety boundary

The product is an educational prototype, not a clinical device or validated
clinical decision system. Clinical content must be reviewed by a qualified
clinician before any real-world clinical use. The interface must keep the
educational-prototype disclaimer visible.

## 8. Non-functional requirements

- **Fast, tap-first interface:** common data entry must require minimal
  navigation.
- **Explainability:** every recommendation must be traceable to a rule and
  protocol reference.
- **Consistent vocabulary:** symptom and condition keys must use the canonical
  vocabulary defined in a later `knowledge_base/symptoms.json`.
- **Traceability:** protocol references must identify a source and a specific
  recommendation, section, or page where possible.
- **Testability:** matching behavior, evidence states, follow-up questions, and
  no-match behavior must be testable.
- **Safety communication:** educational-prototype limitations and the
  non-diagnostic disclaimer must be clear.

## 9. Deferred implementation considerations

The following are intentionally deferred until later stages:

- Defining and validating the canonical symptom vocabulary.
- Creating JSON rule and modifier datasets.
- Implementing the Flask application, inference engine, database models,
  templates, frontend components, and tests.
- Adding report generation.
- Adding an optional read-only rule viewer.

Clinical rules must not be derived from the illustrative schema examples in
this stage. Each future rule requires a source-backed protocol reference and
appropriate clinical review.
