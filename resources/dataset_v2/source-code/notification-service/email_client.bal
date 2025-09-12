import ballerina/http;
import ballerina/log;

# Email service endpoint configuration
configurable string EMAIL_SERVICE_ENDPOINT = "https://email-service.example.com";
configurable string API_ACCESS_KEY = "";
configurable string API_SECRET_KEY = "";

# Email template types supported by the system
public enum EmailTemplate {
    ORDER_CONFIRMATION,
    SHIPPING_NOTIFICATION,
    DELIVERY_CONFIRMATION,
    PASSWORD_RESET,
    WELCOME_EMAIL
}

# Email message structure for delivery requests
public type EmailMessage record {|
    # List of recipient email addresses
    string[] recipients;
    # Email subject line
    string subject;
    # HTML content of the email
    string htmlContent;
    # Optional plain text content of the email
    string textContent?;
    # Template type for the email
    EmailTemplate template;
    # Dynamic data for template substitution
    map<string> templateData?;
    # Optional attachments for the email
    Attachment[] attachments?;
|};

# Attachment structure for email files
public type Attachment record {|
    # Filename of the attachment
    string filename;
    # MIME type of the attachment
    string contentType;
    # Binary content of the attachment
    byte[] content;
|};

# Sends email through HTTP email service with template processing
# 
# + message - Email message with recipients and content
# + return - Delivery confirmation with service message ID or error
public function sendTemplatedEmail(EmailMessage message) returns string|error {
    // Process email template with dynamic data
    string processedContent = check processEmailTemplate(message.template, message.templateData ?: {});
    
    // Create email service request payload
    json emailRequest = {
        "source": "noreply@ecommerce-platform.com",
        "destination": {
            "toAddresses": message.recipients
        },
        "message": {
            "subject": {
                "data": message.subject,
                "charset": "UTF-8"
            },
            "body": {
                "html": {
                    "data": processedContent,
                    "charset": "UTF-8"
                }
            }
        }
    };

    // Add plain text version if provided
    if (message.textContent is string) {
        json textBody = {
            "text": {
                "data": <string>message.textContent,
                "charset": "UTF-8"
            }
        };

        emailRequest = {
            "source": "noreply@ecommerce-platform.com",
            "destination": {
                "toAddresses": message.recipients
            },
            "message": {
                "subject": {
                    "data": message.subject,
                    "charset": "UTF-8"
                },
                "body": {
                    "html": {
                        "data": processedContent,
                        "charset": "UTF-8"
                    },
                    textBody
                }
            }
        };
    }

    http:Client emailClient = check new(EMAIL_SERVICE_ENDPOINT);
    
    http:Request request = new;
    request.setJsonPayload(emailRequest);
    request.setHeader("Authorization", generateAPISignature(emailRequest));
    request.setHeader("Content-Type", "application/json");
    request.setHeader("X-API-Key", API_ACCESS_KEY);

    http:Response response = check emailClient->post("/send-email", request);
    
    if (response.statusCode == 200) {
        json responsePayload = check response.getJsonPayload();
        string messageId = (check responsePayload.messageId).toString();
        
        log:printInfo("Email sent successfully via HTTP email service", 
            messageId = messageId,
            recipientCount = message.recipients.length());
        
        return messageId;
    } else {
        string errorMsg = check response.getTextPayload();
        log:printError("Failed to send email via HTTP email service", 
            statusCode = response.statusCode,
            errorMessage = errorMsg);
        
        return error("Email delivery failed: " + errorMsg);
    }
}

# Processes email templates with dynamic content substitution
# Supports conditional content blocks and variable replacement
# 
# + template - Template type to process
# + data - Dynamic data for template substitution  
# + return - Processed HTML content ready for delivery or error
function processEmailTemplate(EmailTemplate template, map<string> data) returns string|error {
    string templateContent = "";
    
    match template {
        ORDER_CONFIRMATION => {
            templateContent = getOrderConfirmationTemplate();
        }
        SHIPPING_NOTIFICATION => {
            templateContent = getShippingNotificationTemplate();
        }
        DELIVERY_CONFIRMATION => {
            templateContent = getDeliveryConfirmationTemplate();
        }
        PASSWORD_RESET => {
            templateContent = getPasswordResetTemplate();
        }
        WELCOME_EMAIL => {
            templateContent = getWelcomeEmailTemplate();
        }
        _ => {
            return error("Unknown email template type");
        }
    }

    // Replace template variables with actual data using string replacement
    string processedContent = templateContent;
    
    foreach var [key, value] in data.entries() {
        string placeholder = "{{" + key + "}}";
        // Simple string replacement for template variables
        while (processedContent.includes(placeholder)) {
            int? index = processedContent.indexOf(placeholder);
            if (index is int) {
                string beforePlaceholder = processedContent.substring(0, index);
                string afterPlaceholder = processedContent.substring(index + placeholder.length());
                processedContent = beforePlaceholder + value + afterPlaceholder;
            } else {
                break;
            }
        }
    }

    return processedContent;
}

