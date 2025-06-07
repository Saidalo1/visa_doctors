document.addEventListener("DOMContentLoaded", function () {
    const selects = document.querySelectorAll('select[data-name]');

    function getUrlParams(name) {
        const params = new URLSearchParams(window.location.search);
        return params.getAll(name);
    }

    function getUrlParam(name) { // Helper for single value
        const params = new URLSearchParams(window.location.search);
        return params.get(name);
    }

    selects.forEach(function (selectElem) {
        const dataName = selectElem.getAttribute("data-name") || "";
        const nameAttr = selectElem.getAttribute("name");

        

        // Skip date/time range filters which are not select elements we manage this way
        if (dataName.includes("created") || dataName.includes("updated") || 
            dataName.includes("_gte") || dataName.includes("_lte") || 
            selectElem.type === 'text' || selectElem.type === 'date') { // Also skip if it's clearly not a select we handle
            
            return;
        }

        // Make all filters multi-select except for 'survey'
        if (dataName !== "survey") {
            selectElem.setAttribute("multiple", "multiple");
        }

        // Disable the first "all" or placeholder option and use its text as placeholder
        let firstOption = selectElem.querySelector('option:first-child');
        if (firstOption && (firstOption.value === "" || firstOption.value === null || firstOption.value === undefined)) {
            firstOption.disabled = true;
            firstOption.selected = false; // Ensure placeholder is not actually selected
            selectElem.setAttribute('data-placeholder', firstOption.textContent.trim());
        } else if (firstOption) {
            // If the first option is a real value, don't disable it but still use as placeholder if nothing else is selected
             selectElem.setAttribute('data-placeholder', firstOption.textContent.trim());
        }

        let query_name;

        if (dataName.startsWith("question_option_")) { // e.g., question_option_4_2
            query_name = dataName;
        } else if (dataName.startsWith("question_")) { // e.g., question_2 (textual or other non-option survey questions)
            query_name = dataName;
        } else if (dataName === "survey" || dataName === "status") { // Standard filters
            query_name = dataName;
        } else if (dataName === "source") { // 'source' needs __exact
            query_name = dataName + "__exact";
        } else if (nameAttr && nameAttr.endsWith("__exact")) { // Trust nameAttr if it explicitly has __exact
            query_name = nameAttr;
        } else if (dataName) { // Fallback for any other unhandled dataName, assume it might need __exact
            query_name = dataName + "__exact";
            console.warn(`[MultiSelect] Fallback: data-name '${dataName}' is not explicitly handled. Defaulting query_name to '${query_name}'. Review if '__exact' is correct.`);
        } else if (nameAttr) { // Fallback if no dataName, but nameAttr exists
            query_name = nameAttr; // Use nameAttr as is, assuming it's the correct parameter name
            console.warn(`[MultiSelect] Fallback: Using nameAttr '${nameAttr}' as query_name. Assuming it's the correct query parameter name.`);
        } else {
            console.error("[MultiSelect] CRITICAL: Could not determine query_name. data-name:", dataName, "name:", nameAttr, "Element:", selectElem);
            return; // Skip processing this select element
        }
        

        let selectedValues = [];
        if (dataName === "survey") { // Survey is single-select
            const singleValue = getUrlParam(query_name);
            if (singleValue !== null && singleValue !== undefined && singleValue !== "") { // Ensure not empty string
                selectedValues.push(singleValue);
            }
        } else { // Other filters can be multi-select
            selectedValues = getUrlParams(query_name);
        }
        

        // Clear previous selections before applying new ones
        Array.from(selectElem.options).forEach(option => {
            // Don't unselect the disabled placeholder itself, or if the first option is a real, non-disabled one
            if (option !== firstOption || (firstOption && !firstOption.disabled)) { 
                 option.selected = false;
            }
        });

        let valueSet = false;
        if (selectedValues.length > 0) {
            selectedValues.forEach(value => {
                const stringValue = String(value); // Ensure value is a string for CSS.escape
                const selector = `option[value="${CSS.escape(stringValue)}"]`;
                let option = selectElem.querySelector(selector);
                
                if (option) {
                    option.selected = true;
                    valueSet = true;
                } else {
                    console.warn(`[MultiSelect] Option not found for selector: "${selector}" with value: "${stringValue}"`);
                }
            });
        }
        
        // If 'survey' (single select) and no value was set from URL, and there's a disabled placeholder,
        // ensure it appears visually selected by Select2. For native select, this is not strictly needed.
        if (dataName === "survey" && !valueSet && firstOption && firstOption.disabled) {
            // For Select2, if nothing is selected and there's a placeholder, it usually handles it.
            // However, explicitly setting the value to the placeholder's value might be needed if Select2 doesn't pick it up.
            // $(selectElem).val(firstOption.value).trigger('change.select2'); // This might select the disabled option if not careful
        }

        // Trigger Select2 update if it's a Select2 element
        if (typeof $ !== 'undefined' && $(selectElem).data('select2')) {
            
            $(selectElem).trigger('change.select2'); // Use 'change.select2' for Select2
        } else {
            // For non-Select2 elements, a simple 'change' event might be needed if there are other listeners
            // This is less likely for Django admin filters but good for robustness
            const event = new Event('change', { bubbles: true });
            selectElem.dispatchEvent(event);
            
        }
    });
});
