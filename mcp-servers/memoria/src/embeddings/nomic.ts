import type { EmbeddingProvider } from './provider.js';

/**
 * NomicEmbeddingProvider — local embedding via nomic-embed-text-v1.5.
 * Uses @huggingface/transformers (ONNX runtime in Node.js).
 * Matryoshka: outputs 384 dims (from 768) for optimal size/quality ratio.
 */
export class NomicEmbeddingProvider implements EmbeddingProvider {
  readonly dimensions = 384;
  readonly modelName = 'nomic-ai/nomic-embed-text-v1.5';

  private pipe: any = null;
  private ready = false;
  private initPromise: Promise<void> | null = null;

  async initialize(): Promise<void> {
    if (this.pipe) return;
    if (this.initPromise) return this.initPromise;

    this.initPromise = (async () => {
      const { pipeline } = await import('@huggingface/transformers');
      this.pipe = await pipeline('feature-extraction', this.modelName, {
        dtype: 'q8' as any,
      } as any);
      this.ready = true;
    })();

    return this.initPromise;
  }

  isReady(): boolean {
    return this.ready;
  }

  async embedDocument(text: string): Promise<Float32Array> {
    return this.embed(`search_document: ${text}`);
  }

  async embedQuery(text: string): Promise<Float32Array> {
    return this.embed(`search_query: ${text}`);
  }

  async embedDocumentBatch(texts: string[]): Promise<Float32Array[]> {
    if (texts.length === 0) return [];
    if (!this.pipe) await this.initialize();

    const BATCH_SIZE = 32;
    const results: Float32Array[] = [];

    for (let i = 0; i < texts.length; i += BATCH_SIZE) {
      const batch = texts.slice(i, i + BATCH_SIZE);
      const prefixed = batch.map(t => `search_document: ${t}`);
      const output = await this.pipe!(prefixed, { pooling: 'mean', normalize: true });

      const fullDims = output.dims[output.dims.length - 1];
      for (let j = 0; j < batch.length; j++) {
        const offset = j * fullDims;
        const truncated = new Float32Array(this.dimensions);
        for (let k = 0; k < this.dimensions; k++) {
          truncated[k] = output.data[offset + k];
        }
        results.push(l2Normalize(truncated));
      }
    }

    return results;
  }

  private async embed(text: string): Promise<Float32Array> {
    if (!this.pipe) {
      await this.initialize();
    }

    const output = await this.pipe!(text, { pooling: 'mean', normalize: true });
    const full = output.data as Float32Array;

    // Matryoshka: slice to 384 dims and re-normalize
    const truncated = new Float32Array(this.dimensions);
    for (let i = 0; i < this.dimensions; i++) {
      truncated[i] = full[i];
    }
    return l2Normalize(truncated);
  }
}

function l2Normalize(vec: Float32Array): Float32Array {
  let sum = 0;
  for (let i = 0; i < vec.length; i++) {
    sum += vec[i] * vec[i];
  }
  const norm = Math.sqrt(sum);
  if (norm === 0) return vec;
  const result = new Float32Array(vec.length);
  for (let i = 0; i < vec.length; i++) {
    result[i] = vec[i] / norm;
  }
  return result;
}
