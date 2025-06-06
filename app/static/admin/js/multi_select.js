document.addEventListener("DOMContentLoaded", function () {
    const selects = document.querySelectorAll('select[data-name]');

    function getUrlParams(name) { // For multiple values
        const params = new URLSearchParams(window.location.search);
        return params.getAll(name);
    }

    function getUrlParam(name) { // Helper for single value
        const params = new URLSearchParams(window.location.search);
        return params.get(name);
    }

    selects.forEach(function (selectElem) {
        const dataName = selectElem.getAttribute("data-name") || "";
        // console.log("[MultiSelectDebug] Processing select. data-name:", dataName, "Element:", selectElem);

        if (dataName.includes("created") || dataName.includes("updated")) {
            return;
        }

        // Make 'status' and 'source' (and others except 'survey') multi-select
        if (dataName !== "survey") {
            selectElem.setAttribute("multiple", "multiple");
        }

        let firstOption = selectElem.querySelector('option:first-child');
        if (firstOption) {
            firstOption.disabled = true;
            firstOption.selected = false; // Ensure placeholder is not selected by default
            selectElem.setAttribute('data-placeholder', firstOption.textContent.trim());
        }

        let query_name;
        const nameAttr = selectElem.getAttribute("name");

        if (dataName === "status" || dataName === "survey") {
            query_name = dataName; 
        } else if (nameAttr && nameAttr.includes("__exact")) {
             query_name = nameAttr;
        } else if (dataName && nameAttr) { // If dataName exists and nameAttr also exists (e.g. source)
            query_name = nameAttr; // Prefer nameAttr if available for non-status/survey
        } else if (dataName) { // Fallback for other dataNames if nameAttr is missing, assuming __exact
            query_name = dataName + "__exact";
        } else if (nameAttr) { // Fallback if dataName is empty but name attribute exists
            query_name = nameAttr;
        } else {
            // console.warn("[MultiSelectDebug] Could not determine query_name for select with data-name:", dataName, "Element:", selectElem);
            return; 
        }
        // console.log("[MultiSelectDebug] Using query_name:", query_name, "for data-name:", dataName);

        let selectedValues = [];
        if (dataName === "survey") {
            const singleValue = getUrlParam(query_name); 
            if (singleValue) {
                selectedValues.push(singleValue);
            }
        } else {
            selectedValues = getUrlParams(query_name); 
        }
        // console.log("[MultiSelectDebug] Selected values from URL for '" + query_name + "':", JSON.stringify(selectedValues));

        // Clear previous selections before applying new ones to prevent accumulation on back/forward
        Array.from(selectElem.options).forEach(option => {
            if (option !== firstOption) { // Don't unselect the disabled placeholder itself
                 option.selected = false;
            }
        });
        
        let valueSet = false;
        if (selectedValues.length > 0) {
            selectedValues.forEach(value => {
                let option = selectElem.querySelector(`option[value="${value}"]`);
                if (option) {
                    option.selected = true;
                    valueSet = true;
                }
            });
        }

        // If no valid value was set from URL for a single-select (like survey), 
        // and it has a disabled placeholder, ensure the placeholder appears selected visually by Select2.
        // For actual form submission, no value will be sent if placeholder is selected.
        if (dataName === "survey" && !valueSet && firstOption && firstOption.disabled) {
            // For Select2, if nothing is selected and there's a placeholder, it handles it.
            // For a native select, ensuring no option is 'selected=true' is enough.
        }

        if ($(selectElem).data('select2')) {
            // console.log("[MultiSelectDebug] Updating Select2 for data-name:", dataName);
            $(selectElem).trigger('change');
        }
    });
});
