(() => {
    "use strict";

    const form = document.getElementById("assessment-form");
    const status = document.getElementById("assessment-status");
    const patientContext = document.getElementById("patient-context");
    const symptomData = document.getElementById("symptom-data");
    const categorySelect = document.getElementById("category");
    const vitalsList = document.getElementById("vitals-list");
    const addVitalButton = document.getElementById("add-vital");
    const states = {};

    if (
        !form
        || !status
        || !patientContext
        || !symptomData
        || !categorySelect
        || !vitalsList
        || !addVitalButton
    ) {
        return;
    }

    let symptoms;
    try {
        symptoms = JSON.parse(symptomData.textContent);
    } catch (_error) {
        showStatus("The canonical symptom data could not be loaded.", "danger");
        return;
    }

    const supportedCategories = new Set([
        "brain_trauma",
        "chest_trauma",
        "abdominal_trauma",
        "orthopedic_trauma",
    ]);
    document.querySelectorAll("#category option").forEach((option) => {
        if (supportedCategories.has(option.value)) {
            option.disabled = false;
            option.textContent = option.value
                .replaceAll("_", " ")
                .replace(/\b\w/g, (letter) => letter.toUpperCase());
            option.textContent += " (supported)";
        }
    });

    for (const symptom of symptoms) {
        states[symptom.key] = "UNKNOWN";
    }
    const symptomCategories = new Map(
        symptoms.map((symptom) => [symptom.key, symptom.category]),
    );
    const symptomLegend = document.querySelector("#symptom-list")
        ?.closest("fieldset")
        ?.querySelector("legend");

    function updateCategorySymptoms() {
        const category = categorySelect.value;
        document.querySelectorAll(".symptom-card:not(.modifier-card)").forEach((card) => {
            const key = card.querySelector(".state-button")?.dataset.key;
            card.closest(".col-md-6").hidden = (
                symptomCategories.get(key) !== category
            );
        });
        if (symptomLegend) {
            symptomLegend.textContent = `${category.replaceAll("_", " ")} evidence`;
        }
    }

    categorySelect.addEventListener("change", updateCategorySymptoms);
    updateCategorySymptoms();
    let vitalCounter = 0;

    function showStatus(message, kind) {
        status.className = `alert alert-${kind}`;
        status.textContent = message;
    }

    function getPatient() {
        try {
            return JSON.parse(sessionStorage.getItem("erpilotPatient"));
        } catch (_error) {
            return null;
        }
    }

    const patient = getPatient();
    if (!patient || !Number.isInteger(patient.id)) {
        patientContext.className = "alert alert-danger";
        patientContext.innerHTML = (
            "No valid patient ID is available. "
            + '<a href="/register">Register a patient before starting.</a>'
        );
        form.querySelector("button[type='submit']").disabled = true;
    } else {
        patientContext.textContent = (
            `Assessment for patient ID ${patient.id}. `
            + "Confirm the recorded evidence before submitting."
        );
    }

    function updateState(key, state, clickedButton) {
        states[key] = state;
        const buttons = document.querySelectorAll(
            `.state-button[data-key="${CSS.escape(key)}"]`,
        );
        buttons.forEach((button) => {
            const selected = button === clickedButton;
            button.classList.toggle("state-selected", selected);
            button.setAttribute("aria-pressed", String(selected));
        });
        const statusText = document.querySelector(`[data-status-for="${CSS.escape(key)}"]`);
        if (statusText) {
            statusText.textContent = `Recorded state: ${state}`;
        }
    }

    document.querySelectorAll(".state-button").forEach((button) => {
        button.addEventListener("click", () => {
            updateState(button.dataset.key, button.dataset.state, button);
        });
    });

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

    addVitalButton.addEventListener("click", addVitalRow);

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

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
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
        showStatus("Evaluating recorded evidence...", "info");

        try {
            const response = await fetch("/api/triage", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const body = await readResponse(response);
            if (!response.ok) {
                throw new Error(body.error || "The assessment could not be completed.");
            }
            sessionStorage.setItem("erpilotLastAssessment", JSON.stringify(body));
            window.location.assign("/results");
        } catch (error) {
            showStatus(
                error.message || "The assessment service could not be reached.",
                "danger",
            );
        }
    });
})();
