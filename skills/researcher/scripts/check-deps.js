const fs = require('fs');
const path = require('path');
const os = require('os');

function checkDeps() {
    console.log('EXPLORATOR: Checking Web Surfer dependencies...');
    let ok = true;

    // 1. Check playwright-core module
    try {
        require.resolve('playwright-core');
        console.log('  [OK] playwright-core');
    } catch {
        console.error('  [FAIL] playwright-core not found');
        console.error('    Fix: cd ~/.claude/skills/researcher/scripts && npm install playwright-core');
        ok = false;
    }

    // 2. Check Chromium binary
    const cacheDir = process.env.PLAYWRIGHT_BROWSERS_PATH
        || path.join(os.homedir(), '.cache', 'ms-playwright');

    if (fs.existsSync(cacheDir)) {
        const chromiumDirs = fs.readdirSync(cacheDir).filter(d => d.startsWith('chromium-'));
        if (chromiumDirs.length > 0) {
            console.log(`  [OK] Chromium found: ${chromiumDirs[chromiumDirs.length - 1]}`);
        } else {
            console.error('  [FAIL] Chromium not installed in Playwright cache');
            console.error('    Fix: python3 -m playwright install chromium');
            ok = false;
        }
    } else {
        console.error(`  [FAIL] Playwright cache not found: ${cacheDir}`);
        console.error('    Fix: python3 -m playwright install chromium');
        ok = false;
    }

    console.log(ok ? '\nAll dependencies OK.' : '\nSome dependencies missing. See above.');
    return ok;
}

if (require.main === module) {
    if (!checkDeps()) process.exit(1);
}

module.exports = checkDeps;
