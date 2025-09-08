# Gemini Commerce - Security Policies

Security is paramount. All services must comply with the following policies.

1.  **Password Hashing**: User passwords must be hashed using `bcrypt` with a work factor of at least 12. Never store passwords in plaintext.
2.  **Input Validation**: All user-provided input must be rigorously validated and sanitized on the server side to prevent XSS, SQL Injection, and other injection attacks.
3.  **No Hardcoded Secrets**: API keys, database credentials, and other secrets must not be hardcoded in the source code. They should be injected via environment variables or a secret management service.
4.  **Principle of Least Privilege**: Services and users should only have the minimum permissions required to perform their functions.
5.  **HTTPS Everywhere**: All communication between clients and the API gateway, and between services where possible, must use HTTPS.
6.  **Dependency Scanning**: Regularly scan project dependencies for known vulnerabilities.
7.  **Rate Limiting**: Implement rate limiting on sensitive endpoints (e.g., login, password reset) to prevent brute-force attacks.
8.  **Secure Headers**: APIs should return security-related HTTP headers like `Content-Security-Policy`, `X-Content-Type-Options`, etc.
9.  **PII Handling**: Personally Identifiable Information (PII) must be handled with care and encrypted at rest.
10. **Regular Audits**: The security team will conduct regular security audits.
