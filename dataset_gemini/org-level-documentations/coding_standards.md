# Gemini Commerce - Official Coding Standards

All code written for the Gemini Commerce platform must adhere to these standards.

1.  **Naming Conventions**:
    * Variables and function names must use `camelCase` (e.g., `userName`, `calculateTotal`).
    * Class, Struct, and Type names must use `PascalCase` (e.g., `OrderService`, `ProductDetails`).
    * Constants must use `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`).
2.  **Line Length**: The maximum line length is 120 characters.
3.  **Comments**: Code should be self-documenting where possible. Add comments only to explain complex logic or "why" something is done, not "what" it is doing.
4.  **API Documentation**: All public functions, classes, and methods must have API-level documentation (JSDoc, Javadoc, GoDoc, Docstrings, etc.).
5.  **Error Handling**: Do not use generic exceptions. Use specific, meaningful error types. Avoid swallowing exceptions.
6.  **Logging Format**: All log messages must follow the format: `[LEVEL] - {YYYY-MM-DD HH:mm:ss} - Message`.
7.  **No Magic Strings**: Use constants or enums instead of hardcoded strings for keys, identifiers, or statuses.
8.  **Function Size**: Functions should be small and have a single responsibility. A function should generally not exceed 50 lines of code.
9.  **Imports**: Imports should be organized and grouped by standard library, third-party, and internal modules.
10. **Code Formatting**: Use automated formatters for each language (e.g., `gofmt` for Go, `Prettier` for JS, `Black` for Python).
