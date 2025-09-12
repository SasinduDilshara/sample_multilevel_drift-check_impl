import ballerina/http;
import ballerina/log;
import ballerina/crypto;

# Represents the credentials provided by the user for login.
#
# + email - The user's email address.
# + password - The user's plaintext password.
type Credentials record {
    string email;
    string password;
};

# Represents the tokens returned upon successful authentication.
# The `accessToken` is short-lived and used for API requests.
#
# + accessToken - The JWT access token.
type AuthResponse record {
    string accessToken;
};

// In-memory user store for demonstration purposes.
map<record {|string userId; string email; string hashedPassword;
|}> userDatabase = {
    "user1": {userId: "user1", email: "test@example.com", hashedPassword: "$2a$12$R9h.c8YJOh2joz435m9g1eA5gPOBjrSIT.sTUnxAKv5vj2w2p4v3K"} // password is "password123"
};

service /api/v1 on new http:Listener(8080) {
    # Authenticates a user and provides a JWT.
    #
    # + caller - The HTTP caller object.
    # + request - The HTTP request containing the user credentials.
    # - return - An `AuthResponse` with the token or an error.
    resource function post login(http:Caller caller, http:Request request) returns error? {
        // Attempt to decode the JSON payload from the request.
        var payload = request.getJsonPayload();
        if (payload is error) {
            log:printError("Error parsing JSON payload", payload);
            check caller->respond(createErrorResponse(http:STATUS_BAD_REQUEST, "Invalid JSON format"));
            return;
        }

        // Validate the payload against the Credentials type.
        Credentials|error credentials = payload.cloneWithType(Credentials);
        if (credentials is error) {
            log:printError("Error validating credentials structure", credentials);
            check caller->respond(createErrorResponse(http:STATUS_BAD_REQUEST, "Missing or invalid fields: email, password"));
            return;
        }

        // Find the user in our mock database.
        record{|string userId; string email; string hashedPassword;|}[] foundUser = from var user in userDatabase
            where user.email == credentials.email
            select user;

        // We get an array, so we check if it has at least one element.
        if (foundUser.length() == 0) {
            log:printWarn("Login attempt for non-existent user: " + credentials.email);
            check caller->respond(createErrorResponse(http:STATUS_UNAUTHORIZED, "Invalid email or password"));
            return;
        }

        // Check if the provided password matches the stored hash.
        // crypto:bcryptVerify returns true on match, false on mismatch.
        boolean isMatch = check crypto:verifyBcrypt(credentials.password, foundUser[0].hashedPassword);

        if (!isMatch) {
            log:printWarn("Failed login attempt for user: " + credentials.email);
            check caller->respond(createErrorResponse(http:STATUS_UNAUTHORIZED, "Invalid email or password"));
            return;
        }

        // If credentials are valid, generate a token.
        string token = generateMockJwt(foundUser[0].userId);
        log:printInfo("User authenticated successfully: " + credentials.email);

        AuthResponse authResponse = {accessToken: token};

        // Respond to the client with the token.
        http:Response response = new;
        response.setJsonPayload(authResponse.toJson());
        response.statusCode = http:STATUS_OK;
        check caller->respond(response);
    }
}

# A mock function to generate a JWT-like string.
# In a real application, this would use a proper JWT library.
#
# + userId - The ID of the user to include in the token payload.
# - return - A base64 encoded mock JWT string.
function generateMockJwt(string userId) returns string {
    // This is not a real JWT, just for demonstration.
    string header = "{\"alg\":\"HS256\",\"typ\":\"JWT\"}";
    string payload = string `{
        "sub": "${userId}", "name": "Test User", "iat": 1516239022
    }`;
    string signature = "mockSignature";
    return header + "." + payload + "." + signature;
}


# Creates a standardized HTTP error response.
#
# + statusCode - The HTTP status code to use.
# + message - The error message to include in the response body.
# - return - An HTTP response object representing the error.
function createErrorResponse(int statusCode, string message) returns http:Response {
    http:Response response = new;
    response.statusCode = statusCode;
    json errorPayload = {'error: message};
    response.setJsonPayload(errorPayload);
    return response;
}

# A placeholder function for future use, demonstrating file structure.
#
# - return - A boolean indicating status.
function performHealthCheck() returns boolean {
    // In a real service, this would check database connections, etc.
    log:printInfo("Health check performed successfully.");
    return true;
}

# Another placeholder function.
#
# + token - The token to be refreshed.
# - return - A new access token string.
function refreshToken(string token) returns string|error {
    // Logic to validate the refresh token and issue a new access token
    // would go here.
    if (token.length() == 0) {
        return error("Invalid token");
    }
    log:printInfo("Token refresh requested.");
    return generateMockJwt("user1");
}
