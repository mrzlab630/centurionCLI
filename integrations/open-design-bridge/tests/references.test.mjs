import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import test from 'node:test';
import { runDesignRequest } from '../lib/bridge.mjs';
import {
  normalizeDesignReferences,
  searchDesignReferences,
  sweepReferenceCache,
  validateReferenceRequest
} from '../lib/references.mjs';

const fixtures = new Map([
  ['https://fixture/shadcn.json', JSON.stringify({ items: [
    { name: 'dashboard-01', type: 'registry:block', description: 'Analytics dashboard with charts', categories: ['dashboard'], files: [{ path: 'blocks/dashboard/page.tsx' }] },
    { name: 'login-01', type: 'registry:block', description: 'Login form', categories: ['authentication'], files: [{ path: 'blocks/login/page.tsx' }] }
  ] })],
  ['https://fixture/magicui.json', JSON.stringify({ items: [
    { name: 'bento-grid', type: 'registry:ui', title: 'Bento Grid', description: 'Feature grid for landing page', files: [{ path: 'registry/bento-grid.tsx' }] }
  ] })],
  ['https://fixture/hyperui.json', JSON.stringify({ tree: [
    { type: 'blob', path: 'public/examples/marketing/heroes/1.html' },
    { type: 'blob', path: 'public/examples/application/charts/1.html' }
  ] })],
  ['https://fixture/tabler.xml', '<urlset><url><loc>https://preview.tabler.io/dashboard.html</loc></url><url><loc>https://preview.tabler.io/pricing.html</loc></url></urlset>'],
  ['https://fixture/landbook.xml', '<rss><channel><item><title>B2B Analytics Platform</title><link>https://land-book.com/websites/b2b-analytics</link><description><img src="https://cdn.example/b2b.jpg" /></description></item></channel></rss>'],
  ['https://raw.githubusercontent.com/shadcn-ui/ui/main/blocks/dashboard/page.tsx', 'export default function Dashboard(){return <main>Analytics</main>}'],
  ['https://raw.githubusercontent.com/magicuidesign/magicui/main/registry/bento-grid.tsx', 'export function BentoGrid(){return <section>Features</section>}'],
  ['https://raw.githubusercontent.com/markmead/hyperui/main/public/examples/application/charts/1.html', '<section>Analytics chart</section>'],
  ['https://raw.githubusercontent.com/markmead/hyperui/main/public/examples/marketing/heroes/1.html', '<section>Landing hero</section>'],
  ['https://preview.tabler.io/dashboard.html', '<!doctype html><title>Dashboard</title>']
]);

function response(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Not Found',
    headers: { get: (name) => name.toLowerCase() === 'content-length' ? String(Buffer.byteLength(body)) : null },
    arrayBuffer: async () => Buffer.from(body)
  };
}

const publicLookup = async () => [{ address: '203.0.113.10', family: 4 }];

function fixtureFetcher(url) {
  const rewritten = String(url)
    .replace('https://raw.githubusercontent.com/shadcn-ui/ui/main/apps/v4/registry.json', 'https://fixture/shadcn.json')
    .replace('https://raw.githubusercontent.com/magicuidesign/magicui/main/apps/www/public/r/registry.json', 'https://fixture/magicui.json')
    .replace('https://api.github.com/repos/markmead/hyperui/git/trees/main?recursive=1', 'https://fixture/hyperui.json')
    .replace('https://preview.tabler.io/sitemap.xml', 'https://fixture/tabler.xml')
    .replace('https://land-book.com/rss.xml', 'https://fixture/landbook.xml');
  return Promise.resolve(fixtures.has(rewritten) ? response(fixtures.get(rewritten)) : response('', 404));
}

test('reference request validation is bounded', () => {
  const failures = validateReferenceRequest({
    requestVersion: 'wrong',
    query: '',
    sources: ['unknown'],
    limit: 99,
    cacheMaxAgeHours: 0
  });
  for (const marker of ['requestVersion', 'query', 'sources', 'limit', 'cacheMaxAgeHours']) {
    assert(failures.some((failure) => failure.includes(marker)), `missing ${marker} failure`);
  }
});

