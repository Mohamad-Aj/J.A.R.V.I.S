// // Wait until Gmail is fully loaded
// const waitForComposeWindow = () => {
//     return new Promise(resolve => {
//         const check = () => {
//             const compose = document.querySelector("div[role='dialog']");
//             if (compose) resolve(compose);
//             else setTimeout(check, 500);
//         };
//         check();
//     });
// };

// // Listen for messages from popup.js
// chrome.runtime.onMessage.addListener(async (request, sender, sendResponse) => {
//     if (request.action === "fill_email") {
//         const { subject, body } = request;

//         const compose = await waitForComposeWindow();

//         // Fill body
//         const bodyField = compose.querySelector("div[aria-label='Message Body']");
//         if (bodyField) {
//             bodyField.focus();
//             document.execCommand("insertText", false, body);
//         }

//         // Fill subject
//         const subjectInput = compose.querySelector("input[name='subjectbox']");
//         if (subjectInput) {
//             subjectInput.focus();
//             subjectInput.value = subject;
//         }

//         sendResponse({ status: "done" });
//     }
// });


// Wait until Gmail is fully loaded
const waitForComposeWindow = () => {
    return new Promise(resolve => {
        const check = () => {
            const compose = document.querySelector("div[role='dialog']");
            if (compose) resolve(compose);
            else setTimeout(check, 500);
        };
        check();
    });
};

// Listen for messages from popup.js
chrome.runtime.onMessage.addListener(async (request, sender, sendResponse) => {
    if (request.action === "fill_email") {
        const { subject, body, to } = request;

        const compose = await waitForComposeWindow();

        // ✅ Final "To" field fix for Gmail
        if (Array.isArray(to) && to.length > 0) {
            const toField = compose.querySelector("input[aria-label='To recipients']");

            if (toField) {
                toField.focus();

                to.forEach(email => {
                    toField.value = email;
                    toField.dispatchEvent(new Event("input", { bubbles: true }));

                    // Simulate pressing comma or Enter after each email
                    const enterEvent = new KeyboardEvent("keydown", {
                        key: "Enter",
                        code: "Enter",
                        keyCode: 13,
                        which: 13,
                        bubbles: true
                    });
                    toField.dispatchEvent(enterEvent);
                });
            } else {
                console.warn("❌ To field not found");
            }
        }



        // Fill body
        const bodyField = compose.querySelector("div[aria-label='Message Body']");
        if (bodyField) {
            bodyField.focus();
            document.execCommand("insertText", false, body);
        }

        // Fill subject
        const subjectInput = compose.querySelector("input[name='subjectbox']");
        if (subjectInput) {
            subjectInput.focus();
            subjectInput.value = subject;
        }

        // // ✅ Fill To field if provided
        // if (Array.isArray(to) && to.length > 0) {
        //     const toInput = compose.querySelector("textarea[name='to']");
        //     if (toInput) {
        //         toInput.focus();
        //         toInput.value = to.join(", ");
        //         toInput.dispatchEvent(new Event("input", { bubbles: true }));
        //     }
        // }


        sendResponse({ status: "done" });
    }
});

