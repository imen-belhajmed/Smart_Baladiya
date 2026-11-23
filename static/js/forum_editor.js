document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".rich-text-editor").forEach((editor) => {
        const textarea = editor.querySelector('textarea[name="content"]');
        if (!textarea) return;

        editor.querySelectorAll("[data-format]").forEach((button) => {
            button.addEventListener("click", () => {
                const format = button.dataset.format;
                const value = textarea.value;
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;
                const selected = value.slice(start, end);

                if (format === "heading" || format === "bullet" ||
                    format === "number" || format === "quote") {
                    const lineStart = value.lastIndexOf("\n", Math.max(0, start - 1)) + 1;
                    const nextLine = value.indexOf("\n", end);
                    const lineEnd = nextLine === -1 ? value.length : nextLine;
                    const lines = value.slice(lineStart, lineEnd).split("\n");
                    const prefix = {
                        heading: "## ",
                        bullet: "- ",
                        number: "1. ",
                        quote: "> ",
                    }[format];
                    const replacement = lines.map((line) => `${prefix}${line}`).join("\n");
                    textarea.value = value.slice(0, lineStart) + replacement + value.slice(lineEnd);
                    textarea.setSelectionRange(lineStart, lineStart + replacement.length);
                } else if (format === "divider") {
                    const replacement = "\n---\n";
                    textarea.value = value.slice(0, start) + replacement + value.slice(end);
                    textarea.setSelectionRange(start + replacement.length, start + replacement.length);
                } else if (format === "link") {
                    const url = window.prompt("Enter the link URL", "https://");
                    if (!url) return;
                    const label = selected || "link text";
                    const replacement = `[${label}](${url})`;
                    textarea.value = value.slice(0, start) + replacement + value.slice(end);
                    textarea.setSelectionRange(start + replacement.length, start + replacement.length);
                } else {
                    const wrappers = {
                        bold: ["**", "**", "bold text"],
                        italic: ["*", "*", "italic text"],
                        underline: ["<u>", "</u>", "underlined text"],
                        strike: ["~~", "~~", "strikethrough text"],
                        highlight: ["<mark>", "</mark>", "highlighted text"],
                    }[format];
                    if (!wrappers) return;
                    const replacement = `${wrappers[0]}${selected || wrappers[2]}${wrappers[1]}`;
                    textarea.value = value.slice(0, start) + replacement + value.slice(end);
                    textarea.setSelectionRange(start + wrappers[0].length, start + wrappers[0].length + (selected || wrappers[2]).length);
                }

                textarea.focus();
                textarea.dispatchEvent(new Event("input", { bubbles: true }));
            });
        });

        const mediaInput = document.querySelector('input[name="media_files"]');
        if (!mediaInput) return;

        const mediaOffset = Number.parseInt(mediaInput.dataset.mediaOffset || "0", 10);
        const existingIndexes = Array.from(
            textarea.value.matchAll(/\[\[media:(\d+)\]\]/g),
            (match) => Number.parseInt(match[1], 10)
        );
        let nextMediaIndex = Math.max(
            mediaOffset,
            existingIndexes.length ? Math.max(...existingIndexes) + 1 : 0
        );
        let selectedFiles = [];

        mediaInput.addEventListener("change", () => {
            const newlySelected = Array.from(mediaInput.files);
            if (!newlySelected.length) return;

            const markers = newlySelected.map(() => `[[media:${nextMediaIndex++}]]`);
            selectedFiles = selectedFiles.concat(newlySelected);
            if (typeof DataTransfer !== "undefined") {
                const transfer = new DataTransfer();
                selectedFiles.forEach((file) => transfer.items.add(file));
                mediaInput.files = transfer.files;
            }

            const insertionPoint = textarea.selectionEnd;
            const before = textarea.value.slice(0, insertionPoint);
            const after = textarea.value.slice(insertionPoint);
            const prefix = before && !before.endsWith("\n\n") ? "\n\n" : "";
            const suffix = after && !after.startsWith("\n\n") ? "\n\n" : "";
            const insertion = `${prefix}${markers.join("\n\n")}${suffix}`;
            textarea.value = before + insertion + after;
            const caret = before.length + insertion.length;
            textarea.setSelectionRange(caret, caret);
            textarea.focus();
            textarea.dispatchEvent(new Event("input", { bubbles: true }));
        });
    });

    const kindField = document.querySelector('select[name="kind"]');
    const eventFields = document.querySelectorAll(".event-form-field");
    if (!kindField || !eventFields.length) return;

    const syncEventFields = () => {
        const isEvent = kindField.value === "event";
        eventFields.forEach((field) => {
            field.hidden = !isEvent;
        });
        const startField = document.querySelector('[name="event_start"]');
        if (startField) startField.required = isEvent;
        const endField = document.querySelector('[name="event_end"]');
        if (endField) endField.required = isEvent;
    };

    kindField.addEventListener("change", syncEventFields);
    syncEventFields();
});
