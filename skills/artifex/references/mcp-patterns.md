# MCP Server Patterns & Best Practices

Reference for ARTIFEX when forging MCP servers.

## 1. Architecture Rules

- **Stateless:** No in-memory state between tool calls. Each call is independent.
- **Stdio transport:** All Legion MCP servers use stdin/stdout (StdioServerTransport).
- **Zod validation:** Every tool input MUST have a Zod schema. No `any` types.
- **Error handling:** Return error in content, don't throw. Claude sees the error message.
- **Logging:** Use `console.error()` for logs (stderr). stdout is reserved for MCP protocol.

## 2. Tool Design Patterns

### Query Tool (read-only)
```typescript
server.tool(
    'query',
    'Execute a read-only SQL query',
    { sql: z.string().describe('SQL SELECT query') },
    async ({ sql }) => {
        // Validate: only SELECT allowed
        if (!/^\s*SELECT/i.test(sql)) {
            return { content: [{ type: 'text', text: 'Error: Only SELECT queries allowed' }] };
        }
        const result = await pool.query(sql);
        return { content: [{ type: 'text', text: JSON.stringify(result.rows, null, 2) }] };
    }
);
```

### Action Tool (write/mutate)
```typescript
server.tool(
    'restart-process',
    'Restart a PM2 process by name or id',
    { name: z.string().describe('PM2 process name or numeric id') },
    async ({ name }) => {
        const { stdout, stderr } = await execAsync(`pm2 restart ${name}`);
        return { content: [{ type: 'text', text: stdout || stderr }] };
    }
);
```

### Multi-Output Tool
```typescript
server.tool(
    'get-status',
    'Get system status with multiple data points',
    {},
    async () => {
        const [cpu, mem, disk] = await Promise.all([getCpu(), getMem(), getDisk()]);
        return {
            content: [
                { type: 'text', text: `CPU: ${cpu}%\nMemory: ${mem}%\nDisk: ${disk}%` }
            ]
        };
    }
);
```

## 3. Common MCP Servers for Legion

### postgres-mcp
```typescript
// Tools: query (SELECT only), execute (INSERT/UPDATE/DELETE with confirmation)
// Connection: use pg Pool with connection string from env
// Safety: parameterized queries, no raw string interpolation
import { Pool } from 'pg';
const pool = new Pool({ connectionString: process.env.DATABASE_URL });
```

### pm2-mcp
```typescript
// Tools: list, restart, logs, describe
// Uses: child_process.execAsync('pm2 ...')
// Safety: whitelist allowed process names
```

### solana-rpc-mcp
```typescript
// Tools: get-slot, get-balance, get-transaction, get-account-info
// Connection: JSON-RPC to localhost:8899
// Safety: read-only methods only
```

### redis-mcp
```typescript
// Tools: get, set, keys, del
// Connection: ioredis to localhost:6379
// Safety: key prefix restriction (e.g., only 'legion:*')
```

## 4. Registration in settings.json

```json
{
    "mcpServers": {
        "server-name": {
            "command": "node",
            "args": ["/home/user/.claude/mcp-servers/server-name/dist/index.js"],
            "env": {
                "DATABASE_URL": "postgresql://...",
                "CUSTOM_VAR": "value"
            }
        }
    }
}
```

**After registration:** Claude Code must be restarted. Tools become available as `mcp__server-name__tool-name`.

## 5. Validation Checklist

- [ ] `package.json` has `@modelcontextprotocol/sdk` and `zod`
- [ ] `src/index.ts` imports McpServer + StdioServerTransport
- [ ] Every tool has Zod input schema
- [ ] Every tool has a clear description
- [ ] No `TODO` placeholders in production code
- [ ] `npm run build` compiles without errors
- [ ] `dist/index.js` exists
- [ ] Registered in `~/.claude/settings.json`
- [ ] Tested: tool produces valid output
