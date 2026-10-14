# ERPilot Trauma Rule Coverage Matrix

## 1. Purpose, status, and boundaries

This document is a research and planning artifact for future rule-coverage
work. It is not a clinical protocol, a validation study, or an authorization
to add rules. It records what ERPilot currently represents, which official
sources were checked, which evidence pathways are candidates for later
research, and what information the current schema cannot safely represent.

No production rule IDs, symptom keys, JSON datasets, inference behavior,
routes, templates, JavaScript, models, or tests are changed by this document.
All candidate identifiers in this matrix are research IDs only. They must not
be copied into production rule files without source verification, population
review, qualified clinical review, and regression tests.

ERPilot remains an educational, non-clinically-validated prototype. Its
`RED`, `ORANGE`, `YELLOW`, and `GREEN` values are provisional ERPilot
software-display mappings, not NICE, ACOG, ACR, ABA, or other source-assigned
clinical triage categories. The application must not diagnose, order imaging,
prescribe treatment, determine disposition, or replace clinical judgment.

**Research access date:** 14 October 2026. Source pages can change; every
future implementation must re-check the current source, population, wording,
licence, and update status immediately before deriving a rule.

## 2. Current implementation inventory

### 2.1 Implemented datasets

| Area | Current implementation | Count | Population/scope recorded in the data |
| --- | --- | ---: | --- |
| Brain trauma core rules | `BT-01` through `BT-07` | 7 | Adult head-injury criteria represented from NICE NG232 recommendation 1.5.8; the evidence keys are explicitly adult-prefixed. |
| Chest trauma core rules | `CT-01` | 1 | Documented negative chest eFAST limitation from NICE NG39 recommendation 1.3.3. |
| Abdominal trauma core rules | `AT-01` | 1 | Documented negative FAST limitation from NICE NG39 recommendation 1.5.30. |
| Orthopedic trauma core rules | `OT-01`, `OT-02` | 2 | A suspected knee-fracture imaging-review context and a post-intervention neurovascular-documentation context from NICE NG38. |
| Special-condition modifiers | `PREG-01`, `AC-01`, `OPI-01`, `ALG-01` | 4 | Additive review flags; all have `priority_override: "NONE"`. |
| Canonical evidence vocabulary | `knowledge_base/symptoms.json` | 15 | 11 core keys and 4 special-condition keys. |
| Department catalogue | `knowledge_base/departments.json` | 1 | Emergency Department only. |

The current implementation therefore has **11 core rules**, **4 modifiers**,
and **15 canonical evidence keys**. It does not claim complete coverage of
brain, chest, abdominal, pelvic, spinal, orthopedic, burn, vascular, crush,
facial, penetrating, or paediatric trauma.

### 2.2 Existing rule-to-source inventory

