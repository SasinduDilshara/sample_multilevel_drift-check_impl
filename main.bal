import ballerina/io;
import ballerina/os;

configurable string claudeKey = os:getEnv("ANTHROPIC_TOKEN");

public function main() returns error? {

    string sourceFilesXml = check buildSourceFilesXml(SOURCE_FILES_PATH);
    string projectDocs = check readAllDocsFromDir(PROJECT_DOCS_PATH);
    string componentDocs = check readAllDocsFromDir(COMPONENT_DOCS_PATH);

    string SOURCE_FILES = sourceFilesXml;
    string PROJECT_DOCUMENTATION = projectDocs;
    string COMPONENT_DOCUMENTATION = componentDocs;

    string driftPrompt = getDriftPrompt(SOURCE_FILES, PROJECT_DOCUMENTATION, COMPONENT_DOCUMENTATION);
    string sendToClaudeAPIResult = check sendToClaudeAPI(driftPrompt, claudeKey);
    io:println(sendToClaudeAPIResult);
}
