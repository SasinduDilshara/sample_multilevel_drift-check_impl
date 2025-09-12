import ballerina/http;
import ballerina/log;
import ballerina/url;
import ballerina/lang.regexp;

# Verification service module for SMS-based user verification.
# Handles SMS message delivery for verification codes, notifications, and alerts.
# Integrates with external SMS providers via HTTP API.

// SMS provider API configuration
configurable string SMS_PROVIDER_BASE_URL = "https://api.twilio.com/2010-04-01";
configurable string SMS_SENDER_PHONE = "+1234567890";
configurable string SMS_ACCOUNT_SID = "1234567890abcdef";

# The value for the Sms provider token should handle in the user module
configurable string SMS_AUTH_TOKEN = "";

# SMS message types supported by the verification system.
# Each type applies specific formatting rules and delivery priorities.
public enum SMSType {
    ORDER_UPDATE,
    DELIVERY_ALERT,
    SECURITY_CODE,
    PROMOTIONAL,
    REMINDER
}

# SMS message request structure for verification and notification delivery.
# Contains recipient details, message content, and delivery preferences.
public type SMSMessage record {|
    # Recipient phone number (will be validated and formatted to E.164)
    string phoneNumber;
    # Message content to be sent
    string message;
    # Type of message for appropriate formatting
    SMSType messageType;
    # Optional scheduled delivery time (not implemented in current version)
    string? scheduledTime;
    # Message priority level: 1=normal, 2=high, 3=urgent
    int priority = 1;
|};

# SMS delivery response from the SMS provider API.
# Contains delivery confirmation and tracking details.
public type SMSResponse record {|
    # Unique message identifier from SMS provider
    string messageId;
    # Current delivery status (queued, sent, delivered, failed)
    string status;
    # Error description if delivery failed
    string? errorMessage;
    # Message cost in provider's currency (if available)
    decimal? cost;
|};

# Provider API response structure for successful SMS delivery
type ProviderSuccessResponse record {|
    string sid;
    string status;
    decimal? price;
|};

# Provider API response structure for error cases
type ProviderErrorResponse record {|
    string message;
|};

# Sends an SMS message through the configured SMS provider.
# Validates phone number format and applies message type formatting before delivery.
# + smsMessage - SMS content and delivery configuration
# + return - Delivery response with provider message ID and status, or error if delivery fails
public function sendSMSMessage(SMSMessage smsMessage) returns SMSResponse|error {
    // Validate and format phone number to E.164 standard
    string cleanPhone = check validateAndFormatPhoneNumber(smsMessage.phoneNumber);
    
    // Apply message type specific formatting
    string formattedMessage = check formatSMSContent(smsMessage.message, smsMessage.messageType);
    
    // Log warning for messages that may be split into multiple parts
    if (formattedMessage.length() > 160) {
        log:printWarn("SMS message exceeds 160 characters and may be sent as multiple parts", 
            length = formattedMessage.length(),
            phone = cleanPhone);
    }

    // Initialize HTTP client for SMS provider API
    http:Client smsProviderClient = check new(SMS_PROVIDER_BASE_URL, {
        auth: {
            username: SMS_ACCOUNT_SID,
            password: SMS_AUTH_TOKEN
        }
    });

    // Prepare form-encoded request body for SMS provider
    string encodedMessage = check url:encode(formattedMessage, "UTF-8");
    string requestBody = string`From=${SMS_SENDER_PHONE}&To=${cleanPhone}&Body=${encodedMessage}`;
    
    http:Request request = new;
    request.setTextPayload(requestBody);
    request.setHeader("Content-Type", "application/x-www-form-urlencoded");

    // Send SMS request to provider API
    string messagePath = "/Accounts/" + SMS_ACCOUNT_SID + "/Messages.json";
    http:Response response = check smsProviderClient->post(messagePath, request);
    
    if (response.statusCode == 201) {
        json responsePayload = check response.getJsonPayload();
        ProviderSuccessResponse successResponse = check responsePayload.cloneWithType(ProviderSuccessResponse);
        
        SMSResponse smsResponse = {
            messageId: successResponse.sid,
            status: successResponse.status,
            errorMessage: (),
            cost: successResponse.price
        };
        
        log:printInfo("SMS sent successfully", 
            messageId = smsResponse.messageId,
            phone = cleanPhone,
            status = smsResponse.status);
        
        return smsResponse;
    } else {
        json errorPayload = check response.getJsonPayload();
        ProviderErrorResponse errorResponse = check errorPayload.cloneWithType(ProviderErrorResponse);
        
        log:printError("SMS delivery failed", 
            statusCode = response.statusCode,
            errorMessage = errorResponse.message,
            phone = cleanPhone);
        
        SMSResponse failedResponse = {
            messageId: "",
            status: "failed",
            errorMessage: errorResponse.message,
            cost: ()
        };
        
        return failedResponse;
    }
}

