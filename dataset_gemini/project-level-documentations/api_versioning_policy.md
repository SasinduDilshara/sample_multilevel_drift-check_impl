# API Versioning Policy

This document defines the API versioning strategy for the Gemini Commerce platform.

1.  **Mandatory Versioning**: All APIs must be versioned to ensure backward compatibility and smooth transitions for clients.
2.  **URL Path Versioning**: We use URL path versioning. The version must be included in the URL path directly after the domain.
3.  **Version Prefix**: The version prefix must be a 'v' followed by the version number (e.g., `v1`, `v2`).
4.  **Current Version**: The current stable version is `v1`.
5.  **Path Structure**: The standard path structure is `/{api-prefix}/{version}/{resource}`.
6.  **Example**: `https://api.geminicommerce.com/api/v1/users`
7.  **Deprecation Policy**: When a new API version is released, the previous version will be supported for at least 6 months. A `Warning` header will be added to responses from deprecated APIs.
8.  **Breaking Changes**: Any breaking change (e.g., removing a field, changing a data type) requires a major version increment (e.g., from `v1` to `v2`).
9.  **Non-Breaking Changes**: Adding new optional fields or new endpoints are considered non-breaking changes and do not require a version bump.
10. **Client Responsibility**: Clients should always specify the version they are targeting to avoid unexpected behavior.
