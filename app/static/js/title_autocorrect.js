$(document).ready(function () {
    // Функция для форматирования текста
    function capitalizeSentences(text) {
        return text
            .toLowerCase()
            .replace(/(^|[.!?]\s+)([a-z])/g, function (match) {
                return match.toUpperCase();
            });
    }

    // Добавляем анимацию и уведомление
    function showCorrectionNotification($input) {
        const $notification = $('<span class="correction-notification">✔️ Автоисправление</span>');
        $input.after($notification);
        $notification.fadeIn(300).delay(1000).fadeOut(500, function () {
            $(this).remove();
        });
    }

    // Отслеживаем вставку в поле title
    $(document).on('input', 'input[name="title"][type="text"]', function () {
        const $input = $(this);
        const originalText = $input.val();
        const correctedText = capitalizeSentences(originalText);

        if (originalText !== correctedText) {
            $input.val(correctedText).css({
                transition: 'background-color 0.5s ease',
                'background-color': '#d4edda'
            });

            setTimeout(() => $input.css('background-color', ''), 1000);
            showCorrectionNotification($input);
        }
    });
});

// CSS для уведомления
$("<style type='text/css'> .correction-notification { margin-left: 10px; color: green; font-weight: bold; display: none; } </style>").appendTo("head");
