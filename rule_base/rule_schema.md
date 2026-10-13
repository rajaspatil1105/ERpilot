# ERPilot AI Rule Schema

This document defines the authoritative structure for core rules and
special-condition modifiers. The schemas are data contracts for later JSON
datasets. They are not clinical guidance, and the illustrative values below
are not approved clinical rules.

## 1. Core rule schema

Every core rule must contain exactly these fields:

```json
{
  "rule_id": "NS-04",
  "category": "brain_trauma",
  "conditions": [
    "head_injury",
    "vomiting",
    "loss_of_consciousness"
  ],
  "conclusion": "possible_traumatic_brain_injury",
  "priority_flag": "RED",
  "suggested_department": "Neurosurgery",
  "checklist_action": "Consider appropriate clinical assessment",
  "protocol_reference": "Source title and exact recommendation reference"
}
```

The values in this example are schema examples only. They are not approved
clinical rules and must not be copied into an actual rule dataset without
independent source verification and qualified clinical review.

### 1.1 Field definitions

| Field | Required type and meaning |
| --- | --- |
| `rule_id` | String. A unique, stable identifier for the rule. |
| `category` | String. One of the four allowed core trauma categories. |
| `conditions` | Array of canonical condition-key strings. These are the required conditions for the rule. |
| `conclusion` | String. A software conclusion label; it must not be presented as a diagnosis. |
| `priority_flag` | String. One of the exact allowed uppercase priority values. |
| `suggested_department` | String. A source-supported department suggestion; it must not be invented or treated as an autonomous referral. |
| `checklist_action` | String. A source-supported educational checklist action. It must not be an autonomous treatment instruction. |
| `protocol_reference` | String. A source title plus an exact recommendation, section, or page reference where possible. |

### 1.2 Allowed category values

The `category` field must use exactly one of:

- `brain_trauma`
- `chest_trauma`
- `abdominal_trauma`
- `orthopedic_trauma`

### 1.3 Allowed priority values

The `priority_flag` field must use exactly one of these uppercase values:

- `RED`
- `ORANGE`
- `YELLOW`
- `GREEN`

Priority values must be independently justified by the applicable source and
clinical review. They must not be inferred from the illustrative example.

## 2. Special-condition modifier schema

Every modifier must contain exactly these fields:

```json
{
  "modifier_id": "PREG-01",
  "trigger": "pregnant",
  "applies_when_fired": [
    "abdominal_trauma",
    "chest_trauma"
  ],
  "action": "Flag pregnancy for clinician review of applicable imaging considerations",
  "priority_override": "RED",
  "protocol_reference": "Source title and exact recommendation reference"
}
```

This is a structural example only. The example action and priority override
are not approved clinical instructions and must not be copied into the actual
modifier dataset without independent research and qualified clinical review.

### 2.1 Modifier field definitions

| Field | Required type and meaning |
| --- | --- |
| `modifier_id` | String. A unique, stable identifier for the modifier. |
| `trigger` | String. A canonical special-condition key that activates the modifier. |
| `applies_when_fired` | Array of the exact core category strings to which the modifier may apply. |
| `action` | String. A source-supported educational action or review flag. |
| `priority_override` | String. When an override is used, it must use an allowed uppercase priority value and be source-supported. |
| `protocol_reference` | String. A source title plus an exact recommendation, section, or page reference where possible. |

The modifier schema does not create a new trauma category. A modifier adjusts
the output of applicable core rules and must be researched independently.

## 3. Naming conventions

- All symptom and condition keys use `snake_case`.
- Each canonical key must be defined once in
  `knowledge_base/symptoms.json` in a later stage.
- The identical spelling must be used in symptom definitions, rules,
  modifiers, and inference-engine evidence.
- Rule IDs must be unique and stable.
- Modifier IDs must be unique and stable.
- Core rule categories must use exactly the four allowed category values.
- Priority values must use exactly the allowed uppercase values.
- Every core rule and modifier requires a protocol reference.
- Values must be JSON-compatible.
- Individual rule and modifier objects must not contain arbitrary fields.

## 4. Evidence and matching requirements

- A required condition is satisfied only when its evidence state is `present`.
- Missing or unknown observations must not be treated as confirmed absence.
- An explicit `absent` observation is distinct from an unanswered `unknown`
  observation.
- A core rule can fire only when all of its required conditions are present.
- A partial match may be used to identify genuinely missing follow-up
  information, but it is not a fired rule.
- A no-match outcome must remain explicit when no required condition is
  present.

## 5. Validation requirements

Future loaders and tests must validate at least the following:

1. Every object has exactly the fields specified for its structure.
2. Every required field is present with the expected JSON-compatible type.
3. Rule IDs and modifier IDs are unique within their respective datasets.
4. Core categories and priorities use only the allowed values.
5. Condition and trigger keys follow the canonical vocabulary and
   `snake_case` convention.
6. `applies_when_fired` contains only allowed core categories.
7. Every `protocol_reference` is non-empty and traceable to a source and
   specific recommendation, section, or page where possible.
8. No unresolved or unknown observation is silently converted to absence.
9. Priority overrides and actions are supported by the modifier's independent
   source research.

## 6. Protocol-reference requirements

A protocol reference must identify:

- The source organization and complete title.
- The guideline identifier when available.
- An exact recommendation number, section, or page where possible.
- Enough information for a reviewer to verify the source.

The existence of a protocol reference does not by itself make a rule
clinically valid. Future rule datasets require source verification and
qualified clinical review.
