#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawn, spawnSync } from 'node:child_process';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const REPORT = process.argv.includes('--report');
const CONTRACT_ONLY = process.argv.includes('--contract-only');
const REQUIRED_RULES = ['00-centurion-base.md', '05-single-owner-routing.md', '10-antigravity-model-routing.md', '70-external-skill-safety.md'];
const REQUIRED_WORKFLOWS = ['war-room.md', 'quality-gate.md', 'external-skill-audit.md', 'skill-migrator.md', 'frontend-landing-igaming.md', 'frontend-reference-search.md', 'content-copy-system.md', 'agy-delegation.md'];
const REQUIRED_SKILLS = ['product-language-copy.md'];
const REQUIRED_AGY_PLUGIN_FILES = [
  'plugin.json',
  'mcp_config.json',
  path.join('skills', 'centurion-legion', 'SKILL.md')
];
const EXPECTED_LEGIONARIES = [
  ['OPTIO', 'orchestrator'],
  ['LIBRARIUS', 'planner'],
  ['EXPLORATOR', 'researcher'],
  ['PRAEMONITOR', 'praemonitor'],
  ['ARMARIUS', 'skill-quartermaster'],
  ['CODER', 'coder'],
  ['DEBUGGER', 'error-handler'],
  ['TESTER', 'tester'],
  ['REVIEWER', 'reviewer'],
  ['GUARDIAN', 'security'],
  ['PONTIFEX', 'pontifex'],
  ['LUDIFEX', 'ludifex'],
  ['AEDILIS', 'aedilis'],
  ['NOMENCLATOR', 'nomenclator'],
  ['GLOSSATOR', 'glossator'],
  ['PRAECO', 'praeco'],
  ['ALEATOR', 'aleator'],
  ['MERCATOR', 'mercator'],
  ['PICTOR', 'pictor'],
  ['ORATOR', 'orator'],
  ['INDAGATOR', 'indagator'],
  ['ARCHITECTUS', 'architect'],
  ['FABER', 'refactorer'],
  ['SCRIBA', 'documenter'],
  ['INTERPRES', 'prompt-engineer'],
  ['CURATOR', 'context-optimizer'],
  ['ARTIFEX', 'artifex'],
  ['SIGNIFER', 'git-master'],
  ['CENSOR', 'censor'],
  ['VELITES', 'velites'],
  ['HARUSPEX', 'haruspex'],
  ['SICARIUS', 'sicarius'],
  ['AUGUR', 'augur'],
  ['QUAESTOR', 'quaestor'],
  ['EVOCATUS', 'evocate-ad-opus'],
  ['TABULARIUS', 'tabularius'],
  ['CAPABILITIES', 'capabilities']
];
const ROUTING_MATRIX = [
  ['CAPABILITIES', 'покажи список доступных команд и способностей CENTURION'],
  ['SIGNIFER', 'подготовь git commit и pull request notes'],
  ['CURATOR', 'проведи skill surface audit на дубли и context token load'],
  ['INTERPRES', 'сформируй EARS requirements и acceptance criteria из промпта'],
  ['FABER', 'сделай behavior-preserving refactor и убери technical debt'],
  ['DEBUGGER', 'разбери stack trace crash runtime error по логам и воспроизведи'],
  ['LIBRARIUS', 'собери roadmap backlog TODO milestones и worklog'],
  ['OPTIO', 'составь план и маршрутизацию сложной задачи без реализации'],
  ['CODER', 'реализуй feature flag в коде приложения'],
  ['TESTER', 'напиши regression tests и coverage для формы'],
  ['REVIEWER', 'проведи review diff на баги и регрессии'],
  ['GUARDIAN', 'проверь security secrets mcp permissions и dependency риск'],
  ['GUARDIAN', 'deploy production wallet payment flow with private key rotation'],
  ['PRAEMONITOR', 'premortem failure assumptions risk tripwires'],
  ['ARMARIUS', 'найди github skill для antigravity и оцени кандидаты'],
  ['EXPLORATOR', 'найди референсы для SaaS landing pricing page'],
  ['CENSOR', 'проведи adversarial verification war room assumptions'],
  ['ARCHITECTUS', 'спроектируй architecture module boundaries ADR'],
  ['SCRIBA', 'обнови README и API docs guide'],
  ['ARTIFEX', 'создай skill и упакуй AgentSkill из SKILL.md'],
  ['PICTOR', 'создай frontend landing page с animation responsive UI'],
  ['AEDILIS', 'спроектируй UI design system dashboard components accessibility'],
  ['NOMENCLATOR', 'напиши названия кнопок подсказки CTA UX copy'],
  ['GLOSSATOR', 'проверь localization placeholders pluralization RTL text expansion'],
  ['INDAGATOR', 'сделай SEO schema metadata core web vitals аудит'],
  ['MERCATOR', 'сформируй funnel offer value prop conversion strategy'],
  ['ALEATOR', 'оцени iGaming bonus odds responsible gaming dark patterns'],
  ['PONTIFEX', 'проверь docker postgres CI service runtime health'],
  ['LUDIFEX', 'спроектируй Telegram Mini App game core loop и screen map'],
  ['PRAECO', 'реализуй Telegram Bot API Mini Apps SDK callback_data payments flow'],
  ['ORATOR', 'напиши social thread captions hashtags и content calendar'],
  ['VELITES', 'проведи recon port scan http headers attack surface fingerprint'],
  ['HARUSPEX', 'проведи SAST static analysis на SQL injection XSS RCE sinks'],
  ['SICARIUS', 'сделай PoC exploit verification через browser automation'],
  ['AUGUR', 'проанализируй Phantom1225 ScamNet sniper pump dump live pool'],
  ['QUAESTOR', 'проанализируй DEX token on-chain pool wallet trading risk'],
  ['EVOCATUS', 'delegate bounded task to external model opus in tmux and collect result'],
  ['TABULARIUS', 'сверстай HTML report с charts tables и publish handoff']
];
const OVERLAP_MATRIX = [
  ['ARMARIUS', 'найди github skill для antigravity и проверь безопасность', ['GUARDIAN', 'ARTIFEX']],
  ['LIBRARIUS', 'собери worklog roadmap и backlog без анализа runtime logs', ['OPTIO', 'SCRIBA']],
  ['ORATOR', 'напиши social captions и content calendar для launch campaign', ['MERCATOR', 'NOMENCLATOR']],
  ['QUAESTOR', 'проанализируй DEX token pool wallet trading risk без context optimization', ['AUGUR', 'GUARDIAN']],
  ['AUGUR', 'проанализируй ScamNet pump dump live pool и sniper timing', ['QUAESTOR', 'CENSOR']],
  ['CURATOR', 'проведи context token load skill surface drift audit', ['OPTIO', 'TESTER']],
  ['SIGNIFER', 'git commit branch PR release notes после тестов', ['REVIEWER', 'TESTER']],
  ['NOMENCLATOR', 'напиши CTA button labels tooltip copy для pricing page', ['MERCATOR', 'AEDILIS']],
  ['PRAECO', 'Telegram Mini Apps SDK callback_data payments flow для бота', ['LUDIFEX', 'GUARDIAN']],
  ['LUDIFEX', 'Telegram Mini App game concept core loop rewards', ['PRAECO', 'ALEATOR']]
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function assertFiles(directory, files) {
  for (const file of files) {
    assert(fs.existsSync(path.join(directory, file)), `missing ${path.join(directory, file)}`);
  }
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function listSkillSlugs(directory) {
  return fs.readdirSync(directory, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && fs.existsSync(path.join(directory, entry.name, 'SKILL.md')))
    .map((entry) => entry.name)
    .sort();
}

function walkFiles(directory) {
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (['node_modules', '.git', 'dist', 'build'].includes(entry.name)) continue;
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...walkFiles(fullPath));
    else files.push(fullPath);
  }
  return files;
}

