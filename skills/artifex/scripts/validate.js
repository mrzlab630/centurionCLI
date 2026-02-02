const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const skillPath = args[0];

if (!skillPath) {
    console.error('Usage: node validate.js <path-to-skill>');
    process.exit(1);
}

const skillDir = path.resolve(skillPath);
const skillMdPath = path.join(skillDir, 'SKILL.md');
const folderName = path.basename(skillDir);

const errors = [];
const warnings = [];

// 1. Check Structure
if (!fs.existsSync(skillDir)) {
    console.error(`Error: Directory ${skillDir} does not exist.`);
    process.exit(1);
}

if (!fs.existsSync(skillMdPath)) {
    errors.push('Missing SKILL.md file (case-sensitive).');
}

if (fs.existsSync(path.join(skillDir, 'README.md'))) {
    errors.push('Remove README.md from skill folder. Use SKILL.md for docs.');
}

// 2. Check Naming (kebab-case)
const kebabCaseRegex = /^[a-z0-9-]+$/;
if (!kebabCaseRegex.test(folderName)) {
    errors.push(`Folder name "${folderName}" must be kebab-case (no spaces, no caps).`);
}

// 3. Check Frontmatter
if (fs.existsSync(skillMdPath)) {
    const content = fs.readFileSync(skillMdPath, 'utf8');
    const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/);
    
    if (!frontmatterMatch) {
        errors.push('SKILL.md missing valid YAML frontmatter (--- ... ---).');
    } else {
        const fm = frontmatterMatch[1];
        
        // Parse YAML roughly
        const nameMatch = fm.match(/^name:\s*(.+)$/m);
        const descMatch = fm.match(/^description:\s*(.+)$/m);
        
        if (!nameMatch) errors.push('Frontmatter missing "name" field.');
        else {
            const name = nameMatch[1].trim();
            if (name !== folderName) warnings.push(`Frontmatter name "${name}" should match folder name "${folderName}".`);
            if (!kebabCaseRegex.test(name)) errors.push(`Frontmatter name "${name}" must be kebab-case.`);
        }

        if (!descMatch) errors.push('Frontmatter missing "description" field.');
        else {
            const desc = descMatch[1].trim();
            if (desc.length > 1024) errors.push('Description too long (>1024 chars).');
            if (desc.includes('<') || desc.includes('>')) errors.push('Description contains XML tags (< or >) - Forbidden.');
            if (!desc.toLowerCase().includes('use when') && !desc.toLowerCase().includes('triggers')) {
                warnings.push('Description should explicitly state WHEN to use it (triggers).');
            }
        }
    }
}

// Report
console.log(`\n🔍 Validating Skill: ${folderName}\n`);

if (errors.length > 0) {
    console.log('❌ CRITICAL ERRORS:');
    errors.forEach(e => console.log(`   - ${e}`));
    console.log('\nValidation FAILED.');
    process.exit(1);
} else {
    console.log('✅ Structure Valid.');
}

if (warnings.length > 0) {
    console.log('\n⚠️  WARNINGS (Best Practices):');
    warnings.forEach(w => console.log(`   - ${w}`));
} else {
    console.log('✨ Perfect!');
}
