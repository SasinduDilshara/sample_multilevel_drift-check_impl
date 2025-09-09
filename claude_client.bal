import ballerina/http;

// Claude API endpoint
const string CLAUDE_API_URL = "https://api.anthropic.com/v1/messages";

// Request payload for Claude API
type ClaudeRequest record {
    string model;
    int max_tokens;
    Message[] messages;
};

type Message record {
    string role;
    string content;
};

// Response from Claude API
type ClaudeResponse record {
    string id;
    string 'type;
    string role;
    Content[] content;
    string model;
    string stop_reason;
    Usage usage;
};

type Content record {
    string 'type;
    string text;
};

type Usage record {
    int input_tokens;
    int output_tokens;
};

// Function to send drift prompt to Claude API
function sendToClaudeAPI(string driftPrompt, string apiKey) returns string|error {
    
    // Create HTTP client
    http:Client claudeClient = check new (CLAUDE_API_URL);
    
    // Prepare the request payload
    ClaudeRequest request = {
        model: "claude-sonnet-4-20250514",
        max_tokens: 4000,
        messages: [
            {
                role: "user",
                content: driftPrompt
            }
        ]
    };
    
    // Prepare headers
    map<string> headers = {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01"
    };
    
    // Send the request
    http:Response response = check claudeClient->post("", request, headers);
    
    // Check if the response is successful
    if (response.statusCode != 200) {
        string errorMsg = check response.getTextPayload();
        return error("Claude API request failed with status " + response.statusCode.toString() + ": " + errorMsg);
    }
    
    // Parse the response
    json jsonPayload = check response.getJsonPayload();
    ClaudeResponse claudeResponse = check jsonPayload.fromJsonWithType();
    
    // Extract and return the response text
    if (claudeResponse.content.length() > 0) {
        return claudeResponse.content[0].text;
    } else {
        return error("No content received from Claude API");
    }
}
