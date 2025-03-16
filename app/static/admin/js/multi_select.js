document.addEventListener("DOMContentLoaded", function () {
    const selects = document.querySelectorAll('select[data-name]');

    function getUrlParams(name) {
        const params = new URLSearchParams(window.location.search);
        return params.getAll(name);
    }

    selects.forEach(function (selectElem) {
        const dataName = selectElem.getAttribute("data-name") || "";

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

        const query_name = dataName === "status" ? "status__exact" : dataName;
        const selectedValues = getUrlParams(query_name);

        selectedValues.forEach(value => {
            let option = selectElem.querySelector(`option[value="${value}"]`);
            if (option) {
                option.selected = true;
            }
        });

        // Если используется select2, нужно обновить его
        if ($(selectElem).data('select2')) {
            $(selectElem).trigger('change.select2');
        }
    });
});