function assertSingleOwnerContract() {
  const forbiddenPatterns = [
    { re: /recommendedLegion/, label: 'legacy recommendedLegion field' },
    { re: /Recommended Legion/, label: 'legacy Recommended Legion label' },
    { re: /^Adjacent:/m, label: 'legacy Adjacent routing label' },
    { re: /\| `[^`]+` \| [A-Z][A-Z-]+ \+ [A-Z][A-Z-]+/m, label: 'multi-owner workflow row' },
    { re: /local [A-Z][A-Z-]+\/[A-Z][A-Z-]+ workflows/, label: 'paired-owner workflow wording' }
  ];
  const checkedRoots = ['agent', 'agy-plugin', 'docs', 'scripts', 'mcp-server'];
  const files = checkedRoots.flatMap((root) => walkFiles(path.join(KIT_ROOT, root)))
    .concat([path.join(KIT_ROOT, 'README.md')])
    .filter((file) => /\.(md|mjs|json)$/.test(file))
    .filter((file) => path.relative(KIT_ROOT, file) !== path.join('scripts', 'smoke.mjs'));

  const violations = [];
  for (const file of files) {
    const relative = path.relative(KIT_ROOT, file);
    const text = fs.readFileSync(file, 'utf8');
    for (const pattern of forbiddenPatterns) {
      if (pattern.re.test(text)) violations.push(`${relative}: ${pattern.label}`);
    }
  }

  assert(violations.length === 0, `single-owner routing violations: ${violations.join('; ')}`);
}

function assertLegionSurface() {
  const source = fs.readFileSync(path.join(KIT_ROOT, 'mcp-server', 'index.mjs'), 'utf8');
  const expectedNames = EXPECTED_LEGIONARIES.map(([name]) => name).sort();
  const expectedSlugs = EXPECTED_LEGIONARIES.map(([, slug]) => slug).sort();
  const canonicalSkillRoot = path.join(os.homedir(), '.agents', 'skills');
  const installedSlugs = listSkillSlugs(canonicalSkillRoot);
  const missingInstalled = expectedSlugs.filter((slug) => !installedSlugs.includes(slug));
  const extraExpected = expectedSlugs.filter((slug, index, list) => list.indexOf(slug) !== index);

  assert(expectedNames.length === 37, `expected Legion surface should contain 37 owners, got ${expectedNames.length}`);
  assert(missingInstalled.length === 0, `expected skills missing from canonical root: ${missingInstalled.join(', ')}`);
  assert(extraExpected.length === 0, `duplicate expected skill slugs: ${extraExpected.join(', ')}`);

  for (const [name, slug] of EXPECTED_LEGIONARIES) {
    assert(source.includes(`name: '${name}'`), `MCP LEGIONARIES missing ${name}`);
    assert(source.includes(`slug: '${slug}'`), `MCP LEGIONARIES missing slug ${slug}`);
  }

  const mapping = fs.readFileSync(path.join(KIT_ROOT, 'docs', 'LEGION_MAPPING.md'), 'utf8');
  for (const [name] of EXPECTED_LEGIONARIES) {
    assert(mapping.includes(`| ${name} |`), `LEGION_MAPPING.md missing ${name}`);
  }

  const handoffNames = [...source.matchAll(/name: '([A-Z]+)'/g)].map((match) => match[1]);
  const unknownHandoffs = [...new Set(handoffNames.filter((name) => !expectedNames.includes(name)))];
  assert(unknownHandoffs.length === 0, `unknown handoff owner names: ${unknownHandoffs.join(', ')}`);
}

function stripAnsi(text) {
  return text.replace(/\x1b\[[0-9;]*m/g, '');
}

function agyBinary() {
  const local = path.join(os.homedir(), '.local', 'bin', 'agy');
  return fs.existsSync(local) ? local : 'agy';
}

function validateAgyPlugin(pluginDir) {
  const result = spawnSync(agyBinary(), ['plugin', 'validate', pluginDir], {
    cwd: KIT_ROOT,
    encoding: 'utf8',
    env: { ...process.env, AGY_CLI_DISABLE_AUTO_UPDATE: '1' }
  });
  assert(!result.error, `agy plugin validate failed to start: ${result.error?.message}`);
  assert(result.status === 0, `agy plugin validate failed: ${result.stderr || result.stdout}`);
  const output = stripAnsi(`${result.stdout}\n${result.stderr}`);
  assert(output.includes('skills') && output.includes('1 processed'), 'agy plugin validate did not process skills');
  assert(output.includes('mcpServers') && output.includes('2 processed'), 'agy plugin validate did not process both MCP servers');
}

function assertAgyPlugin(pluginDir) {
  assertFiles(pluginDir, REQUIRED_AGY_PLUGIN_FILES);
  const plugin = readJson(path.join(pluginDir, 'plugin.json'));
  assert(plugin.name === 'centurion-legion', 'agy plugin name mismatch');
  assert(plugin.disabled === false, 'agy plugin should be enabled');
  const mcpConfig = readJson(path.join(pluginDir, 'mcp_config.json'));
  const server = mcpConfig.mcpServers?.['centurion-legion'];
  assert(server?.command === 'node', 'agy plugin MCP command mismatch');
  assert(server?.args?.[0]?.endsWith(path.join('mcp-server', 'index.mjs')), 'agy plugin MCP args missing server path');
  assert(server?.env?.CENTURION_AGENT_ROOT, 'agy plugin MCP missing CENTURION_AGENT_ROOT');
  assert(server?.env?.CENTURION_SKILL_ROOT?.endsWith(path.join('.agents', 'skills')), 'agy plugin MCP missing canonical skill root');
  assertSerenaMcp(mcpConfig.mcpServers?.serena, 'agy plugin');
  validateAgyPlugin(pluginDir);
}

function assertSerenaMcp(server, label) {
  assert(server?.command === 'uvx', `${label} missing Serena MCP command`);
  assert(Array.isArray(server.args), `${label} Serena MCP args missing`);
  assert(server.args.includes('serena-agent'), `${label} Serena package missing`);
  assert(server.args.includes('start-mcp-server'), `${label} Serena server command missing`);
  assert(server.args.includes('--project-from-cwd'), `${label} Serena must activate projects from cwd`);
  assert(server.args.includes('--context') && server.args[server.args.indexOf('--context') + 1] === 'codex', `${label} Serena must use constrained codex context`);
  assert(server.args.includes('--enable-web-dashboard') && server.args[server.args.indexOf('--enable-web-dashboard') + 1] === 'false', `${label} Serena dashboard must be disabled`);
  assert(server.args.includes('--open-web-dashboard') && server.args[server.args.indexOf('--open-web-dashboard') + 1] === 'false', `${label} Serena must not open dashboard`);
}

function smokeInstaller() {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'antigravity-legion-install-'));
  try {
    const target = path.join(tempRoot, 'antigravity');
    const cliTarget = path.join(tempRoot, 'antigravity-cli');
    const result = spawnSync(process.execPath, [
      path.join(KIT_ROOT, 'installer', 'install.mjs'),
      '--target', target,
      '--cli-target', cliTarget,
      '--skip-agy-install'
    ], {
      cwd: KIT_ROOT,
      encoding: 'utf8'
    });
    assert(result.status === 0, `installer smoke failed: ${result.stderr || result.stdout}`);
    const report = JSON.parse(result.stdout);
    assert(report.copiedAgentPackTo === path.join(target, 'agent'), 'installer report missing IDE agent target');
    assert(report.agyCliPlugin?.pluginDir === path.join(cliTarget, 'plugins', 'centurion-legion'), 'installer report missing agy CLI plugin target');
    assert(report.agyCliPlugin?.agyInstall?.skipped === true, 'installer smoke must not call real agy plugin install');
    assert(report.agyCliPlugin?.manifest?.record?.source === 'local-install', 'installer smoke missing local manifest fallback');
    assert(fs.existsSync(path.join(target, 'agent', 'rules', '05-single-owner-routing.md')), 'installer did not copy IDE agent pack');
    const ideMcpConfig = readJson(path.join(target, 'mcp_config.json'));
    assertSerenaMcp(ideMcpConfig.mcpServers?.serena, 'IDE config');
    assertAgyPlugin(report.agyCliPlugin.pluginDir);
    const manifest = readJson(path.join(cliTarget, 'import_manifest.json'));
    const record = manifest.imports?.find((entry) => entry.name === 'centurion-legion');
    assert(record?.source === 'local-install', 'agy import manifest missing local-install record');
    assert(record.components?.includes('skills') && record.components?.includes('mcpServers'), 'agy import manifest missing plugin components');
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
}

function smokeAgyOrderGuard() {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'agy-order-guard-'));
  const symlinkTarget = fs.mkdtempSync(path.join(os.tmpdir(), 'agy-order-guard-symlink-'));
  const orderId = 'smoke-agy-order-20260825';
  const snapshotPath = path.join(os.tmpdir(), `${orderId}-snapshot.json`);
  const snapshotRelative = `.centurion/agents_results/${orderId}/AGY_SNAPSHOT.json`;
  const resultRelative = `.centurion/agents_results/${orderId}/AGY_RESULT.json`;
  const productArtifact = 'product/report.html';
  try {
    fs.writeFileSync(path.join(tempRoot, 'index.html'), '<main>before</main>\n');
    fs.writeFileSync(path.join(tempRoot, 'package.json'), '{"type":"module"}\n');
    const guard = path.join(KIT_ROOT, 'scripts', 'agy-order-guard.mjs');
    const verifyArgs = ['verify', '--workspace', tempRoot, '--order-id', orderId, '--before', snapshotPath, '--allowed', `index.html,${productArtifact}`, '--result', resultRelative];
    const verify = (...extra) => spawnSync(process.execPath, [guard, ...verifyArgs, ...extra], { encoding: 'utf8' });
    const writeResult = (result) => fs.writeFileSync(path.join(tempRoot, resultRelative), `${JSON.stringify(result, null, 2)}\n`);
    const canonical = (overrides = {}) => ({
      resultVersion: 'AGENT_RESULT_JSON_V1',
      orderId,
      executor: 'agy',
      status: 'done',
      summary: 'Canonical AGY smoke result.',
      filesChanged: [
        { path: 'index.html', action: 'modified' },
        { path: productArtifact, action: 'added' }
      ],
      artifacts: [{ path: productArtifact, exists: true, type: 'html', note: 'Product artifact stays outside the controller namespace.' }],
      proof: [{ command: 'synthetic smoke', cwd: tempRoot, status: 'pass', exitCode: 0, summary: 'passed' }],
      selfReview: { performed: true, findings: [], fixesApplied: [] },
      scopeDeviations: [],
      forbiddenPatternHits: [],
      remainingRisks: [],
      questions: [],
      errors: [],
      stdoutSummary: '',
      stderrSummary: '',
      ...overrides
    });
    const legacy = {
      orderVersion: 'AGY_ORDER_V1',
      owner: 'PICTOR',
      status: 'done',
      filesChanged: ['index.html', productArtifact],
      proof: [{ command: 'synthetic smoke', result: 'passed', summary: 'passed' }],
      selfReviewFixed: 'yes',
      scopeViolations: [],
      forbiddenPatternHits: [],
      remainingRisks: []
    };

    const snap = spawnSync(process.execPath, [guard, 'snapshot', '--workspace', tempRoot, '--order-id', orderId, '--out', snapshotPath], { encoding: 'utf8' });
    assert(snap.status === 0, `agy-order-guard snapshot failed: ${snap.stderr || snap.stdout}`);
    assert(fs.existsSync(snapshotPath), 'namespaced AGY snapshot was not created');
    const originalSnapshot = fs.readFileSync(snapshotPath);
    const originalDigest = fs.readFileSync(`${snapshotPath}.sha256`);
    const repeatedSnapshot = spawnSync(process.execPath, [guard, 'snapshot', '--workspace', tempRoot, '--order-id', orderId, '--out', snapshotPath], { encoding: 'utf8' });
    assert(repeatedSnapshot.status !== 0, 'repeated AGY snapshot must fail');
    assert(fs.readFileSync(snapshotPath).equals(originalSnapshot), 'repeated AGY snapshot must preserve the original bytes');
    assert(fs.readFileSync(`${snapshotPath}.sha256`).equals(originalDigest), 'repeated AGY snapshot must preserve custody digest');
    fs.writeFileSync(path.join(tempRoot, 'index.html'), '<main>after</main>\n');
    fs.mkdirSync(path.join(tempRoot, 'product'), { recursive: true });
    fs.writeFileSync(path.join(tempRoot, productArtifact), '<main>product artifact</main>\n');
    fs.mkdirSync(path.dirname(path.join(tempRoot, resultRelative)), { recursive: true });

    writeResult(canonical());
    const ok = verify('--forbidden', 'fonts\\.googleapis,font-size\\s*:[^;]*vw');
    assert(ok.status === 0, `canonical AGY result should pass by default: ${ok.stderr || ok.stdout}`);

    writeResult(legacy);
    const legacyDefault = verify();
    assert(legacyDefault.status !== 0, 'legacy AGY_ORDER_V1 result must fail without --allow-legacy');
    assert((legacyDefault.stdout || '').includes('result.resultVersion'), 'default legacy rejection should identify the missing canonical result version');
    const legacyAllowed = verify('--allow-legacy');
    assert(legacyAllowed.status === 0, `legacy result should pass only with --allow-legacy: ${legacyAllowed.stderr || legacyAllowed.stdout}`);

    writeResult({ ...canonical(), orderVersion: 'AGY_ORDER_V1' });
    const hybrid = verify();
    assert(hybrid.status !== 0 && (hybrid.stdout || '').includes('legacy fields'), 'canonical/legacy hybrid result must fail in default mode');
    writeResult(canonical({ orderId: 'smoke-agy-wrong-order-20260825' }));
    const wrongOrder = verify();
    assert(wrongOrder.status !== 0 && (wrongOrder.stdout || '').includes('orderId'), 'wrong canonical orderId must fail');
    writeResult(canonical({ executor: 'codex' }));
    const wrongExecutor = verify();
    assert(wrongExecutor.status !== 0 && (wrongExecutor.stdout || '').includes('executor'), 'wrong canonical executor must fail');
    writeResult(canonical({ filesChanged: ['index.html'], selfReview: [] }));
    const malformedNested = verify();
    assert(malformedNested.status !== 0, 'malformed canonical nested shapes must fail');
    assert((malformedNested.stdout || '').includes('filesChanged[0]') && (malformedNested.stdout || '').includes('selfReview'), 'nested-shape rejection should report filesChanged and selfReview');
    writeResult(canonical({ selfReview: { performed: false, findings: [], fixesApplied: [] } }));
    const missingSelfReview = verify();
    assert(missingSelfReview.status !== 0 && (missingSelfReview.stdout || '').includes('selfReview.performed=true'), 'done canonical result must report performed self-review');
    writeResult(canonical({ scopeDeviations: ['outside scope'] }));
    const reportedScopeDeviation = verify();
    assert(reportedScopeDeviation.status !== 0 && (reportedScopeDeviation.stdout || '').includes('scope deviations'), 'reported canonical scope deviations must block done acceptance');
    writeResult(canonical({ forbiddenPatternHits: ['forbidden'] }));
    const reportedForbiddenHit = verify();
    assert(reportedForbiddenHit.status !== 0 && (reportedForbiddenHit.stdout || '').includes('forbidden'), 'reported canonical forbidden hits must block done acceptance');
    writeResult(canonical({ proof: [] }));
    const emptyProof = verify();
    assert(emptyProof.status !== 0 && (emptyProof.stdout || '').includes('at least one proof'), 'done canonical result with empty proof must fail');
    writeResult(canonical({ proof: [{ command: 'synthetic smoke', cwd: tempRoot, status: 'fail', exitCode: 1, summary: 'failed' }] }));
    const failedProof = verify();
    assert(failedProof.status !== 0 && (failedProof.stdout || '').includes('every proof[].status'), 'done canonical result with failed proof must fail');
    writeResult(canonical({ filesChanged: [{ path: 'index.html', action: 'modified' }] }));
    const underReported = verify();
    assert(underReported.status !== 0 && (underReported.stdout || '').includes('filesChanged[].path mismatch'), 'canonical filesChanged under-reporting must fail');
    writeResult(canonical({ filesChanged: [...canonical().filesChanged, { path: 'product/absent.html', action: 'added' }] }));
    const overReported = verify();
    assert(overReported.status !== 0 && (overReported.stdout || '').includes('filesChanged[].path mismatch'), 'canonical filesChanged over-reporting must fail');

    writeResult(canonical());
    fs.writeFileSync(path.join(tempRoot, 'AGY_RESULT.json'), '{ malformed legacy root result');
    const legacyRoot = spawnSync(process.execPath, [guard, 'verify', '--workspace', tempRoot, '--order-id', orderId, '--before', snapshotRelative, '--allowed', 'index.html', '--result', 'AGY_RESULT.json'], { encoding: 'utf8' });
    assert(legacyRoot.status !== 0, 'agy-order-guard must reject a legacy root result path');
    assert((legacyRoot.stderr || '').includes('result path must be namespaced'), 'root result rejection should happen before result parsing');
    assert(fs.existsSync(path.join(tempRoot, 'AGY_RESULT.json')), 'legacy root result should remain untouched by guard');
    fs.rmSync(path.join(tempRoot, 'AGY_RESULT.json'), { force: true });
    const traversalResult = `.centurion/agents_results/${orderId}/../${orderId}/AGY_RESULT.json`;
    const traversal = spawnSync(process.execPath, [guard, ...verifyArgs.slice(0, -1), traversalResult], { encoding: 'utf8' });
    assert(traversal.status !== 0 && (traversal.stderr || '').includes("'..'"), 'control-artifact traversal must fail before result access');
    const unsafeId = spawnSync(process.execPath, [guard, 'snapshot', '--workspace', tempRoot, '--order-id', '../unsafe-order', '--out', snapshotPath], { encoding: 'utf8' });
    assert(unsafeId.status !== 0 && (unsafeId.stderr || '').includes('unsafe'), 'unsafe orderId must fail');
    const inWorkspaceSnapshot = spawnSync(process.execPath, [guard, 'verify', '--workspace', tempRoot, '--order-id', orderId, '--before', `.centurion/agents_results/${orderId}/AGY_SNAPSHOT.json`, '--allowed', 'index.html', '--result', resultRelative], { encoding: 'utf8' });
    assert(inWorkspaceSnapshot.status !== 0 && (inWorkspaceSnapshot.stderr || '').includes('outside the workspace'), 'in-workspace snapshot custody path must fail');

    fs.writeFileSync(snapshotPath, Buffer.from('{"tampered":true}\n'));
    const tampered = verify();
    assert(tampered.status !== 0 && (tampered.stderr || '').includes('raw snapshot evidence'), 'tampered snapshot must be rejected with raw evidence');
    const rejectedEvidence = fs.readdirSync(path.dirname(snapshotPath)).find((name) => name.endsWith('.rejected.bin'));
    assert(rejectedEvidence && fs.readFileSync(path.join(path.dirname(snapshotPath), rejectedEvidence)).equals(Buffer.from('{"tampered":true}\n')), 'tampered snapshot raw bytes must be preserved');
    fs.writeFileSync(snapshotPath, originalSnapshot);
    fs.writeFileSync(`${snapshotPath}.sha256`, originalDigest);

    const parseRejectedBytes = Buffer.from('{ invalid snapshot json\n');
    fs.writeFileSync(snapshotPath, parseRejectedBytes);
    fs.writeFileSync(`${snapshotPath}.sha256`, `${crypto.createHash('sha256').update(parseRejectedBytes).digest('hex')}\n`);
    const parseRejected = verify();
    assert(parseRejected.status !== 0 && (parseRejected.stderr || '').includes('raw snapshot evidence'), 'AGY invalid JSON snapshot must preserve raw evidence after digest verification');
    const parseEvidence = fs.readdirSync(path.dirname(snapshotPath)).find((name) => name.endsWith('.rejected.bin') && fs.readFileSync(path.join(path.dirname(snapshotPath), name)).equals(parseRejectedBytes));
    assert(parseEvidence, 'AGY invalid JSON snapshot evidence must preserve exact raw bytes');

    fs.writeFileSync(snapshotPath, originalSnapshot);
    const invalidDigestBytes = Buffer.from('invalid digest content\n');
    fs.writeFileSync(`${snapshotPath}.sha256`, invalidDigestBytes);
    const invalidDigest = verify();
    assert(invalidDigest.status !== 0 && (invalidDigest.stderr || '').includes('digest') && (invalidDigest.stderr || '').includes('raw snapshot evidence'), 'AGY invalid digest content must be rejected with raw snapshot evidence');
    const invalidDigestEvidence = fs.readdirSync(path.dirname(snapshotPath)).find((name) => name.endsWith('.rejected.bin') && fs.readFileSync(path.join(path.dirname(snapshotPath), name)).equals(originalSnapshot));
    assert(invalidDigestEvidence, 'AGY invalid digest evidence must preserve exact raw snapshot bytes');

    fs.writeFileSync(snapshotPath, originalSnapshot);
    fs.rmSync(`${snapshotPath}.sha256`, { force: true });
    const missingDigest = verify();
    assert(missingDigest.status !== 0 && (missingDigest.stderr || '').includes('raw snapshot evidence'), 'AGY missing digest must preserve raw snapshot evidence');
    const missingDigestEvidence = fs.readdirSync(path.dirname(snapshotPath)).find((name) => name.endsWith('.rejected.bin') && fs.readFileSync(path.join(path.dirname(snapshotPath), name)).equals(originalSnapshot));
    assert(missingDigestEvidence, 'AGY missing digest evidence must preserve exact raw bytes');
    fs.writeFileSync(`${snapshotPath}.sha256`, originalDigest);

    const snapshotSymlinkTarget = path.join(symlinkTarget, 'AGY_SNAPSHOT.json');
    fs.writeFileSync(snapshotSymlinkTarget, originalSnapshot);
    fs.rmSync(snapshotPath, { force: true });
    fs.symlinkSync(snapshotSymlinkTarget, snapshotPath, 'file');
    const symlinkedSnapshot = verify();
    assert(symlinkedSnapshot.status !== 0 && (symlinkedSnapshot.stderr || '').includes('symlink'), 'AGY snapshot symlink must be rejected before reading bytes');
    fs.rmSync(snapshotPath, { force: true });
    fs.writeFileSync(snapshotPath, originalSnapshot);

    const digestSymlinkTarget = path.join(symlinkTarget, 'AGY_SNAPSHOT.sha256');
    fs.writeFileSync(digestSymlinkTarget, originalDigest);
    fs.rmSync(`${snapshotPath}.sha256`, { force: true });
    fs.symlinkSync(digestSymlinkTarget, `${snapshotPath}.sha256`, 'file');
    const symlinkedDigest = verify();
    assert(symlinkedDigest.status !== 0 && (symlinkedDigest.stderr || '').includes('symlink component rejected'), 'AGY companion digest symlink must be rejected before reading bytes');
    fs.rmSync(`${snapshotPath}.sha256`, { force: true });
    fs.writeFileSync(`${snapshotPath}.sha256`, originalDigest);

    fs.writeFileSync(path.join(tempRoot, 'package.json'), '{"type":"module","mutated":true}\n');
    const bad = verify();
    assert(bad.status !== 0, 'agy-order-guard verify should fail on scope drift');
    assert((bad.stdout || '').includes('package.json'), 'agy-order-guard scope failure should mention package.json');

    fs.writeFileSync(path.join(symlinkTarget, 'AGY_SNAPSHOT.json'), fs.readFileSync(snapshotPath));
    fs.writeFileSync(path.join(symlinkTarget, 'AGY_RESULT.json'), JSON.stringify(canonical()));
    const namespacePath = path.dirname(path.join(tempRoot, snapshotRelative));
    fs.rmSync(namespacePath, { recursive: true, force: true });
    fs.symlinkSync(symlinkTarget, namespacePath, 'dir');
    const symlinked = verify();
    assert(symlinked.status !== 0 && (symlinked.stderr || '').includes('symlink alias'), 'symlinked control namespace must fail');
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
    fs.rmSync(snapshotPath, { force: true });
    fs.rmSync(`${snapshotPath}.sha256`, { force: true });
    fs.rmSync(symlinkTarget, { recursive: true, force: true });
  }
}

function smokeAgyWorkspaceSymlink() {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'agy-order-guard-product-symlink-'));
  const outsideRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'agy-order-guard-product-outside-'));
  const orderId = 'smoke-agy-product-symlink-20260825';
  const snapshotPath = path.join(os.tmpdir(), `${orderId}-snapshot.json`);
  const resultRelative = `.centurion/agents_results/${orderId}/AGY_RESULT.json`;
  const productArtifact = 'product/report.html';
  const outsideTarget = path.join(outsideRoot, 'outside.html');
  const outsideArtifact = path.join(outsideRoot, 'rejected-artifact.json');
  const rejectedSnapshotPath = path.join(os.tmpdir(), `${orderId}-symlink-${process.pid}.json`);
  try {
    const guard = path.join(KIT_ROOT, 'scripts', 'agy-order-guard.mjs');
    fs.writeFileSync(path.join(tempRoot, 'index.html'), '<main>before</main>\n');
    fs.writeFileSync(path.join(tempRoot, 'package.json'), '{"type":"module"}\n');
    const initialSnapshot = spawnSync(process.execPath, [guard, 'snapshot', '--workspace', tempRoot, '--order-id', orderId, '--out', snapshotPath], { encoding: 'utf8' });
    assert(initialSnapshot.status === 0, `initial AGY symlink fixture snapshot failed: ${initialSnapshot.stderr || initialSnapshot.stdout}`);

    fs.mkdirSync(path.join(tempRoot, 'product'), { recursive: true });
    fs.writeFileSync(outsideTarget, '<main>outside secret</main>\n');
    const outsideBytes = fs.readFileSync(outsideTarget);
    fs.symlinkSync(outsideTarget, path.join(tempRoot, productArtifact), 'file');

    const rejectedSnapshot = spawnSync(process.execPath, [guard, 'snapshot', '--workspace', tempRoot, '--order-id', orderId, '--out', rejectedSnapshotPath], { encoding: 'utf8' });
    assert(rejectedSnapshot.status !== 0, 'AGY snapshot must reject a product-file symlink');
    assert((rejectedSnapshot.stderr || '').includes('symlink component rejected'), 'AGY snapshot symlink rejection should be explicit');
    assert(fs.readFileSync(outsideTarget).equals(outsideBytes), 'AGY snapshot symlink rejection must not alter the outside target');
    assert(!fs.existsSync(outsideArtifact), 'AGY snapshot symlink rejection created an outside artifact');

    fs.mkdirSync(path.dirname(path.join(tempRoot, resultRelative)), { recursive: true });
    fs.writeFileSync(path.join(tempRoot, resultRelative), `${JSON.stringify({ resultVersion: 'AGENT_RESULT_JSON_V1' })}\n`);
    const rejectedVerify = spawnSync(process.execPath, [guard, 'verify', '--workspace', tempRoot, '--order-id', orderId, '--before', snapshotPath, '--allowed', `index.html,${productArtifact}`, '--result', resultRelative], { encoding: 'utf8' });
    assert(rejectedVerify.status !== 0, 'AGY verify must reject a product-file symlink');
    assert((rejectedVerify.stderr || '').includes('symlink component rejected'), 'AGY verify symlink rejection should be explicit');
    assert(fs.readFileSync(outsideTarget).equals(outsideBytes), 'AGY verify symlink rejection must not alter the outside target');
    assert(!fs.existsSync(outsideArtifact), 'AGY verify symlink rejection created an outside artifact');
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
    fs.rmSync(snapshotPath, { force: true });
    fs.rmSync(`${snapshotPath}.sha256`, { force: true });
    fs.rmSync(rejectedSnapshotPath, { force: true });
    fs.rmSync(`${rejectedSnapshotPath}.sha256`, { force: true });
    fs.rmSync(outsideRoot, { recursive: true, force: true });
  }
}

function smokeStandaloneKitImport() {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'antigravity-legion-standalone-'));
  const standaloneKit = path.join(tempRoot, 'kit');
  const orderId = 'smoke-standalone-import-20260825';
  try {
    fs.cpSync(KIT_ROOT, standaloneKit, { recursive: true });
    const guard = path.join(standaloneKit, 'scripts', 'agy-order-guard.mjs');
    const snapshotPath = path.join(tempRoot, `${orderId}-snapshot.json`);
    const result = spawnSync(process.execPath, [guard, 'snapshot', '--workspace', standaloneKit, '--order-id', orderId, '--out', snapshotPath], {
      cwd: standaloneKit,
      encoding: 'utf8'
    });
    assert(result.status === 0, `standalone kit guard import failed: ${result.stderr || result.stdout}`);
    assert(fs.existsSync(snapshotPath) && fs.existsSync(`${snapshotPath}.sha256`), 'standalone kit did not create controller custody snapshot');
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
}

function smokeLegionContracts() {
  const validator = path.join(KIT_ROOT, 'legion-contracts', 'scripts', 'legion-contract.mjs');
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'agy-legion-contract-'));
  try {
    const resultFile = path.join(tempRoot, '.centurion', 'agents_results', 'smoke-agy-contract-20260825', 'AGY_RESULT.json');
    fs.mkdirSync(path.dirname(resultFile), { recursive: true });
    fs.writeFileSync(resultFile, JSON.stringify({
      resultVersion: 'AGENT_RESULT_JSON_V1',
      orderId: 'smoke-agy-contract-20260825',
      executor: 'agy',
      status: 'done',
      summary: 'Canonical bundled contract accepted.',
      filesChanged: [{ path: 'index.html', action: 'modified' }],
      artifacts: [],
      proof: [{ command: 'synthetic', cwd: tempRoot, status: 'pass', exitCode: 0, summary: 'passed' }],
      selfReview: { performed: true, findings: [], fixesApplied: [] },
      scopeDeviations: [],
      forbiddenPatternHits: [],
      remainingRisks: [],
      questions: [],
      errors: [],
      stdoutSummary: '',
      stderrSummary: ''
    }, null, 2));
    const ok = spawnSync(process.execPath, [validator, 'validate-agent-result', '--file', resultFile, '--order-id', 'smoke-agy-contract-20260825', '--executor', 'agy'], { encoding: 'utf8' });
    assert(ok.status === 0, `canonical AGY result should pass bundled shared contract: ${ok.stderr || ok.stdout}`);
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
}

function send(child, payload) {
  child.stdin.write(`${JSON.stringify(payload)}\n`);
}

function sendRaw(child, line) {
  child.stdin.write(`${line}\n`);
}

async function smokeMcp() {
  const child = spawn(process.execPath, [path.join(KIT_ROOT, 'mcp-server', 'index.mjs')], {
    cwd: KIT_ROOT,
    stdio: ['pipe', 'pipe', 'pipe']
  });
  const responses = [];
  let stdout = '';
  let stderr = '';
  child.stdout.on('data', (chunk) => {
    stdout += chunk.toString('utf8');
    const lines = stdout.split('\n');
    stdout = lines.pop() || '';
    for (const line of lines) {
      if (line.trim()) responses.push(JSON.parse(line));
    }
  });
  child.stderr.on('data', (chunk) => { stderr += chunk.toString('utf8'); });

  send(child, { jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05' } });
  send(child, { jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} });
  send(child, { jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name: 'quality_gate', arguments: { changeType: 'agent-config' } } });
  send(child, { jsonrpc: '2.0', id: 4, method: 'tools/call', params: { name: 'external_skill_sources', arguments: {} } });
  send(child, { jsonrpc: '2.0', id: 5, method: 'tools/call', params: { name: 'external_skill_intake', arguments: { repository: 'google-antigravity/antigravity-sdk-python' } } });
  send(child, { jsonrpc: '2.0', id: 6, method: 'tools/call', params: { name: 'frontend_source_intake', arguments: { category: 'igaming-reference', repository: 'QI-D/mini-casino-frontend' } } });
  send(child, { jsonrpc: '2.0', id: 7, method: 'tools/call', params: { name: 'content_source_intake', arguments: { category: 'copywriting-reference', repository: 'isaacavazquez/website' } } });
  send(child, { jsonrpc: '2.0', id: 8, method: 'tools/call', params: { name: 'frontend_reference_search', arguments: { query: 'SaaS landing pricing testimonials', pageType: 'landing', stack: 'tailwind', limit: 5 } } });
  send(child, { jsonrpc: '2.0', id: 9, method: 'tools/call', params: { name: 'select_legionary', arguments: { task: 'найди референсы для SaaS landing pricing page' } } });
  send(child, { jsonrpc: '2.0', id: 10, method: 'tools/call', params: { name: 'mission_prep', arguments: { task: 'создай frontend landing page по референсам' } } });
  send(child, { jsonrpc: '2.0', id: 11, method: 'tools/call', params: { name: 'select_legionary', arguments: { task: 'создай frontend landing page по референсам' } } });
  send(child, { jsonrpc: '2.0', id: 12, method: 'tools/call', params: { name: 'select_legionary', arguments: { task: 'найди github skill для antigravity и проверь' } } });
  send(child, { jsonrpc: '2.0', id: 13, method: 'tools/call', params: { name: 'select_legionary', arguments: { task: 'создай iGaming casino lobby UI' } } });
  send(child, { jsonrpc: '2.0', id: 14, method: 'tools/call', params: { name: 'select_legionary', arguments: { task: 'design system architecture for dashboard components' } } });
  send(child, { jsonrpc: '2.0', id: 15, method: 'tools/call', params: { name: 'agy_delegation_brief', arguments: { task: 'создай responsive React landing hero animation', owner: 'PICTOR', workspace: '/tmp/example-ui', orderId: 'smoke-agy-brief-20260825', changeType: 'frontend' } } });
  send(child, { jsonrpc: '2.0', id: 16, method: 'tools/call', params: { name: 'agy_delegation_brief', arguments: { task: 'deploy production wallet payment flow with private key rotation', owner: 'GUARDIAN', workspace: '/tmp/example-risk', orderId: 'smoke-agy-risk-20260825', changeType: 'security' } } });
  sendRaw(child, '{"jsonrpc":"2.0","id":17,"id":1700,"method":"ping"}');
  for (let index = 0; index < ROUTING_MATRIX.length; index += 1) {
    send(child, { jsonrpc: '2.0', id: 100 + index, method: 'tools/call', params: { name: 'select_legionary', arguments: { task: ROUTING_MATRIX[index][1] } } });
  }
  for (let index = 0; index < OVERLAP_MATRIX.length; index += 1) {
    send(child, { jsonrpc: '2.0', id: 200 + index, method: 'tools/call', params: { name: 'select_legionary', arguments: { task: OVERLAP_MATRIX[index][1] } } });
  }

  await new Promise((resolve) => setTimeout(resolve, 250));
  child.kill('SIGTERM');

  assert(!stderr, `MCP server wrote to stderr: ${stderr}`);
  assert(responses.some((response) => response.id === 1 && response.result?.serverInfo?.name === 'centurion-legion'), 'initialize response missing');
  const list = responses.find((response) => response.id === 2);
  assert(list?.result?.tools?.length >= 5, 'tools/list returned too few tools');
  assert(list.result.tools.some((tool) => tool.name === 'agy_delegation_brief'), 'tools/list missing agy_delegation_brief');
  const gate = responses.find((response) => response.id === 3);
  assert(gate?.result?.content?.[0]?.text.includes('MCP stdio smoke'), 'quality_gate response missing expected proof text');
  const sources = responses.find((response) => response.id === 4);
  assert(sources?.result?.content?.[0]?.text.includes('rmyndharis/antigravity-skills'), 'external_skill_sources missing catalog content');
  const intake = responses.find((response) => response.id === 5);
  assert(intake?.result?.content?.[0]?.text.includes('programmatic SDK path'), 'external_skill_intake missing safety guidance');
  const frontendIntake = responses.find((response) => response.id === 6);
  assert(frontendIntake?.result?.content?.[0]?.text.includes('responsible-gaming'), 'frontend_source_intake missing iGaming safety guidance');
  assert(frontendIntake?.result?.content?.[0]?.text.includes('Owner:'), 'frontend_source_intake missing owner');
  assert(frontendIntake?.result?.content?.[0]?.text.includes('Conditional handoffs:'), 'frontend_source_intake missing conditional handoffs');
  assert(!frontendIntake?.result?.content?.[0]?.text.includes('Recommended Legion'), 'frontend_source_intake returned legacy recommended legion wording');
  const contentIntake = responses.find((response) => response.id === 7);
  assert(contentIntake?.result?.content?.[0]?.text.includes('claim audit'), 'content_source_intake missing claim safety guidance');
  assert(contentIntake?.result?.content?.[0]?.text.includes('Owner:'), 'content_source_intake missing owner');
  assert(contentIntake?.result?.content?.[0]?.text.includes('Conditional handoffs:'), 'content_source_intake missing conditional handoffs');
  assert(!contentIntake?.result?.content?.[0]?.text.includes('Recommended Legion'), 'content_source_intake returned legacy recommended legion wording');
  const referenceSearch = responses.find((response) => response.id === 8);
  const referenceText = referenceSearch?.result?.content?.[0]?.text || '';
  assert(referenceText.includes('Frontend reference index'), 'frontend_reference_search missing index header');
  assert(referenceText.includes('installAllowlist=false'), 'frontend_reference_search missing safety policy');
  assert(referenceText.includes('Owner: EXPLORATOR'), 'frontend_reference_search missing owner guidance');
  assert(/shadcnblocks|Flowbite|HyperUI/i.test(referenceText), 'frontend_reference_search missing expected landing references');
  const selection = responses.find((response) => response.id === 9);
  const selected = JSON.parse(selection?.result?.content?.[0]?.text || '{}');
  assert(selected.owner?.name === 'EXPLORATOR', 'select_legionary did not route reference search to EXPLORATOR owner');
  assert(Array.isArray(selected.handoffs) && selected.handoffs.every((handoff) => handoff.trigger), 'select_legionary missing conditional handoff triggers');
  const missionPrep = responses.find((response) => response.id === 10);
  const missionText = missionPrep?.result?.content?.[0]?.text || '';
  assert(missionText.includes('Owner:'), 'mission_prep missing owner');
  assert(missionText.includes('Owner: PICTOR'), 'mission_prep did not keep build-from-references task under PICTOR owner');
  assert(missionText.includes('Conditional handoffs:'), 'mission_prep missing conditional handoffs');
  assert(!missionText.includes('Adjacent:'), 'mission_prep returned legacy Adjacent label');
  const buildSelection = responses.find((response) => response.id === 11);
  const buildSelected = JSON.parse(buildSelection?.result?.content?.[0]?.text || '{}');
  assert(buildSelected.owner?.name === 'PICTOR', 'select_legionary did not keep build-from-references task under PICTOR owner');
  assert(buildSelected.handoffs?.some((handoff) => handoff.name === 'EXPLORATOR'), 'build-from-references task missing EXPLORATOR handoff');
  const skillSearch = responses.find((response) => response.id === 12);
  const skillSelected = JSON.parse(skillSearch?.result?.content?.[0]?.text || '{}');
  assert(skillSelected.owner?.name === 'ARMARIUS', 'external skill discovery did not route to ARMARIUS owner');
  assert(skillSelected.handoffs?.some((handoff) => handoff.name === 'GUARDIAN'), 'external skill discovery missing GUARDIAN safety handoff');
  const igamingUi = responses.find((response) => response.id === 13);
  const igamingSelected = JSON.parse(igamingUi?.result?.content?.[0]?.text || '{}');
  assert(igamingSelected.owner?.name === 'PICTOR', 'iGaming UI build did not route to PICTOR owner');
  assert(igamingSelected.handoffs?.some((handoff) => handoff.name === 'ALEATOR'), 'iGaming UI build missing ALEATOR handoff');
  assert(igamingSelected.handoffs?.some((handoff) => handoff.name === 'GUARDIAN'), 'iGaming UI build missing GUARDIAN handoff');
  const uiDesignSystem = responses.find((response) => response.id === 14);
  const uiDesignSelected = JSON.parse(uiDesignSystem?.result?.content?.[0]?.text || '{}');
  assert(uiDesignSelected.owner?.name === 'AEDILIS', 'UI design-system task did not route to AEDILIS owner');
  const agyBrief = responses.find((response) => response.id === 15);
  const agyText = agyBrief?.result?.content?.[0]?.text || '';
  assert(agyText.includes('AUXILIUM AGY delegation brief'), 'agy_delegation_brief missing header');
  assert(agyText.includes('Legion owner remains: PICTOR'), 'agy_delegation_brief did not preserve primary owner');
  assert(agyText.includes('AGY_ORDER v1 prompt shape'), 'agy_delegation_brief missing AGY_ORDER prompt shape');
  assert(agyText.includes('AGY_RESULT.json'), 'agy_delegation_brief missing structured result file');
  assert(agyText.includes('AGY orderId: smoke-agy-brief-20260825'), 'agy_delegation_brief missing exact order identity');
  assert(agyText.includes('Control namespace: .centurion/agents_results/smoke-agy-brief-20260825'), 'agy_delegation_brief missing control namespace');
  assert(agyText.includes('--order-id smoke-agy-brief-20260825'), 'agy_delegation_brief missing namespaced order-id commands');
  assert(agyText.includes('--result .centurion/agents_results/smoke-agy-brief-20260825/AGY_RESULT.json'), 'agy_delegation_brief missing namespaced result command');
  assert(!agyText.includes('--result AGY_RESULT.json'), 'agy_delegation_brief must not advertise a root result path');
  assert(agyText.includes('"resultVersion": "AGENT_RESULT_JSON_V1"'), 'agy_delegation_brief missing canonical result version');
  assert(agyText.includes('"orderId": "smoke-agy-brief-20260825"'), 'agy_delegation_brief missing canonical order identity');
  assert(agyText.includes('"executor": "agy"'), 'agy_delegation_brief missing canonical executor identity');
  assert(agyText.includes('"filesChanged": [{"path":"relative/path","action":'), 'agy_delegation_brief missing object-shaped filesChanged field');
  assert(agyText.includes('"selfReview": {"performed":true'), 'agy_delegation_brief missing canonical self-review object');
  assert(agyText.includes('Legacy compatibility only (--allow-legacy; not the default):'), 'agy_delegation_brief missing labeled legacy compatibility section');
  assert(agyText.includes('--allow-legacy'), 'agy_delegation_brief missing explicit legacy compatibility flag');
  assert(agyText.includes('SELF_REVIEW_PERFORMED=<true|false>'), 'agy_delegation_brief missing canonical final self-review marker');
  assert(agyText.includes('agy-order-guard.mjs'), 'agy_delegation_brief missing owner-side guard command');
  assert(agyText.includes('Do not delegate to agy when:'), 'agy_delegation_brief missing blocked delegation guidance');
  const blockedAgyBrief = responses.find((response) => response.id === 16);
  const blockedAgyText = blockedAgyBrief?.result?.content?.[0]?.text || '';
  assert(blockedAgyText.includes('Legion owner remains: GUARDIAN'), 'high-risk agy_delegation_brief did not preserve GUARDIAN owner');
  assert(blockedAgyText.includes('Delegation verdict: owner-only'), 'high-risk agy_delegation_brief did not block delegation');
  assert(blockedAgyText.includes('high-risk secrets, production, payment, wallet, exploit, or destructive surface'), 'high-risk agy_delegation_brief missing risk reason');
  const duplicateIdResponses = responses.filter((response) => response.id === 17 || response.id === 1700);
  assert(duplicateIdResponses.length === 0, 'duplicate JSON-RPC id request must not be accepted with either id value');
  const duplicateIdError = responses.find((response) => response.error?.code === -32700 && response.error.message.includes('duplicate key'));
  assert(duplicateIdError, 'duplicate JSON-RPC id request must return a parse error');

  const routingFailures = [];
  const routingPasses = [];
  for (let index = 0; index < ROUTING_MATRIX.length; index += 1) {
    const [expectedOwner, task] = ROUTING_MATRIX[index];
    const response = responses.find((item) => item.id === 100 + index);
    const payload = JSON.parse(response?.result?.content?.[0]?.text || '{}');
    const selectedOwner = payload.owner?.name;
    if (selectedOwner !== expectedOwner) routingFailures.push(`${task} -> ${selectedOwner || 'none'}; expected ${expectedOwner}`);
    else routingPasses.push({ owner: selectedOwner, slug: payload.owner?.slug, task });
  }
  assert(routingFailures.length === 0, `routing matrix failures: ${routingFailures.join(' | ')}`);

  const overlapFailures = [];
  for (let index = 0; index < OVERLAP_MATRIX.length; index += 1) {
    const [expectedOwner, task, expectedHandoffs] = OVERLAP_MATRIX[index];
    const response = responses.find((item) => item.id === 200 + index);
    const payload = JSON.parse(response?.result?.content?.[0]?.text || '{}');
    const selectedOwner = payload.owner?.name;
    const handoffNames = new Set((payload.handoffs || []).map((handoff) => handoff.name));
    if (selectedOwner !== expectedOwner) overlapFailures.push(`${task} -> ${selectedOwner || 'none'}; expected ${expectedOwner}`);
    for (const handoffName of expectedHandoffs) {
      if (!handoffNames.has(handoffName)) overlapFailures.push(`${task} missing handoff ${handoffName}`);
    }
  }
  assert(overlapFailures.length === 0, `overlap routing failures: ${overlapFailures.join(' | ')}`);
  if (REPORT) {
    const owners = [...new Set(routingPasses.map((pass) => pass.owner))].sort();
    process.stdout.write(`Legion routing eval: ${routingPasses.length}/${ROUTING_MATRIX.length} cases pass; ${owners.length}/${EXPECTED_LEGIONARIES.length} owners covered\n`);
    for (const pass of routingPasses) {
      process.stdout.write(`- ${pass.owner} / ${pass.slug}: ${pass.task}\n`);
    }
  }
}

async function main() {
  if (CONTRACT_ONLY) {
    await smokeMcp();
    smokeAgyOrderGuard();
    smokeAgyWorkspaceSymlink();
    smokeStandaloneKitImport();
    smokeLegionContracts();
    process.stdout.write('antigravity-legion-kit contract smoke: pass\n');
    return;
  }
  assertFiles(path.join(KIT_ROOT, 'agent', 'rules'), REQUIRED_RULES);
  assertFiles(path.join(KIT_ROOT, 'agent', 'workflows'), REQUIRED_WORKFLOWS);
  assertFiles(path.join(KIT_ROOT, 'agent', 'skills'), REQUIRED_SKILLS);
  assertAgyPlugin(path.join(KIT_ROOT, 'agy-plugin'));
  assertLegionSurface();
  assertSingleOwnerContract();

  const packageJson = readJson(path.join(KIT_ROOT, 'package.json'));
  assert(packageJson.bin?.['centurion-legion-mcp'], 'package bin centurion-legion-mcp missing');
  assert(packageJson.bin?.['install-antigravity-legion'], 'package bin install-antigravity-legion missing');
  assert(fs.existsSync(path.join(KIT_ROOT, 'docs', 'EXTERNAL_CATALOG.md')), 'external catalog missing');
  assert(fs.existsSync(path.join(KIT_ROOT, 'docs', 'external-catalog.json')), 'external catalog JSON missing');
  assert(fs.existsSync(path.join(KIT_ROOT, 'docs', 'FRONTEND_CATALOG.md')), 'frontend catalog missing');
  assert(fs.existsSync(path.join(KIT_ROOT, 'docs', 'frontend-catalog.json')), 'frontend catalog JSON missing');
  assert(fs.existsSync(path.join(KIT_ROOT, 'docs', 'FRONTEND_REFERENCE_INDEX.md')), 'frontend reference index missing');
  assert(fs.existsSync(path.join(KIT_ROOT, 'docs', 'frontend-reference-index.json')), 'frontend reference index JSON missing');
  assert(fs.existsSync(path.join(KIT_ROOT, 'docs', 'CONTENT_COPY_CATALOG.md')), 'content copy catalog missing');
  assert(fs.existsSync(path.join(KIT_ROOT, 'docs', 'content-copy-catalog.json')), 'content copy catalog JSON missing');

  const mcpSchema = readJson('/opt/antigravity/resources/app/extensions/antigravity/schemas/mcp_config.schema.json');
  assert(mcpSchema.properties?.mcpServers, 'Antigravity MCP schema not found or changed');

  const catalogCheck = spawnSync(process.execPath, [path.join(KIT_ROOT, 'scripts', 'refresh-external-catalog.mjs'), '--check'], {
    cwd: KIT_ROOT,
    encoding: 'utf8'
  });
  assert(catalogCheck.status === 0, `catalog check failed: ${catalogCheck.stderr || catalogCheck.stdout}`);

  const frontendCatalogCheck = spawnSync(process.execPath, [path.join(KIT_ROOT, 'scripts', 'refresh-frontend-catalog.mjs'), '--check'], {
    cwd: KIT_ROOT,
    encoding: 'utf8'
  });
  assert(frontendCatalogCheck.status === 0, `frontend catalog check failed: ${frontendCatalogCheck.stderr || frontendCatalogCheck.stdout}`);

  const frontendReferenceCheck = spawnSync(process.execPath, [path.join(KIT_ROOT, 'scripts', 'refresh-frontend-reference-index.mjs'), '--check'], {
    cwd: KIT_ROOT,
    encoding: 'utf8'
  });
  assert(frontendReferenceCheck.status === 0, `frontend reference index check failed: ${frontendReferenceCheck.stderr || frontendReferenceCheck.stdout}`);

  const contentCatalogCheck = spawnSync(process.execPath, [path.join(KIT_ROOT, 'scripts', 'refresh-content-catalog.mjs'), '--check'], {
    cwd: KIT_ROOT,
    encoding: 'utf8'
  });
  assert(contentCatalogCheck.status === 0, `content catalog check failed: ${contentCatalogCheck.stderr || contentCatalogCheck.stdout}`);

  await smokeMcp();
  smokeInstaller();
  smokeAgyOrderGuard();
  smokeAgyWorkspaceSymlink();
  smokeStandaloneKitImport();
  smokeLegionContracts();
  process.stdout.write('antigravity-legion-kit smoke: pass\n');
}

main().catch((error) => {
  process.stderr.write(`antigravity-legion-kit smoke: fail: ${error.message}\n`);
  process.exitCode = 1;
});
