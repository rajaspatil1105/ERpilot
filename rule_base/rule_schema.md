# Rule Schema — ERPilot AI

This file is the single source of truth for field names, value formats, and
naming conventions across `rule_base/`. Every rule file must match this
exactly. If a rule or modifier needs a field not listed here, update this
file first, then update the rules — never add a field silently in a JSON
file without reflecting it here.

---

## 1. Symptom / condition naming convention

- All symptom and condition keys are `snake_case`.
- Every key used anywhere in `rule_base/` **must** already exist in
  `knowledge_base/symptoms.json`. Do not invent a new key inside a rule file.
- No abbreviations unless the abbreviation itself is the canonical form
  defined in `symptoms.json` (e.g. use `loss_of_consciousness`, not `loc`,
  unless `loc` is explicitly defined as the canonical key).
- Spelling must match exactly, including underscores — `loss_of_consciousness`
  and `lossofconsciousness` are different keys as far as the matcher is
  concerned, and a mismatch means a rule silently never fires.

---

## 2. Core rule object (`rule_base/core/*.json`)

Every rule in a core rule file is an object with exactly these fields, in
this order:

| Field                 | Type            | Notes |
|-----------------------|-----------------|-------|
| `rule_id`              | string          | Unique across the entire project, not just the file. Format: `"<DEPT-CODE>-<NN>"`, e.g. `"NS-04"`. |
| `category`             | string          | One of: `brain_trauma`, `chest_trauma`, `abdominal_trauma`, `orthopedic_trauma`. |
| `conditions`           | array of string | Symptom keys required for this rule to fire. Must all exist in `symptoms.json`. |
| `conclusion`           | string          | Short snake_case label for the suspected injury, e.g. `possible_traumatic_brain_injury`. |
| `priority_flag`        | string          | Exactly one of: `RED`, `ORANGE`, `YELLOW`, `GREEN`. Uppercase, no other casing accepted. |
| `suggested_department` | string          | Human-readable department name, e.g. `"Neurosurgery"`. Must exist in `departments.json`. |
| `checklist_action`     | string          | Phrased as a prompt, not an instruction. E.g. `"Consider immediate CT head, consider neuro consult"` — never `"Order CT head now"`. |
| `protocol_reference`   | string          | Cites the real source this rule is derived from. No rule ships without this. |

### Example

```json
{
  "rule_id": "NS-04",
  "category": "brain_trauma",
  "conditions": ["head_injury", "vomiting", "loss_of_consciousness"],
  "conclusion": "possible_traumatic_brain_injury",
  "priority_flag": "RED",
  "suggested_department": "Neurosurgery",
  "checklist_action": "Consider immediate CT head, consider neuro consult",
  "protocol_reference": "ATLS Primary Survey - Disability (GCS assessment)"
}
```

---

## 3. Special-condition modifier object (`rule_base/special_conditions/*.json`)

Modifiers do **not** classify trauma on their own — they adjust the output
of core rules that already fired. Every modifier has exactly these fields:

| Field                | Type            | Notes |
|-----------------------|-----------------|-------|
| `modifier_id`          | string          | Unique across the project. Format: `"<TAG-NN>"`, e.g. `"PREG-01"`. |
| `trigger`              | string          | The patient flag that activates this modifier. Must exist in the patient flag list (Section 4). |
| `applies_when_fired`   | array of string | List of `category` values this modifier applies to, or `["*"]` if it applies regardless of category. |
| `action`               | string          | Phrased as a prompt, same rule as `checklist_action` above. |
| `priority_override`    | string or null  | One of `RED`, `ORANGE`, `YELLOW`, `GREEN`, or `null` if this modifier doesn't change priority. |
| `protocol_reference`   | string          | Cites the real source. No modifier ships without this. |

### Example

```json
{
  "modifier_id": "PREG-01",
  "trigger": "pregnant",
  "applies_when_fired": ["abdominal_trauma", "chest_trauma"],
  "action": "Avoid standard CT protocol - page OB immediately, assess fetal distress",
  "priority_override": "RED",
  "protocol_reference": "ATLS Special Populations - Pregnant Trauma Patient"
}
```

---

## 4. Patient flag vocabulary (used by `trigger`)

These are the only valid values for a modifier's `trigger` field. Do not
introduce a new trigger value without adding it here first.

| Trigger                  | Meaning |
|---------------------------|---------|
| `pregnant`                 | Patient is pregnant. |
| `on_anticoagulants`        | Patient takes blood-thinning medication (home medication, not administered in ER). |
| `narcotic_intoxication`    | Patient is currently under the influence of narcotics/opioids. |
| `allergy_anesthesia`       | Documented anesthesia allergy on file. |

---

## 5. Priority flag values

Exactly four values, uppercase, no variants:

- `RED` — immediate treatment
- `ORANGE` — very urgent
- `YELLOW` — delayed
- `GREEN` — minor injury

---

## 6. Language rules (applies to `checklist_action` and `action`)

- Always phrased as a prompt or suggestion for staff to consider, never as
  a command or a verdict.
- Correct: `"Consider immediate CT head, consider neuro consult"`
- Incorrect: `"Order CT head now"` / `"Patient has brain trauma"`
- This is not a style preference — it's the difference between a checklist
  tool and a tool that quietly makes clinical decisions. See
  `docs/requirement_analysis.md`.

---

## 7. Checklist before adding any new rule or modifier

- [ ] Every condition/trigger key already exists in `knowledge_base/symptoms.json` or Section 4 above.
- [ ] `rule_id` / `modifier_id` is unique across the whole project, not just this file.
- [ ] `priority_flag` / `priority_override` uses one of the four exact values, uppercase.
- [ ] `checklist_action` / `action` is phrased as a prompt, not a command.
- [ ] `protocol_reference` cites a real, checkable source.
- [ ] No extra fields added beyond what's defined in Section 2 or 3.