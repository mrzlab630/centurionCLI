import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

export const MAX_JSON_INPUT_BYTES = 1024 * 1024;

async function readBoundedStream(stream, label, maxBytes) {
  const chunks = [];
  let bytes = 0;
  for await (const chunk of stream) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    bytes += buffer.length;
    if (bytes > maxBytes) {
      if (stream !== process.stdin) stream.destroy();
      throw new Error(`${label} exceeds ${maxBytes} bytes`);
    }
    chunks.push(buffer);
  }
  return Buffer.concat(chunks, bytes).toString('utf8');
}

export async function readJsonInput(source, options = {}) {
  if (!source) throw new Error('--request is required');
  const label = options.label ?? 'JSON request';
  const maxBytes = options.maxBytes ?? MAX_JSON_INPUT_BYTES;
  const stream = source === '-'
    ? process.stdin
    : fs.createReadStream(path.resolve(source), { highWaterMark: 64 * 1024 });
  return JSON.parse(await readBoundedStream(stream, label, maxBytes));
}
