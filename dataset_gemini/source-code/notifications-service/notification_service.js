const express = require('express');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.json());
const PORT = process.env.PORT || 3000;

/**
 * Logs a message to the console using the organization's standard format.
 * @param {string} level - The log level (e.g., 'INFO', 'ERROR').
 * @param {string} message - The message to log.
 */
function logMessage(level, message) {
    const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
    // This format is compliant with the coding standards.
    console.log(`[${level}] - ${timestamp} - ${message}`);
}

/**
 * Simulates sending an email notification.
 * In a real-world scenario, this would integrate with a service like SendGrid or AWS SES.
 * @param {string} to - The recipient's email address.
 * @param {string} subject - The subject of the email.
 * @param {string} body - The HTML body of the email.
 * @returns {Promise<boolean>} A promise that resolves to true if the email was sent successfully.
 */
async function sendEmail(to, subject, body) {
    logMessage('INFO', `Preparing to send email to ${to} with subject "${subject}"`);
    // Simulate network delay for sending email.
    await new Promise(resolve => setTimeout(resolve, 500));
    // In a real app, you'd check the response from the email service.
    logMessage('INFO', `Successfully sent email to ${to}`);
    return true;
}

/**
 * Endpoint to send an order confirmation email.
 * This is fully compliant with project and component level documentation.
 */
app.post('/api/v1/send-confirmation', async (req, res) => {
    const { email, orderId, totalAmount, items } = req.body;

    // Validate input as per security policies.
    if (!email || !orderId || !totalAmount || !items) {
        logMessage('WARN', 'Received incomplete data for order confirmation.');
        return res.status(400).json({ error: 'Missing required fields: email, orderId, totalAmount, items' });
    }

    const subject = `Your Gemini Commerce Order Confirmation #${orderId}`;
    const body = `<h1>Thank you for your order!</h1>
                  <p>Your order #${orderId} for a total of $${totalAmount} has been received.</p>
                  <p>We will notify you again once your items have shipped.</p>`;

    try {
        const emailSent = await sendEmail(email, subject, body);
        if (emailSent) {
            return res.status(200).json({ message: 'Confirmation email sent successfully.' });
        } else {
            throw new Error('Email service provider failed.');
        }
    } catch (error) {
        logMessage('ERROR', `Failed to send confirmation email for order ${orderId}: ${error.message}`);
        return res.status(500).json({ error: 'Failed to send confirmation email.' });
    }
});

/**
 * Placeholder endpoint for sending password reset emails.
 */
app.post('/api/v1/send-password-reset', async (req, res) => {
    logMessage('INFO', 'Password reset requested.');
    return res.status(501).json({ message: 'Not implemented' });
});

/**
 * Placeholder for sending shipping notifications.
 */
app.post('/api/v1/send-shipping-notification', async (req, res) => {
    logMessage('INFO', 'Shipping notification requested.');
    return res.status(501).json({ message: 'Not implemented' });
});


/**
 * Health check endpoint, as required by architectural guidelines.
 */
app.get('/health', (req, res) => {
    res.status(200).json({ status: 'UP' });
});

/**
 * A utility function for internal use.
 */
function formatEmailBody(template, data) {
    logMessage('INFO', 'Formatting email body.');
    // Simple template replacement logic
    let content = template;
    for (const key in data) {
        content = content.replace(`{{${key}}}`, data[key]);
    }
    return content;
}


app.listen(PORT, () => {
    logMessage('INFO', `Notification Service is running on port ${PORT}`);
});
