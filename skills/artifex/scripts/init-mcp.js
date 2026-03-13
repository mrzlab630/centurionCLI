const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const serverName = args[0];
const description = args[1];

if (!serverName || !description) {
    console.error('Usage: node init-mcp.js <server-name> "<Description>" [--tools tool1,tool2]');
    process.exit(1);
}

// Enforce kebab-case
if (!/^[a-z0-9-]+$/.test(serverName)) {
    console.error('Error: Server name must be kebab-case (lowercase, numbers, hyphens only).');
    process.exit(1);
}

// Parse --tools flag
const toolsIdx = args.indexOf('--tools');
const toolNames = toolsIdx !== -1 && args[toolsIdx + 1]
    ? args[toolsIdx + 1].split(',').map(t => t.trim())
    : ['example-tool'];

const mcpRoot = path.join(process.env.HOME, '.claude/mcp-servers');
const serverDir = path.join(mcpRoot, serverName);

if (fs.existsSync(serverDir)) {
    console.error(`MCP server "${serverName}" already exists at ${serverDir}`);
    process.exit(1);
}

// Create structure
fs.mkdirSync(path.join(serverDir, 'src'), { recursive: true });

// package.json
const packageJson = {
    name: `@legion/${serverName}`,
    version: '1.0.0',
    description: description,
    type: 'module',
    main: 'dist/index.js',
    scripts: {
        build: 'tsc',
        start: 'node dist/index.js'
    },
    dependencies: {
        '@modelcontextprotocol/sdk': '^1.0.0',
        'zod': '^3.23.0'
    },
    devDependencies: {
        'typescript': '^5.5.0',
        '@types/node': '^22.0.0'
    }
};
fs.writeFileSync(
    path.join(serverDir, 'package.json'),
    JSON.stringify(packageJson, null, 2)
);

// tsconfig.json
const tsconfig = {
    compilerOptions: {
        target: 'ES2022',
        module: 'Node16',
        moduleResolution: 'Node16',
        outDir: './dist',
        rootDir: './src',
        strict: true,
        esModuleInterop: true,
        skipLibCheck: true,
        declaration: true
    },
    include: ['src/**/*']
};
fs.writeFileSync(
    path.join(serverDir, 'tsconfig.json'),
    JSON.stringify(tsconfig, null, 2)
);

// Generate tool definitions
const toolDefs = toolNames.map(name => {
    const camelName = name.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    return `
server.tool(
    '${name}',
    'TODO: Describe what ${name} does',
    {
        // Define input parameters with Zod
        input: z.string().describe('TODO: describe input'),
    },
    async ({ input }) => {
        // TODO: Implement ${name}
        return {
            content: [
                { type: 'text', text: JSON.stringify({ result: 'TODO: implement' }) }
            ]
        };
    }
);`;
}).join('\n');

// src/index.ts
const indexTs = `import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

const server = new McpServer({
    name: '${serverName}',
    version: '1.0.0',
});
${toolDefs}

async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('${serverName} MCP server running on stdio');
}

main().catch(console.error);
`;
fs.writeFileSync(path.join(serverDir, 'src/index.ts'), indexTs);

// .gitignore
fs.writeFileSync(path.join(serverDir, '.gitignore'), 'node_modules/\ndist/\n');

// Output
console.log(`\n✅ MCP server "${serverName}" created at ${serverDir}`);
console.log(`\n📋 Next steps:`);
console.log(`   1. cd ${serverDir}`);
console.log(`   2. npm install`);
console.log(`   3. Edit src/index.ts — implement tool logic`);
console.log(`   4. npm run build`);
console.log(`   5. Register in ~/.claude/settings.json:`);
console.log(`      "${serverName}": {`);
console.log(`        "command": "node",`);
console.log(`        "args": ["${path.join(serverDir, 'dist/index.js')}"]`);
console.log(`      }`);
console.log(`   6. Restart Claude Code`);
console.log(`\n🔍 Validate: node ~/.claude/skills/artifex/scripts/validate-mcp.js ${serverDir}`);
