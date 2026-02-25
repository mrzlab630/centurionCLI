#!/usr/bin/env node
/**
 * EXPLORATOR Stealth Browser v3.0 (Playwright)
 *
 * Usage:
 *   node browse.js <URL> [options]
 *
 * Options:
 *   --timeout <ms>      Navigation timeout (default: 30000)
 *   --wait <ms>         Post-load wait for dynamic content (default: 2000)
 *   --screenshot        Save screenshot to debug dir
 *   --full-page         Full-page screenshot (implies --screenshot)
 *   --json              Machine-readable JSON output to stdout
 *   --max-chars <n>     Text output limit (default: 5000)
 *   --selector <css>    Extract only matching elements
 *
 * Environment:
 *   PLAYWRIGHT_BROWSERS_PATH — override browser cache path
 */

const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');
const os = require('os');

// ─── CLI Argument Parser ────────────────────────────────────────────
function parseArgs(argv) {
    const args = { url: null, timeout: 30000, wait: 2000, screenshot: false, fullPage: false, json: false, maxChars: 5000, selector: null };
    const raw = argv.slice(2);

    for (let i = 0; i < raw.length; i++) {
        switch (raw[i]) {
            case '--timeout':    args.timeout = parseInt(raw[++i], 10) || 30000; break;
            case '--wait':       args.wait = parseInt(raw[++i], 10) || 2000; break;
            case '--screenshot': args.screenshot = true; break;
            case '--full-page':  args.fullPage = true; args.screenshot = true; break;
            case '--json':       args.json = true; break;
            case '--max-chars':  args.maxChars = parseInt(raw[++i], 10) || 5000; break;
            case '--selector':   args.selector = raw[++i]; break;
            case '--help': case '-h': printUsage(); process.exit(0);
            default:
                if (!raw[i].startsWith('--') && !args.url) args.url = raw[i];
                break;
        }
    }
    return args;
}

function printUsage() {
    console.log(`Usage: node browse.js <URL> [options]
Options:
  --timeout <ms>      Navigation timeout (default: 30000)
  --wait <ms>         Post-load wait (default: 2000)
  --screenshot        Save screenshot
  --full-page         Full-page screenshot
  --json              JSON output for agent consumption
  --max-chars <n>     Text limit (default: 5000)
  --selector <css>    Extract matching elements only
  -h, --help          Show this help`);
}

// ─── URL Validation ─────────────────────────────────────────────────
function validateUrl(input) {
    if (!input) return null;
    // Auto-prepend https if no protocol
    if (!/^https?:\/\//i.test(input)) input = 'https://' + input;
    try {
        const parsed = new URL(input);
        if (!['http:', 'https:'].includes(parsed.protocol)) return null;
        return parsed.href;
    } catch {
        return null;
    }
}

// ─── Find Chromium (cross-platform) ─────────────────────────────────
function findChromiumPath() {
    const cacheDir = process.env.PLAYWRIGHT_BROWSERS_PATH
        || path.join(os.homedir(), '.cache', 'ms-playwright');

    if (!fs.existsSync(cacheDir)) return null;

    const chromiumDirs = fs.readdirSync(cacheDir)
        .filter(d => d.startsWith('chromium-'))
        .sort();

    if (chromiumDirs.length === 0) return null;

    const latest = chromiumDirs[chromiumDirs.length - 1];
    const base = path.join(cacheDir, latest);

    // Platform-specific executable paths
    const candidates = [
        path.join(base, 'chrome-linux', 'chrome'),
        path.join(base, 'chrome-linux64', 'chrome'),
        path.join(base, 'chrome-mac', 'Chromium.app', 'Contents', 'MacOS', 'Chromium'),
        path.join(base, 'chrome-win', 'chrome.exe'),
        path.join(base, 'chrome-win64', 'chrome.exe'),
    ];

    for (const p of candidates) {
        if (fs.existsSync(p)) return p;
    }
    return null;
}

// ─── Debug Dir with Timestamped Files ───────────────────────────────
function getDebugDir() {
    const dir = path.join(os.homedir(), '.claude', 'debug');
    fs.mkdirSync(dir, { recursive: true });
    return dir;
}

function timestamp() {
    return new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
}

// ─── Main ───────────────────────────────────────────────────────────
async function browse(config) {
    const url = validateUrl(config.url);
    if (!url) {
        console.error('Error: Invalid URL. Only http/https allowed.');
        process.exit(1);
    }

    const executablePath = findChromiumPath();
    if (!executablePath) {
        console.error('Error: Chromium not found. Run: python3 -m playwright install chromium');
        process.exit(1);
    }

    const result = { url, title: null, status: null, text: null, screenshot: null, error: null };

    let browser;
    try {
        browser = await chromium.launch({
            headless: true,
            executablePath,
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled'],
        });

        const context = await browser.newContext({
            viewport: { width: 1280, height: 800 },
            userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale: 'en-US',
            javaScriptEnabled: true,
        });

        // Stealth: hide webdriver flag
        await context.addInitScript(() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
        });

        const page = await context.newPage();

        if (!config.json) console.log(`Navigating: ${url}`);

        const response = await page.goto(url, {
            waitUntil: 'domcontentloaded',
            timeout: config.timeout,
        });

        result.status = response ? response.status() : null;

        // Smart wait: wait for network idle OR timeout, whichever comes first
        await Promise.race([
            page.waitForLoadState('networkidle').catch(() => {}),
            new Promise(r => setTimeout(r, config.wait)),
        ]);

        // Scroll down once to trigger lazy-loaded content
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(500);

        result.title = await page.title();

        // Extract content
        if (config.selector) {
            const elements = await page.$$eval(config.selector, els =>
                els.map(el => el.innerText.trim()).filter(Boolean)
            );
            result.text = elements.join('\n---\n').slice(0, config.maxChars);
        } else {
            result.text = (await page.evaluate(() => document.body.innerText))
                .slice(0, config.maxChars);
        }

        // Screenshot
        if (config.screenshot) {
            const debugDir = getDebugDir();
            const fileName = `browse-${timestamp()}.png`;
            const screenshotPath = path.join(debugDir, fileName);
            await page.screenshot({ path: screenshotPath, fullPage: config.fullPage });
            result.screenshot = screenshotPath;
        }

        // HTML dump (always, for debug)
        const debugDir = getDebugDir();
        const htmlPath = path.join(debugDir, 'browse-latest.html');
        fs.writeFileSync(htmlPath, await page.content());

        await context.close();

    } catch (e) {
        result.error = e.message;
    } finally {
        if (browser) await browser.close();
    }

    // ─── Output ─────────────────────────────────────────────────
    if (config.json) {
        console.log(JSON.stringify(result, null, 2));
    } else {
        if (result.error) {
            console.error(`Error: ${result.error}`);
        } else {
            console.log(`Title: ${result.title}`);
            console.log(`Status: ${result.status}`);
            if (result.screenshot) console.log(`Screenshot: ${result.screenshot}`);
            console.log(`\n--- PAGE CONTENT ---`);
            console.log(result.text);
        }
    }

    process.exit(result.error ? 1 : 0);
}

// ─── Entry Point ────────────────────────────────────────────────────
const config = parseArgs(process.argv);
if (!config.url) {
    printUsage();
    process.exit(0);
}
browse(config);
