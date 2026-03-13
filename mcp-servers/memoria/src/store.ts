import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

// --- V2 storage types (INT8 quantized, base64) ---

export interface StoredChunk {
  id: string;
  text: string;
  source: string;
  metadata: {
    heading: string;
    breadcrumb: string;
    startLine: number;
    endLine: number;
    indexedAt: string;
    fileModified: string;
  };
  embedding_b64: string;
}

export interface StoreData {
  version: 2;
  model: string;
  dimensions: number;
  lastReindexTime?: string;
  chunks: StoredChunk[];
}

// --- V1 types (for migration) ---

interface StoredChunkV1 {
  id: string;
  text: string;
  source: string;
  metadata: {
    heading: string;
    startLine: number;
    endLine: number;
    indexedAt: string;
    fileModified: string;
  };
  embedding: number[];
}

interface StoreDataV1 {
  version: 1;
  model: string;
  dimensions: number;
  chunks: StoredChunkV1[];
}

// --- Public input type for add() ---

export interface ChunkInput {
  id: string;
  text: string;
  source: string;
  metadata: {
    heading: string;
    breadcrumb: string;
    startLine: number;
    endLine: number;
    indexedAt: string;
    fileModified: string;
  };
  embedding: Float32Array;
}

export interface SearchResult {
  id: string;
  text: string;
  source: string;
  heading: string;
  breadcrumb: string;
  score: number;
  startLine: number;
  endLine: number;
}

/** Recency boost: fresh memories rank higher in search results */
const RECENCY_HALF_LIFE_DAYS = 30;
const RECENCY_WEIGHT = 0.15; // max 15% boost for recent content

/** Stale penalty: memories from files untouched >90 days get score reduction */
const STALE_THRESHOLD_DAYS = 90;
const STALE_PENALTY = 0.15; // max 15% penalty for stale content

// --- INT8 Quantization Helpers ---

export function quantizeToInt8(float32: Float32Array): Int8Array {
  const int8 = new Int8Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    int8[i] = Math.round(Math.max(-127, Math.min(127, float32[i] * 127)));
  }
  return int8;
}

export function int8ToBase64(int8: Int8Array): string {
  return Buffer.from(new Uint8Array(int8.buffer, int8.byteOffset, int8.byteLength)).toString('base64');
}

export function base64ToInt8(b64: string): Int8Array {
  const buf = Buffer.from(b64, 'base64');
  // Copy to own ArrayBuffer to avoid Buffer pool aliasing
  const uint8 = new Uint8Array(buf);
  return new Int8Array(uint8.buffer);
}

function dequantizeToFloat32(int8: Int8Array): Float32Array {
  const float32 = new Float32Array(int8.length);
  for (let i = 0; i < int8.length; i++) {
    float32[i] = int8[i] / 127;
  }
  return float32;
}

function embeddingToBase64(embedding: Float32Array): string {
  return int8ToBase64(quantizeToInt8(embedding));
}

/**
 * VectorStore — JSON-backed in-memory vector storage with INT8 quantized embeddings.
 * Brute-force cosine similarity. Optimal for <10K chunks.
 * V2: INT8 base64 encoding, heading breadcrumbs, lazy reindex tracking.
 */
export class VectorStore {
  private data: StoreData;
  private dirty = false;

  constructor(
    private readonly filePath: string,
    private readonly model: string,
    private readonly dimensions: number,
  ) {
    this.data = { version: 2, model, dimensions, chunks: [] };
  }

  load(): void {
    if (!existsSync(this.filePath)) return;
    try {
      const raw = readFileSync(this.filePath, 'utf-8');
      const parsed = JSON.parse(raw);

      if (parsed.model !== this.model || parsed.dimensions !== this.dimensions) return;

      if (parsed.version === 2) {
        this.data = parsed as StoreData;
      } else if (parsed.version === 1) {
        this.migrateV1(parsed as StoreDataV1);
      }
    } catch {
      // Corrupted file — start fresh
    }
  }

