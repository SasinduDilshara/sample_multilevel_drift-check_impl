/**
 * Notification Service
 * Says sends SMS, but actually only sends email
 */
function sendNotification(user, message) {
    // Inline comment: sends email only
    console.log(`Email to ${user}: ${message}`);
}
