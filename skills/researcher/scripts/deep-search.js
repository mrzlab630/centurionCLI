#!/usr/bin/env node
/**
 * EXPLORATOR Deep Search — Perplexity API integration
 *
 * Usage:
 *   node deep-search.js "query" [model] [recency]
 *
 * Models:
 *   sonar              — Fast (~1s), cheap ($0.005/req)
 *   sonar-pro          — Deep search, more citations
 *   sonar-reasoning    — Complex questions with chain-of-thought
 *   sonar-deep-research — Multi-step research agent (~30s+)
 *
 * Recency:
 *   day, week, month, year (optional filter)
 *
 * Environment:
 *   PERPLEXITY_API_KEY — API key (required)
 */

const https = require('https');
const path = require('path');
const fs = require('fs');

// --- Config ---
const DEFAULT_MODEL = 'sonar';
const MAX_TOKENS = 2000;
const API_KEY = process.env.PERPLEXITY_API_KEY || '';

if (!API_KEY) {
    console.error('❌ PERPLEXITY_API_KEY not set.');
    console.error('   Export it: export PERPLEXITY_API_KEY="pplx-..."');
    process.exit(1);
}

// --- Parse args ---
const query = process.argv[2];
const model = process.argv[3] || DEFAULT_MODEL;
const recency = process.argv[4] || null;

if (!query) {
    console.log('Usage: node deep-search.js "query" [model] [recency]');
    console.log('Models: sonar, sonar-pro, sonar-reasoning, sonar-deep-research');
    console.log('Recency: day, week, month, year');
    process.exit(0);
}

// --- Build payload ---
const payload = {
    model,
    messages: [
        {
            role: 'system',
            content: 'Be precise and thorough. Cite sources with [n] markers. If the question is in Russian, answer in Russian. Structure your answer with headers when appropriate.'
        },
        { role: 'user', content: query }
    ],
    max_tokens: MAX_TOKENS
};

if (recency) {
    payload.search_recency_filter = recency;
}

// --- Execute request ---
const data = JSON.stringify(payload);

const options = {
    hostname: 'api.perplexity.ai',
    path: '/chat/completions',
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(data)
    }
};

const startTime = Date.now();

const req = https.request(options, (res) => {
    let raw = '';
    res.on('data', chunk => raw += chunk);
    res.on('end', () => {
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

        try {
            const r = JSON.parse(raw);

            if (r.error) {
                console.error(`❌ API Error: ${r.error.message || JSON.stringify(r.error)}`);
                process.exit(1);
            }

            const content = r.choices?.[0]?.message?.content || 'No response';
            const citations = r.citations || [];
            const searchResults = r.search_results || [];
            const usage = r.usage || {};
            const cost = usage.cost || {};

            // --- Output ---
            console.log('═══════════════════════════════════════════');
            console.log(`⚔️  EXPLORATOR INTELLIGENCE REPORT`);
            console.log(`📡 Model: ${model} | ⏱ ${elapsed}s | 🔍 Recency: ${recency || 'all'}`);
            console.log('═══════════════════════════════════════════');
            console.log('');
            console.log(content);

            if (citations.length > 0) {
                console.log('');
                console.log('───── SOURCES ─────');
                citations.forEach((c, i) => {
                    const sr = searchResults[i];
                    const title = sr?.title ? ` ${sr.title}` : '';
                    console.log(`[${i + 1}]${title}`);
                    console.log(`    ${c}`);
                });
            }

            console.log('');
            console.log('───── META ─────');
            console.log(`Tokens: ${usage.prompt_tokens || 0} in / ${usage.completion_tokens || 0} out`);
            console.log(`Cost: $${(cost.total_cost || 0).toFixed(4)}`);
            console.log(`Searches: ${usage.num_search_queries || 0}`);

            // --- Save to file for agent consumption ---
            const report = {
                query,
                model,
                recency,
                elapsed: parseFloat(elapsed),
                content,
                citations,
                searchResults,
                usage,
                timestamp: new Date().toISOString()
            };

            const outDir = path.join(__dirname, '..', 'reports');
            if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

            const outFile = path.join(outDir, `report-${Date.now()}.json`);
            fs.writeFileSync(outFile, JSON.stringify(report, null, 2));
            console.log(`\n📄 Report saved: ${outFile}`);

        } catch (e) {
            console.error('Parse error:', e.message);
            console.error('Raw response:', raw.slice(0, 500));
            process.exit(1);
        }
    });
});

req.on('error', (e) => {
    console.error(`Request error: ${e.message}`);
    process.exit(1);
});

req.write(data);
req.end();
