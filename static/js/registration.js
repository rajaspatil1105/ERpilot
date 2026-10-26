(() => {
    "use strict";

    const form = document.getElementById("registration-form");
    const status = document.getElementById("registration-status");
    const continueLink = document.getElementById("continue-assessment");
    const codePanel = document.getElementById("patient-code-panel");
    const codeValue = document.getElementById("patient-code");
    const copyCode = document.getElementById("copy-patient-code");
    const demoButton = document.getElementById("fill-demo-patient");

    if (!form || !status || !continueLink || !codePanel || !codeValue || !copyCode || !demoButton) {
        return;
    }

    demoButton.addEventListener("click", () => {
        form.elements.name.value = "Alex Demo";
        form.elements.age.value = "32";
        form.elements.gender.value = "Male";
        form.elements.incident_type.value = "Demo collision";
        status.className = "alert alert-info";
        status.textContent = "Fictional demo details loaded. Saving creates a demo patient record.";
    });

    function showStatus(message, kind) {
        status.className = `alert alert-${kind}`;
        status.textContent = message;
    }

    function markInvalid(fieldName, invalid) {
        const field = form.elements[fieldName];
        if (field) {
            field.classList.toggle("is-invalid", invalid);
        }
    }

    function validateForm() {
        let valid = true;
        const textFields = ["name", "gender", "incident_type"];
        for (const fieldName of textFields) {
            const field = form.elements[fieldName];
            const invalid = !field.value.trim();
            markInvalid(fieldName, invalid);
            valid = valid && !invalid;
        }

        const ageValue = form.elements.age.value.trim();
        const age = Number(ageValue);
        const invalidAge = (
            !ageValue
            || !Number.isSafeInteger(age)
            || age < 0
        );
        markInvalid("age", invalidAge);
        return valid && !invalidAge;
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
        continueLink.classList.add("d-none");
        codePanel.classList.add("d-none");
        if (!validateForm()) {
            showStatus("Correct the highlighted fields before continuing.", "danger");
            return;
        }

        const payload = {
            name: form.elements.name.value.trim(),
            age: Number(form.elements.age.value),
            gender: form.elements.gender.value.trim(),
            incident_type: form.elements.incident_type.value.trim(),
        };

        showStatus("Saving patient details...", "info");
        try {
            const response = await fetch("/api/patients", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const body = await readResponse(response);
            if (!response.ok) {
                markInvalid(body.field, true);
                throw new Error(body.error || "Patient registration failed.");
            }
            sessionStorage.setItem("erpilotPatient", JSON.stringify(body));
            codeValue.textContent = body.patient_code;
            copyCode.dataset.copyText = body.patient_code;
            codePanel.classList.remove("d-none");
            continueLink.classList.remove("d-none");
            showStatus(`Patient registered. Code ${body.patient_code}.`, "success");
        } catch (error) {
            showStatus(
                error.message || "The patient service could not be reached.",
                "danger",
            );
        }
    });
})();