  private migrateV1(v1: StoreDataV1): void {
    process.stderr.write(`MEMORIA: migrating store v1 -> v2 (${v1.chunks.length} chunks)...\n`);

    // Keep manual memories (re-quantize), clear file-indexed (will re-index with new chunker)
    const manualChunks: StoredChunk[] = v1.chunks
      .filter(c => c.source.startsWith('manual:'))
      .map(c => ({
        id: c.id,
        text: c.text,
        source: c.source,
        metadata: { ...c.metadata, breadcrumb: '' },
        embedding_b64: int8ToBase64(quantizeToInt8(new Float32Array(c.embedding))),
      }));

    this.data = {
      version: 2,
      model: v1.model,
      dimensions: v1.dimensions,
      chunks: manualChunks,
    };
    this.dirty = true;
    this.save();

    const cleared = v1.chunks.length - manualChunks.length;
    process.stderr.write(
      `MEMORIA: migration complete. ${manualChunks.length} manual preserved, ${cleared} file chunks cleared (will re-index).\n`,
    );
  }

  save(): void {
    if (!this.dirty) return;
    const dir = dirname(this.filePath);
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    writeFileSync(this.filePath, JSON.stringify(this.data), 'utf-8');
    this.dirty = false;
  }

  get chunkCount(): number {
    return this.data.chunks.length;
  }

  get lastReindexTime(): string | undefined {
    return this.data.lastReindexTime;
  }

  setLastReindexTime(time: string): void {
    this.data.lastReindexTime = time;
    this.dirty = true;
  }

  getSources(): Map<string, number> {
    const map = new Map<string, number>();
    for (const chunk of this.data.chunks) {
      map.set(chunk.source, (map.get(chunk.source) || 0) + 1);
    }
    return map;
  }

  getFileModified(source: string): string | undefined {
    const chunk = this.data.chunks.find(c => c.source === source);
    return chunk?.metadata.fileModified;
  }

  add(input: ChunkInput): void {
    const stored: StoredChunk = {
      id: input.id,
      text: input.text,
      source: input.source,
      metadata: input.metadata,
      embedding_b64: embeddingToBase64(input.embedding),
    };
    // Deduplicate by id
    this.data.chunks = this.data.chunks.filter(c => c.id !== stored.id);
    this.data.chunks.push(stored);
    this.dirty = true;
  }

  removeById(id: string): number {
    const before = this.data.chunks.length;
    this.data.chunks = this.data.chunks.filter(c => c.id !== id);
    const removed = before - this.data.chunks.length;
    if (removed > 0) this.dirty = true;
    return removed;
  }

  removeBySource(source: string): number {
    const before = this.data.chunks.length;
    this.data.chunks = this.data.chunks.filter(c => c.source !== source);
    const removed = before - this.data.chunks.length;
    if (removed > 0) this.dirty = true;
    return removed;
  }

  clear(): void {
    if (this.data.chunks.length > 0) {
      this.data.chunks = [];
      this.dirty = true;
    }
  }

  search(queryEmbedding: Float32Array, topK: number = 5, threshold: number = 0.3, recencyBoost: boolean = true): SearchResult[] {
    const now = Date.now();
    const results: SearchResult[] = [];

    for (const chunk of this.data.chunks) {
      const storedEmbedding = dequantizeToFloat32(base64ToInt8(chunk.embedding_b64));
      let score = cosineSimilarity(queryEmbedding, storedEmbedding);

      if (chunk.metadata.fileModified) {
        const ageMs = now - new Date(chunk.metadata.fileModified).getTime();
        const ageDays = Math.max(0, ageMs / (1000 * 60 * 60 * 24));

        // Recency boost for fresh content
        if (recencyBoost) {
          const decay = Math.exp(-ageDays * Math.LN2 / RECENCY_HALF_LIFE_DAYS);
          score *= (1 + RECENCY_WEIGHT * decay);
        }

        // Stale penalty for old content
        if (ageDays > STALE_THRESHOLD_DAYS) {
          const staleRatio = Math.min(1, (ageDays - STALE_THRESHOLD_DAYS) / STALE_THRESHOLD_DAYS);
          score *= (1 - STALE_PENALTY * staleRatio);
        }
      }

      if (score >= threshold) {
        results.push({
          id: chunk.id,
          text: chunk.text,
          source: chunk.source,
          heading: chunk.metadata.heading,
          breadcrumb: chunk.metadata.breadcrumb || '',
          score,
          startLine: chunk.metadata.startLine,
          endLine: chunk.metadata.endLine,
        });
      }
    }

    results.sort((a, b) => b.score - a.score);
    return results.slice(0, topK);
  }

