#!/usr/bin/env node

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { join } from 'node:path';
import { homedir } from 'node:os';
import { VectorStore } from './store.js';
import { MarkdownIndexer } from './indexer.js';
import { NomicEmbeddingProvider } from './embeddings/nomic.js';

const DATA_PATH = join(homedir(), '.claude', 'mcp-servers', 'memoria', 'data', 'memoria.json');

// --- Initialize components ---
const embedder = new NomicEmbeddingProvider();
const store = new VectorStore(DATA_PATH, embedder.modelName, embedder.dimensions);
const indexer = new MarkdownIndexer(store, embedder);

// --- MCP Server ---
const server = new McpServer({
  name: 'memoria',
  version: '1.2.0',
});

// Tool: memory_search — semantic search with lazy reindex
server.tool(
  'memory_search',
  'Semantic search across Legion memory files. Returns the most relevant chunks for a natural language query.',
  {
    query: z.string().describe('Natural language search query'),
    top_k: z.number().optional().default(5).describe('Max results to return (default 5)'),
    threshold: z.number().optional().default(0.3).describe('Minimum similarity score 0-1 (default 0.3)'),
    recency_boost: z.boolean().optional().default(true).describe('Boost recent memories in ranking (default true)'),
    expand_context: z.boolean().optional().default(false).describe('Include ±1 neighboring chunks for high-scoring results (score >0.7)'),
  },
  async ({ query, top_k, threshold, recency_boost, expand_context }) => {
    if (!embedder.isReady()) {
      await embedder.initialize();
    }

    // Lazy reindex: fire-and-forget if stale >5m
    if (indexer.isStale() && !indexer.isReindexing) {
      indexer.triggerLazyReindex();
    }

    const queryEmbedding = await embedder.embedQuery(query);
    const results = store.search(queryEmbedding, top_k, threshold, recency_boost);

    if (results.length === 0) {
      return {
        content: [{ type: 'text' as const, text: 'No relevant memories found.' }],
      };
    }

    const formatted = results.map((r, i) => {
      let entry = `[${i + 1}] Score: ${r.score.toFixed(3)} | ${r.source}:${r.startLine}\n` +
        (r.heading ? `    Heading: ${r.heading}\n` : '') +
        (r.breadcrumb && r.breadcrumb !== r.heading ? `    Context: ${r.breadcrumb}\n` : '') +
        `    ${r.text.slice(0, 500)}${r.text.length > 500 ? '...' : ''}`;

      // Context expansion: attach neighbor chunks for high-confidence results
      if (expand_context && r.score >= 0.7) {
        const neighbors = store.getNeighborChunks(r.id, 1);
        if (neighbors.length > 0) {
          const neighborText = neighbors
            .map(n => `      [neighbor] ${n.metadata.heading || 'no heading'}: ${n.text.slice(0, 300)}${n.text.length > 300 ? '...' : ''}`)
            .join('\n');
          entry += `\n${neighborText}`;
        }
      }

      return entry;
    }).join('\n\n');

    return {
      content: [{ type: 'text' as const, text: `Found ${results.length} results:\n\n${formatted}` }],
    };
  },
);

// Tool: memory_reindex — rescan all memory directories and rebuild index
server.tool(
  'memory_reindex',
  'Rescan all Legion memory directories (~/.claude/projects/*/memory/ and ~/.claude/skills/*/memory/) and update the vector index. Use force=true to rebuild from scratch.',
  {
    force: z.boolean().optional().default(false).describe('Force full rebuild (default: incremental)'),
  },
  async ({ force }) => {
    if (!embedder.isReady()) {
      await embedder.initialize();
    }

    const result = await indexer.indexAll(force);

    return {
      content: [{
        type: 'text' as const,
        text: `Reindex complete:\n` +
          `  Files scanned: ${result.filesScanned}\n` +
          `  Chunks added: ${result.chunksAdded}\n` +
          `  Chunks removed: ${result.chunksRemoved}\n` +
          `  Chunks unchanged: ${result.chunksUnchanged}\n` +
          `  Total chunks: ${store.chunkCount}\n` +
          (result.errors.length > 0 ? `  Errors:\n${result.errors.map(e => `    - ${e}`).join('\n')}` : ''),
      }],
    };
  },
);

// Tool: memory_store — manually store a text memory
server.tool(
  'memory_store',
  'Manually store a text snippet in semantic memory (for insights discovered during conversation).',
  {
    text: z.string().describe('Text content to memorize'),
    source: z.string().optional().describe('Source identifier (default: "manual")'),
    heading: z.string().optional().default('').describe('Optional heading/topic for the memory'),
  },
  async ({ text, source, heading }) => {
    if (!embedder.isReady()) {
      await embedder.initialize();
    }

    const { createHash } = await import('node:crypto');
    const actualSource = source || `manual:${new Date().toISOString()}`;
    const id = createHash('sha256').update(actualSource + ':' + text).digest('hex').slice(0, 16);

    const prefix = heading ? `${heading}\n\n` : '';
    const embedding = await embedder.embedDocument(prefix + text);

    store.add({
      id,
      text,
      source: actualSource,
      metadata: {
        heading: heading || '',
        breadcrumb: heading || '',
        startLine: 0,
        endLine: 0,
        indexedAt: new Date().toISOString(),
        fileModified: new Date().toISOString(),
      },
      embedding,
    });
    store.save();

    return {
      content: [{ type: 'text' as const, text: `Stored memory chunk: ${id} (${text.length} chars)` }],
    };
  },
);

