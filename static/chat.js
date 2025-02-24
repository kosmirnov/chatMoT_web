document.querySelector("form").addEventListener("submit", function (event) {
    event.preventDefault();
    const messageInput = document.querySelector(
        'textarea[name="message"]'
    );
    const message = messageInput.value.trim();
    const chatContainer = document.querySelector(".messages");

    // Append the user's message to the chat container (still displaying user input)
    if (message) {
        const roleDiv = document.createElement("div");
        roleDiv.classList.add("message-role");
        roleDiv.classList.add("user");

        roleDiv.textContent = "User";
        chatContainer.appendChild(roleDiv);

        const userMessageDiv = document.createElement("div");
        userMessageDiv.classList.add("user-message");
        userMessageDiv.textContent = message;
        chatContainer.appendChild(userMessageDiv);
    }

    // Clear the message input
    messageInput.value = "";

    // Send the user's input as registration to the server using AJAX
    fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ registration: message }), // Always send registration
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.success) {
                const roleDiv = document.createElement("div");
                roleDiv.classList.add("message-role");
                roleDiv.classList.add("assistant");
                roleDiv.textContent = "Model";
                chatContainer.appendChild(roleDiv);

                // Prepare the model message container (for streamed response)
                const assistantMessageDiv = document.createElement("div");
                assistantMessageDiv.classList.add("assistant-message");
                chatContainer.appendChild(assistantMessageDiv);

                // Open a connection to receive streamed responses from /stream endpoint
                const eventSource = new EventSource("/stream");
                eventSource.onmessage = function (event) {
                    const streamChunk = event.data; // Get chunk of streamed data
                    if (streamChunk.startsWith("Error:")) {
                        assistantMessageDiv.textContent = streamChunk; // Display error message
                        eventSource.close(); // Close stream on error
                    } else {
                        assistantMessageDiv.textContent += streamChunk; // Append chunk to message
                    }
                    // Scroll to bottom on each chunk
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                };
                eventSource.onerror = function (error) {
                    console.error("EventSource failed:", error); // Keep original error log
                    // Added detailed error logging:
                    console.error("EventSource error details:", error);
                    console.error("EventSource readyState:", eventSource.readyState);
                    console.error("EventSource URL:", eventSource.url);

                    assistantMessageDiv.textContent = "Error receiving response from model.";
                    eventSource.close(); // Close stream on error
                };
                eventSource.onclose = function() {
                    console.log("Stream closed."); // Optional: Log when stream closes
                };

            } else {
                // Handle error case (from /chat endpoint)
                alert("Error: " + data.error); // Basic error handling for /chat errors
            }
        });
});