const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function checkDeps() {
    console.log('🔍 EXPLORATOR: Checking Web Surfer dependencies...');
    
    const requiredModules = ['puppeteer-extra', 'puppeteer-extra-plugin-stealth', 'puppeteer'];
    const missing = [];

    // Check Node Modules
    for (const mod of requiredModules) {
        try {
            require.resolve(mod);
        } catch (e) {
            missing.push(mod);
        }
    }

    if (missing.length > 0) {
        console.error('❌ Missing Node dependencies:');
        console.error(`   Run this in your repo root or skills folder:\n   npm install ${missing.join(' ')}`);
        return false;
    }

    // Check System Deps (Try launching chrome in dry run)
    try {
        const puppeteer = require('puppeteer-extra');
        const StealthPlugin = require('puppeteer-extra-plugin-stealth');
        puppeteer.use(StealthPlugin());
        
        // Use a lightweight check without full launch if possible, 
        // but launch is the only real test.
        // We'll skip deep system check here to avoid slow startup, 
        // relying on the script failure to prompt user later.
        console.log('✅ Node dependencies OK.');
        return true;
    } catch (e) {
        console.error('⚠️  System check warning:', e.message);
        return false;
    }
}

if (require.main === module) {
    if (!checkDeps()) process.exit(1);
}

module.exports = checkDeps;
