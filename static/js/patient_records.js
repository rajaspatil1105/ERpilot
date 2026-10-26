(() => {
    "use strict";

    const search = document.getElementById("patient-search");
    const searchStatus = document.getElementById("patient-search-status");
    const searchResults = document.getElementById("patient-search-results");
    const recordPanel = document.getElementById("patient-record");
    if (!search || !searchStatus || !searchResults || !recordPanel) return;

    function addText(parent, tag, value, className = "") {
        const element = document.createElement(tag);
        element.textContent = String(value ?? "");
        if (className) element.className = className;
        parent.appendChild(element);
        return element;
    }

    async function getJson(url) {
        const response = await fetch(url);
        let body;
        try { body = await response.json(); } catch (_error) { body = {}; }
        if (!response.ok) throw new Error(body.error || "Patient records could not be loaded.");
        return body;
    }

    function renderSearchResults(patients) {
        searchResults.replaceChildren();
        if (!patients.length) {
            addText(searchResults, "p", "No matching patients found.", "text-muted");
            return;
        }
        patients.forEach((patient) => {
            const row = document.createElement("div");
            row.className = "list-group-item d-flex justify-content-between align-items-center gap-3";
            const text = document.createElement("div");
            addText(text, "strong", patient.name, "d-block");
            addText(text, "span", `Code ${patient.patient_code} · Patient ID ${patient.id} · ${patient.age} · ${patient.assessment_count} assessment(s)`, "small text-muted");
            const button = document.createElement("button");
            button.className = "btn btn-sm btn-primary";
            button.type = "button";
            button.textContent = "View record";
            button.addEventListener("click", () => loadRecord(patient.id));
            row.append(text, button);
            searchResults.appendChild(row);
        });
    }

    function renderAssessment(patient, assessment) {
        const article = document.createElement("article");
        article.className = "card form-card mb-3";
        const body = document.createElement("div");
        body.className = "card-body";
        addText(body, "h3", `Assessment ${assessment.assessment_id}`, "h5");
        const doneCount = assessment.checklist.filter((item) => item.status === "done" || item.completed).length;
        const totalCount = assessment.checklist.length;
        addText(body, "p", `${new Date(assessment.created_at).toLocaleString()} · ${assessment.category} · ${assessment.workflow_mode === "unknown_trauma" ? "Unknown Trauma" : "Known category"} · ${doneCount}/${totalCount} done`, "small text-muted");
        if (!assessment.checklist.length) {
            addText(body, "p", "No checklist items were saved.", "text-muted");
        }
        const list = document.createElement("ul");
        for (const item of assessment.checklist) {
            const line = document.createElement("li");
            const stateLabel = ({ done: "Done", in_progress: "In progress", not_applicable: "Not applicable", not_started: "Not started" })[item.status] || (item.completed ? "Done" : "Not started");
            addText(line, "strong", `${stateLabel}: ${item.title}`);
            if (item.remark) addText(line, "p", `Remark: ${item.remark}`, "mb-1");
            list.appendChild(line);
        }
        body.appendChild(list);
        const open = document.createElement("button");
        open.type = "button";
        open.className = "btn btn-outline-primary";
        open.textContent = "Open checklist";
        open.addEventListener("click", () => {
            sessionStorage.setItem("erpilotPatient", JSON.stringify(patient));
            sessionStorage.setItem("erpilotLastAssessment", JSON.stringify({
                assessment_id: assessment.assessment_id,
                patient_id: patient.id,
                patient_name: patient.name,
                patient_code: patient.patient_code,
                workflow_mode: assessment.workflow_mode,
                category: assessment.category,
                selected_category: assessment.category === "Unknown trauma" ? null : assessment.category,
                evidence: assessment.evidence,
                modifier_evidence: assessment.modifier_evidence,
                vitals: assessment.vitals,
                checklist: assessment.checklist,
            }));
            window.location.assign("/results");
        });
        body.appendChild(open);
        article.appendChild(body);
        return article;
    }

    async function loadRecord(patientId) {
        recordPanel.replaceChildren();
        recordPanel.classList.remove("d-none");
        addText(recordPanel, "p", "Loading patient record…", "text-muted");
        try {
            const record = await getJson(`/api/patients/${patientId}/records`);
            recordPanel.replaceChildren();
            const recordHeader = document.createElement("div");
            recordHeader.className = "record-heading mb-3";
            const identity = document.createElement("div");
            addText(identity, "h2", record.patient.name, "h3 mb-1");
            addText(identity, "p", `Code ${record.patient.patient_code} · Patient ID ${record.patient.id} · Age ${record.patient.age} · ${record.patient.gender} · ${record.patient.incident_type}`, "text-muted mb-0");
            const copyButton = document.createElement("button");
            copyButton.type = "button";
            copyButton.className = "btn btn-outline-success";
            copyButton.textContent = "Copy patient code";
            copyButton.dataset.copyText = record.patient.patient_code;
            copyButton.dataset.copyStatus = "patient-search-status";
            recordHeader.append(identity, copyButton);
            recordPanel.appendChild(recordHeader);
            if (!record.assessments.length) addText(recordPanel, "p", "No assessments are saved for this patient.", "text-muted");
            record.assessments.forEach((assessment) => recordPanel.appendChild(renderAssessment(record.patient, assessment)));
        } catch (error) {
            recordPanel.replaceChildren();
            addText(recordPanel, "p", error.message, "alert alert-danger");
        }
    }

    let timer;
    search.addEventListener("input", () => {
        clearTimeout(timer);
        const query = search.value.trim();
        searchResults.replaceChildren();
        recordPanel.replaceChildren();
        recordPanel.classList.add("d-none");
        if (query.length < 2) {
            searchStatus.textContent = "Enter at least 2 characters to search.";
            return;
        }
        searchStatus.textContent = "Searching…";
        timer = setTimeout(async () => {
            try {
                const response = await getJson(`/api/patients?search=${encodeURIComponent(query)}`);
                renderSearchResults(response.patients);
                searchStatus.textContent = `${response.patients.length} result(s)`;
            } catch (error) {
                searchStatus.textContent = error.message;
            }
        }, 220);
    });
})();
