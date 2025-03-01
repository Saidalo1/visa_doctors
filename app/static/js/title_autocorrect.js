// Function to format text
function capitalizeSentences(text) {
    return text
        .toLowerCase()
        .replace(/(^|[.!?]\s+)([a-z])/g, function (match) {
            return match.toUpperCase();
        });
}

// Get the current language from Django Admin
const language = $('html').attr('lang');

// Get correction message based on language
function getCorrectionMessage() {
    return language === 'uz' ? '✔️ Avto tuzatish' : '✔️ Auto-corrected';
}

// Add animation and notification
function showCorrectionNotification($input) {
    $input.siblings('.correction-notification').remove(); // Remove any existing notification
    const $notification = $(`<span class="correction-notification">${getCorrectionMessage()}</span>`);
    $input.after($notification);
    $notification.fadeIn(300).delay(1000).fadeOut(500, function () {
        $(this).remove();
    });
}

// Track input for title fields
$(document).on('input', 'input[name^="title_"][type="text"]', function () {
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

// CSS for notification
$("<style type='text/css'> .correction-notification { margin-left: 10px; color: green; font-weight: bold; display: none; } </style>").appendTo("head");
