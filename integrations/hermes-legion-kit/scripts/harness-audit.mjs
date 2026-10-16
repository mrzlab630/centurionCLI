#!/usr/bin/env node
import { auditClient } from '../../codex-legion-kit/scripts/codex-surface-audit.mjs';
try {const r=auditClient('hermes',process.argv.slice(2));console.log(JSON.stringify(r,null,2));if(!r.ok)process.exitCode=1;}
catch(e){console.error(e.message);process.exitCode=1;}
