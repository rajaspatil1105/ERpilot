# ERPilot AI Protocol Research Notes

## 1. Purpose and status

This document records source-backed research notes for the educational ERPilot
AI prototype. It is not a complete clinical protocol and must not be used to
diagnose, triage, or treat a real patient.

The notes below use only the initial sources and findings supplied for Stage 0.
They distinguish supplied findings from research tasks that remain unresolved.
Before implementation, the applicable current guidance must be checked,
specific recommendations must be cited, and the resulting content must be
reviewed by a qualified clinician.

## 2. Source A - NICE NG232

### Source identification

- **Organization:** National Institute for Health and Care Excellence (NICE)
- **Title:** *Head injury: assessment and early management*
- **Guideline identifier:** NG232
- **Official URL:** <https://www.nice.org.uk/guidance/NG232/chapter/recommendations>
- **Publication/update information:** Not recorded in the supplied Stage 0
  brief; verify the current publication and update details before
  implementation.
- **Verification status:** Official source URL supplied. The exact current
  recommendation text and numbers for each research area remain to be
  verified before any rule is derived.

### Relevant research areas

The supplied research brief identifies these areas for review:

- Glasgow Coma Scale (GCS).
- Loss of consciousness and amnesia.
- Vomiting and neurological deficits.
- Seizures and suspected skull fracture.
- Age-specific assessment criteria.
- Anticoagulant and antiplatelet treatment.
- Intoxication and the need to exclude important traumatic brain injury before
  attributing depressed consciousness to intoxication.
- Emergency assessment and CT criteria.

### Supported research direction

NG232 may inform future brain-trauma rules and separate anticoagulant or
intoxication modifier research. Exact recommendation numbers must be recorded
for every implemented finding. Adult and paediatric criteria must be kept
distinct.

### Limitations and unresolved questions

- No individual recommendation numbers or thresholds are asserted here
  because they were not supplied in the Stage 0 brief.
- Adult and paediatric criteria must not be combined without explicit source
  support.
- GCS, loss of consciousness, amnesia, vomiting, neurological deficits,
  seizures, suspected skull fracture, anticoagulant use, antiplatelet use, and
  intoxication require separate review of their population and timing
  conditions.
- A future implementation must not infer a diagnosis or treatment instruction
  from a general research area.

### Proposed ERPilot research area

- Brain trauma core rules.
- Anticoagulant special-condition modifier.
- Narcotic/opioid intoxication special-condition modifier.
- Follow-up questions for genuinely unknown evidence.

## 3. Source B - NICE NG39

### Source identification

- **Organization:** National Institute for Health and Care Excellence (NICE)
- **Title:** *Major trauma: assessment and initial management*
- **Guideline identifier:** NG39
- **Official URL:** <https://www.nice.org.uk/guidance/ng39/chapter/Recommendations>
- **Publication/update information:** Not recorded in the supplied Stage 0
  brief; verify the current publication and update details before
  implementation.
- **Verification status:** The four findings listed below are supplied as
  specifically verified findings for this stage. The complete current
  recommendations and their populations must still be checked before
  implementation.

### Relevant findings

- **Recommendation 1.3.3:** A negative chest eFAST does not exclude
  pneumothorax.
- **Recommendation 1.5.30:** A negative FAST does not exclude intraperitoneal
  or retroperitoneal haemorrhage.
- **Recommendations 1.4.4-1.4.7:** These describe different
  chest-imaging considerations for adults and children.

These are concise paraphrases of the supplied findings, not quotations.

### Proposed ERPilot research area

- Chest trauma rules and the distinction between adult and paediatric
  imaging-related evidence.
- Abdominal trauma rules that preserve the limitation of a negative FAST.
- Pelvic injury and major limb trauma research.
- Haemodynamic instability, suspected haemorrhage, and imaging research.

### Limitations and safety boundary

- A negative chest eFAST must not be represented as excluding pneumothorax.
- A negative FAST must not be represented as excluding intraperitoneal or
  retroperitoneal haemorrhage.
- The imaging recommendations must not be merged across adult and paediatric
  populations.
- These findings must not be converted into autonomous treatment
  instructions.
- The supplied brief does not provide complete recommendation text,
  thresholds, or all population restrictions. These remain implementation
  research tasks.

## 4. Source C - American College of Surgeons

### Source identification

- **Organization:** American College of Surgeons (ACS), Trauma Quality
  Programs
- **Title:** *Trauma Quality Programs Best Practices Guidelines*
- **Official URL:** <https://www.facs.org/quality-programs/trauma/quality/best-practices-guidelines/>
- **Guideline identifier and publication/update information:** The supplied
  brief does not specify an individual guideline identifier or update date.
  Verify the applicable full guideline before implementation.
- **Verification status:** The supplied URL is a source index. It is not
  sufficient evidence for an individual clinical rule.

### Relevant research areas

- Management of traumatic brain injury.
- Chest-wall injuries.
- Orthopaedic trauma.
- Other applicable injury-specific guidance.

### Proposed ERPilot research area

ACS guidance may inform future brain-trauma, chest-trauma, and
orthopedic-trauma rule research after the applicable full guideline is
selected.

### Limitations and unresolved questions

- The landing page must not be used as the sole protocol reference for an
  individual rule.
- The applicable full guideline and exact section must be identified before a
  rule is derived.
- No ACS thresholds, diagnoses, priority levels, department assignments, or
  treatment instructions are asserted in this document.

## 5. Source D - ACOG Committee Opinion 723

### Source identification

- **Organization:** American College of Obstetricians and Gynecologists
  (ACOG)
- **Title:** *Guidelines for Diagnostic Imaging During Pregnancy and
  Lactation*
- **Guideline identifier:** Committee Opinion 723
- **Official URL:** <https://www.acog.org/clinical/clinical-guidance/committee-opinion/articles/2017/10/guidelines-for-diagnostic-imaging-during-pregnancy-and-lactation>
- **Publication/update information:** The supplied brief identifies the
  committee opinion but does not provide current update information. Verify
  the latest applicable guidance before implementation.
- **Verification status:** The relevant finding below is supplied for this
  stage. Current applicability and exact source wording require verification.

### Relevant finding

Necessary radiography or CT should not automatically be withheld solely
because a patient is pregnant. Imaging choices must be made through
appropriate clinical assessment.

This is a concise paraphrase of the supplied finding, not a quotation.

### Proposed ERPilot research area

- Pregnancy special-condition modifier.
- Review flags for applicable chest-trauma and abdominal-trauma outputs.
- Source-backed documentation of imaging considerations.

### Limitations and safety boundary

- Do not encode a blanket rule to avoid CT in pregnancy.
- Do not encode a blanket rule that mandates imaging.
- This finding does not establish a priority override, department assignment,
  diagnostic conclusion, or treatment instruction.
- The latest applicable guidance and the patient's clinical context must be
  reviewed before implementation.

## 6. Cross-source implementation rules

- Use an official source and an exact recommendation, section, or page
  reference for every future rule or modifier.
- Treat the ACS landing page as an index only until the applicable full
  guideline is identified.
- Preserve adult and paediatric population distinctions.
- Do not invent quotations, recommendation numbers, page numbers, symptoms,
  thresholds, diagnoses, priority levels, department assignments, or treatment
  instructions.
- Never infer that an unreported symptom is absent.
- Do not make pregnancy, anticoagulant, or intoxication modifiers broader than
  their supporting evidence.
- If a source is insufficient, record the gap and leave the proposed rule
  unresolved.
- All clinical content requires qualified clinician review before any
  real-world use.
