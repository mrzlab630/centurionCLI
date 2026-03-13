const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const filePath = args[0];

if (!filePath) {
    console.error('Usage: node validate-cli.js <path-to-cli-tool>');
    process.exit(1);
}

const fullPath = path.resolve(filePath);
const fileName = path.basename(fullPath);
const ext = path.extname(fullPath);

const errors = [];
const warnings = [];
const info = [];

// 1. Check file exists
if (!fs.existsSync(fullPath)) {
    console.error(`Error: File ${fullPath} does not exist.`);
    process.exit(1);
}

const content = fs.readFileSync(fullPath, 'utf8');

// 2. Detect language
const isPython = ext === '.py';
const isNode = ext === '.js';

if (!isPython && !isNode) {
    errors.push(`Unsupported extension "${ext}". Expected .py or .js`);
}

info.push(`Language: ${isPython ? 'Python' : 'Node.js'}`);

// 3. Check shebang
if (isPython && !content.startsWith('#!/usr/bin/env python3')) {
    warnings.push('Missing shebang: #!/usr/bin/env python3');
}
if (isNode && !content.startsWith('#!/usr/bin/env node')) {
    warnings.push('Missing shebang: #!/usr/bin/env node');
}

// 4. Check executable permission
try {
    fs.accessSync(fullPath, fs.constants.X_OK);
    info.push('Executable: YES');
} catch {
    warnings.push('File is not executable. Run: chmod +x ' + fullPath);
}

// 5. Language-specific checks
if (isPython) {
    // Check legion_core import
    if (!content.includes('from legion_core import') && !content.includes('import legion_core')) {
        errors.push('Missing import from legion_core. Add: from legion_core import legion_tool, LegionIO');
    }

    // Check @legion_tool decorator
    if (!content.includes('@legion_tool')) {
        errors.push('Missing @legion_tool decorator on main function.');
    } else {
        info.push('Decorator: @legion_tool found');
    }

    // Check sys.path setup for legion_core
    if (!content.includes("sys.path.insert") && !content.includes("PYTHONPATH")) {
        warnings.push('No sys.path.insert for legion_core. Tool may fail to import.');
    }

    // Check argparse setup
    if (content.includes('setup_args')) {
        const argMatches = content.match(/parser\.add_argument\(/g);
        if (argMatches) {
            info.push(`Arguments defined: ${argMatches.length}`);
        } else {
            warnings.push('setup_args function found but no parser.add_argument() calls.');
        }
    }

    // Check main guard
    if (!content.includes('if __name__')) {
        warnings.push('Missing if __name__ == "__main__" guard.');
    }
}

if (isNode) {
    // Check JSON markers
    if (!content.includes('LEGION_JSON_START') && !content.includes('<<<LEGION_JSON_START>>>')) {
        errors.push('Missing Legion JSON markers. Tool output won\'t be parseable by mission_control.');
    } else {
        info.push('JSON markers: found');
    }

    // Check output function
    if (!content.includes('function output') && !content.includes('const output')) {
        warnings.push('No output() function. Ensure structured JSON output with markers.');
    }

    // Check error handling
    if (!content.includes('.catch') && !content.includes('try')) {
        warnings.push('No error handling found. Uncaught errors won\'t produce structured output.');
    }
}

// 6. Universal checks
// Check for TODO placeholders
const todoMatches = content.match(/TODO/g);
if (todoMatches) {
    warnings.push(`${todoMatches.length} TODO placeholder(s) found — implement before use.`);
}

// Check for hardcoded paths
const homeMatches = content.match(/\/home\/[a-z]+\//g);
if (homeMatches) {
    warnings.push(`Hardcoded home path found (${homeMatches[0]}...). Use $HOME or os.environ.`);
}

// Check for secrets
const secretPatterns = [/API_KEY\s*=\s*['"][^'"]+['"]/g, /PASSWORD\s*=\s*['"][^'"]+['"]/g, /SECRET\s*=\s*['"][^'"]+['"]/g];
for (const pattern of secretPatterns) {
    if (pattern.test(content)) {
        errors.push('SECURITY: Hardcoded secret/API key found in source code!');
        break;
    }
}

// Check file size
const stats = fs.statSync(fullPath);
info.push(`Size: ${stats.size} bytes (${Math.round(stats.size / 1024 * 10) / 10} KB)`);
if (stats.size > 50000) {
    warnings.push('File is large (>50KB). Consider splitting into modules.');
}

// Report
console.log(`\n🔍 Validating CLI Tool: ${fileName}\n`);

if (info.length > 0) {
    console.log('ℹ️  INFO:');
    info.forEach(i => console.log(`   ${i}`));
}

if (errors.length > 0) {
    console.log('\n❌ CRITICAL ERRORS:');
    errors.forEach(e => console.log(`   - ${e}`));
    console.log('\nValidation FAILED.');
    process.exit(1);
} else {
    console.log('\n✅ Structure Valid.');
}

if (warnings.length > 0) {
    console.log('\n⚠️  WARNINGS:');
    warnings.forEach(w => console.log(`   - ${w}`));
} else {
    console.log('✨ Perfect!');
}