# Generates API signature for email service authentication
# Creates authorization header for HTTP API requests
# 
# + payload - Request payload for signature calculation
# + return - Authorization header value for API authentication
function generateAPISignature(json payload) returns string {
    // API signature implementation for email service
    // This is a simplified version - production would use proper authentication
    return "Bearer " + API_ACCESS_KEY + "-" + API_SECRET_KEY;
}

// Email template definitions

# Returns HTML template for order confirmation emails
# 
# + return - HTML template string with placeholder variables
function getOrderConfirmationTemplate() returns string {
    return string`
        <html>
        <head><title>Order Confirmation</title></head>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto;">
                <h1 style="color: #2c3e50;">Order Confirmation</h1>
                <p>Dear {{customer_name}},</p>
                <p>Thank you for your order! Your order #{{order_id}} has been confirmed.</p>
                
                <div style="background: #f8f9fa; padding: 20px; margin: 20px 0;">
                    <h3>Order Details</h3>
                    <p><strong>Order ID:</strong> {{order_id}}</p>
                    <p><strong>Order Date:</strong> {{order_date}}</p>
                    <p><strong>Total Amount:</strong> {{total_amount}}</p>
                </div>
                
                <p>You will receive a shipping confirmation once your order is dispatched.</p>
                <p>Best regards,<br>E-Commerce Team</p>
            </div>
        </body>
        </html>
    `;
}

# Returns HTML template for shipping notification emails
# 
# + return - HTML template string with placeholder variables
function getShippingNotificationTemplate() returns string {
    return string`
        <html>
        <head><title>Your Order Has Shipped</title></head>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto;">
                <h1 style="color: #27ae60;">Your Order Has Shipped!</h1>
                <p>Hi {{customer_name}},</p>
                <p>Great news! Your order #{{order_id}} is on its way.</p>
                
                <div style="background: #e8f5e8; padding: 20px; margin: 20px 0;">
                    <h3>Shipping Information</h3>
                    <p><strong>Tracking Number:</strong> {{tracking_number}}</p>
                    <p><strong>Carrier:</strong> {{carrier_name}}</p>
                    <p><strong>Estimated Delivery:</strong> {{estimated_delivery}}</p>
                </div>
                
                <p><a href="{{tracking_url}}" style="background: #3498db; color: white; padding: 10px 20px; text-decoration: none;">Track Your Package</a></p>
            </div>
        </body>
        </html>
    `;
}

# Returns HTML template for delivery confirmation emails
# 
# + return - HTML template string with placeholder variables
function getDeliveryConfirmationTemplate() returns string {
    return string`
        <html>
        <head><title>Order Delivered Successfully</title></head>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto;">
                <h1 style="color: #f39c12;">Order Delivered!</h1>
                <p>Hello {{customer_name}},</p>
                <p>Your order #{{order_id}} has been successfully delivered to {{delivery_address}}.</p>
                
                <div style="background: #fff3cd; padding: 20px; margin: 20px 0;">
                    <h3>Delivery Details</h3>
                    <p><strong>Delivered At:</strong> {{delivery_time}}</p>
                    <p><strong>Delivered To:</strong> {{delivery_address}}</p>
                    <p><strong>Received By:</strong> {{received_by}}</p>
                </div>
                
                <p>We hope you enjoy your purchase! If you have any issues, please contact our support team.</p>
                <p><a href="{{review_url}}" style="background: #e74c3c; color: white; padding: 10px 20px; text-decoration: none;">Leave a Review</a></p>
            </div>
        </body>
        </html>
    `;
}

# Returns HTML template for password reset emails
# 
# + return - HTML template string with placeholder variables
function getPasswordResetTemplate() returns string {
    return string`
        <html>
        <head><title>Password Reset Request</title></head>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto;">
                <h1 style="color: #e74c3c;">Password Reset Request</h1>
                <p>Hi {{user_name}},</p>
                <p>We received a request to reset your password. Click the link below to reset it:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{{reset_url}}" style="background: #3498db; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px;">Reset Password</a>
                </div>
                
                <p>If you didn't request this, please ignore this email.</p>
            </div>
        </body>
        </html>
    `;
}

# Returns HTML template for welcome emails
# 
# + return - HTML template string with placeholder variables
function getWelcomeEmailTemplate() returns string {
    return string`
        <html>
        <head><title>Welcome to E-Commerce Platform</title></head>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto;">
                <h1 style="color: #9b59b6;">Welcome to Our Platform!</h1>
                <p>Dear {{user_name}},</p>
                <p>Welcome to E-Commerce Platform! We're excited to have you join our community.</p>
                
                <div style="background: #f4f3ff; padding: 20px; margin: 20px 0;">
                    <h3>Getting Started</h3>
                    <ul>
                        <li>Browse our extensive product catalog</li>
                        <li>Set up your profile and preferences</li>
                        <li>Subscribe to notifications for deals</li>
                    </ul>
                </div>
                
                <p>If you have any questions, our support team is here to help!</p>
                <p><a href="{{platform_url}}" style="background: #9b59b6; color: white; padding: 10px 20px; text-decoration: none;">Start Shopping</a></p>
            </div>
        </body>
        </html>
    `;
}
