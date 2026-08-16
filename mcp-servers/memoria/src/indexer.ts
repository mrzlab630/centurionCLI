import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { homedir } from 'node:os';
import { chunkMarkdown } from './chunker.js';
import type { VectorStore, ChunkInput } from './store.js';
import type { EmbeddingProvider } from './embeddings/provider.js';

export interface IndexResult {
  filesScanned: number;
  chunksAdded: number;
  chunksRemoved: number;
  chunksUnchanged: number;
  errors: string[];
}

const STALE_THRESHOLD_MS = 5 * 60 * 1000; // 5 minutes

/**
 * MarkdownIndexer — scans memory directories, chunks markdown, embeds, stores.
 * Incremental: only re-embeds files that changed (by mtime).
 * Lazy reindex: auto-triggers if >5 minutes since last reindex.
 */
export class MarkdownIndexer {
  private readonly scanPaths: string[];
  private _isReindexing = false;
  private lastReindexMs = 0;

  constructor(
    private readonly store: VectorStore,
    private readonly embedder: EmbeddingProvider,
  ) {
    const home = homedir();
    this.scanPaths = [
      join(home, '.claude', 'projects'),
      join(home, '.claude', 'skills'),
    ];
    // Restore lastReindexTime from persisted store
    const stored = store.lastReindexTime;
    if (stored) {
      this.lastReindexMs = new Date(stored).getTime();
    }
  }

  get isReindexing(): boolean {
    return this._isReindexing;
  }

  isStale(): boolean {
    return Date.now() - this.lastReindexMs > STALE_THRESHOLD_MS;
  }

  /** Fire-and-forget lazy reindex. Non-blocking, safe to call from search path. */
  triggerLazyReindex(): void {
    if (this._isReindexing || !this.isStale()) return;
    this.indexAll(false).then(result => {
      if (result.chunksAdded > 0 || result.chunksRemoved > 0) {
        process.stderr.write(
          `MEMORIA: lazy reindex — +${result.chunksAdded} -${result.chunksRemoved} =${result.chunksUnchanged} (total: ${this.store.chunkCount})\n`,
        );
      }
    }).catch(err => {
      process.stderr.write(`MEMORIA: lazy reindex failed — ${err}\n`);
    });
  }

  async indexAll(force: boolean = false): Promise<IndexResult> {
    this._isReindexing = true;
    try {
      return await this._indexAll(force);
    } finally {
      this._isReindexing = false;
      this.lastReindexMs = Date.now();
      this.store.setLastReindexTime(new Date().toISOString());
    }
  }

  private async _indexAll(force: boolean): Promise<IndexResult> {
    const result: IndexResult = {
      filesScanned: 0,
      chunksAdded: 0,
      chunksRemoved: 0,
      chunksUnchanged: 0,
      errors: [],
    };

    if (force) {
      result.chunksRemoved = this.store.chunkCount;
      this.store.clear();
    }

    const files = this.discoverFiles();
    result.filesScanned = files.length;

    const currentSources = new Set(files);

    // Remove chunks for deleted files (keep manual memories)
    const storedSources = this.store.getSources();
    for (const [source] of storedSources) {
      if (source.startsWith('manual:')) continue;
      if (!currentSources.has(source)) {
        result.chunksRemoved += this.store.removeBySource(source);
      }
    }

    // Index new or changed files
    for (const filePath of files) {
      try {
        const stat = statSync(filePath);
        const mtime = stat.mtime.toISOString();
        const storedMtime = this.store.getFileModified(filePath);

        if (!force && storedMtime === mtime) {
          const sourceChunks = this.store.getSources().get(filePath) || 0;
          result.chunksUnchanged += sourceChunks;
          continue;
        }

        // File changed or new — re-index
        result.chunksRemoved += this.store.removeBySource(filePath);

        const content = readFileSync(filePath, 'utf-8');
        if (content.trim().length < 50) continue;

        const chunks = chunkMarkdown(content, filePath);

        // Embed all chunks — use breadcrumb for richer semantic context
        const texts = chunks.map(c => {
          const prefix = c.breadcrumb || c.heading;
          return prefix ? `${prefix}\n\n${c.text}` : c.text;
        });

        const embeddings = await this.embedder.embedDocumentBatch(texts);

        for (let i = 0; i < chunks.length; i++) {
          const input: ChunkInput = {
            id: chunks[i].id,
            text: chunks[i].text,
            source: filePath,
            metadata: {
              heading: chunks[i].heading,
              breadcrumb: chunks[i].breadcrumb,
              startLine: chunks[i].startLine,
              endLine: chunks[i].endLine,
              indexedAt: new Date().toISOString(),
              fileModified: mtime,
            },
            embedding: embeddings[i],
          };
          this.store.add(input);
          result.chunksAdded++;
        }
      } catch (err) {
        result.errors.push(`${filePath}: ${err instanceof Error ? err.message : String(err)}`);
      }
    }

    this.store.save();
    return result;
  }

  private discoverFiles(): string[] {
    const files: string[] = [];

    for (const basePath of this.scanPaths) {
      if (!existsSync(basePath)) continue;

      try {
        const entries = readdirSync(basePath, { withFileTypes: true });
        for (const entry of entries) {
          if (!entry.isDirectory()) continue;
          const memoryDir = join(basePath, entry.name, 'memory');
          this.scanDir(memoryDir, files);
        }
      } catch {
        // Skip inaccessible directories
      }
    }

    return files;
  }

  private scanDir(dir: string, files: string[]): void {
    if (!existsSync(dir)) return;
    try {
      const entries = readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const fullPath = resolve(dir, entry.name);
        if (entry.isFile() && entry.name.endsWith('.md')) {
          files.push(fullPath);
        } else if (entry.isDirectory()) {
          this.scanDir(fullPath, files);
        }
      }
    } catch {
      // Skip
    }
  }
}
