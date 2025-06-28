// popup.js

// ─── wake up your Render container on popup open ───
fetch("https://jarvis-email-api.onrender.com/health").catch(() => { });

document.getElementById("generate").addEventListener("click", () => {
    const prompt = document.getElementById("prompt").value;
    const output = document.getElementById("output");

    output.innerHTML = "Generating...";

    fetch("https://jarvis-email-api.onrender.com/generate_email", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ prompt: prompt })
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                output.innerHTML = "Error: " + data.error;
            } else {
                output.innerHTML = "Email generated and injected into Gmail!";

                // ✅ Extract any emails from the prompt
                const toEmails = extractEmails(prompt);

                chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
                    chrome.tabs.sendMessage(tabs[0].id, {
                        action: "fill_email",
                        subject: data.subject,
                        body: data.body,
                        to: toEmails
                    }, function (response) {
                        if (chrome.runtime.lastError) {
                            console.error("Could not inject:", chrome.runtime.lastError.message);
                        } else {
                            console.log("Injected successfully", response);
                        }
                    });
                });
            }
        })
        .catch(err => {
            output.innerHTML = `Fetch error: ${err.message}`;
        });
});

function extractEmails(text) {
    const regex = /[\w\.-]+@[\w\.-]+\.\w+/g;
    return text.match(regex) || [];
}
