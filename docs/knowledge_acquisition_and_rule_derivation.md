# Knowledge Acquisition and Rule Derivation

## Purpose and status

This document inventories the source references and rule data actually present
in ERPilot. It explains how documented source findings were represented as
explicit evidence keys and software checks. It does not establish clinical
validity. The project remains an educational prototype and is not intended for
real-patient care.

The inventory was derived from:

- `rule_base/core/*.json`
- `rule_base/special_conditions/*.json`
- `knowledge_base/symptoms.json`
- `knowledge_base/protocols.md`

The protocol notes contain paraphrases supplied during project development.
They are not a substitute for checking the current full guideline or for
qualified clinical review.

## Source inventory

| Source | Repository reference | Use in implementation |
| --- | --- | --- |
| NICE, *Head injury: assessment and early management* | NG232 recommendations 1.4.2, 1.5.8, and 1.5.13; official URL in `protocols.md` | Brain-trauma criteria, opioid-intoxication context, and anticoagulant-treatment modifier |
| NICE, *Major trauma: assessment and initial management* | NG39 recommendations 1.3.3 and 1.5.30 | Negative chest eFAST and negative FAST limitations |
| NICE, *Fractures (non-complex): assessment and management* | NG38 recommendations 1.2.1 and 1.5.7 | Orthopedic knee-imaging review and neurovascular documentation review |
| ACOG, *Guidelines for Diagnostic Imaging During Pregnancy and Lactation* | Committee Opinion 723; official URL in `protocols.md` | Pregnancy imaging-review modifier |
| NICE, *Drug allergy: diagnosis and management* | CG183 recommendation 1.2.5 | Allergy-information visibility modifier |
| American College of Surgeons Trauma Quality Programs | Source index only in `protocols.md` | Not used as direct evidence for a current rule |

## Core rule mapping

The core matcher treats each listed condition as a required evidence key. A
core rule reaches `FULL_MATCH` only when every condition is explicitly
`PRESENT`. A single-condition rule therefore maps one documented criterion to
one software evaluation.

| Rule ID | Evidence trigger | Source reference | Implemented action and scope |
| --- | --- | --- | --- |
| BT-01 | Initial emergency-department GCS 12 or less | NICE NG232 1.5.8 | Flags clinician review of the cited urgent CT-head criterion. Adult criterion only; the RED value is provisional. |
| BT-02 | GCS below 15 at two hours | NICE NG232 1.5.8 | Same conservative review flag; no diagnosis or autonomous order. |
| BT-03 | Suspected open or depressed skull fracture | NICE NG232 1.5.8 | Same conservative review flag; the software does not diagnose a fracture. |
| BT-04 | Sign of basal skull fracture | NICE NG232 1.5.8 | Same conservative review flag; the software does not establish the sign. |
| BT-05 | Post-traumatic seizure | NICE NG232 1.5.8 | Same conservative review flag; the software records supplied evidence only. |
| BT-06 | Focal neurological deficit | NICE NG232 1.5.8 | Same conservative review flag; no autonomous treatment or disposition. |
| BT-07 | More than one vomiting episode | NICE NG232 1.5.8 | Same conservative review flag; adult population and source scope remain required. |
| CT-01 | Documented negative chest eFAST | NICE NG39 1.3.3 | Preserves the warning that a negative chest eFAST does not exclude pneumothorax. It does not diagnose pneumothorax. |
| AT-01 | Documented negative FAST | NICE NG39 1.5.30 | Preserves the warning that a negative FAST does not exclude intraperitoneal or retroperitoneal haemorrhage. It does not diagnose haemorrhage. |
| OT-01 | Suspected knee fracture in a person over 2 | NICE NG38 1.2.1 | Flags review of whether the Ottawa knee rules indicate an X-ray. It does not apply the Ottawa rules or order imaging. |
| OT-02 | Documented reduction or cast, splint, or traction application | NICE NG38 1.5.7 | Flags review of neurovascular assessment before and after the intervention and documentation of findings. It does not perform or direct the examination. |