| Research ID | Production ID | Current evidence trigger | Current source reference | Evidence status and boundary |
| --- | --- | --- | --- | --- |
| `IMPL-BR-01` | `BT-01` | Initial emergency-department GCS 12 or less | NICE NG232, 1.5.8 | **Source-backed, adult-only, implementation-limited.** The software flags review of the cited criterion; it does not order CT or establish a diagnosis. |
| `IMPL-BR-02` | `BT-02` | GCS below 15 at two hours | NICE NG232, 1.5.8 | **Source-backed, adult-only, implementation-limited.** Timing and reliable GCS provenance are not fully modeled by the current state-only evidence schema. |
| `IMPL-BR-03` | `BT-03` | Suspected open or depressed skull fracture | NICE NG232, 1.5.8 | **Source-backed, adult-only, implementation-limited.** “Suspected” is clinician-entered evidence; the software does not diagnose a fracture. |
| `IMPL-BR-04` | `BT-04` | Sign of basal skull fracture | NICE NG232, 1.5.8 | **Source-backed, adult-only, implementation-limited.** The sign is not decomposed into a structured finding. |
| `IMPL-BR-05` | `BT-05` | Post-traumatic seizure | NICE NG232, 1.5.8 | **Source-backed, adult-only, implementation-limited.** The event time, witness, and clinical confirmation are not modeled. |
| `IMPL-BR-06` | `BT-06` | Focal neurological deficit | NICE NG232, 1.5.8 | **Source-backed, adult-only, implementation-limited.** The software records supplied evidence only and does not perform a neurological examination. |
| `IMPL-BR-07` | `BT-07` | More than one vomiting episode | NICE NG232, 1.5.8 | **Source-backed, adult-only, implementation-limited.** The current boolean key does not preserve count or timing. |
| `IMPL-CH-01` | `CT-01` | Negative chest eFAST | NICE NG39, 1.3.3 | **Source-backed limitation.** A negative result does not exclude pneumothorax; the rule deliberately does not diagnose pneumothorax or issue an order. |
| `IMPL-AB-01` | `AT-01` | Negative FAST | NICE NG39, 1.5.30 | **Source-backed limitation.** A negative result does not exclude intraperitoneal or retroperitoneal haemorrhage; no haemodynamic threshold is inferred. |
| `IMPL-OR-01` | `OT-01` | Suspected knee fracture in a person over 2 | NICE NG38, 1.2.1 | **Source-backed review context.** The software flags review of whether the Ottawa knee rules indicate an X-ray; it does not apply the rule or order imaging. |
| `IMPL-OR-02` | `OT-02` | Reduction or cast, splint, or traction application | NICE NG38, 1.5.7 | **Source-backed documentation context.** The software flags review of neurovascular assessment/documentation before and after the intervention; it does not perform or direct the examination. |
| `IMPL-MOD-01` | `PREG-01` | Documented pregnancy | ACOG Committee Opinion 723 | **Source-backed review modifier, exact operational wording requires re-check.** It does not prohibit or mandate imaging and does not alter core priority. |
| `IMPL-MOD-02` | `AC-01` | Documented anticoagulant treatment | NICE NG232, 1.5.13 | **Source-backed, brain-trauma-only review modifier.** Medication use is not inferred; no drug-specific threshold, imaging order, or priority override is encoded. |
| `IMPL-MOD-03` | `OPI-01` | Documented or clinician-suspected opioid intoxication | NICE NG232, 1.4.2 | **Source-backed context modifier.** The context is kept visible so depressed consciousness is not attributed to intoxication before important head injury is excluded; intoxication is not diagnosed. |
| `IMPL-MOD-04` | `ALG-01` | Documented anaesthesia allergy status | NICE CG183, 1.2.5 | **Source-backed documentation modifier.** The cited recommendation supports recording drug name, reaction, severity, and date for suspected drug allergy; it does not establish anaesthesia-specific treatment decisions. |

The current rule validator checks field shape, canonical keys, categories,
priorities, IDs, departments, and non-empty traceable references. It cannot
determine whether a clinical claim is supported by its cited source. That
source-to-rule review remains a required human research and clinical-review
step.

## 3. Official source verification log

The links below are the official landing pages or source-owner pages used for
this research pass. A source being listed does not make a proposed rule
approved.

