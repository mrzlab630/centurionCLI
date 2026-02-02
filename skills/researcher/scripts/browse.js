const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const path = require('path');

puppeteer.use(StealthPlugin());

async function browse(url) {
    console.log(`🌍 Surfing (Stealth): ${url}`);
    
    // Path to Playwright's Chromium (since system chrome is missing)
    // Find dynamic path? We hardcode based on previous 'find' output for now.
    // Ideally use 'which google-chrome' if installed.
    const executablePath = '/home/yokinaboy/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome';

    const browser = await puppeteer.launch({
        headless: "new",
        executablePath: executablePath,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1280, height: 800 });

        console.log('Navigating...');
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
        
        // Wait for DDOS-GUARD to pass
        console.log('Waiting for guards...');
        await new Promise(r => setTimeout(r, 15000));

        // Scroll to trigger lazy load
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await new Promise(r => setTimeout(r, 2000));

        const title = await page.title();
        console.log(`📄 Title: ${title}`);

        // Take Debug Screenshot
        await page.screenshot({ path: '/home/yokinaboy/agent-tools/web-surfer/debug.png', fullPage: false });
        console.log('📸 Screenshot saved: debug.png');

        // Save HTML for debug
        const html = await page.content();
        require('fs').writeFileSync('/home/yokinaboy/agent-tools/web-surfer/debug.html', html);
        console.log('📄 HTML dump saved: debug.html');

        // Extract Items (Try broader selector)
        const items = await page.evaluate(() => {
            const results = [];
            // Target specific product rows
            const rows = document.querySelectorAll('.goods-item-content');
            
            rows.forEach(row => {
                const titleEl = row.querySelector('.goods_name_link');
                const priceEl = row.querySelector('.goods_price');
                
                if (titleEl && priceEl) {
                    results.push({
                        text: titleEl.innerText.trim(),
                        price: priceEl.innerText.trim(),
                        href: titleEl.href
                    });
                }
            });
            return results.slice(0, 15);
        });

        console.log(`\n--- FOUND ${items.length} GOODS ---`);
        items.forEach(i => console.log(`- ${i.text} [${i.price}] (${i.href})`));

    } catch (e) {
        console.error('Error:', e.message);
    } finally {
        await browser.close();
    }
}

const args = process.argv.slice(2);
browse(args[0] || 'https://plati.market/search/Papara');
