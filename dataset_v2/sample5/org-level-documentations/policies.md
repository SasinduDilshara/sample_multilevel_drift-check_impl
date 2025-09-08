# Policies

1. All passwords must be hashed before storage.
2. Sensitive data must be encrypted using AES-256.
3. Services must not expose internal implementation details.
4. Every API must use HTTPS.
5. All endpoints should include versioning in URLs.
6. Error messages must not leak sensitive info.
7. Each commit must be peer reviewed.
8. CI/CD pipelines must run security scans.
9. Logging must exclude sensitive PII data.
10. Environment variables must be used for secrets.
11. JWT tokens must expire within 15 minutes.
12. All microservices must implement health check endpoints.