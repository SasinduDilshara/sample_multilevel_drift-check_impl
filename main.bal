// import ballerina/io;
import ballerina/io;
import ballerina/os;

configurable string claudeKey = os:getEnv("BAL_CODEGEN_ANTHROPIC_TOKEN");

public function main() returns error? {

    string sourceFilesXml = check buildSourceFilesXml(SOURCE_FILES_PATH);
    
    // string orgDocs = check readAllDocsFromDir(ORG_DOCS_PATH);
    string projectDocs = check readAllDocsFromDir(PROJECT_DOCS_PATH);
    string componentDocs = check readAllDocsFromDir(COMPONENT_DOCS_PATH);

    string SOURCE_FILES = sourceFilesXml;
    // string ORGANIZATION_DOCUMENTATION = orgDocs;
    string PROJECT_DOCUMENTATION = projectDocs;
    string COMPONENT_DOCUMENTATION = componentDocs;

    // io:println("--- ✅ Inputs Generated Successfully ---");

    // io:println("\n(ORGANIZATION_DOCUMENTATION) ---");
    // io:println(ORGANIZATION_DOCUMENTATION);

    // io:println("\n(PROJECT_DOCUMENTATION) ---");
    // io:println(PROJECT_DOCUMENTATION);
    
    // io:println("\n(COMPONENT_DOCUMENTATION) ---");
    // io:println(COMPONENT_DOCUMENTATION);

    // io:println("\n(SOURCE_FILES) ---");
    // io:println(SOURCE_FILES);

    // io:println(SOURCE_FILES == "" ? "No source files found." : "Source files loaded successfully.");

    string driftPrompt = getDriftPrompt(SOURCE_FILES, PROJECT_DOCUMENTATION, COMPONENT_DOCUMENTATION);
    string sendToClaudeAPIResult = check sendToClaudeAPI(driftPrompt, claudeKey);
    io:println(sendToClaudeAPIResult);
}
