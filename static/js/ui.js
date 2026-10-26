(() => {
    "use strict";

    function fallbackCopy(value) {
        const input = document.createElement("textarea");
        input.value = value;
        input.setAttribute("readonly", "");
        input.style.position = "fixed";
        input.style.opacity = "0";
        document.body.appendChild(input);
        input.select();
        const copied = document.execCommand("copy");
        input.remove();
        return copied;
    }

    document.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-copy-text]");
        if (!button || !button.dataset.copyText) return;
        let copied = false;
        try {
            if (navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(button.dataset.copyText);
                copied = true;
            } else {
                copied = fallbackCopy(button.dataset.copyText);
            }
        } catch (_error) {
            copied = fallbackCopy(button.dataset.copyText);
        }
        const original = button.textContent;
        button.textContent = copied ? "Copied" : "Copy failed";
        button.setAttribute("aria-live", "polite");
        window.setTimeout(() => { button.textContent = original; }, 1600);
        if (!copied && button.dataset.copyStatus) {
            const status = document.getElementById(button.dataset.copyStatus);
            if (status) status.textContent = "Could not copy automatically. Select and copy the code.";
        }
    });
})();
