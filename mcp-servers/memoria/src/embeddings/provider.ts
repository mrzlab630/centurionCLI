/**
 * EmbeddingProvider — abstract interface for embedding models.
 * Swap implementations without changing any other code.
 */
export interface EmbeddingProvider {
  readonly dimensions: number;
  readonly modelName: string;

  /** Load model into memory. Call once on startup. */
  initialize(): Promise<void>;

  /** Embed a single text for document indexing. */
  embedDocument(text: string): Promise<Float32Array>;

  /** Embed a single text for search query. */
  embedQuery(text: string): Promise<Float32Array>;

  /** Embed multiple texts for document indexing. */
  embedDocumentBatch(texts: string[]): Promise<Float32Array[]>;

  /** Check if model is loaded. */
  isReady(): boolean;
}