# Validates and formats phone number to international E.164 standard.
# Removes formatting characters and adds country code if missing.
# + phoneNumber - Raw phone number input from user
# + return - Formatted phone number in E.164 format (+1234567890) or error for invalid numbers
function validateAndFormatPhoneNumber(string phoneNumber) returns string|error {
    // Remove all non-digit characters except leading plus sign
    regexp:RegExp cleanupPattern = check regexp:fromString("[^+\\d]");
    string cleaned = cleanupPattern.replaceAll(phoneNumber, "");
    
    // Add US country code if no country code is present
    if (!cleaned.startsWith("+")) {
        if (cleaned.length() == 10) {
            cleaned = "+1" + cleaned;
        } else if (cleaned.length() == 11 && cleaned.startsWith("1")) {
            cleaned = "+" + cleaned;
        } else {
            return error("Invalid phone number format: " + phoneNumber);
        }
    }
    
    // Validate final phone number length
    if (cleaned.length() < 10 || cleaned.length() > 15) {
        return error("Phone number length invalid: " + phoneNumber);
    }
    
    return cleaned;
}

# Applies message type specific formatting and required compliance text.
# Adds appropriate prefixes and suffixes based on message type and regulatory requirements.
# + message - Raw message content
# + messageType - Type of SMS message for formatting rules
# + return - Formatted message ready for delivery or error if formatting fails
function formatSMSContent(string message, SMSType messageType) returns string|error {
    string formattedMessage = message;
    
    match messageType {
        ORDER_UPDATE => {
            // Add order update identifier prefix
            formattedMessage = "[Order Update] " + message;
        }
        DELIVERY_ALERT => {
            // Add delivery alert identifier prefix
            formattedMessage = "[Delivery Alert] " + message;
        }
        SECURITY_CODE => {
            // Format security codes with clear instructions and validity period
            formattedMessage = "Your verification code is: " + message + ". Valid for 10 minutes. Do not share.";
        }
        PROMOTIONAL => {
            // Add required opt-out instructions for promotional messages
            formattedMessage = message + " Reply STOP to opt-out.";
        }
        REMINDER => {
            // Add reminder identifier prefix
            formattedMessage = "[Reminder] " + message;
        }
        _ => {
            // No additional formatting for unspecified types
            formattedMessage = message;
        }
    }
    
    return formattedMessage;
}

# Provider API response structure for status check
type ProviderStatusResponse record {|
    string status;
|};

# Retrieves current delivery status for a previously sent SMS message.
# Queries the SMS provider API for message delivery confirmation.
# + messageId - Provider message identifier returned from sendSMSMessage
# + return - Current delivery status string (queued, sent, delivered, failed) or error if query fails
public function checkSMSStatus(string messageId) returns string|error {
    http:Client smsProviderClient = check new(SMS_PROVIDER_BASE_URL, {
        auth: {
            username: SMS_ACCOUNT_SID,
            password: SMS_AUTH_TOKEN
        }
    });
    
    string statusPath = "/Accounts/" + SMS_ACCOUNT_SID + "/Messages/" + messageId + ".json";
    http:Response response = check smsProviderClient->get(statusPath);
    
    if (response.statusCode == 200) {
        json responsePayload = check response.getJsonPayload();
        ProviderStatusResponse statusResponse = check responsePayload.cloneWithType(ProviderStatusResponse);
        return statusResponse.status;
    } else {
        return error("Failed to retrieve SMS status for message: " + messageId);
    }
}

# Sends multiple SMS messages with basic error handling.
# Processes each message individually and collects all responses.
# Note: Current implementation does not include rate limiting delays.
# + messages - Array of SMS messages to be sent
# + return - Array of delivery responses corresponding to each input message
public function sendBulkSMS(SMSMessage[] messages) returns SMSResponse[]|error {
    SMSResponse[] responses = [];
    int totalMessages = messages.length();
    
    log:printInfo("Starting bulk SMS processing", totalMessages = totalMessages);
    
    int successCount = 0;
    int failureCount = 0;
    
    foreach int i in 0 ..< totalMessages {
        SMSMessage currentMessage = messages[i];
        
        do {
            SMSResponse response = check sendSMSMessage(currentMessage);
            responses.push(response);
            
            if (response.status != "failed") {
                successCount += 1;
            } else {
                failureCount += 1;
            }
        } on fail error e {
            // Create error response for failed message processing
            SMSResponse errorResponse = {
                messageId: "",
                status: "failed",
                errorMessage: "Message processing failed: " + e.message(),
                cost: ()
            };
            responses.push(errorResponse);
            failureCount += 1;
        }
    }
    
    log:printInfo("Bulk SMS processing completed", 
        totalMessages = totalMessages,
        successCount = successCount,
        failureCount = failureCount);
    
    return responses;
}
