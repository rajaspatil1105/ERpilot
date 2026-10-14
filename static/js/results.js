(() => {
    "use strict";

    const errorBox = document.getElementById("results-error");
    const content = document.getElementById("results-content");
    const outcomeSummary = document.getElementById("outcome-summary");
    const priorityAlert = document.getElementById("priority-alert");
    const metadata = document.getElementById("assessment-metadata");
    const matchedRules = document.getElementById("matched-rules");
    const unmatchedRules = document.getElementById("unmatched-rules");
    const modifierRules = document.getElementById("modifier-rules");
    const reviewChecklist = document.getElementById("review-checklist");
    const reportDownloads = document.getElementById("report-downloads");
    const noMatchMessage = document.getElementById("no-match-message");
    const symptomData = document.getElementById("symptom-data");

    if (
        !errorBox
        || !content
        || !outcomeSummary
        || !priorityAlert
        || !metadata
        || !matchedRules
        || !unmatchedRules
        || !modifierRules
        || !reviewChecklist
        || !reportDownloads
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

    function categoryLabel(category) {
        return String(category || "Uncategorised")
            .replaceAll("_", " ")
            .replace(/\b\w/g, (letter) => letter.toUpperCase());
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
            const url = urlMatch[0].replace(/[).,]+$/, "");
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

    function statusDetails(status) {
        return {
            FULL_MATCH: {
                className: "status-full",
                text: "Full match: every required condition was recorded as present.",
            },
            PARTIAL_MATCH: {
                className: "status-partial",
                text: "Partial match: at least one condition is present and another remains unresolved.",
            },
            NO_MATCH: {
                className: "status-none",
                text: "No match: the evidence does not satisfy this rule; unknown evidence is not confirmed absent.",
            },
        }[status] || {
            className: "status-none",
            text: "The returned rule status is not configured for display.",
        };
    }

    function ruleCard(evaluation, explanation, labels) {
        const column = document.createElement("div");
        column.className = "col-lg-6";
        const card = document.createElement("article");
        card.className = "card rule-card";
        const header = document.createElement("div");
        const details = statusDetails(evaluation.match_status);
        header.className = "card-header d-flex justify-content-between gap-2";
        addText(header, "h3", evaluation.rule_id, "h5 mb-0");
        addText(
            header,
            "span",
            evaluation.match_status,
            `badge status-badge ${details.className}`,
        );
        card.appendChild(header);

        const body = document.createElement("div");
        body.className = "card-body";
        addText(body, "p", details.text, "status-explanation");
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
            addText(body, "p", `Configured review area: ${evaluation.suggested_department}`);
        }
        if (evaluation.checklist_action) {
            addText(body, "p", `Clinician-review item: ${evaluation.checklist_action}`);
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

    function createRuleGroup(category, heading) {
        const group = document.createElement("section");
        group.className = "rule-category-group";
        group.setAttribute("aria-labelledby", `${heading}-${category}`);
        addText(
            group,
            "h3",
            categoryLabel(category),
            "h4 rule-category-heading",
        ).id = `${heading}-${category}`;
        const grid = document.createElement("div");
        grid.className = "row g-3";
        group.appendChild(grid);
        return { group, grid };
    }

    function renderRuleGroups(container, evaluations, labels, explanations, heading) {
        if (!evaluations.length) {
            return false;
        }
        const groups = new Map();
        for (const evaluation of evaluations) {
            const category = evaluation.category || "uncategorised";
            if (!groups.has(category)) {
                groups.set(category, createRuleGroup(category, heading));
            }
            groups.get(category).grid.appendChild(
                ruleCard(evaluation, explanations[evaluation.rule_id], labels),
            );
        }
        for (const { group } of groups.values()) {
            container.appendChild(group);
        }
        return true;
    }

    function modifierCard(evaluation, labels) {
        const column = document.createElement("div");
        column.className = "col-lg-6";
        const card = document.createElement("article");
        card.className = "card rule-card";
        const header = document.createElement("div");
        const details = statusDetails(evaluation.match_status);
        header.className = "card-header d-flex justify-content-between gap-2";
        addText(header, "h3", evaluation.modifier_id, "h5 mb-0");
        addText(
            header,
            "span",
            evaluation.match_status,
            `badge status-badge ${details.className}`,
        );
        card.appendChild(header);

        const body = document.createElement("div");
        body.className = "card-body";
        addText(body, "p", details.text, "status-explanation");
        addText(body, "p", `Trigger: ${conditionLabel(evaluation.trigger, labels)}`);
        addText(body, "p", `Review item: ${evaluation.action}`);
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

    function addChecklistItem(item, index) {
        const card = document.createElement("article");
        card.className = "review-checklist-item";
        const row = document.createElement("div");
        row.className = "form-check";
        const input = document.createElement("input");
        input.className = "form-check-input";
        input.type = "checkbox";
        input.id = `review-item-${index}`;
        const label = document.createElement("label");
        label.className = "form-check-label fw-semibold";
        label.htmlFor = input.id;
        label.textContent = `Review ${item.id}`;
        row.appendChild(input);
        row.appendChild(label);
        card.appendChild(row);
        addText(card, "p", item.action, "mb-2 mt-2");
        if (item.department) {
            addText(card, "p", `Configured review area: ${item.department}`, "small text-muted");
        }
        const reviewStatus = addText(
            card,
            "p",
            "Not marked as reviewed on this page.",
            "small text-muted mb-2",
        );
        input.addEventListener("change", () => {
            reviewStatus.textContent = input.checked
                ? "Marked as reviewed on this page only."
                : "Not marked as reviewed on this page.";
        });
        addProtocol(card, item.source);
        return card;
    }

    function renderReviewChecklist(matched, modifiers) {
        const items = matched
            .filter((evaluation) => evaluation.checklist_action)
            .map((evaluation) => ({
                id: `rule ${evaluation.rule_id}`,
                action: evaluation.checklist_action,
                department: evaluation.suggested_department,
                source: evaluation.protocol_reference,
            }));
        for (const modifier of modifiers.fired_modifiers || []) {
            if (modifier.action) {
                items.push({
                    id: `modifier ${modifier.modifier_id}`,
                    action: modifier.action,
                    source: modifier.protocol_reference,
                });
            }
        }
        if (!items.length) {
            addText(
                reviewChecklist,
                "p",
                "No configured option for this finding.",
                "text-muted",
            );
            return;
        }
        items.forEach((item, index) => {
            reviewChecklist.appendChild(addChecklistItem(item, index));
        });
    }

    function showError(message) {
        errorBox.className = "alert alert-danger";
        errorBox.textContent = message;
        content.classList.add("d-none");
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
    addDefinition(metadata, "Category", categoryLabel(result.category));
    addDefinition(
        metadata,
        "Recorded evidence",
        `${Object.keys(result.evidence || {}).length} core evidence entries`,
    );

    const matched = [
        ...(inference.full_matches || []),
        ...(inference.partial_matches || []),
    ];
    const redEvaluations = matched.filter(
        (evaluation) => evaluation.priority_flag === "RED",
    );
    if (redEvaluations.length) {
        addText(
            priorityAlert,
            "strong",
            "Provisional RED software-display priority",
        );
        addText(
            priorityAlert,
            "p",
            "One or more applicable rule evaluations use RED. This is not "
                + "a clinically validated triage category; review the "
                + "recorded evidence and qualified clinical judgment.",
        );
        addText(
            priorityAlert,
            "p",
            `Applicable RED rule IDs: ${
                redEvaluations.map((evaluation) => evaluation.rule_id).join(", ")
            }`,
            "mb-0",
        );
        priorityAlert.classList.remove("d-none");
    }

    if (!renderRuleGroups(
        matchedRules,
        matched,
        labels,
        explanations,
        "matched",
    )) {
        addText(
            matchedRules,
            "p",
            "No full or partial rule matches were returned.",
            "text-muted",
        );
    }

    const unmatched = inference.no_matches || [];
    noMatchMessage.textContent = unmatched.length
        ? "These rules did not match. Their unknown and explicitly absent conditions are shown without interpretation."
        : "The API returned no unmatched rules.";
    renderRuleGroups(unmatchedRules, unmatched, labels, explanations, "unmatched");

    const modifiers = result.modifier_result
        || inference.modifiers
        || { evaluations: [], fired_modifiers: [] };
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
    renderReviewChecklist(matched, modifiers);

    for (const [format, label] of [["pdf", "Download PDF"], ["docx", "Download DOCX"]]) {
        const link = document.createElement("a");
        link.className = "btn btn-outline-primary";
        link.href = (
            `/api/patients/${encodeURIComponent(result.patient_id)}`
            + `/assessments/${encodeURIComponent(result.assessment_id)}`
            + `/report/${format}`
        );
        link.textContent = label;
        reportDownloads.appendChild(link);
    }

    errorBox.classList.add("d-none");
    content.classList.remove("d-none");
})();
