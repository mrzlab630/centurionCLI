import { createHash } from 'node:crypto';

export interface Chunk {
  id: string;
  text: string;
  heading: string;
  breadcrumb: string;
  startLine: number;
  endLine: number;
}

const MIN_CHUNK_LENGTH = 50;
const MAX_CHUNK_LENGTH = 1500;

/**
 * Split a markdown file into semantic chunks by headings.
 * Tracks heading hierarchy for breadcrumb context.
 * Code-fence-aware: never splits inside ``` blocks.
 */
export function chunkMarkdown(content: string, source: string): Chunk[] {
  const lines = content.split('\n');
  const chunks: Chunk[] = [];

  // Heading hierarchy for breadcrumbs
  const headingStack: { level: number; text: string }[] = [];
  let currentHeading = '';
  let currentBreadcrumb = '';
  let currentText = '';
  let startLine = 1;
  let inCodeBlock = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Track code fences (``` or ~~~)
    if (/^(`{3,}|~{3,})/.test(line.trim())) {
      inCodeBlock = !inCodeBlock;
      currentText += line + '\n';

      // Safety: force-split extremely long code blocks
      if (inCodeBlock && currentText.length > MAX_CHUNK_LENGTH * 2) {
        chunks.push(makeChunk(currentText.trim(), currentHeading, currentBreadcrumb, startLine, i + 1, source));
        currentText = '';
        startLine = i + 2;
      }
      continue;
    }

    // Inside code block — accumulate without splitting
    if (inCodeBlock) {
      currentText += line + '\n';
      if (currentText.length > MAX_CHUNK_LENGTH * 2) {
        chunks.push(makeChunk(currentText.trim(), currentHeading, currentBreadcrumb, startLine, i + 1, source));
        currentText = '';
        startLine = i + 2;
      }
      continue;
    }

    // Heading detection (H1-H3 = chunk boundaries)
    const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);

    if (headingMatch) {
      const level = headingMatch[1].length;
      const headingText = headingMatch[2].trim();

      // Flush previous chunk
      if (currentText.trim().length >= MIN_CHUNK_LENGTH) {
        chunks.push(makeChunk(currentText.trim(), currentHeading, currentBreadcrumb, startLine, i, source));
      }

      // Update heading hierarchy — pop deeper/same levels, push current
      while (headingStack.length > 0 && headingStack[headingStack.length - 1].level >= level) {
        headingStack.pop();
      }
      headingStack.push({ level, text: headingText });

      currentHeading = line.trim();
      currentBreadcrumb = headingStack.map(h => h.text).join(' > ');
      currentText = '';
      startLine = i + 1;
    } else {
      currentText += line + '\n';

      // Split if too long — prefer blank-line boundaries
      if (currentText.length > MAX_CHUNK_LENGTH) {
        const splitPoint = currentText.lastIndexOf('\n\n');
        if (splitPoint > MIN_CHUNK_LENGTH) {
          const first = currentText.slice(0, splitPoint).trim();
          if (first.length >= MIN_CHUNK_LENGTH) {
            chunks.push(makeChunk(first, currentHeading, currentBreadcrumb, startLine, i, source));
          }
          currentText = currentText.slice(splitPoint + 2);
          startLine = i + 1;
        }
      }
    }
  }

  // Flush last chunk
  if (currentText.trim().length >= MIN_CHUNK_LENGTH) {
    chunks.push(makeChunk(currentText.trim(), currentHeading, currentBreadcrumb, startLine, lines.length, source));
  }

  // If no chunks (file too short or no headings), treat whole file as one chunk
  if (chunks.length === 0 && content.trim().length >= MIN_CHUNK_LENGTH) {
    chunks.push(makeChunk(content.trim(), '', '', 1, lines.length, source));
  }

  return chunks;
}

function makeChunk(
  text: string,
  heading: string,
  breadcrumb: string,
  startLine: number,
  endLine: number,
  source: string,
): Chunk {
  const id = createHash('sha256')
    .update(source + ':' + text)
    .digest('hex')
    .slice(0, 16);

  return { id, text, heading, breadcrumb, startLine, endLine };
}
