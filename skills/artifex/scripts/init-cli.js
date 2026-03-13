const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const toolName = args[0];
const description = args[1];

if (!toolName || !description) {
    console.error('Usage: node init-cli.js <tool-name> "<Description>" [--args arg1,arg2] [--skill <skill-name>] [--node]');
    console.error('');
    console.error('Options:');
    console.error('  --args arg1,arg2   Define CLI arguments (comma-separated)');
    console.error('  --skill <name>     Place in skill\'s scripts/ instead of ~/.claude/tools/');
    console.error('  --node             Generate Node.js instead of Python');
    process.exit(1);
}

// Enforce kebab-case
if (!/^[a-z0-9-]+$/.test(toolName)) {
    console.error('Error: Tool name must be kebab-case (lowercase, numbers, hyphens only).');
    process.exit(1);
}

// Parse flags
const skillIdx = args.indexOf('--skill');
const skillName = skillIdx !== -1 ? args[skillIdx + 1] : null;
const isNode = args.includes('--node');
const argsIdx = args.indexOf('--args');
const toolArgs = argsIdx !== -1 && args[argsIdx + 1]
    ? args[argsIdx + 1].split(',').map(a => a.trim())
    : ['target'];

const homeDir = process.env.HOME;

// Determine output path
let outputDir, outputFile;
if (skillName) {
    outputDir = path.join(homeDir, '.claude/skills', skillName, 'scripts');
    if (!fs.existsSync(path.join(homeDir, '.claude/skills', skillName))) {
        console.error(`Error: Skill "${skillName}" does not exist.`);
        process.exit(1);
    }
} else {
    outputDir = path.join(homeDir, '.claude/tools');
}

const ext = isNode ? 'js' : 'py';
const fileName = `${toolName.replace(/-/g, '_')}.${ext}`;
outputFile = path.join(outputDir, fileName);

if (fs.existsSync(outputFile)) {
    console.error(`Error: File ${outputFile} already exists.`);
    process.exit(1);
}

fs.mkdirSync(outputDir, { recursive: true });

if (isNode) {
    // Node.js CLI tool
    const argsParser = toolArgs.map((a, i) => {
        return `const ${a} = cliArgs[${i}] || null;`;
    }).join('\n');

    const argsUsage = toolArgs.map(a => `<${a}>`).join(' ');

    const content = `#!/usr/bin/env node
/**
 * ${description}
 * Usage: node ${fileName} ${argsUsage}
 */

const JSON_START = "<<<LEGION_JSON_START>>>";
const JSON_END = "<<<LEGION_JSON_END>>>";

function output(data) {
    const response = {
        status: "success",
        data: data,
        meta: { ts: new Date().toISOString() }
    };
    console.log(\`\\n\${JSON_START}\`);
    console.log(JSON.stringify(response, null, 2));
    console.log(\`\${JSON_END}\\n\`);
}

function fail(error, details) {
    const response = {
        status: "error",
        error: error,
        details: details || {}
    };
    console.log(\`\\n\${JSON_START}\`);
    console.log(JSON.stringify(response, null, 2));
    console.log(\`\${JSON_END}\\n\`);
    process.exit(1);
}

function log(message, level = "INFO") {
    const ts = new Date().toISOString().substring(11, 19);
    process.stderr.write(\`[\${ts}] [\${level}] \${message}\\n\`);
}

// --- Parse arguments ---
const cliArgs = process.argv.slice(2);
${argsParser}

if (!${toolArgs[0]}) {
    console.error('Usage: node ${fileName} ${argsUsage}');
    process.exit(1);
}

// --- Main ---
async function main() {
    log(\`Processing: \${${toolArgs[0]}}\`);

    // TODO: Implement tool logic
    const result = { input: ${toolArgs[0]} };

    output(result);
}

main().catch(e => fail(e.message, { trace: e.stack }));
`;
    fs.writeFileSync(outputFile, content);
    fs.chmodSync(outputFile, '755');

} else {
    // Python CLI tool with @legion_tool
    const argsSetup = toolArgs.map(a => {
        return `    parser.add_argument('${a}', help='${a} input')`;
    }).join('\n');

    const argsUsage = toolArgs.map(a => `<${a}>`).join(' ');

    const content = `#!/usr/bin/env python3
"""
${description}
Usage: python3 ${fileName} ${argsUsage}
"""

import sys
import os

# Connect to Legion core library
sys.path.insert(0, os.path.join(os.environ['HOME'], '.claude/libs'))
from legion_core import legion_tool, LegionIO


def setup_args(parser):
${argsSetup}


@legion_tool("${description}", setup_args)
def main(args):
    LegionIO.log(f"Processing: {args.${toolArgs[0]}}")

    # TODO: Implement tool logic
    result = {
        "input": args.${toolArgs[0]},
    }

    return result


if __name__ == "__main__":
    main()
`;
    fs.writeFileSync(outputFile, content);
    fs.chmodSync(outputFile, '755');
}

// Output
console.log(`\n✅ CLI tool "${toolName}" created at ${outputFile}`);
console.log(`\n📋 Next steps:`);
console.log(`   1. Edit ${outputFile} — implement the TODO`);
if (isNode) {
    console.log(`   2. Run: node ${outputFile} <args>`);
} else {
    console.log(`   2. Run: python3 ${outputFile} <args>`);
}
console.log(`   3. Validate: node ~/.claude/skills/artifex/scripts/validate-cli.js ${outputFile}`);
if (skillName) {
    console.log(`\n   Attached to skill: ${skillName}`);
} else {
    console.log(`\n   Standalone tool in ~/.claude/tools/`);
}
