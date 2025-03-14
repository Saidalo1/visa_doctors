window.addEventListener("load", function () {
    (function ($) {
        function toggleFields() {
            $(".dynamic-responses").each(function (index) {
                console.log(`Checking .dynamic-responses #${index}`);

                // 1) Найдём <select> с именем, заканчивающимся на '-question'
                var $select = $(this).find("select[name$='-question']");
                if (!$select.length) {
                    console.log("❌ Не найден <select> внутри .dynamic-responses");
                    return;
                }
                console.log("✅ Найден <select>: ", $select);

                // 2) Получаем выбранный <option>
                var $optionSelected = $select.find("option:selected");
                console.log("Выбранный option:", $optionSelected);

                // 3) Пробуем получить data-атрибуты
                var inputType = $optionSelected.data("input-type");
                var hasCustom = $optionSelected.data("has-custom");

                console.log(`🎯 inputType: ${inputType}, hasCustom: ${hasCustom}`);

                // 4) Находим текстовое поле и select с вариантами ответов
                var $textarea = $(this).find("textarea[name$='-text_answer']");
                var $selectedOptions = $(this).find("select[name$='-selected_options']");

                console.log("Текстовое поле:", $textarea.length ? "✅ найдено" : "❌ не найдено");
                console.log("Select с вариантами:", $selectedOptions.length ? "✅ найдено" : "❌ не найдено");

                // 5) Показываем/скрываем нужные поля
                if (inputType === "text") {
                    $selectedOptions.closest(".form-group").hide();
                    $textarea.closest(".form-group").show();
                    console.log("🟢 Режим текстового ввода: скрываем select, показываем textarea");
                } else {
                    $selectedOptions.closest(".form-group").show();
                    if (hasCustom === true || hasCustom === "true") {
                        $textarea.closest(".form-group").show();
                        console.log("🟢 Режим выбора с кастомным ответом: показываем оба");
                    } else {
                        $textarea.closest(".form-group").hide();
                        console.log("🟢 Режим выбора: скрываем textarea, показываем select");
                    }
                }
            });
        }

        // Запускаем при загрузке
        toggleFields();

        // Обработчик изменения <select>
        $(document).on("change", "select[name$='-question']", function () {
            console.log("🔄 Изменился select, вызываем toggleFields()");
            toggleFields();
        });

        // Обработчик добавления нового formset'а
        $(document).on("formset:added", function (event, $row, formsetName) {
            if (formsetName === "responses") {
                console.log("➕ Добавлен новый formset, вызываем toggleFields()");
                toggleFields();
            }
        });
    })(django.jQuery);
});