// Tool: memory_forget — remove memories by source or id
server.tool(
  'memory_forget',
  'Remove memories from the vector store by source file path or chunk ID.',
  {
    source: z.string().optional().describe('Remove all chunks from this source file'),
    id: z.string().optional().describe('Remove a specific chunk by ID'),
  },
  async ({ source, id }) => {
    let removed = 0;
    if (id) {
      removed = store.removeById(id);
    } else if (source) {
      removed = store.removeBySource(source);
    } else {
      return {
        content: [{ type: 'text' as const, text: 'Provide either source or id to remove.' }],
      };
    }
    store.save();
    return {
      content: [{ type: 'text' as const, text: `Removed ${removed} chunk(s). Total remaining: ${store.chunkCount}` }],
    };
  },
);

// Tool: memory_list — list all memories grouped by source
server.tool(
  'memory_list',
  'List all stored memories grouped by source. Filter by "manual" (runtime-stored) or "files" (indexed from .md files).',
  {
    filter: z.enum(['manual', 'files', 'all']).optional().default('all').describe('Filter: "manual" = runtime memories, "files" = indexed .md files, "all" = everything'),
  },
  async ({ filter }) => {
    const listFilter = filter === 'all' ? undefined : filter as 'manual' | 'files';
    const groups = store.listChunks(listFilter);

    if (groups.length === 0) {
      return {
        content: [{ type: 'text' as const, text: `No memories found (filter: ${filter}).` }],
      };
    }

    const formatted = groups.map(g => {
      const headings = g.headings.length > 0 ? `\n    Topics: ${g.headings.join(', ')}` : '';
      return `  ${g.source}\n    Chunks: ${g.count} | Modified: ${g.modified.slice(0, 10)}${headings}`;
    }).join('\n\n');

    return {
      content: [{
        type: 'text' as const,
        text: `MEMORIA — ${groups.length} sources (filter: ${filter}):\n\n${formatted}`,
      }],
    };
  },
);

// Tool: memory_status — show index statistics
server.tool(
  'memory_status',
  'Show current memory index statistics: chunk count, sources, model info.',
  {},
  async () => {
    const sources = store.getSources();
    const sourceList = Array.from(sources.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([s, n]) => `  ${s} (${n} chunks)`)
      .join('\n');

    const lastReindex = store.lastReindexTime
      ? new Date(store.lastReindexTime).toLocaleString()
      : 'never';

    const stats = store.getStats();

    return {
      content: [{
        type: 'text' as const,
        text: `MEMORIA Status (v1.2.0):\n` +
          `  Model: ${embedder.modelName}\n` +
          `  Dimensions: ${embedder.dimensions}\n` +
          `  Storage: INT8 quantized (base64)\n` +
          `  Model loaded: ${embedder.isReady()}\n` +
          `  Total chunks: ${store.chunkCount}\n` +
          `  Avg chunk size: ${stats.avgChunkSize} chars\n` +
          `  Sources: ${stats.sourceCount} files\n` +
          `  Stale chunks (>90d): ${stats.staleCount}\n` +
          `  Oldest file: ${stats.oldestFile.slice(0, 10)}\n` +
          `  Newest file: ${stats.newestFile.slice(0, 10)}\n` +
          `  Last reindex: ${lastReindex}\n` +
          `  Reindex stale: ${indexer.isStale() ? 'yes (>5m)' : 'no'}\n` +
          `  Source details:\n${sourceList || '  (empty)'}`,
      }],
    };
  },
);

// --- Startup ---
async function main() {
  // Load existing store from disk (auto-migrates v1 -> v2)
  store.load();

  const transport = new StdioServerTransport();
  await server.connect(transport);

  // Auto-reindex in background (non-blocking)
  indexer.indexAll(false).then(result => {
    if (result.chunksAdded > 0 || result.chunksRemoved > 0) {
      process.stderr.write(
        `MEMORIA: auto-reindex — +${result.chunksAdded} -${result.chunksRemoved} =${result.chunksUnchanged} (total: ${store.chunkCount})\n`,
      );
    }
  }).catch(err => {
    process.stderr.write(`MEMORIA: auto-reindex failed — ${err}\n`);
  });
}

main().catch((err) => {
  process.stderr.write(`MEMORIA fatal: ${err}\n`);
  process.exit(1);
});
