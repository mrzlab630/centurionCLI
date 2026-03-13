const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const serverPath = args[0];

if (!serverPath) {
    console.error('Usage: node validate-mcp.js <path-to-mcp-server>');
    process.exit(1);
}

const serverDir = path.resolve(serverPath);
const folderName = path.basename(serverDir);

const errors = [];
const warnings = [];
const info = [];

// 1. Check directory exists
if (!fs.existsSync(serverDir)) {
    console.error(`Error: Directory ${serverDir} does not exist.`);
    process.exit(1);
}

// 2. Check naming (kebab-case)
if (!/^[a-z0-9-]+$/.test(folderName)) {
    errors.push(`Folder name "${folderName}" must be kebab-case.`);
}

// 3. Check package.json
const pkgPath = path.join(serverDir, 'package.json');
if (!fs.existsSync(pkgPath)) {
    errors.push('Missing package.json.');
} else {
    try {
        const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));

        if (!pkg.dependencies || !pkg.dependencies['@modelcontextprotocol/sdk']) {
            errors.push('Missing dependency: @modelcontextprotocol/sdk');
        }
        if (!pkg.dependencies || !pkg.dependencies['zod']) {
            warnings.push('Missing dependency: zod (recommended for input validation).');
        }
        if (!pkg.scripts || !pkg.scripts.build) {
            warnings.push('Missing "build" script in package.json.');
        }
        if (pkg.type !== 'module') {
            warnings.push('package.json should have "type": "module" for ESM imports.');
        }
        info.push(`Package: ${pkg.name}@${pkg.version}`);
    } catch (e) {
        errors.push(`Invalid package.json: ${e.message}`);
    }
}

// 4. Check tsconfig.json
const tsconfigPath = path.join(serverDir, 'tsconfig.json');
if (!fs.existsSync(tsconfigPath)) {
    warnings.push('Missing tsconfig.json (needed for TypeScript compilation).');
}

// 5. Check source files
const srcDir = path.join(serverDir, 'src');
if (!fs.existsSync(srcDir)) {
    errors.push('Missing src/ directory.');
} else {
    const indexPath = path.join(srcDir, 'index.ts');
    if (!fs.existsSync(indexPath)) {
        errors.push('Missing src/index.ts (server entry point).');
    } else {
        const content = fs.readFileSync(indexPath, 'utf8');

        // Check for MCP SDK imports
        if (!content.includes('McpServer') && !content.includes('Server')) {
            errors.push('src/index.ts does not import McpServer from MCP SDK.');
        }
        if (!content.includes('StdioServerTransport')) {
            errors.push('src/index.ts does not import StdioServerTransport.');
        }

        // Check for tool definitions
        const toolMatches = content.match(/server\.tool\s*\(/g);
        if (!toolMatches) {
            errors.push('No tools defined (no server.tool() calls found).');
        } else {
            info.push(`Tools defined: ${toolMatches.length}`);
        }

        // Check for TODO placeholders
        const todoMatches = content.match(/TODO/g);
        if (todoMatches) {
            warnings.push(`${todoMatches.length} TODO placeholder(s) found — implement before use.`);
        }

        // Check for Zod usage
        if (!content.includes('z.')) {
            warnings.push('No Zod schema validation found — all tool inputs should use Zod.');
        }
    }
}

// 6. Check compiled output
const distDir = path.join(serverDir, 'dist');
if (!fs.existsSync(distDir)) {
    warnings.push('No dist/ directory — run "npm run build" before registering.');
} else {
    const distIndex = path.join(distDir, 'index.js');
    if (!fs.existsSync(distIndex)) {
        warnings.push('dist/index.js not found — run "npm run build".');
    } else {
        info.push('Compiled: dist/index.js exists.');
    }
}

// 7. Check node_modules
if (!fs.existsSync(path.join(serverDir, 'node_modules'))) {
    warnings.push('No node_modules/ — run "npm install" first.');
}

// 8. Check settings.json registration
const settingsPath = path.join(process.env.HOME, '.claude/settings.json');
if (fs.existsSync(settingsPath)) {
    try {
        const settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
        const mcpServers = settings.mcpServers || {};
        if (mcpServers[folderName]) {
            info.push(`Registered in settings.json: YES`);
        } else {
            warnings.push(`Not registered in ~/.claude/settings.json — add "${folderName}" to mcpServers.`);
        }
    } catch (e) {
        warnings.push('Could not read settings.json.');
    }
}

// Report
console.log(`\n🔍 Validating MCP Server: ${folderName}\n`);

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