| Source | Official location | Relevant scope checked | Verification result |
| --- | --- | --- | --- |
| NICE, *Head injury: assessment and early management* | [NG232 recommendations](https://www.nice.org.uk/guidance/ng232/chapter/recommendations) | Adult and paediatric head-injury assessment, CT criteria, anticoagulant context, and intoxication context. | **Usable source.** The current repository mappings cite 1.4.2, 1.5.8, and 1.5.13. Adult and under-16 criteria must remain separate. |
| NICE, *Major trauma: assessment and initial management* | [NG39 recommendations](https://www.nice.org.uk/guidance/ng39/chapter/recommendations) | Chest trauma, eFAST, haemorrhage, abdominal/pelvic imaging boundaries, and adult/child distinctions. | **Usable source with narrow mappings.** The current CT-01 and AT-01 limitations are intentionally narrower than a complete trauma pathway. NG39 excludes burns care. |
| NICE, *Fractures (non-complex): assessment and management* | [NG38 recommendations](https://www.nice.org.uk/guidance/ng38/chapter/recommendations) and [scope/context](https://www.nice.org.uk/guidance/ng38/chapter/context) | Non-complex fractures in children and adults, skeletal maturity, imaging, and documentation. | **Usable source with exclusions.** NG38 covers children and adults but excludes skull, spinal, pelvic, and open fractures; skeletal maturity can matter. |
| NICE, *Spinal injury: assessment and initial management* | [NG41 recommendations](https://www.nice.org.uk/guidance/NG41/chapter/recommendations) | Dangerous mechanisms, neurological symptoms, unreliable assessment, and cervical-spine assessment. | **Usable candidate source.** No spinal production rule currently exists. The full adult/child pathway and wording must be modeled before implementation. |
| ACOG, *Guidelines for Diagnostic Imaging During Pregnancy and Lactation*, Committee Opinion 723 | [ACOG Committee Opinion 723](https://www.acog.org/clinical/guidance/committee-opinion/2017/10/guidelines-for-diagnostic-imaging-during-pregnancy-and-lactation) | Imaging considerations during pregnancy and lactation. | **Usable modifier source.** The source is guidance about imaging decisions, not a blanket prohibition or mandate. The exact current document language and update status require re-check. |
| NICE, *Drug allergy: diagnosis and management* | [CG183 recommendations](https://www.nice.org.uk/guidance/cg183/chapter/recommendations) | Information to record for suspected drug allergy. | **Usable narrow source.** Recommendation 1.2.5 supports recording the drug, reaction/symptoms and severity, and date/time where appropriate. It does not support an anaesthesia-specific treatment rule. |
| American Burn Association, *Burn Patient Referral Guidelines* | [ABA referral guidance](https://www.ameriburn.org/burn-care-team/resources/guidelines-for-burn-patient-referral) | Burn-centre consultation/referral framework, including thermal, chemical, electrical, inhalation, paediatric, and anatomic considerations. | **Candidate specialist source.** The page is a source for later research, not a production rule. Population, local service availability, and permission for reuse must be reviewed. |
| American College of Surgeons Trauma Quality Programs | [ACS best-practices index](https://www.facs.org/quality-programs/trauma/quality/best-practices-guidelines/) | Injury-specific best-practice guideline index. | **Source index only.** An individual guideline and exact passage must be selected before it can support a rule. |
| ACR Appropriateness Criteria | [ACR Appropriateness Criteria portal](https://acsearch.acr.org/) | Potential imaging pathways for head, spine, chest, abdomen, pelvis, and extremity trauma. | **Candidate specialist source with reuse restriction.** The exact topic/version and scenario must be selected; redistribution or derivative use requires a permission review. |

### 3.1 Important source paraphrases and non-claims

The following are faithful planning paraphrases, not quotations to copy into
the application:

* NICE NG232 1.5.8 supplies adult head-injury CT criteria including the seven
  criteria represented by BT-01 through BT-07. The implementation maps each
  criterion to a clinician-review flag; it does not turn the rule into an
  autonomous CT order.
* NICE NG232 1.4.2 states that a depressed conscious level should not be
  attributed to intoxication until an important traumatic brain injury has
  been excluded. This supports the narrow context flag in OPI-01, not a
  diagnosis of opioid intoxication.
* NICE NG39 1.3.3 warns that a negative chest eFAST does not exclude
  pneumothorax. NICE NG39 1.5.30 warns that a negative FAST does not exclude
  intraperitoneal or retroperitoneal haemorrhage. These are limitations of
  negative tests, not positive diagnoses.
* NICE NG41 describes a separate spinal-injury assessment pathway. A
  dangerous mechanism or neurological symptom must not be collapsed into the
  current orthopedic category without source and population review.
* ACOG Committee Opinion 723 supports clinical review of imaging choices in
  pregnancy; it does not support a blanket “no imaging” rule.
* NICE CG183 1.2.5 supports documenting suspected drug-allergy details. It
  does not establish that an “anaesthesia allergy” is a specific reaction,
  contraindication, or treatment plan.

## 4. Coverage matrix for future research

The rows below are research work items. “Verified source” means that an
official source and a relevant section or recommendation were located; it
does not mean the row is ready for implementation. “Unresolved” means that
the source, population, data structure, or safe software action is not yet
sufficient.

| Research ID | Domain and population | Candidate question or evidence bundle | Candidate safe software output | Source/status | Main blocker before implementation |
| --- | --- | --- | --- | --- | --- |
| `COV-BR-A01` | Adult brain trauma, 16+ | Preserve the complete NG232 adult CT-criteria set, including criterion timing and evidence provenance. | Explainable review flag with criterion, population, and timing visible. | NICE NG232 1.5.8; **verified source, partially represented**. | Current boolean keys do not encode reliable age, exact time, GCS value, or assessor. |
| `COV-BR-P01` | Paediatric brain trauma, under 16 | Separate the under-16 CT pathway and its risk-factor combinations from adult criteria. | Separate paediatric review workflow; never reuse BT-01–BT-07. | NICE NG232 1.5.9 and related under-16 recommendations; **verified source, not implemented**. | Need child age, risk-factor structure, non-accidental-injury boundary, and clinician-reviewed combinations. |
| `COV-BR-A02` | Adult brain trauma | Loss of consciousness, amnesia, mechanism, and other history that may qualify or modify head-injury assessment. | Ask only targeted questions for unresolved evidence; do not infer absence. | NICE NG232 1.5 and related recommendations; **source located, mapping unresolved**. | Need temporal and event-history data rather than one state per key. |
| `COV-BR-A03` | Adult/paediatric brain trauma | Anticoagulant and antiplatelet treatment, drug class, and medication certainty. | Additive medication-review flag with explicit documented/unknown state. | NICE NG232 1.5.13 and surrounding context; **verified narrow modifier, broader mapping unresolved**. | Current vocabulary cannot distinguish drug class, medication name, dose, last dose, or source of documentation. |
| `COV-BR-A04` | Adult/paediatric brain trauma | Intoxication or reduced consciousness where attribution to intoxication must not obscure head injury. | Context/review flag only; never infer intoxication from GCS, medication, or one symptom. | NICE NG232 1.4.2; **verified narrow modifier**. | Need separate clinician-suspected status, cause attribution, and reliability of examination. |
| `COV-CH-A01` | Adult chest trauma | Haemodynamic instability, suspected chest haemorrhage, and when imaging could delay definitive care. | Review/checklist flag describing an evidence limitation or need for clinician assessment. | NICE NG39 1.3 and related recommendations; **source verified, not implemented**. | Vitals, response to resuscitation, timing, imaging availability, and care setting are not modeled. |
| `COV-CH-P01` | Paediatric chest trauma | Keep paediatric chest-imaging considerations separate from adult criteria. | Population-specific review flag only after age and source criteria are structured. | NICE NG39 1.4.4–1.4.7; **source identified, not implemented**. | Need exact paediatric population and imaging context; no adult/child merge. |
| `COV-CH-A02` | Adult/paediatric chest trauma | Negative eFAST and the limits of a negative result. | Preserve the existing CT-01 limitation and test provenance. | NICE NG39 1.3.3; **verified and implemented narrowly**. | Need test quality, time, operator/team, and body-region result fields for a reliable extension. |
| `COV-AB-A01` | Adult abdominal trauma | Negative FAST and residual haemorrhage uncertainty. | Preserve the existing AT-01 limitation; no diagnosis or automatic disposition. | NICE NG39 1.5.30; **verified and implemented narrowly**. | Need test region, quality, timing, haemodynamic context, and separate pelvic findings. |
| `COV-AB-P01` | Paediatric abdominal trauma | Paediatric abdominal imaging and haemorrhage assessment distinct from adult pathways. | Separate paediatric review workflow. | NICE NG39 relevant child recommendations; **source area identified, mapping unresolved**. | Exact criteria and age band must be extracted and represented without adult assumptions. |
| `COV-PE-A01` | Adult pelvic trauma | Suspected pelvic fracture with instability and major haemorrhage context. | Review/consultation flag, not an autonomous binder, embolisation, surgery, or transfer order. | NICE NG39 section 1.2; **source identified, not implemented**. | Numerical haemodynamics, mechanism, open injury, resources, and treatment authority are outside current schema. |
| `COV-PE-P01` | Paediatric pelvic trauma | Paediatric pelvic injury pathway and age-specific imaging/management boundaries. | Separate paediatric research row and clinician-review output. | NICE NG39 and specialist guidance to be selected; **unresolved**. | No source-specific paediatric mapping has been approved. |
| `COV-SP-A01` | Adult spinal trauma | Dangerous mechanism, spinal pain/tenderness, neurological symptoms, distracting injury, intoxication, and reliable assessment. | Structured spinal-assessment checklist/review flag. | NICE NG41; **verified candidate source, not implemented**. | Current four-category model has no spinal category and cannot represent a reliable exam or immobilisation context. |
| `COV-SP-P01` | Paediatric spinal trauma | Paediatric spinal assessment and cervical-spine criteria distinct from adult rules. | Separate paediatric review workflow. | NICE NG41; **source identified, population mapping unresolved**. | Need exact child criteria and a decision not to fold them into adult orthopedic rules. |
| `COV-OR-A01` | Adult orthopedic trauma | Non-complex extremity fracture imaging, skeletal maturity, and documentation pathways. | Review flag with body site and decision-rule context. | NICE NG38; **verified source, partial implementation**. | NG38 excludes open, pelvic, spinal, skull, and other complex injuries; body site is not a general structured field. |
| `COV-OR-P01` | Paediatric orthopedic trauma | Skeletal maturity and paediatric non-complex fracture pathways. | Separate paediatric review flag; preserve growth-plate context. | NICE NG38 context/recommendations; **verified source, not implemented**. | Current `person_over_2` key is not a substitute for skeletal maturity or a complete child pathway. |
| `COV-OR-A02` | Adult/paediatric orthopedic trauma | Neurovascular status before and after reduction, cast, splint, or traction. | Documentation checklist flag only. | NICE NG38 1.5.7; **verified and implemented narrowly**. | Need structured limb, pulse, sensation, movement, time, and intervention fields; do not infer findings. |
| `COV-BU-A01` | Adult burns | Burn depth, area, anatomy, inhalation, chemical, electrical, and concomitant injury referral context. | Research-only referral/consultation review flag after source and local pathway approval. | ABA Burn Patient Referral Guidelines; **candidate specialist source**. | No burns category exists; exact thresholds, local service rules, licensing, and clinician review are required. |
| `COV-BU-P01` | Paediatric burns | Child-specific burn-centre consultation and safeguarding considerations. | Separate paediatric review workflow. | ABA Burn Patient Referral Guidelines; **candidate specialist source**. | Need a verified child scope, age/weight representation, and non-accidental-injury boundary. |
| `COV-FA-A01` | Adult/paediatric facial trauma | Airway, bleeding, orbital, dental, and associated head/neck injury considerations. | Review flag only after a selected specialty source is verified. | **Unresolved.** NG39 may cover major-trauma airway/bleeding context but is not a complete facial-trauma pathway. | Must select an authoritative specialty source and avoid implying maxillofacial diagnosis or referral. |
| `COV-CR-A01` | Adult/paediatric crush injury | Crush mechanism, compartment/vascular risk, and associated systemic risk. | Evidence-collection/review workflow only. | **Unresolved.** ACS is currently only a source index in this repository. | Need an exact guideline and structured timing, limb, mechanism, and examination data. |
| `COV-VA-A01` | Adult/paediatric vascular extremity trauma | Hard/soft vascular signs and post-intervention documentation. | Review flag only; no vascular diagnosis or procedure instruction. | **Unresolved.** ACR or specialty vascular guidance may be candidates. | Need selected source, population, body-site, pulse/neurology data, and provenance. |
| `COV-PE-N01` | Adult/paediatric penetrating trauma | Penetrating mechanism and body-region-specific assessment. | Source-specific review flag only. | **Unresolved.** NG39 and specialty guidance need separate scope review. | Need a source, mechanism detail, body region, and distinction between suspected and documented injury. |
| `COV-IM-A01` | Adult imaging | Head, cervical spine, chest, abdomen, pelvis, and extremity imaging appropriateness by scenario. | Never an automatic imaging order; at most a source-linked review prompt. | ACR Appropriateness Criteria and NICE pathways; **candidate sources with reuse review**. | Exact topic/version, patient scenario, local policy, and ACR permissions must be resolved. |
| `COV-IM-P01` | Paediatric imaging | Paediatric imaging choices and radiation-sensitive population handling. | Separate source-linked review prompt. | NICE/ACR/ACOG where applicable; **unresolved composite**. | Cannot combine sources or adult pathways; requires modality, age, pregnancy/lactation, and local-policy context. |
| `COV-MOD-A01` | Pregnancy, all trauma categories | Document pregnancy and route imaging decisions to clinician review without a blanket prohibition. | Additive review flag; preserve core result and priority. | ACOG Committee Opinion 723; **verified narrow modifier, implemented**. | Exact source wording/update and modality-specific scope must be rechecked before expansion. |
| `COV-MOD-A02` | Allergy, all trauma categories | Record drug name, reaction/severity, and date/time where appropriate. | Visibility/documentation flag, not a treatment or contraindication decision. | NICE CG183 1.2.5; **verified narrow modifier, implemented**. | Current key is anaesthesia-specific but the source is general drug-allergy documentation; data model should not imply more than the source. |
| `COV-FLOW-A01` | All populations | Follow-up questions for partial matches and unknown evidence. | Ask for one genuinely missing observation, retain `UNKNOWN` until answered. | Software/requirements design; **not a medical rule**. | Current backward chaining reports unknown conditions but there is no question planner or evidence provenance. |

## 5. Adult and paediatric separation policy

The first implementation of brain rules is adult-specific. Future work must not
solve this by adding an age condition to an adult rule and assuming that the
adult recommendation now covers children. The safer design is separate
population-scoped rule sets or explicit population metadata with validator
checks that prevent a rule from matching outside its supported population.

At minimum, future population context should distinguish:

* adult (16 years and over) versus child/young person (under 16), where the
  source uses that boundary;
* age in years and months where the source requires it;
* skeletal maturity where an orthopedic recommendation depends on growth-plate
  status;
* pregnancy and lactation where the source makes those contexts relevant;
* care setting and timing, such as pre-hospital, emergency department,
  initial assessment, two hours after injury, or post-procedure;
* suspected, documented, measured, and clinician-verified evidence.

If a source does not clearly support a population, the row remains unresolved.
No adult threshold, imaging criterion, referral rule, or treatment wording may
be generalized to children.

## 6. Candidate evidence vocabulary and structured data

These are design proposals, not additions to `knowledge_base/symptoms.json`.
The current vocabulary remains unchanged until a future implementation task is
approved.

### 6.1 Candidate evidence groups

| Group | Candidate fields (research names only) | Why the current state-only key is insufficient |
| --- | --- | --- |
| Population | `age_years`, `age_months`, `population_band`, `skeletal_maturity`, `pregnancy_status`, `lactation_status` | A single `PRESENT` state cannot prove age boundaries, maturity, or the relevant pregnancy context. |
| Event timing | `injury_time`, `arrival_time`, `assessment_time`, `procedure_time`, `time_since_injury` | NG232 and post-intervention checks contain timing; a boolean key loses it. |
| Neurology | `gcs_value`, `gcs_time`, `gcs_assessor`, `loss_of_consciousness`, `amnesia`, `seizure_event`, `focal_deficit` | Numeric, temporal, witnessed, and assessor-provenance data cannot be safely reduced to one state. |
| Mechanism | `mechanism_type`, `fall_height`, `axial_load`, `vehicle_collision_context`, `penetrating_mechanism`, `crush_mechanism` | Thresholds and mechanism subtypes require structured values and units; missing detail must remain unknown. |
| Examination | `skull_fracture_sign`, `spinal_tenderness`, `neurological_sign`, `limb_motor`, `limb_sensation`, `limb_pulse` | “Present” must identify the finding and body site; the application cannot perform the examination. |
| Tests | `test_name`, `test_result`, `test_region`, `test_time`, `test_operator`, `test_quality`, `test_source` | CT, FAST, and eFAST findings need provenance and region; a negative test is not a universal negative injury finding. |
| Vitals/resuscitation | `heart_rate`, `blood_pressure`, `respiratory_rate`, `oxygenation`, `perfusion_finding`, `resuscitation_response` | Current rule files intentionally avoid thresholds; future thresholds require units, timing, repeated values, and source review. |
| Procedures | `procedure_type`, `body_site`, `pre_procedure_exam`, `post_procedure_exam`, `findings_documented` | OT-02 is a context flag, not a procedure instruction; before/after documentation needs separate records. |
| Medication | `medication_name`, `medication_class`, `last_dose_time`, `medication_source`, `medication_status` | AC-01 must not infer anticoagulant use from symptoms or an incomplete medication field. |
| Allergy | `allergen_name`, `reaction_description`, `reaction_severity`, `reaction_date`, `allergy_source`, `allergy_status` | CG183 1.2.5 calls for details; `anesthesia_allergy_documented` alone cannot represent them. |
| Burns | `burn_mechanism`, `burn_depth`, `burn_area`, `burn_anatomical_site`, `inhalation_concern`, `chemical_agent`, `electrical_voltage` | A burns pathway requires population, anatomy, mechanism, severity, and local referral context. |
| Provenance | `evidence_state`, `observed_value`, `unit`, `observed_at`, `recorded_by`, `source_type`, `uncertainty_reason` | The current `PRESENT`/`ABSENT`/`UNKNOWN` contract is correct but too small for audit-grade clinical context. |

### 6.2 Proposed observation model (not implemented)

A future evidence record should be considered as a typed observation rather
than only a string-to-state mapping:

```text
Observation
  key: canonical candidate key
  state: PRESENT | ABSENT | UNKNOWN
  value: optional typed value
  unit: optional unit
  observed_at: optional timestamp
  source: patient report | clinician | measured | investigation | record
  population_context: adult | child | unknown
  uncertainty_reason: optional reason
```

Rules should declare the population, timing, value constraints, and source
requirements they need. The validator should reject a rule that silently uses a
value or population outside that declaration. This is a future schema
extension, not a design change made in this stage.

## 7. Inference and workflow blueprint

### 7.1 Current behavior to preserve

1. The selected category loads its own core rule dataset.
2. Forward chaining evaluates every supplied rule and preserves every
   `FULL_MATCH`, `PARTIAL_MATCH`, and `NO_MATCH`.
3. A required condition is satisfied only by explicit `PRESENT`.
4. Explicit `ABSENT` remains distinct from missing or `UNKNOWN`.
5. Modifiers are evaluated separately, only for their applicable categories,
   and may coexist with one another.
6. Modifier results do not overwrite core outcomes or priorities.
7. Explanations contain the rule/modifier ID, matched or unresolved
   conditions, and protocol reference.
8. An explicit no-match result is retained when no rule fires; it is not a
   diagnosis of absence.

### 7.2 Proposed future workflow

| Step | Future behavior | Safety/traceability requirement |
| --- | --- | --- |
| 1. Intake | Collect patient population, category, setting, time, and evidence source. | Block or visibly mark population/context that is unknown; do not assume adult. |
| 2. Evidence normalization | Convert submitted observations into typed records while retaining raw provenance. | Reject malformed values; preserve `UNKNOWN` and an uncertainty reason. |
| 3. Scope gate | Select only rules whose category, population, timing, and source requirements apply. | Do not evaluate adult rules for children or a procedure rule without procedure context. |
| 4. Forward evaluation | Evaluate all in-scope core rules and then all applicable modifiers. | Preserve ordering, all matches, no-match results, and additive modifier results. |
| 5. Backward evaluation | For a selected software conclusion, list exact candidate rules and missing conditions. | A missing condition creates a question candidate, not a positive finding. |
| 6. Follow-up planner | Ask the smallest useful question for a genuinely unknown condition. | Never ask a leading question that converts uncertainty to absence; record answer provenance. |
| 7. Explanation | Render evidence, match state, rule ID, source reference, and limitation. | Use source-faithful paraphrase or licensed exact wording; distinguish software flag from clinical action. |
| 8. Review handoff | Show clinician-review/checklist flags and unresolved conflicts. | No automatic order, diagnosis, referral, treatment, or disposition. |
| 9. Persistence/report | Store the complete evidence and evaluation snapshot. | Preserve source, timestamp, population, unknown status, and the exact rule dataset version. |

### 7.3 Conflicts and multiple matches

The engine should continue to report all applicable matches. It should not
silently pick a “highest” clinical result, suppress a conflicting rule, or
allow a modifier to rewrite a core conclusion. If future sources conflict,
the report should identify the conflict and require qualified review.

## 8. Imaging, procedure, department, and referral boundaries

### 8.1 Imaging

Current CT-01, AT-01, BT-01–BT-07, and OT-01 are intentionally review or
limitation flags. They do not issue imaging orders. A future imaging row must
record at least the population, body region, mechanism/findings, timing,
clinical setting, and the exact source scenario. It must also distinguish:

* “a negative test does not exclude an injury” from “an injury is present”;
* “review whether a source criterion applies” from “order a modality”;
* adult from paediatric criteria;
* local policy and resource availability from source guidance.

### 8.2 Procedures and examination

OT-02 is a documentation reminder around an intervention. It must not become
an instruction to reduce, cast, splint, apply traction, immobilize, or perform
a neurovascular examination autonomously. A future procedure workflow needs
explicit before/after observations and a clinician-entered record.

### 8.3 Departments

The current single department, Emergency Department, is a software catalogue
value. It is not a referral decision. Future department metadata would need
local service configuration, availability, escalation ownership, and a clear
“review only” presentation. No source in this matrix authorizes ERPilot to
select or contact a clinical service automatically.

### 8.4 Referral and disposition

Burn-centre, major-trauma-centre, surgery, interventional-radiology,
neurosurgery, orthopedic, vascular, and other referral pathways require an
exact source and local operational policy. A guideline landing page or source
index is not enough. Until then, candidate rows may produce only a
source-linked review prompt and must not set an automatic destination,
transfer, admission, discharge, or treatment disposition.

## 9. Priority and safety mapping

The matrix deliberately separates:

1. **Evidence status:** what was explicitly supplied or remains unknown.
2. **Rule match status:** `FULL_MATCH`, `PARTIAL_MATCH`, or `NO_MATCH`.
3. **Clinical-source scope:** what the cited guidance actually discusses.
4. **ERPilot display priority:** a provisional software mapping.

No future row may use a source recommendation number as if it were a
validated ERPilot priority. Any provisional display mapping must be documented
as an ERPilot mapping and tested so that it cannot overwrite core outcomes or
be changed by a modifier unless a separately reviewed software requirement
explicitly permits it.

## 10. Source-use and licensing notes

Source content should be represented primarily by citation, a short
source-faithful paraphrase, and a link. Do not copy full guideline sections
into JSON, reports, or UI without permission.

* NICE publishes a UK Open Content Licence and separate international-use
  information. NICE recommendations and substantial algorithms have
  attribution and wording/structure constraints; the applicable licence and
  jurisdiction must be checked before redistributing or adapting content.
  See [NICE UK open content licence](https://www.nice.org.uk/reusing-our-content/nice-uk-open-content-licence)
  and [international use of NICE content](https://www.nice.org.uk/reusing-our-content/use-of-our-content-internationally).
* ACOG states that its publications are copyrighted and that reproduction
  generally requires permission, subject to its stated limited exceptions.
  See [ACOG permissions](https://www.acog.org/womens-health/about-acog/permissions).
* ACR Appropriateness Criteria materials require a topic/version review and
  a permission review before copying, modifying, or redistributing criteria.
  See the [ACR Appropriateness Criteria portal](https://acsearch.acr.org/).
* ABA guidance must be checked for its current copyright, attribution,
  redistribution, and local-use terms before it is copied into a product.

This matrix does not provide legal advice. A future release intended for
distribution outside a private research workspace needs a documented
source-use decision for every reproduced or adapted passage.

## 11. Prioritized gap analysis

### Priority 0 — safety and scope gates

1. Add a population/context gate before any adult rule is considered for a
   child or a skeletal-immaturity-dependent orthopedic pathway.
2. Preserve `UNKNOWN` and reject malformed evidence; never default unknown
   medication, allergy, pregnancy, intoxication, test quality, or vital status
   to `ABSENT`.
3. Keep source-supported review flags separate from diagnoses, orders,
   treatment, referrals, and disposition.
4. Preserve complete provenance and the exact rule/source version used for a
   persisted result.

### Priority 1 — high-value missing pathways

1. Research and model paediatric head injury separately from adult NG232
   criteria.
2. Research spinal injury using NG41, including reliable-assessment and
   neurological-symptom context, without folding it into orthopedic trauma.
3. Extend chest, abdominal, and pelvic trauma research only after timing,
   haemodynamic context, test provenance, and adult/child scope are
   representable.
4. Formalize typed medication, allergy, pregnancy, and intoxication evidence
   without broadening the current conservative modifiers.

### Priority 2 — specialty domains

1. Select exact authoritative sources for burns, facial trauma, crush injury,
   penetrating trauma, and vascular extremity trauma.
2. Establish local referral/service boundaries before any department or
   referral output is considered.
3. Decide whether ACR content can be used under the intended distribution
   model before deriving imaging rules.

### Priority 3 — workflow and completeness

1. Implement a backward-chaining question planner that asks only about
   genuinely unknown conditions.
2. Add rule-version and source-version metadata to persistence and reports.
3. Add a source-change review process and revalidate all mappings when a
   guideline is updated or withdrawn.

## 12. Required future validator and test extensions

Future implementation work should add tests without weakening the existing
suite. At minimum:

* **Population isolation:** adult rules do not fire for paediatric evidence;
  paediatric rules do not fire without their own source-backed criteria.
* **Timing and value validation:** GCS, age, mechanism, vital, test, and
  procedure observations require valid types, units, ranges where supported,
  and timestamps where the source requires them.
* **Provenance:** measured, documented, clinician-suspected, patient-reported,
  and inferred values remain distinguishable; unsupported inference is rejected.
* **Unknown semantics:** missing, malformed, and unresolved observations stay
  `UNKNOWN` or produce an explicit validation error; they never become
  `ABSENT`.
* **Scope gating:** a rule is not evaluated outside its category, population,
  setting, timing, or procedure applicability.
* **Modifier coexistence:** pregnancy, anticoagulant, opioid, and allergy
  modifiers can coexist, remain additive, and preserve core result and
  priority.
* **Negative-test limitations:** CT-01 and AT-01 continue to report a
  limitation rather than a positive diagnosis.
* **Explainability:** every fired rule includes its stable ID, matched
  conditions, population/context, protocol reference, and software-only
  limitation.
* **Source traceability:** every production row has a source-owner URL and
  exact recommendation, section, page, or version; source-index-only entries
  fail validation until narrowed.
* **Persistence/reporting:** the stored result includes the evidence snapshot,
  unknown reasons, source/rule version, all core matches, all modifiers, and
  the same no-match semantics shown in the UI.
* **Regression:** all Stage 0–9 tests remain green, including route isolation,
  report access control, frontend payload separation, and the AC-01
  NG232 1.5.13 consistency test.

## 13. Decision checklist before the next implementation stage

Do not implement a candidate row until all answers below are documented:

1. Is the source current, official, and specific to the proposed population?
2. Is the exact recommendation, section, page, or version recorded?
3. Does the source support the trigger, conclusion wording, and checklist
   action separately?
4. Is the proposed output a review/checklist flag rather than an unsupported
   diagnosis, order, treatment, referral, or disposition?
5. Can the evidence be recorded with the required value, timing, population,
   provenance, and uncertainty information?
6. Are adult, paediatric, pregnancy, lactation, skeletal-maturity, and care
   setting boundaries explicit?
7. Can `PRESENT`, `ABSENT`, and `UNKNOWN` be tested independently?
8. Can every result be explained and persisted without losing source context?
9. Are source licensing and attribution requirements satisfied for the
   intended distribution?
10. Has a qualified clinician reviewed the proposed mapping and its limits?

Until these questions are answered, the row should remain a research gap in
this matrix rather than become a production rule.

