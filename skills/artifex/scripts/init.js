const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const skillName = args[0];
const description = args[1];

if (!skillName || !description) {
    console.error('Usage: node init.js <skill-name-kebab-case> "<Description. Use when...>" [options]');
    console.log('Options: --scripts, --references, --assets');
    process.exit(1);
}

// Enforce kebab-case
if (!/^[a-z0-9-]+$/.test(skillName)) {
    console.error('Error: Skill name must be kebab-case (lowercase, numbers, hyphens only).');
    process.exit(1);
}

const skillsRoot = path.join(process.env.HOME, 'agent-tools/skills');
const skillDir = path.join(skillsRoot, skillName);

if (fs.existsSync(skillDir)) {
    console.error(`Skill "${skillName}" already exists at ${skillDir}`);
    process.exit(1);
}

// Create Structure
fs.mkdirSync(skillDir, { recursive: true });

if (args.includes('--scripts')) fs.mkdirSync(path.join(skillDir, 'scripts'));
if (args.includes('--references')) fs.mkdirSync(path.join(skillDir, 'references'));
if (args.includes('--assets')) fs.mkdirSync(path.join(skillDir, 'assets'));

// Create SKILL.md Template from Best Practices
const content = `---
name: ${skillName}
description: ${description}
allowed-tools: Read, Write, Exec
---

# ${skillName.toUpperCase().replace(/-/g, ' ')}

## Overview
(Briefly explain what this skill does)

## Instructions
-# Workflow: [Main Task Name]
--# Step 1: [Action]
Instruction...

--# Step 2: [Action]
Instruction...

## Troubleshooting
- **Error:** [Common error]
- **Solution:** [Fix]

## Resources
${args.includes('--scripts') ? '- Scripts: See \`scripts/\` for executable tools.' : ''}
${args.includes('--references') ? '- References: See \`references/\` for detailed documentation.' : ''}
`;

fs.writeFileSync(path.join(skillDir, 'SKILL.md'), content);

console.log(`✅ Skill "${skillName}" created at ${skillDir}`);
console.log(`👉 Next step: Edit ${path.join(skillDir, 'SKILL.md')}`);
console.log(`   (Don't forget to run validate.js after editing!)`);
