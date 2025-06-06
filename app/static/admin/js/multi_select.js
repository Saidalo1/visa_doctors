document.addEventListener("DOMContentLoaded", function () {
    const selects = document.querySelectorAll('select[data-name]');

    function getUrlParams(name) {
        const params = new URLSearchParams(window.location.search);
        return params.getAll(name);
    }

    selects.forEach(function (selectElem) {
        const dataName = selectElem.getAttribute("data-name") || "";
        // console.log("[MultiSelectDebug] Processing select. data-name:", dataName, "Element:", selectElem); // LOG 1
        

        if (dataName.includes("created") || dataName.includes("updated")) {
            return;
        }

        selectElem.setAttribute("multiple", "multiple");

        let firstOption = selectElem.querySelector('option:first-child');
        if (firstOption) {
            firstOption.disabled = true;
            firstOption.selected = false;
            selectElem.setAttribute('data-placeholder', firstOption.textContent.trim());
        }

        let query_name;
        if (dataName === "status" || dataName === "survey") {
            // For 'status' and 'survey', the dataName directly matches the URL parameter name
            query_name = dataName;
        } else {
            // For other filters (like 'source', 'question_X'), assume Django appends '__exact'
            // or a similar lookup if they are standard field filters.
            query_name = dataName + "__exact";
        }
        // console.log("[MultiSelectDebug] Determined query_name:", query_name, "based on dataName:", dataName);
        const selectedValues = getUrlParams(query_name);
        // console.log("[MultiSelectDebug] Selected values from URL for '" + query_name + "':", JSON.stringify(selectedValues));

        selectedValues.forEach(value => {
            let option = selectElem.querySelector(`option[value="${value}"]`);
            if (option) {
                option.selected = true;
            }
        });

        // Если используется select2, нужно обновить его
        if ($(selectElem).data('select2')) {
            // console.log("[MultiSelectDebug] Updating Select2 for data-name:", dataName);
            $(selectElem).trigger('change'); // Use standard 'change' event for Select2 update
        }
    });
});
