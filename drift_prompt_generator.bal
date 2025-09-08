import ballerina/io;
import ballerina/lang.regexp;

string PROMPT = check io:fileReadString("drift_prompt.txt");

function getDriftPrompt(string sourceContent, string projectDoc, string componentDoc, string orgDoc) returns string {
    PROMPT = regexp:replace(re `\{\{SOURCE_FILES\}\}`, PROMPT, sourceContent);
    PROMPT = regexp:replace(re `\{\{PROJECT_DOCUMENTATION\}\}`, PROMPT, projectDoc);
    PROMPT = regexp:replace(re `\{\{COMPONENT_DOCUMENTATION\}\}`, PROMPT, componentDoc);
    PROMPT = regexp:replace(re `\{\{ORGANIZATION_DOCUMENTATION\}\}`, PROMPT, orgDoc);
    return PROMPT;
}
