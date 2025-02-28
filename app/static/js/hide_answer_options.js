$(document).ready(function () {
    // Function to toggle visibility of AnswerOption block and tab
    function toggleAnswerOptions() {
        const val = $('#id_input_type').val();
        const answerOptionsTab = $('a[href="#answer-options-tab"]').parent();

        if (val === 'text') {
            // Hide the inline block
            $('.dynamic-options').hide();
            // Remove the required attribute (HTML only)
            $('input[name^="options-"][name$="-text"]').prop('required', false);
            // Hide the "Answer Options" tab
            answerOptionsTab.hide();
            // If the hidden tab was active, switch to the "General" tab
            if (answerOptionsTab.hasClass('active')) {
                $('a[href="#general-tab"]').tab('show');
            }
        } else {
            // Show the inline block
            $('.dynamic-options').show();
            // Add the required attribute
            $('input[name^="options-"][name$="-text"]').prop('required', true);
            // Show the "Answer Options" tab
            answerOptionsTab.show();
        }
    }

    // Bind change event and trigger on load
    $('#id_input_type').change(toggleAnswerOptions).trigger('change');
});
