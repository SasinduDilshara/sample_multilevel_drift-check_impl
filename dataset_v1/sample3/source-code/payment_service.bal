# Payment Service
# Org-level doc requires encryption (missing, violation)
service /payment on new http:Listener(8080) {

    resource function post pay(@http:Payload json payment) returns json {
        // No encryption used here - violates org guideline
        return { "status": "success" };
    }
}
