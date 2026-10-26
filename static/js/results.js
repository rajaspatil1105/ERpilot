(() => {
    "use strict";

    const errorBox = document.getElementById("checklist-error");
    const content = document.getElementById("checklist-content");
    const patientHeading = document.getElementById("checklist-patient");
    const assessmentHeading = document.getElementById("checklist-assessment");
    const itemsContainer = document.getElementById("checklist-items");
    const templateSelect = document.getElementById("task-template");
    const addTaskButton = document.getElementById("add-task");
    const saveButton = document.getElementById("save-checklist");
    const saveStatus = document.getElementById("save-status");
    const reviseEvidence = document.getElementById("revise-evidence");
    const copyCodeButton = document.getElementById("copy-checklist-code");

    if (!errorBox || !content || !patientHeading || !assessmentHeading
        || !itemsContainer || !templateSelect || !addTaskButton
        || !saveButton || !saveStatus || !reviseEvidence || !copyCodeButton) return;

    const guidance = {
        imaging: {
            group: "Tests & imaging",
            title: "CT / X-ray / ultrasound decision",
            details: "If selected by the responsible clinician, record the body region, clinical indication, modality, order/completion time, and result. This prompt does not indicate that imaging is required.",
            source: "NICE NG39, recommendations 1.4.3, 1.4.5 and 1.5.28",
            source_url: "https://www.nice.org.uk/guidance/ng39/chapter/Recommendations",
        },
        "blood-tests": {
            group: "Tests & imaging",
            title: "Clinician-selected blood tests",
            details: "Enter each test selected by the responsible clinician, its indication, collection time, and result. This MVP does not prescribe a standard trauma blood-test panel.",
            source: "Local clinical protocol / responsible clinician",
        },
        "head-imaging": {
            group: "Tests & imaging",
            title: "Head injury imaging decision",
            details: "Record the responsible clinician's imaging decision using the age-specific head-injury criteria and radiology discussion. NICE identifies CT as the primary initial investigation for acute clinically important traumatic brain injury; MRI is not the primary initial test.",
            source: "NICE NG232, recommendations 1.4.8, 1.5.1 and 1.5.2",
            source_url: "https://www.nice.org.uk/guidance/ng232/chapter/recommendations",
        },
        mri: {
            group: "Tests & imaging",
            title: "MRI decision",
            details: "Record the clinician's indication and decision. NICE states MRI is not the primary investigation for acute clinically important traumatic brain injury; use it only when specifically selected for a clinical indication.",
            source: "NICE NG232, recommendations 1.5.1 and 1.5.2",
            source_url: "https://www.nice.org.uk/guidance/ng232/chapter/recommendations",
        },
        "chest-drain": {
            group: "Procedures",
            title: "Chest decompression / chest drain decision",
            details: "Conditional documentation prompt only: for a clinician-suspected tension pneumothorax, record the decision when haemodynamic instability or severe respiratory compromise is present. If selected or performed, follow the current local protocol and record the responsible team and status. This is not a procedure instruction.",
            source: "NICE NG39, recommendations 1.4.1 and 1.4.2",
            source_url: "https://www.nice.org.uk/guidance/ng39/chapter/Recommendations",
        },
        "custom-procedure": {
            group: "Procedures",
            title: "Other clinician-selected procedure / intervention",
            details: "Record the clinician-selected procedure, indication, responsible team, time, and status. Follow local protocol; this prompt does not indicate that a procedure is required.",
            source: "Local clinical protocol",
        },
    };

    let result;
    let items;
    let dirty = false;
    try {
        result = JSON.parse(sessionStorage.getItem("erpilotLastAssessment"));
        if (!result || !Number.isInteger(result.assessment_id)
            || !Number.isInteger(result.patient_id) || !Array.isArray(result.checklist)) {
            throw new Error("No saved assessment checklist is available. Open it from Patient Records.");
        }
        items = result.checklist;
        try {
            const savedDraft = JSON.parse(sessionStorage.getItem("erpilotChecklistDraft"));
            if (savedDraft?.assessment_id === result.assessment_id && Array.isArray(savedDraft.checklist)) {
                items = savedDraft.checklist;
                dirty = true;
                saveStatus.textContent = "Recovered unsaved checklist edits from this browser.";
            }
        } catch (_error) {
            sessionStorage.removeItem("erpilotChecklistDraft");
        }
    } catch (error) {
        errorBox.className = "alert alert-warning";
        errorBox.textContent = error.message || "The checklist could not be loaded.";
        return;
    }

    function addText(parent, tag, value, className = "") {
        const element = document.createElement(tag);
        element.textContent = String(value ?? "");
        if (className) element.className = className;
        parent.appendChild(element);
        return element;
    }

    function renderSource(parent, source, sourceUrl) {
        if (!source) return;
        const line = document.createElement("p");
        line.className = "small text-muted mb-2";
        addText(line, "span", `${source} `);
        if (sourceUrl && /^https?:\/\//i.test(sourceUrl)) {
            const link = addText(line, "a", "Guidance");
            link.href = sourceUrl;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
        }
        parent.appendChild(line);
    }

    function renderItem(item, index) {
        const card = document.createElement("article");
        card.className = "card form-card checklist-task";
        const body = document.createElement("div");
        body.className = "card-body p-3 p-md-4";
        const checkRow = document.createElement("div");
        checkRow.className = "form-check mb-2";
        const label = document.createElement("label");
        label.className = "form-label fw-semibold mb-0";
        label.textContent = item.title;
        const statusSelect = document.createElement("select");
        statusSelect.className = "form-select checklist-status";
        statusSelect.setAttribute("aria-label", `Status for ${item.title}`);
        const statuses = [
            ["not_started", "Not started"],
            ["in_progress", "In progress"],
            ["done", "Done"],
            ["not_applicable", "Not applicable"],
        ];
        statuses.forEach(([value, labelText]) => {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = labelText;
            statusSelect.appendChild(option);
        });
        statusSelect.value = item.status || (item.completed ? "done" : "not_started");
        statusSelect.addEventListener("change", () => {
            item.status = statusSelect.value;
            item.completed = statusSelect.value === "done";
            markUnsaved();
        });
        const statusRow = document.createElement("div");
        statusRow.className = "checklist-status-row";
        statusRow.append(label, statusSelect);
        checkRow.appendChild(statusRow);
        body.appendChild(checkRow);
        if (item.details) addText(body, "p", item.details, "text-muted mb-2");
        if (Array.isArray(item.rule_ids) && item.rule_ids.length) {
            addText(body, "p", `Generated from configured item(s): ${item.rule_ids.join(", ")}`, "small text-muted mb-2");
        }
        if (item.source) renderSource(body, item.source, item.source_url);
        if (Array.isArray(item.sources)) {
            item.sources.forEach((source) => {
                const match = source.match(/https?:\/\/\S+/);
                renderSource(body, source.replace(/https?:\/\/\S+/, "").trim(), match?.[0]);
            });
        }
        const remarkLabel = addText(body, "label", "Remark", "form-label mt-2");
        const remark = document.createElement("textarea");
        remark.className = "form-control checklist-remark";
        remark.rows = 2;
        remark.maxLength = 5000;
        remark.value = item.remark || "";
        remark.id = `task-remark-${index}`;
        remarkLabel.htmlFor = remark.id;
        remark.placeholder = "Add a remark for the patient record";
        remark.addEventListener("input", () => {
            item.remark = remark.value;
            markUnsaved();
        });
        body.appendChild(remark);
        card.appendChild(body);
        return card;
    }

    function render() {
        itemsContainer.replaceChildren();
        const groupOrder = ["Calls & escalation", "Tests & imaging", "Procedures", "Other actions"];
        const groups = new Map();
        items.forEach((item) => {
            const group = item.group || inferGroup(item.title);
            if (!groups.has(group)) groups.set(group, []);
            groups.get(group).push(item);
        });
        const names = [...groups.keys()].sort((a, b) => {
            const ai = groupOrder.indexOf(a);
            const bi = groupOrder.indexOf(b);
            return (ai < 0 ? groupOrder.length : ai) - (bi < 0 ? groupOrder.length : bi) || a.localeCompare(b);
        });
        names.forEach((name) => {
            const section = document.createElement("section");
            section.className = "checklist-group";
            section.setAttribute("aria-label", name);
            addText(section, "h3", name, "h5 mb-3");
            const cards = document.createElement("div");
            cards.className = "d-grid gap-3";
            groups.get(name).forEach((item, index) => cards.appendChild(renderItem(item, index)));
            section.appendChild(cards);
            itemsContainer.appendChild(section);
        });
        patientHeading.textContent = `Checklist for ${result.patient_name || "Patient"}`;
        assessmentHeading.textContent = `Code ${result.patient_code || "—"} · Patient ID ${result.patient_id} · Assessment ${result.assessment_id} · ${result.workflow_mode === "unknown_trauma" ? "Unknown trauma" : (result.selected_category || result.category)}`;
        copyCodeButton.dataset.copyText = result.patient_code || "";
        copyCodeButton.disabled = !result.patient_code;
        content.classList.remove("d-none");
    }

    function inferGroup(title) {
        const normalized = String(title).toLowerCase();
        if (/page|call|escalat|refer/.test(normalized)) return "Calls & escalation";
        if (/procedure|intervention|drain|decompression/.test(normalized)) return "Procedures";
        if (/ct|x-ray|xray|mri|imag|blood|test|scan|investigat/.test(normalized)) return "Tests & imaging";
        return "Other actions";
    }

    function markUnsaved() {
        dirty = true;
        saveStatus.textContent = "Unsaved changes — save to update the patient record.";
        sessionStorage.setItem("erpilotChecklistDraft", JSON.stringify({
            assessment_id: result.assessment_id,
            checklist: items,
        }));
    }

    window.addEventListener("beforeunload", (event) => {
        if (!dirty) return;
        event.preventDefault();
        event.returnValue = "";
    });

    reviseEvidence.addEventListener("click", () => {
        sessionStorage.setItem("erpilotAssessmentDraft", JSON.stringify(result));
    });

    addTaskButton.addEventListener("click", () => {
        const task = guidance[templateSelect.value];
        if (!task) {
            saveStatus.textContent = "Choose a checklist prompt first.";
            return;
        }
        const newItem = {
            id: `manual:${crypto.randomUUID()}`,
            ...task,
            completed: false,
            status: "not_started",
            remark: "",
        };
        if (!items.some((item) => item.id === newItem.id)) items.push(newItem);
        templateSelect.value = "";
        markUnsaved();
        render();
    });

    saveButton.addEventListener("click", async () => {
        saveButton.disabled = true;
        saveButton.textContent = "Saving…";
        saveStatus.textContent = "";
        try {
            const response = await fetch(
                `/api/patients/${result.patient_id}/assessments/${result.assessment_id}/checklist`,
                {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ items }),
                },
            );
            let body;
            try { body = await response.json(); } catch (_error) { body = {}; }
            if (!response.ok) throw new Error(body.error || "Checklist could not be saved.");
            items = body.checklist;
            result.checklist = items;
            sessionStorage.setItem("erpilotLastAssessment", JSON.stringify(result));
            sessionStorage.removeItem("erpilotChecklistDraft");
            dirty = false;
            saveStatus.textContent = "Saved to the patient record.";
            render();
        } catch (error) {
            saveStatus.textContent = error.message || "The checklist service could not be reached.";
        } finally {
            saveButton.disabled = false;
            saveButton.textContent = "Save checklist";
        }
    });

    render();
})();
