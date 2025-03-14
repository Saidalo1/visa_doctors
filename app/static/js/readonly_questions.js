window.addEventListener("load", function () {
    (function ($) {
        function toggleFields() {
            $(".dynamic-responses").each(function (index) {
                // 1) Find the <select> element for the question
                var $select = $(this).find("select[name$='-question']");
                if (!$select.length) {
                    return;
                }

                // 2) Get the selected option
                var $optionSelected = $select.find("option:selected");

                // 3) Retrieve data attributes
                var inputType = $optionSelected.data("input-type");
                var hasCustom = $optionSelected.data("has-custom");

                // 4) Find the textarea and select for answer options
                var $textarea = $(this).find("textarea[name$='-text_answer']");
                var $selectedOptions = $(this).find("select[name$='-selected_options']");

                // 5) Show/hide fields based on input type
                if (inputType === "text") {
                    // Для текстовых вопросов показываем только текстовое поле
                    $selectedOptions.closest(".form-group").hide();
                    $textarea.closest(".form-group").show();
                } else if (inputType === "single_choice" || inputType === "multiple_choice") {
                    // Для вопросов с выбором вариантов показываем поле выбора
                    $selectedOptions.closest(".form-group").show();
                    
                    // Проверяем, есть ли у вопроса опции с пользовательским вводом
                    if (hasCustom === true || hasCustom === "true") {
                        // Проверяем, выбрана ли опция с пользовательским вводом
                        var hasSelectedCustomOption = false;
                        
                        // Если есть выбранные опции, проверяем их
                        if ($selectedOptions.val() && $selectedOptions.val().length > 0) {
                            // Здесь мы могли бы проверить, имеет ли выбранная опция has_custom_input,
                            // но у нас нет прямого доступа к этой информации через DOM.
                            // Поэтому просто показываем текстовое поле, если у вопроса есть опции с has_custom_input
                            hasSelectedCustomOption = true;
                        }
                        
                        if (hasSelectedCustomOption) {
                            $textarea.closest(".form-group").show();
                        } else {
                            $textarea.closest(".form-group").hide();
                        }
                    } else {
                        // Если у вопроса нет опций с пользовательским вводом, скрываем текстовое поле
                        $textarea.closest(".form-group").hide();
                    }
                } else {
                    // По умолчанию скрываем текстовое поле
                    $textarea.closest(".form-group").hide();
                }

                // 6) Disable question selection if already set
                if ($select.val() !== "") {
                    $select.prop("disabled", true);
                    $(this)
                        .find(".related-widget-wrapper-link.change-related, .related-widget-wrapper-link.view-related")
                        .addClass("disabled")
                        .attr("aria-disabled", "true");
                } else {
                    $select.prop("disabled", false);
                    $(this)
                        .find(".related-widget-wrapper-link.change-related, .related-widget-wrapper-link.view-related")
                        .removeClass("disabled")
                        .removeAttr("aria-disabled");
                }
            });
        }

        // Run on page load
        toggleFields();

        // Handler for question select change
        $(document).on("change", "select[name$='-question']", function () {
            toggleFields();
        });

        // Handler for adding new formset
        $(document).on("formset:added", function (event, $row, formsetName) {
            if (formsetName === "responses") {
                toggleFields();
            }
        });

        // Handler for selected options change
        $(document).on("change", "select[name$='-selected_options']", function() {
            toggleFields();
        });
    })(django.jQuery);
});
