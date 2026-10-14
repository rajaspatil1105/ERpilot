(() => {
    "use strict";

    const questionList = document.getElementById("follow-up-questions");
    if (!questionList) {
        return;
    }

    let result;
    try {
        result = JSON.parse(sessionStorage.getItem("erpilotLastAssessment"));
    } catch (_error) {
        result = null;
    }
    if (
        !result
        || typeof result !== "object"
        || !result.inference_result
        || !Array.isArray(result.inference_result.follow_up_questions)
    ) {
        return;
    }

    function addText(parent, tag, text, className = "") {
        const element = document.createElement(tag);
        element.textContent = text;
        if (className) {
            element.className = className;
        }
        parent.appendChild(element);
        return element;
    }

    function addQuestion(question) {
        const column = document.createElement("div");
        column.className = "col-lg-6";
        const card = document.createElement("article");
        card.className = "card h-100";
        const body = document.createElement("div");
        body.className = "card-body";
        addText(body, "h3", question.question_id, "h5");
        addText(body, "p", question.prompt);
        addText(
            body,
            "p",
            `Required by rule IDs: ${question.required_by_rule_ids.join(", ")}`,
            "small text-muted",
        );
        const controls = document.createElement("div");
        controls.className = "btn-group";
        controls.setAttribute("role", "group");
        controls.setAttribute("aria-label", question.prompt);
        for (const [label, response] of [
            ["Yes", "YES"],
            ["No", "NO"],
            ["Unknown", "UNKNOWN"],
        ]) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "btn btn-outline-primary";
            button.textContent = label;
            button.addEventListener("click", async () => {
                button.disabled = true;
                try {
                    const responseObject = await fetch(
                        `/api/patients/${encodeURIComponent(result.patient_id)}`
                            + `/assessments/${encodeURIComponent(result.assessment_id)}`
                            + `/questions/${encodeURIComponent(question.question_id)}`,
                        {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ response }),
                        },
                    );
                    const bodyObject = await responseObject.json();
                    if (!responseObject.ok) {
                        throw new Error(
                            bodyObject.error
                            || "The follow-up answer could not be processed.",
                        );
                    }
                    sessionStorage.setItem(
                        "erpilotLastAssessment",
                        JSON.stringify(bodyObject),
                    );
                    window.location.reload();
                } catch (error) {
                    addText(
                        body,
                        "p",
                        error.message,
                        "alert alert-danger mt-3",
                    );
                    button.disabled = false;
                }
            });
            controls.appendChild(button);
        }
        body.appendChild(controls);
        card.appendChild(body);
        column.appendChild(card);
        questionList.appendChild(column);
    }

    for (const question of result.inference_result.follow_up_questions) {
        addQuestion(question);
    }
    if (result.inference_result.follow_up_questions.length === 0) {
        addText(
            questionList,
            "p",
            "No additional relevant questions remain for the current evidence.",
            "text-muted",
        );
    }
})();
