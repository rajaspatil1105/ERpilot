(() => {
    "use strict";

    const form = document.getElementById("assessment-form");
    const status = document.getElementById("assessment-status");
    const patientContext = document.getElementById("patient-context");
    const symptomData = document.getElementById("symptom-data");
    const categorySelect = document.getElementById("category");
    const evidenceCount = document.getElementById("evidence-count");
    const vitalsList = document.getElementById("vitals-list");
    const addVitalButton = document.getElementById("add-vital");
    const submitButton = document.getElementById("submit-assessment");
    const states = {};

    if (
        !form
        || !status
        || !patientContext
        || !symptomData
        || !categorySelect
        || !evidenceCount
        || !vitalsList
        || !addVitalButton
        || !submitButton
    ) {
        return;
    }

    let symptoms;
    try {
        symptoms = JSON.parse(symptomData.textContent);
        if (
            !Array.isArray(symptoms)
            || symptoms.some((symptom) => (
                !symptom
                || typeof symptom.key !== "string"
                || typeof symptom.category !== "string"
            ))
        ) {
            throw new Error("The symptom data is not a valid list.");
        }
    } catch (_error) {
        showStatus("The canonical symptom data could not be loaded.", "danger");
        return;
    }

    const symptomCategories = new Map(
        symptoms.map((symptom) => [symptom.key, symptom.category]),
    );
    for (const symptom of symptoms) {
        states[symptom.key] = "UNKNOWN";
    }

    const supportedCategories = new Set(
        [...categorySelect.options]
            .filter((option) => !option.disabled)
            .map((option) => option.value),
    );
    if (!supportedCategories.has(categorySelect.value)) {
        const firstSupported = [...supportedCategories][0];
        if (firstSupported) {
            categorySelect.value = firstSupported;
        }
    }

    let vitalCounter = 0;
    let isSubmitting = false;

    function showStatus(message, kind) {
        status.className = `alert alert-${kind}`;
        status.textContent = message;
    }

    function readableState(state) {
        return {
            PRESENT: "Yes",
            ABSENT: "No",
            UNKNOWN: "Unknown",
        }[state] || "Unknown";
    }

    function getPatient() {
        try {
            return JSON.parse(sessionStorage.getItem("erpilotPatient"));
        } catch (_error) {
            return null;
        }
    }

    function updateCategoryVisibility() {
        const category = categorySelect.value;
        document.querySelectorAll(".symptom-category-panel").forEach((panel) => {
            const visible = panel.dataset.category === category;
            panel.hidden = !visible;
        });
        updateCount();
    }

    function relevantKeys() {
        const category = categorySelect.value;
        return symptoms
            .filter((symptom) => (
                symptom.category === category
                || symptom.category === "special_condition"
            ))
            .map((symptom) => symptom.key);
    }

    function updateCount() {
        const keys = relevantKeys();
        const answered = keys.filter((key) => states[key] !== "UNKNOWN").length;
        const remaining = keys.length - answered;
        evidenceCount.textContent = (
            `Answered: ${answered} | Remaining: ${remaining}`
        );
    }

    function updateState(key, state, clickedButton) {
        states[key] = state;
        const card = document.querySelector(
            `.symptom-card[data-symptom-key="${CSS.escape(key)}"]`,
        );
        if (!card) {
            return;
        }
        card.querySelectorAll(".state-button").forEach((button) => {
            const selected = button === clickedButton;
            button.classList.toggle("state-selected", selected);
            button.setAttribute("aria-pressed", String(selected));
        });
        const statusText = card.querySelector(".evidence-status");
        if (statusText) {
            statusText.textContent = `Recorded state: ${readableState(state)}`;
        }
        updateCount();
    }

    function addVitalRow() {
        const rowId = vitalCounter;
        vitalCounter += 1;
        const row = document.createElement("div");
        row.className = "vital-row row g-2 align-items-end mb-2";
        row.innerHTML = `
            <div class="col-sm-5">
                <label class="form-label" for="vital-name-${rowId}">
                    Vital name
                </label>
                <input class="form-control vital-name" id="vital-name-${rowId}" type="text">
            </div>
            <div class="col-sm-5">
                <label class="form-label" for="vital-value-${rowId}">
                    Numeric value
                </label>
                <input class="form-control vital-value" id="vital-value-${rowId}" type="number" step="any">
            </div>
            <div class="col-sm-2">
                <button class="btn btn-outline-danger remove-vital w-100" type="button">
                    Remove
                </button>
            </div>
        `;
        row.querySelector(".remove-vital").addEventListener("click", () => {
            row.remove();
        });
        vitalsList.appendChild(row);
    }

    function collectVitals() {
        const vitals = {};
        for (const row of vitalsList.querySelectorAll(".vital-row")) {
            const name = row.querySelector(".vital-name").value.trim();
            const rawValue = row.querySelector(".vital-value").value.trim();
            const value = Number(rawValue);
            if (!name || !rawValue || !Number.isFinite(value)) {
                throw new Error("Each vital reading needs a name and finite number.");
            }
            if (Object.prototype.hasOwnProperty.call(vitals, name)) {
                throw new Error(`Vital name "${name}" was entered more than once.`);
            }
            vitals[name] = value;
        }
        return vitals;
    }

    async function readResponse(response) {
        try {
            return await response.json();
        } catch (_error) {
            return { error: "The server returned an invalid response." };
        }
    }

    const patient = getPatient();
    if (!patient || !Number.isInteger(patient.id)) {
        patientContext.className = "alert alert-danger";
        patientContext.textContent = "No valid patient ID is available. ";
        const link = document.createElement("a");
        link.href = "/register";
        link.textContent = "Register a patient before starting.";
        patientContext.appendChild(link);
        submitButton.disabled = true;
    } else {
        patientContext.textContent = (
            `Assessment for patient ID ${patient.id}. `
            + "Confirm the recorded evidence before submitting."
        );
    }

    categorySelect.addEventListener("change", updateCategoryVisibility);
    document.querySelectorAll(".state-button").forEach((button) => {
        button.addEventListener("click", () => {
            updateState(button.dataset.key, button.dataset.state, button);
        });
    });
    addVitalButton.addEventListener("click", addVitalRow);
    updateCategoryVisibility();

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (isSubmitting) {
            return;
        }
        if (!patient || !Number.isInteger(patient.id)) {
            showStatus("Register a valid patient before submitting.", "danger");
            return;
        }

        let vitals;
        try {
            vitals = collectVitals();
        } catch (error) {
            showStatus(error.message, "danger");
            return;
        }

        const payload = {
            patient_id: patient.id,
            category: categorySelect.value,
            evidence: Object.fromEntries(
                Object.entries(states).filter(
                    ([key]) => symptomCategories.get(key) === categorySelect.value,
                ),
            ),
            modifier_evidence: Object.fromEntries(
                Object.entries(states).filter(
                    ([key]) => symptomCategories.get(key) === "special_condition",
                ),
            ),
            vitals,
        };

        isSubmitting = true;
        submitButton.disabled = true;
        addVitalButton.disabled = true;
        submitButton.textContent = "Submitting...";
        showStatus("Evaluating recorded evidence...", "info");

        try {
            const response = await fetch("/api/triage", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const body = await readResponse(response);
            if (!response.ok) {
                throw new Error(
                    body.error || "The assessment could not be completed.",
                );
            }
            sessionStorage.setItem("erpilotLastAssessment", JSON.stringify(body));
            window.location.assign("/results");
        } catch (error) {
            showStatus(
                error.message || "The assessment service could not be reached.",
                "danger",
            );
            isSubmitting = false;
            submitButton.disabled = false;
            addVitalButton.disabled = false;
            submitButton.textContent = "Submit assessment";
        }
    });
})();
