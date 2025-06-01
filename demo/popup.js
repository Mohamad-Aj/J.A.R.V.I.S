// document.getElementById("generate").addEventListener("click", () => {
//     const prompt = document.getElementById("prompt").value;
//     const output = document.getElementById("output");

//     output.innerHTML = "⏳ Generating...";

//     fetch("https://jarvis-email-api.onrender.com/generate_email", {
//         method: "POST",
//         headers: {
//             "Content-Type": "application/json"
//         },
//         body: JSON.stringify({ prompt: prompt })
//     })
//         .then(response => response.json())
//         .then(data => {
//             if (data.error) {
//                 output.innerHTML = "❌ Error: " + data.error;
//             } else {
//                 output.innerHTML = `
//         <strong>Subject:</strong> ${data.subject}<br>
//         <strong>Body:</strong><br>
//         <pre>${data.body}</pre>
//         `;

//                 // Send subject and body to Gmail content script
//                 chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
//                     chrome.tabs.sendMessage(tabs[0].id, {
//                         action: "fill_email",
//                         subject: data.subject,
//                         body: data.body
//                     }, function (response) {
//                         if (chrome.runtime.lastError) {
//                             console.error("Could not inject:", chrome.runtime.lastError.message);
//                         } else {
//                             console.log("Injected successfully", response);
//                         }
//                     });
//                 });
//             }
//         });

// });



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
                output.innerHTML = "❌ Error: " + data.error;
            } else {
                output.innerHTML = "Email generated and injected into Gmail!";


                // ✅ Extract any emails from the prompt
                const toEmails = extractEmails(prompt);

                chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
                    chrome.tabs.sendMessage(tabs[0].id, {
                        action: "fill_email",
                        subject: data.subject,
                        body: data.body,
                        to: extractEmails(prompt) // ✅ Add this line only
                    }, function (response) {
                        if (chrome.runtime.lastError) {
                            console.error("Could not inject:", chrome.runtime.lastError.message);
                        } else {
                            console.log("Injected successfully", response);
                        }
                    });
                });
            }
        });
});

function extractEmails(text) {
    const regex = /[\w\.-]+@[\w\.-]+\.\w+/g;
    return text.match(regex) || [];
}

