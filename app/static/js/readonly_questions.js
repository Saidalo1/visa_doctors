window.addEventListener("load", function () {
    (function ($) {
        function toggleFields() {
            $(".dynamic-responses").each(function (index) {
                console.log(`Checking .dynamic-responses #${index}`);

                // 1) Find the <select> element for the question
                var $select = $(this).find("select[name$='-question']");
                if (!$select.length) {
                    console.log("❌ No <select> found inside .dynamic-responses");
                    return;
                }
                console.log("✅ Found <select>: ", $select);

                // 2) Get the selected option
                var $optionSelected = $select.find("option:selected");
                console.log("Selected option:", $optionSelected);

                // 3) Retrieve data attributes
                var inputType = $optionSelected.data("input-type");
                var hasCustom = $optionSelected.data("has-custom");

                console.log(`🎯 inputType: ${inputType}, hasCustom: ${hasCustom}`);

                // 4) Find the textarea and select for answer options
                var $textarea = $(this).find("textarea[name$='-text_answer']");
                var $selectedOptions = $(this).find("select[name$='-selected_options']");

                console.log("Textarea:", $textarea.length ? "✅ Found" : "❌ Not found");
                console.log("Select options:", $selectedOptions.length ? "✅ Found" : "❌ Not found");

                // 5) Show/hide fields based on input type
                if (inputType === "text") {
                    $selectedOptions.closest(".form-group").hide();
                    $textarea.closest(".form-group").show();
                    console.log("🟢 Text input mode: hiding select, showing textarea");
                } else {
                    $selectedOptions.closest(".form-group").show();
                    if (hasCustom === true || hasCustom === "true") {
                        $textarea.closest(".form-group").show();
                        console.log("🟢 Choice mode with custom input: showing both fields");
                    } else {
                        $textarea.closest(".form-group").hide();
                        console.log("🟢 Choice mode: hiding textarea, showing select");
                    }
                }

                // 6) Disable question selection if already set
                if ($select.val() !== "") {
                    $select.prop("disabled", true);
                    $(this)
                        .find(".related-widget-wrapper-link.change-related, .related-widget-wrapper-link.view-related")
                        .addClass("disabled")
                        .attr("aria-disabled", "true");
                    console.log("🔒 Question field is now disabled.");
                } else {
                    $select.prop("disabled", false);
                    $(this)
                        .find(".related-widget-wrapper-link.change-related, .related-widget-wrapper-link.view-related")
                        .removeClass("disabled")
                        .removeAttr("aria-disabled");
                    console.log("🔓 Question field is now enabled.");
                }
            });
        }

        // Run on page load
        toggleFields();

        // Run when question select changes
        $(document).on("change", "select[name$='-question']", function () {
            console.log("🔄 Select changed, updating fields...");
            toggleFields();
        });

        // Run when a new formset is added
        $(document).on("formset:added", function (event, $row, formsetName) {
            if (formsetName === "responses") {
                console.log("➕ New formset added, updating fields...");
                toggleFields();
            }
        });
    })(django.jQuery);
});
