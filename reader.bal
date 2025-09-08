import ballerina/io;
import ballerina/file;
import ballerina/lang.regexp;
const string DATA_ROOT = "/Users/admin/Desktop/multi-level-drift-check/multi-level-drift-check/dataset_gemini";
const string ORG_DOCS_PATH = "/Users/admin/Desktop/multi-level-drift-check/multi-level-drift-check/dataset_gemini/org-level-documentations";
const string PROJECT_DOCS_PATH = "/Users/admin/Desktop/multi-level-drift-check/multi-level-drift-check/dataset_gemini/project-level-documentations";
const string COMPONENT_DOCS_PATH = "/Users/admin/Desktop/multi-level-drift-check/multi-level-drift-check/dataset_gemini/component-level-documentations";
const string SOURCE_FILES_PATH = "/Users/admin/Desktop/multi-level-drift-check/multi-level-drift-check/dataset_gemini/source-code";

function readAllDocsFromDir(string dirPath) returns string|error {
    string content = "";
    file:MetaData[] & readonly dirEntries = check file:readDir(dirPath);

    foreach file:MetaData & readonly entry in dirEntries {
        string currentPath = entry.absPath;
        string relativePath = regexp:replace(re `${DATA_ROOT}`, currentPath, "");
        if entry.dir {
            content += check readAllDocsFromDir(currentPath);
        } else {
            string fileContent = check io:fileReadString(currentPath);
            content += string `\n\n---\nFile: ${relativePath}\n---\n${fileContent}`;
        }
    }
    return content;
}


function buildSourceFilesXml(string dirPath) returns string|error {
    string[] fileBlocks = [];
    file:MetaData[] & readonly dirEntries = check file:readDir(dirPath);

    foreach file:MetaData entry in dirEntries {
        if !entry.dir {
            string filePath = entry.absPath;
            string fileContent = check io:fileReadString(filePath);

            string relativePath = regexp:replace(re `${DATA_ROOT}/source-code`, filePath, "");

            string block = string `
    <file name="${relativePath}">
        ${fileContent}
    </file>`;
            fileBlocks.push(block);
        } else {
            string subDirXml = check buildSourceFilesXml(entry.absPath);
            string innerContent = regexp:replace(re `<source_files>`, subDirXml, "");
            innerContent = regexp:replace(re `</source_files>`, innerContent, "").trim();
            if innerContent != "" {
                fileBlocks.push(innerContent);
            }
        }
    }

    return string `<source_files>${string:'join("\n", ...fileBlocks)}\n</source_files>`;
}
