(() => {
    "use strict";

    const errorBox = document.getElementById("results-error");
    const content = document.getElementById("results-content");
    const outcomeSummary = document.getElementById("outcome-summary");
    const metadata = document.getElementById("assessment-metadata");
    const matchedRules = document.getElementById("matched-rules");
    const unmatchedRules = document.getElementById("unmatched-rules");
    const modifierRules = document.getElementById("modifier-rules");
    const noMatchMessage = document.getElementById("no-match-message");
    const symptomData = document.getElementById("symptom-data");

    if (
        !errorBox
        || !content
        || !outcomeSummary
        || !metadata
        || !matchedRules
        || !unmatchedRules
        || !modifierRules
        || !noMatchMessage
        || !symptomData
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

    function addDefinition(parent, term, value) {
        addText(parent, "dt", term, "col-sm-4 fw-semibold");
        addText(parent, "dd", value, "col-sm-8");
    }

    function conditionLabel(key, labels) {
        return labels[key] ? `${labels[key]} (${key})` : key;
    }

    function addConditionList(parent, title, values, labels) {
        if (!Array.isArray(values) || values.length === 0) {
            return;
        }
        addText(parent, "h4", title, "h6 mt-3");
        const list = document.createElement("ul");
        for (const value of values) {
            addText(list, "li", conditionLabel(value, labels));
        }
        parent.appendChild(list);
    }

    function addProtocol(parent, reference) {
        if (!reference) {
            return;
        }
        const paragraph = document.createElement("p");
        addText(paragraph, "strong", "Protocol reference: ");
        const urlMatch = reference.match(/https?:\/\/\S+/);
        if (urlMatch) {
            const beforeUrl = reference.slice(0, urlMatch.index);
            const url = urlMatch[0];
            if (beforeUrl) {
                paragraph.appendChild(document.createTextNode(beforeUrl));
            }
            const link = document.createElement("a");
            link.href = url;
            link.target = "_blank";
            link.rel = "noopener";
            link.textContent = url;
            paragraph.appendChild(link);
        } else {
            paragraph.appendChild(document.createTextNode(reference));
        }
        parent.appendChild(paragraph);
    }

    function ruleCard(evaluation, explanation, labels) {
        const column = document.createElement("div");
        column.className = "col-lg-6";
        const card = document.createElement("article");
        card.className = "card rule-card";
        const header = document.createElement("div");
        header.className = "card-header d-flex justify-content-between gap-2";
        addText(header, "h3", evaluation.rule_id, "h5 mb-0");
        addText(header, "span", evaluation.match_status, "badge text-bg-secondary");
        card.appendChild(header);

        const body = document.createElement("div");
        body.className = "card-body";
        if (evaluation.conclusion) {
            addText(body, "p", `Conclusion: ${evaluation.conclusion}`);
        }
        if (evaluation.priority_flag) {
            addText(
                body,
                "p",
                `Software priority flag: ${evaluation.priority_flag} (not a definitive clinical triage decision).`,
            );
        }
        if (evaluation.suggested_department) {
            addText(body, "p", `Suggested department: ${evaluation.suggested_department}`);
        }
        if (evaluation.checklist_action) {
            addText(body, "p", `Checklist action: ${evaluation.checklist_action}`);
        }
        addConditionList(body, "Present conditions", evaluation.present_conditions, labels);
        addConditionList(body, "Explicitly absent conditions", evaluation.absent_conditions, labels);
        addConditionList(body, "Unknown or missing conditions", evaluation.unknown_conditions, labels);
        if (explanation) {
            addText(body, "p", explanation, "small text-muted mt-3");
        }
        addProtocol(body, evaluation.protocol_reference);
        card.appendChild(body);
        column.appendChild(card);
        return column;
    }

    function showError(message) {
        errorBox.className = "alert alert-danger";
        errorBox.textContent = message;
        content.classList.add("d-none");
    }

    function modifierCard(evaluation, labels) {
        const column = document.createElement("div");
        column.className = "col-lg-6";
        const card = document.createElement("article");
        card.className = "card rule-card";
        const header = document.createElement("div");
        header.className = "card-header d-flex justify-content-between gap-2";
        addText(header, "h3", evaluation.modifier_id, "h5 mb-0");
        addText(header, "span", evaluation.match_status, "badge text-bg-secondary");
        card.appendChild(header);

        const body = document.createElement("div");
        body.className = "card-body";
        addText(body, "p", `Trigger: ${conditionLabel(evaluation.trigger, labels)}`);
        addText(body, "p", `Action: ${evaluation.action}`);
        addText(
            body,
            "p",
            `Priority override: ${evaluation.priority_override} (NONE preserves the core software priority).`,
        );
        addConditionList(body, "Matched conditions", evaluation.matched_conditions, labels);
        addConditionList(body, "Unknown or missing conditions", evaluation.unknown_conditions, labels);
        addConditionList(body, "Explicitly absent conditions", evaluation.absent_conditions, labels);
        if (evaluation.explanation) {
            addText(body, "p", evaluation.explanation, "small text-muted mt-3");
        }
        addProtocol(body, evaluation.protocol_reference);
        card.appendChild(body);
        column.appendChild(card);
        return column;
    }

    let result;
    let symptoms;
    try {
        result = JSON.parse(sessionStorage.getItem("erpilotLastAssessment"));
        symptoms = JSON.parse(symptomData.textContent);
        if (
            !result
            || typeof result !== "object"
            || !result.inference_result
            || !Array.isArray(result.inference_result.evaluations)
            || typeof result.outcome !== "string"
        ) {
            throw new Error("The stored assessment response is incomplete.");
        }
    } catch (error) {
        showError(error.message || "No valid assessment result is available.");
        return;
    }

    const labels = {};
    for (const symptom of symptoms) {
        labels[symptom.key] = symptom.label;
    }
    const inference = result.inference_result;
    const explanations = {};
    for (const explanation of inference.explanations || []) {
        explanations[explanation.rule_id] = explanation.text;
    }

    const outcomeClass = {
        FULL_MATCH: "outcome-full",
        PARTIAL_MATCH: "outcome-partial",
        NO_MATCH: "outcome-none",
    }[result.outcome] || "outcome-none";
    outcomeSummary.className = `outcome-panel ${outcomeClass}`;
    addText(outcomeSummary, "h2", `Software outcome: ${result.outcome}`, "h3");
    if (result.outcome === "NO_MATCH") {
        addText(
            outcomeSummary,
            "p",
            "No rule matched the recorded evidence. Unknown information is not a confirmed negative finding.",
        );
    } else if (result.outcome === "PARTIAL_MATCH") {
        addText(
            outcomeSummary,
            "p",
            "Some rule conditions were recorded as present, while other conditions remain unknown or incomplete.",
        );
    } else {
        addText(
            outcomeSummary,
            "p",
            "All conditions for one or more rules were recorded as present. Review the rule details and protocol reference.",
        );
    }

    addDefinition(metadata, "Assessment ID", String(result.assessment_id));
    addDefinition(metadata, "Patient ID", String(result.patient_id));
    addDefinition(metadata, "Category", result.category || "Not provided");

    const matched = [
        ...(inference.full_matches || []),
        ...(inference.partial_matches || []),
    ];
    for (const evaluation of matched) {
        matchedRules.appendChild(
            ruleCard(evaluation, explanations[evaluation.rule_id], labels),
        );
    }
    if (matched.length === 0) {
        addText(matchedRules, "p", "No full or partial rule matches were returned.", "text-muted");
    }

    const unmatched = inference.no_matches || [];
    noMatchMessage.textContent = unmatched.length
        ? "These rules did not match. Their unknown and explicitly absent conditions are shown without interpretation."
        : "The API returned no unmatched rules.";
    for (const evaluation of unmatched) {
        unmatchedRules.appendChild(
            ruleCard(evaluation, explanations[evaluation.rule_id], labels),
        );
    }

    const modifiers = result.modifier_result
        || inference.modifiers
        || { evaluations: [] };
    for (const evaluation of modifiers.evaluations || []) {
        modifierRules.appendChild(modifierCard(evaluation, labels));
    }
    if (!modifierRules.children.length) {
        addText(
            modifierRules,
            "p",
            "No applicable special-condition modifiers were evaluated.",
            "text-muted",
        );
    }

    errorBox.classList.add("d-none");
    content.classList.remove("d-none");
})();
