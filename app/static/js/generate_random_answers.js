$(document).ready(function () {
    let questions = [];

    async function fetchQuestions() {
        const currentDomain = window.location.origin;
        try {
            const response = await fetch(`${currentDomain}/questions/`);
            const data = await response.json();
            questions = data;
            console.log("Questions fetched:", questions);
        } catch (error) {
            console.error("Failed to fetch questions", error);
        }
    }

    function addAutoGenerateButton() {
        if (!$("#auto-generate-request").length && $(".opblock-section-request-body").length) {
            const buttonHtml = '<button id="auto-generate-request" class="btn">Auto-Generate Request Body</button>';
            $(".opblock-section-request-body").prepend(buttonHtml);
            console.log("Auto-generate button added!");
        }
    }

    $(document).on("click", "#auto-generate-request", async function () {
        console.log("Auto-generate button clicked");

        await fetchQuestions();

        if (!questions.length) {
            alert("No questions available. Please fetch questions first.");
            return;
        }

        const responses = questions.map(q => {
            const selectableOptions = (q.options || [])
                .flatMap(opt => opt.children.length ? opt.children : opt)
                .filter(opt => opt.is_selectable);

            const selectedOption = selectableOptions.length
                ? selectableOptions[Math.floor(Math.random() * selectableOptions.length)]
                : null;

            const requiresCustomInput = selectedOption && selectedOption.has_custom_input;

            const response = {
                question: q.id,
                selected_options: selectedOption ? [selectedOption.id] : []
            };

            if (q.input_type === "text" || requiresCustomInput) {
                response.text_answer = `Random answer for ${q.title}`;
            }

            return response;
        });

        const requestBody = JSON.stringify({responses}, null, 2);
        const textArea = document.querySelector(".body-param__text");

        if (textArea) {
            textArea.value = requestBody;
            textArea.dispatchEvent(new Event('input', {bubbles: true}));
            console.log("Request body auto-generated:", requestBody);
        }
    });

    const observer = new MutationObserver(addAutoGenerateButton);
    observer.observe(document.body, {childList: true, subtree: true});

    addAutoGenerateButton();
});