The source directly supports the documented criterion or limitation in each
row. The `suggested_department`, provisional priority, and checklist wording
are ERPilot software fields and must not be read as NICE-assigned triage
categories or autonomous clinical instructions.

## Modifier mapping

Modifiers are evaluated separately from the selected core category. They are
additive review flags with `priority_override: "NONE"` in the current JSON
datasets.

| Modifier ID | Trigger | Applicable categories | Source reference | Implemented action and scope |
| --- | --- | --- | --- | --- |
| PREG-01 | `pregnancy_status_documented_pregnant` | All four core categories | ACOG Committee Opinion 723, imaging statement | Flags clinician review of applicable imaging considerations. It neither prohibits nor mandates imaging and does not change core priority. |
| AC-01 | `anticoagulant_treatment_documented` | Brain trauma only | NICE NG232 1.5.13 | Flags documented anticoagulant treatment for review of applicable head-injury guidance. It does not infer medication use, use drug-specific thresholds, order imaging, or change core priority. |
| OPI-01 | `opioid_intoxication_documented_or_suspected` | Brain trauma only | NICE NG232 1.4.2 | Preserves the context that depressed consciousness should not be attributed to intoxication before important traumatic brain injury is excluded. It does not diagnose intoxication. |
| ALG-01 | `anesthesia_allergy_documented` | All four core categories | NICE CG183 1.2.5 | Flags documented allergy information for visibility and review. It does not make anaesthesia-specific treatment decisions or infer a reaction or contraindication. |

## Evidence and inference translation

The application uses the following software semantics:

- `PRESENT` is explicit submitted evidence that a condition is present.
- `ABSENT` is explicit submitted evidence that a condition is absent.
- `UNKNOWN` is unresolved or missing information.
- Missing keys are observed as `UNKNOWN` by the matcher.
- `FULL_MATCH` means all required conditions are present.
- `PARTIAL_MATCH` means at least one condition is present and at least one
  required condition remains unknown or missing.
- `NO_MATCH` means no required condition is present. An explicit absence is
  retained separately from unknown evidence.
- A modifier fires only when its trigger is `PRESENT` and the selected
  category is in `applies_when_fired`.
- Modifier results are stored under `inference_result["modifiers"]` and do not
  overwrite the core outcome or priority.
- Explanations are generated from the evaluation, including rule ID,
  conditions, match status, and protocol reference.

## Traceability and safe rule changes

To add or update a rule:

1. Add or update the canonical evidence key in `knowledge_base/symptoms.json`.
2. Add exactly the schema fields required by `rule_base/rule_schema.md`.
3. Use a unique stable rule or modifier ID.
4. Record an official source and a recommendation, section, or page where
   available in the JSON `protocol_reference`.
5. Update `knowledge_base/protocols.md` with the source-to-rule limitation.
6. Add tests for valid matching, partial or no-match behavior, unknown versus
   absent evidence, invalid data, explainability, and persistence.
7. Run the complete pytest, JavaScript syntax, and diff checks.

The validator rejects unknown keys, duplicate IDs, invalid categories,
invalid priorities, malformed condition lists, and empty protocol references.
It cannot establish that a source supports the clinical meaning of a rule;
that remains a documentation and review responsibility.

## Known gaps and unresolved mapping defects

The following are deliberately recorded rather than silently corrected:

1. PREG-01 cites the ACOG Committee Opinion and an imaging statement rather
   than a numbered recommendation. The protocol notes explicitly treat this
   as a paraphrase and require current-source verification.
2. The protocol notes preserve historical research-stage wording that
   predates the Stage 7 opioid and anticoagulant implementations. Current
   JSON and Stage 7 sections should be read together.
3. The ACS URL is a source index and is not used as direct evidence for any
   implemented rule.
4. NG39 publication/update metadata and complete population restrictions are
   not recorded in the repository notes. The implementation intentionally
   avoids adding thresholds, diagnoses, treatment instructions, or adult/
   paediatric claims beyond the documented mappings.

No external expert review, clinical validation, accuracy study, sensitivity,
specificity, or real-patient evaluation is documented.
