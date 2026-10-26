"""Build simple, source-linked MVP checklist tasks from configured rules."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any


BASE_TASKS = (
    {
        "id": "base:escalation",
        "group": "Calls & escalation",
        "title": "Escalation / page, if indicated",
        "details": (
            "Follow the local written trauma response pathway. Record the "
            "service or senior clinician contacted, whom you spoke with, "
            "time, and response."
        ),
        "source": "NICE NG40, recommendation 1.3.3",
        "source_url": "https://www.nice.org.uk/guidance/ng40/chapter/recommendations",
    },
    {
        "id": "base:investigations",
        "group": "Tests & imaging",
        "title": "Clinician-selected tests, if indicated",
        "details": (
            "Record each clinician-selected CT, X-ray, ultrasound, or blood "
            "test, the indication, order/completion status, and result. This "
            "prompt does not select or order a test."
        ),
        "source": "NICE NG39, recommendations 1.4.3 and 1.5.28",
        "source_url": "https://www.nice.org.uk/guidance/ng39/chapter/Recommendations",
    },
    {
        "id": "base:procedure",
        "group": "Procedures",
        "title": "Clinician-selected procedure / intervention, if indicated",
        "details": (
            "Record the clinician's decision, procedure, responsible team, "
            "time, and status. Follow local protocols; this prompt is not an "
            "instruction to perform a procedure."
        ),
        "source": "NICE NG39, recommendations 1.4.1 and 1.4.2",
        "source_url": "https://www.nice.org.uk/guidance/ng39/chapter/Recommendations",
    },
)


def build_checklist(
    inference_result: Mapping[str, Any],
    existing: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Create generated tasks and preserve previously recorded completion/notes."""

    generated: list[dict[str, Any]] = []
    generated.extend(_task(task) for task in BASE_TASKS)

    actions: dict[str, dict[str, Any]] = {}
    for status_field in ("full_matches", "partial_matches"):
        evaluations = inference_result.get(status_field, [])
        if not isinstance(evaluations, list):
            continue
        for evaluation in evaluations:
            if not isinstance(evaluation, Mapping):
                continue
            action = evaluation.get("checklist_action")
            if not isinstance(action, str) or not action.strip():
                continue
            task = actions.setdefault(
                action,
                {
                    "id": "rule:" + hashlib.sha1(action.encode("utf-8")).hexdigest()[:16],
                    "group": _action_group(action),
                    "title": action.strip(),
                    "details": "",
                    "rule_ids": [],
                    "sources": [],
                    "completed": False,
                    "remark": "",
                },
            )
            rule_id = evaluation.get("rule_id")
            if isinstance(rule_id, str) and rule_id not in task["rule_ids"]:
                task["rule_ids"].append(rule_id)
            reference = evaluation.get("protocol_reference")
            if isinstance(reference, str) and reference and reference not in task["sources"]:
                task["sources"].append(reference)
    generated.extend(actions.values())

    previous_by_id = {
        item.get("id"): item
        for item in (existing or [])
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    }
    merged = []
    emitted: set[str] = set()
    for task in generated:
        previous = previous_by_id.get(task["id"], {})
        previous_status = previous.get("status")
        status = (
            "done"
            if previous.get("completed") is True
            else previous_status
            if previous_status in {"not_started", "in_progress", "done", "not_applicable"}
            else "not_started"
        )
        merged.append({
            **task,
            "completed": status == "done",
            "remark": previous.get("remark", task["remark"]),
            "status": status,
        })
        emitted.add(task["id"])
    for item in existing or []:
        if not isinstance(item, Mapping):
            continue
        item_id = item.get("id")
        if isinstance(item_id, str) and item_id not in emitted:
            merged.append(dict(item))
            emitted.add(item_id)
    return merged


def _task(template: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **template,
        "completed": False,
        "status": "not_started",
        "remark": "",
    }


def _action_group(action: str) -> str:
    normalized = action.casefold()
    if any(word in normalized for word in ("page", "call", "escalat", "refer")):
        return "Calls & escalation"
    if any(word in normalized for word in ("procedure", "intervention", "drain", "decompression")):
        return "Procedures"
    if any(word in normalized for word in ("ct", "x-ray", "xray", "mri", "image", "blood", "test", "scan", "investigat")):
        return "Tests & imaging"
    return "Other actions"
