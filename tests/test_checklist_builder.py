from checklist_builder import build_checklist


def test_rule_matches_generate_one_task_per_distinct_checklist_action():
    inference = {
        "full_matches": [
            {
                "rule_id": "BT-01",
                "checklist_action": "Review CT head indication.",
                "protocol_reference": "NICE NG232 recommendation 1.5.8",
            },
            {
                "rule_id": "BT-05",
                "checklist_action": "Review CT head indication.",
                "protocol_reference": "NICE NG232 recommendation 1.5.8",
            },
        ],
        "partial_matches": [],
    }

    tasks = build_checklist(inference)
    generated = next(task for task in tasks if task["title"] == "Review CT head indication.")
    assert generated["rule_ids"] == ["BT-01", "BT-05"]
    assert generated["completed"] is False
    assert generated["remark"] == ""


def test_checklist_merge_preserves_completion_remarks_and_manual_tasks():
    inference = {
        "full_matches": [
            {
                "rule_id": "BT-01",
                "checklist_action": "Review CT head indication.",
                "protocol_reference": "NICE NG232",
            }
        ],
        "partial_matches": [],
    }
    old = build_checklist(inference)
    rule_task = next(task for task in old if task["id"].startswith("rule:"))
    rule_task["completed"] = True
    rule_task["status"] = "done"
    rule_task["remark"] = "Imaging reviewed."
    old.append({"id": "manual:task-1", "title": "Local task", "completed": False, "remark": ""})

    merged = build_checklist(inference, old)
    persisted = {task["id"]: task for task in merged}
    assert persisted[rule_task["id"]]["completed"] is True
    assert persisted[rule_task["id"]]["remark"] == "Imaging reviewed."
    assert persisted["manual:task-1"]["title"] == "Local task"