  /** Get neighboring chunks from the same source for context expansion */
  getNeighborChunks(chunkId: string, radius: number = 1): StoredChunk[] {
    const idx = this.data.chunks.findIndex(c => c.id === chunkId);
    if (idx === -1) return [];

    const source = this.data.chunks[idx].source;
    // Collect all chunks from same source, sorted by startLine
    const sourceChunks = this.data.chunks
      .filter(c => c.source === source)
      .sort((a, b) => a.metadata.startLine - b.metadata.startLine);

    const posInSource = sourceChunks.findIndex(c => c.id === chunkId);
    if (posInSource === -1) return [];

    const neighbors: StoredChunk[] = [];
    for (let i = Math.max(0, posInSource - radius); i <= Math.min(sourceChunks.length - 1, posInSource + radius); i++) {
      if (i !== posInSource) {
        neighbors.push(sourceChunks[i]);
      }
    }
    return neighbors;
  }

  /** Get index statistics */
  getStats(): { totalChunks: number; avgChunkSize: number; oldestFile: string; newestFile: string; staleCount: number; sourceCount: number } {
    const chunks = this.data.chunks;
    if (chunks.length === 0) {
      return { totalChunks: 0, avgChunkSize: 0, oldestFile: 'n/a', newestFile: 'n/a', staleCount: 0, sourceCount: 0 };
    }

    const avgChunkSize = Math.round(chunks.reduce((sum, c) => sum + c.text.length, 0) / chunks.length);
    const now = Date.now();
    const staleCutoff = STALE_THRESHOLD_DAYS * 24 * 60 * 60 * 1000;

    let oldest = chunks[0].metadata.fileModified;
    let newest = chunks[0].metadata.fileModified;
    let staleCount = 0;
    const sources = new Set<string>();

    for (const chunk of chunks) {
      sources.add(chunk.source);
      const mod = chunk.metadata.fileModified;
      if (mod < oldest) oldest = mod;
      if (mod > newest) newest = mod;
      if (now - new Date(mod).getTime() > staleCutoff) staleCount++;
    }

    return { totalChunks: chunks.length, avgChunkSize, oldestFile: oldest, newestFile: newest, staleCount, sourceCount: sources.size };
  }

  listChunks(filter?: 'manual' | 'files'): { source: string; count: number; modified: string; headings: string[] }[] {
    const groups = new Map<string, { count: number; modified: string; headings: Set<string> }>();

    for (const chunk of this.data.chunks) {
      const isManual = chunk.source.startsWith('manual:');
      if (filter === 'manual' && !isManual) continue;
      if (filter === 'files' && isManual) continue;

      const group = groups.get(chunk.source);
      if (group) {
        group.count++;
        if (chunk.metadata.heading) group.headings.add(chunk.metadata.heading);
        if (chunk.metadata.fileModified > group.modified) group.modified = chunk.metadata.fileModified;
      } else {
        groups.set(chunk.source, {
          count: 1,
          modified: chunk.metadata.fileModified,
          headings: new Set(chunk.metadata.heading ? [chunk.metadata.heading] : []),
        });
      }
    }

    return Array.from(groups.entries())
      .map(([source, data]) => ({
        source,
        count: data.count,
        modified: data.modified,
        headings: Array.from(data.headings),
      }))
      .sort((a, b) => b.modified.localeCompare(a.modified));
  }
}

function cosineSimilarity(a: Float32Array, b: Float32Array): number {
  let dot = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  const denom = Math.sqrt(normA) * Math.sqrt(normB);
  return denom === 0 ? 0 : dot / denom;
}
