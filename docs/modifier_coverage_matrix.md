# Special-condition modifier coverage matrix

This matrix records the behavior in the current modifier JSON, schema, matcher,
routes, and UI. These modifiers add clinician-review context; they do not
replace the core trauma outcome. No clinical effects beyond the configured
actions below are inferred here.

| ID | Evidence trigger | Applicable categories | Configured action | Core matching / priority / follow-up effect | Verification |
| --- | --- | --- | --- | --- | --- |
| PREG-01 | `pregnancy_status_documented_pregnant` = PRESENT | Brain, chest, abdominal, orthopedic trauma | Flag documented pregnancy for clinician review of applicable imaging considerations; pregnancy alone does not prohibit necessary imaging. | No core-rule or priority change (`NONE`); no follow-up rule is added. It appears as a separate modifier result and checklist item when fired. | API fires independently and in combinations; browser result and checklist coverage is included in the modifier follow-up workflow. Full category-by-category scope is verified by tests. |
| AC-01 | `anticoagulant_treatment_documented` = PRESENT | Brain trauma | Flag documented anticoagulant treatment for clinician review of applicable head-injury guidance. | No core-rule or priority change (`NONE`); no follow-up rule is added. | API state, source, brain-only scope, combinations, and persistence tested. |
| OPI-01 | `opioid_intoxication_documented_or_suspected` = PRESENT | Brain trauma | Flag documented or suspected opioid intoxication for clinician review in the described head-injury context. | No core-rule or priority change (`NONE`); no follow-up rule is added. | API state, brain-only scope, combinations, and persistence tested. |
| ALG-01 | `anesthesia_allergy_documented` = PRESENT | Brain, chest, abdominal, orthopedic trauma | Flag documented anaesthesia allergy for clinician review; keep it separate from other adverse drug reactions and infer no specific reaction or contraindication. | No core-rule or priority change (`NONE`); no follow-up rule is added. | API state, combination, persistence, browser result/checklist, and follow-up retention tested. |

## Evaluation and combination behavior

- Only modifiers applicable to the assessment category are evaluated.
- PRESENT fires only the matching trigger. ABSENT, UNKNOWN, and omitted evidence
  do not fire a modifier. The response preserves submitted evidence; omitted
  and explicit UNKNOWN states remain distinguishable there, although both are
  summarized as `unknown or missing` in each modifier's prose explanation.
- The matcher builds modifier evaluations separately from core inference. The
  route attaches these results after core evaluation and repeats this process
  after a follow-up answer using the assessment's persisted modifier evidence.
- The current specification defines the modifiers as additive review items,
  with `priority_override: NONE`; it does not define interactions that change
  rule matching, applicability, follow-up questions, or core outcomes.
- Multiple fired modifiers produce separate result cards and review checklist
  entries. The implementation does not deduplicate different modifier IDs;
  same-ID data is rejected by modifier-file validation.

## Coverage gaps and ambiguities

- The initial test suite covered each trigger's positive match but not every
  category's complete scope, all combinations, order invariance, omitted
  evidence, or UI retention across a follow-up. Those gaps are addressed by
  the Stage 7 regression tests.
- UNKNOWN and omitted evidence share the same explanation wording. Structured
  submitted evidence differentiates them, so no behavioral defect is
  established; a more specific prose distinction is not specified.
- ALG-01 is keyed to an anaesthesia-specific allergy status while its configured
  NICE CG183 reference describes general drug-allergy recording. The project
  does not resolve whether that source supports this narrower trigger/action;
  this audit preserves the existing text and does not broaden the clinical
  claim.
- The project documents no additional clinical interaction among modifiers.
  Combination checks therefore verify additive display and unchanged core
  behavior only, not an invented combined recommendation.