test('reference search returns diverse sources and a temporary manifest', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-reference-search-'));
  try {
    const result = await searchDesignReferences({
      requestVersion: 'CENTURION_REFERENCE_REQUEST_V1',
      searchId: 'analytics-landing',
      query: 'B2B analytics landing page',
      artifactType: 'landing-page',
      platform: 'web',
      sources: ['shadcn', 'magicui', 'hyperui', 'tabler', 'landbook'],
      limit: 5
    }, {
      cwd: root,
      env: { CENTURION_DESIGN_ROOT: root },
      fetcher: fixtureFetcher,
      lookup: publicLookup
    });
    assert.equal(result.status, 'done');
    assert.equal(result.references.length, 5);
    assert.equal(new Set(result.references.map((item) => item.source)).size, 5);
    assert(fs.existsSync(result.manifestPath));
    assert(path.isAbsolute(result.manifestPath));
    assert.equal(result.references.find((item) => item.source === 'landbook').policy, 'inspire-only');
    assert.equal(result.references.find((item) => item.source === 'landbook').snippet, null);
    assert(result.references.filter((item) => item.policy === 'import-and-adapt').some((item) => item.snippet?.absolutePath));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('design references reject tampered snippets', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-reference-tamper-'));
  try {
    const cache = path.join(root, '.reference-cache', 'one');
    const snippet = path.join(cache, 'snippets', 'one.html');
    fs.mkdirSync(path.dirname(snippet), { recursive: true });
    fs.writeFileSync(snippet, '<section>one</section>');
    const manifest = path.join(cache, 'reference-manifest.json');
    fs.writeFileSync(manifest, JSON.stringify({
      manifestVersion: 'CENTURION_REFERENCE_MANIFEST_V1',
      strategy: 'compose',
      references: [{ id: 'hyperui:one', snippet: { absolutePath: snippet, relativePath: 'snippets/one.html', sha256: 'bad' } }]
    }));
    assert.throws(() => normalizeDesignReferences({ manifestPath: manifest }, { cwd: root, allowedRoots: [root] }), /SHA-256 mismatch/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('design references reject inconsistent snippet byte metadata', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-reference-bytes-'));
  try {
    const cache = path.join(root, '.reference-cache', 'one');
    const snippet = path.join(cache, 'snippet.html');
    fs.mkdirSync(cache, { recursive: true });
    fs.writeFileSync(snippet, '<section>one</section>');
    const sha256 = crypto.createHash('sha256').update(fs.readFileSync(snippet)).digest('hex');
    const manifest = path.join(cache, 'reference-manifest.json');
    fs.writeFileSync(manifest, JSON.stringify({
      manifestVersion: 'CENTURION_REFERENCE_MANIFEST_V1',
      references: [{ id: 'one', snippet: { absolutePath: snippet, relativePath: 'snippet.html', sha256, bytes: 1 } }]
    }));
    assert.throws(() => normalizeDesignReferences({ manifestPath: manifest }, { cwd: root, allowedRoots: [root] }), /byte count mismatch/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('reference manifests and snippets cannot escape through symlinks', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-reference-symlink-'));
  const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-reference-outside-'));
  try {
    const outsideManifest = path.join(outside, 'reference-manifest.json');
    fs.writeFileSync(outsideManifest, JSON.stringify({ manifestVersion: 'CENTURION_REFERENCE_MANIFEST_V1', references: [] }));
    const manifestLink = path.join(root, 'manifest-link.json');
    fs.symlinkSync(outsideManifest, manifestLink);
    assert.throws(() => normalizeDesignReferences({ manifestPath: manifestLink }, { cwd: root, allowedRoots: [root] }), /regular file/);

    const cache = path.join(root, 'cache');
    fs.mkdirSync(cache, { recursive: true });
    const outsideSnippet = path.join(outside, 'snippet.html');
    fs.writeFileSync(outsideSnippet, '<section>outside</section>');
    const snippetLink = path.join(cache, 'snippet.html');
    fs.symlinkSync(outsideSnippet, snippetLink);
    const manifest = path.join(cache, 'reference-manifest.json');
    fs.writeFileSync(manifest, JSON.stringify({
      manifestVersion: 'CENTURION_REFERENCE_MANIFEST_V1',
      references: [{ id: 'one', snippet: { absolutePath: snippetLink, relativePath: 'snippet.html', sha256: 'unused' } }]
    }));
    assert.throws(() => normalizeDesignReferences({ manifestPath: manifest }, { cwd: root, allowedRoots: [root] }), /missing or unsafe/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
    fs.rmSync(outside, { recursive: true, force: true });
  }
});

test('reference search expands common Russian design terms', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-reference-russian-'));
  try {
    const result = await searchDesignReferences({
      requestVersion: 'CENTURION_REFERENCE_REQUEST_V1',
      searchId: 'russian-query',
      query: 'лендинг для B2B аналитики',
      sources: ['shadcn', 'magicui'],
      limit: 2
    }, { cwd: root, env: { CENTURION_DESIGN_ROOT: root }, fetcher: fixtureFetcher, lookup: publicLookup });
    assert.equal(result.status, 'done');
    assert(result.references.some((reference) => reference.id === 'shadcn:dashboard-01'));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('reference TTL removes only expired cache directories', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-reference-ttl-'));
  try {
    const oldDir = path.join(root, 'old');
    const newDir = path.join(root, 'new');
    fs.mkdirSync(oldDir, { recursive: true });
    fs.mkdirSync(newDir, { recursive: true });
    const old = new Date(Date.now() - 2 * 60 * 60 * 1000);
    fs.utimesSync(oldDir, old, old);
    assert.equal(sweepReferenceCache(root, 1), 1);
    assert.equal(fs.existsSync(oldDir), false);
    assert.equal(fs.existsSync(newDir), true);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('accepted design bundle preserves portable reference evidence', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-reference-design-'));
  const mockOd = path.resolve('tests/fixtures/mock-od.mjs');
  try {
    const snippet = path.join(root, '.reference-cache', 'one', 'snippets', 'one.html');
    fs.mkdirSync(path.dirname(snippet), { recursive: true });
    fs.writeFileSync(snippet, '<section>Analytics dashboard</section>');
    const sha256 = crypto.createHash('sha256').update(fs.readFileSync(snippet)).digest('hex');
    const manifest = path.join(root, '.reference-cache', 'one', 'reference-manifest.json');
    fs.writeFileSync(manifest, JSON.stringify({
      manifestVersion: 'CENTURION_REFERENCE_MANIFEST_V1',
      strategy: 'compose',
      references: [{
        id: 'hyperui:one', source: 'hyperui', title: 'Analytics', policy: 'import-and-adapt',
        snippet: { absolutePath: snippet, relativePath: 'snippets/one.html', sha256, bytes: fs.statSync(snippet).size, truncated: false }
      }]
    }));
    const result = await runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'with-references',
      action: 'create',
      brief: 'Create an analytics landing.',
      orchestrator: { client: 'hermes', owner: 'AEDILIS' },
      references: { manifestPath: manifest, selectedIds: ['hyperui:one'], strategy: 'compose' },
      artifact: { outputDir: path.join(root, 'out') },
      screenshot: { enabled: false }
    }, {
      cwd: root,
      env: {
        ...process.env,
        MOCK_OD_STATE_DIR: path.join(root, 'state'),
        CENTURION_DESIGN_ROOT: root,
        CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd])
      }
    });
    assert.equal(result.status, 'done');
    assert.equal(result.orchestrator.client, 'hermes');
    assert(fs.existsSync(result.references.acceptedManifestPath));
    assert(fs.existsSync(result.references.acceptedSnippets[0].absolutePath));
    const accepted = fs.readFileSync(result.references.acceptedManifestPath, 'utf8');
    assert(!accepted.includes('.reference-cache'));
    assert(fs.existsSync(path.join(root, 'state', 'written-files', 'context', 'centurion', 'reference-manifest.json')));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('design production rejects a snippet changed after request normalization', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-reference-toctou-'));
  const mockOd = path.resolve('tests/fixtures/mock-od.mjs');
  try {
    const snippet = path.join(root, '.reference-cache', 'one', 'snippets', 'one.html');
    fs.mkdirSync(path.dirname(snippet), { recursive: true });
    fs.writeFileSync(snippet, '<section>trusted</section>');
    const sha256 = crypto.createHash('sha256').update(fs.readFileSync(snippet)).digest('hex');
    const manifest = path.join(root, '.reference-cache', 'one', 'reference-manifest.json');
    fs.writeFileSync(manifest, JSON.stringify({
      manifestVersion: 'CENTURION_REFERENCE_MANIFEST_V1',
      references: [{
        id: 'hyperui:one', source: 'hyperui', title: 'One', policy: 'import-and-adapt',
        snippet: { absolutePath: snippet, relativePath: 'snippets/one.html', sha256, bytes: fs.statSync(snippet).size, truncated: false }
      }]
    }));
    const request = {
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'reference-toctou',
      action: 'create',
      brief: 'Create a landing.',
      references: { manifestPath: manifest, selectedIds: ['hyperui:one'] },
      artifact: { outputDir: path.join(root, 'out') },
      screenshot: { enabled: false }
    };
    const result = await runDesignRequest(request, {
      cwd: root,
      afterNormalize: () => fs.writeFileSync(snippet, '<section>tampered</section>'),
      env: {
        ...process.env,
        MOCK_OD_STATE_DIR: path.join(root, 'state'),
        CENTURION_DESIGN_ROOT: root,
        CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd])
      }
    });
    assert.equal(result.status, 'failed');
    assert(result.errors.some((error) => error.includes('SHA-256 mismatch')));
    assert.equal(fs.existsSync(path.join(root, 'out')), false);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('reference snippet read fails closed if the manifest cache is replaced after validation', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-reference-parent-race-'));
  const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-reference-parent-race-outside-'));
  const mockOd = path.resolve('tests/fixtures/mock-od.mjs');
  try {
    const cache = path.join(root, '.reference-cache', 'one');
    const snippet = path.join(cache, 'snippets', 'one.html');
    fs.mkdirSync(path.dirname(snippet), { recursive: true });
    fs.writeFileSync(snippet, '<section>trusted</section>');
    const sha256 = crypto.createHash('sha256').update(fs.readFileSync(snippet)).digest('hex');
    const manifest = path.join(cache, 'reference-manifest.json');
    fs.writeFileSync(manifest, JSON.stringify({
      manifestVersion: 'CENTURION_REFERENCE_MANIFEST_V1',
      references: [{
        id: 'hyperui:one', source: 'hyperui', title: 'One', policy: 'import-and-adapt',
        snippet: { absolutePath: snippet, relativePath: 'snippets/one.html', sha256, bytes: fs.statSync(snippet).size, truncated: false }
      }]
    }));
    const outsideCache = path.join(outside, 'one');
    fs.mkdirSync(path.join(outsideCache, 'snippets'), { recursive: true });
    fs.writeFileSync(path.join(outsideCache, 'reference-manifest.json'), fs.readFileSync(manifest));
    fs.writeFileSync(path.join(outsideCache, 'snippets', 'one.html'), '<section>attacker</section>');
    let raced = false;
    const result = await runDesignRequest({
      requestVersion: 'CENTURION_OD_REQUEST_V1',
      requestId: 'reference-parent-race',
      action: 'create',
      brief: 'Create a landing.',
      references: { manifestPath: manifest, selectedIds: ['hyperui:one'] },
      artifact: { outputDir: path.join(root, 'out') },
      screenshot: { enabled: false }
    }, {
      cwd: root,
      storageHook: ({ operation }) => {
        if (operation !== 'reference-snippet-load' || raced) return;
        raced = true;
        fs.renameSync(cache, `${cache}-trusted`);
        fs.symlinkSync(outsideCache, cache, 'dir');
      },
      env: {
        ...process.env,
        MOCK_OD_STATE_DIR: path.join(root, 'state'),
        CENTURION_DESIGN_ROOT: root,
        CENTURION_OD_COMMAND_JSON: JSON.stringify([process.execPath, mockOd])
      }
    }).catch((error) => ({ status: 'failed', errors: [error.message] }));
    assert.equal(result.status, 'failed');
    assert(result.errors.some((error) => error.includes('changed during the anchored filesystem operation')));
    assert.equal(fs.existsSync(path.join(root, 'out')), false);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
    fs.rmSync(outside, { recursive: true, force: true });
  }
});

test('reference search rejects disallowed redirects and private DNS results', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'centurion-reference-ssrf-'));
  try {
    const redirectFetcher = async () => ({
      ok: false,
      status: 302,
      statusText: 'Found',
      headers: { get: (name) => name.toLowerCase() === 'location' ? 'https://127.0.0.1/private' : null },
      arrayBuffer: async () => Buffer.alloc(0)
    });
    const redirected = await searchDesignReferences({
      requestVersion: 'CENTURION_REFERENCE_REQUEST_V1',
      searchId: 'redirect-ssrf',
      query: 'dashboard',
      sources: ['tabler'],
      limit: 1
    }, {
      cwd: root,
      env: { CENTURION_DESIGN_ROOT: root },
      fetcher: redirectFetcher,
      lookup: publicLookup
    });
    assert.equal(redirected.status, 'failed');
    assert(redirected.warnings.some((warning) => warning.includes('origin is not allowed')));

    const privateDns = await searchDesignReferences({
      requestVersion: 'CENTURION_REFERENCE_REQUEST_V1',
      searchId: 'dns-ssrf',
      query: 'dashboard',
      sources: ['tabler'],
      limit: 1
    }, {
      cwd: root,
      env: { CENTURION_DESIGN_ROOT: root },
      fetcher: fixtureFetcher,
      lookup: async () => [{ address: '127.0.0.1', family: 4 }]
    });
    assert.equal(privateDns.status, 'failed');
    assert(privateDns.warnings.some((warning) => warning.includes('private or unavailable')));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
