#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import {
  CONTROL_NAMESPACE_ROOT,
  AGY_RESULT_FILE,
  AGY_SNAPSHOT_FILE,
  deriveControlPaths,
  validateOrderId
} from '../lib/control-artifact-namespace.mjs';
import { parseStrictJson } from '../legion-contracts/lib/contracts.mjs';

const KIT_ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const AGENT_ROOT = process.env.CENTURION_AGENT_ROOT || path.join(KIT_ROOT, 'agent');
const CANONICAL_SKILL_ROOT = process.env.CENTURION_SKILL_ROOT || path.join(os.homedir(), '.agents', 'skills');
const CATALOG_JSON_PATH = path.join(KIT_ROOT, 'docs', 'external-catalog.json');
const FRONTEND_CATALOG_JSON_PATH = path.join(KIT_ROOT, 'docs', 'frontend-catalog.json');
const FRONTEND_REFERENCE_INDEX_JSON_PATH = path.join(KIT_ROOT, 'docs', 'frontend-reference-index.json');
const CONTENT_CATALOG_JSON_PATH = path.join(KIT_ROOT, 'docs', 'content-copy-catalog.json');

const LEGIONARIES = [
  { name: 'OPTIO', slug: 'orchestrator', kind: 'command', use: 'planning, routing, handoffs' },
  { name: 'LIBRARIUS', slug: 'planner', kind: 'command', use: 'task planning, TODOs, sequencing, and durable project knowledge' },
  { name: 'CODER', slug: 'coder', kind: 'build', use: 'implementation and focused fixes' },
  { name: 'DEBUGGER', slug: 'error-handler', kind: 'build', use: 'runtime debugging, logs, stack traces, crashes, and flaky behavior' },
  { name: 'TESTER', slug: 'tester', kind: 'build', use: 'tests, evals, proof design' },
  { name: 'REVIEWER', slug: 'reviewer', kind: 'build', use: 'code review and regression risk' },
  { name: 'GUARDIAN', slug: 'security', kind: 'security', use: 'security, secrets, MCP safety gates' },
  { name: 'PRAEMONITOR', slug: 'praemonitor', kind: 'command', use: 'premortem and failure forecasts' },
  { name: 'ARMARIUS', slug: 'skill-quartermaster', kind: 'command', use: 'external skill discovery before safety audit' },
  { name: 'EXPLORATOR', slug: 'researcher', kind: 'command', use: 'codebase, documentation, web, and reference research' },
  { name: 'CENSOR', slug: 'censor', kind: 'security', use: 'adversarial verification' },
  { name: 'ARCHITECTUS', slug: 'architect', kind: 'architecture', use: 'system design and module boundaries' },
  { name: 'FABER', slug: 'refactorer', kind: 'architecture', use: 'behavior-preserving refactors and technical-debt cleanup' },
  { name: 'SCRIBA', slug: 'documenter', kind: 'craft', use: 'README, docs, API notes' },
  { name: 'INTERPRES', slug: 'prompt-engineer', kind: 'craft', use: 'prompt specs, EARS requirements, and domain framing' },
  { name: 'CURATOR', slug: 'context-optimizer', kind: 'craft', use: 'context optimization, skill-surface audits, and token discipline' },
  { name: 'ARTIFEX', slug: 'artifex', kind: 'craft', use: 'skill creation, migration, and packaging' },
  { name: 'SIGNIFER', slug: 'git-master', kind: 'craft', use: 'git operations, commits, branches, conflicts, and PR prep' },
  { name: 'LUDIFEX', slug: 'ludifex', kind: 'product', use: 'Telegram Mini App game concepts, screens, loops, rules, and rewards' },
  { name: 'PICTOR', slug: 'pictor', kind: 'product', use: 'frontend implementation and UI polish' },
  { name: 'AEDILIS', slug: 'aedilis', kind: 'product', use: 'UX architecture and accessibility' },
  { name: 'NOMENCLATOR', slug: 'nomenclator', kind: 'product', use: 'product language, UX writing, naming, CTA, microcopy' },
  { name: 'GLOSSATOR', slug: 'glossator', kind: 'product', use: 'localization readiness, glossary, placeholders, text expansion' },
  { name: 'PRAECO', slug: 'praeco', kind: 'product', use: 'Telegram Bot API, Mini Apps SDK, grammY, payments, and platform constraints' },
  { name: 'INDAGATOR', slug: 'indagator', kind: 'product', use: 'SEO, schema, search visibility, Core Web Vitals' },
  { name: 'MERCATOR', slug: 'mercator', kind: 'product', use: 'positioning, funnel, conversion strategy' },
  { name: 'ALEATOR', slug: 'aleator', kind: 'product', use: 'ethical gamification and iGaming mechanics' },
  { name: 'ORATOR', slug: 'orator', kind: 'product', use: 'social posts, threads, captions, replies, and content calendars' },
  { name: 'PONTIFEX', slug: 'pontifex', kind: 'ops', use: 'DevOps, DB, runtime health' },
  { name: 'VELITES', slug: 'velites', kind: 'security', use: 'active reconnaissance, ports, HTTP headers, and attack surface' },
  { name: 'HARUSPEX', slug: 'haruspex', kind: 'security', use: 'static vulnerability analysis, dangerous patterns, and SAST candidates' },
  { name: 'SICARIUS', slug: 'sicarius', kind: 'security', use: 'exploit verification via browser automation and PoC attempts' },
  { name: 'AUGUR', slug: 'augur', kind: 'security', use: 'Phantom1225, ScamNet, pool intelligence, and pump/dump behavior' },
  { name: 'QUAESTOR', slug: 'quaestor', kind: 'security', use: 'crypto/on-chain, DEX, token, pool, and trading-risk intelligence' },
  { name: 'EVOCATUS', slug: 'evocate-ad-opus', kind: 'utility', use: 'bounded external-model delegation in tmux and result collection' },
  { name: 'TABULARIUS', slug: 'tabularius', kind: 'utility', use: 'reports, charts, HTML publishing, and large analysis formatting' },
  { name: 'CAPABILITIES', slug: 'capabilities', kind: 'utility', use: 'capability and command reference' }
];

const TOOLS = [
  {
    name: 'mission_prep',
    description: 'Return a compact Antigravity/CENTURION mission plan for a task.',
    inputSchema: {
      type: 'object',
      properties: {
        task: { type: 'string', description: 'User task or mission statement.' },
        workspace: { type: 'string', description: 'Optional workspace path.' }
      },
      required: ['task']
    }
  },
  {
    name: 'select_legionary',
    description: 'Select one primary owner and conditional handoffs for a task.',
    inputSchema: {
      type: 'object',
      properties: {
        task: { type: 'string' }
      },
      required: ['task']
    }
  },
  {
    name: 'load_skill_brief',
    description: 'Load a short brief from the canonical Legion skill root.',
    inputSchema: {
      type: 'object',
      properties: {
        skill: { type: 'string', description: 'Skill slug, such as coder, tester, security, or architect.' }
      },
      required: ['skill']
    }
  },
  {
    name: 'war_room',
    description: 'Generate a structured adversarial plan with Prosecutor, Advocate, and Judge.',
    inputSchema: {
      type: 'object',
      properties: {
        topic: { type: 'string' },
        horizon: { type: 'string', default: '6 months' }
      },
      required: ['topic']
    }
  },
  {
    name: 'quality_gate',
    description: 'Return a proof checklist before claiming completion.',
    inputSchema: {
      type: 'object',
      properties: {
        changeType: { type: 'string', description: 'code, docs, frontend, backend, infra, security, or agent-config.' }
      }
    }
  },
  {
    name: 'agy_delegation_brief',
    description: 'Return a bounded AUXILIUM AGY delegation brief plus acceptance gates for a task.',
    inputSchema: {
      type: 'object',
      properties: {
        task: { type: 'string', description: 'Task to consider delegating to agy.' },
        owner: { type: 'string', description: 'Optional current Legionary owner. If omitted, routing selects one.' },
        workspace: { type: 'string', description: 'Workspace path where agy should run. Default: current working directory.' },
        orderId: { type: 'string', description: 'Safe AGY order identity used for all controller artifacts.' },
        changeType: { type: 'string', description: 'Optional gate type: code, docs, frontend, backend, infra, security, or agent-config.' },
        allowedPaths: { type: 'array', items: { type: 'string' }, description: 'Files or directories agy may read/edit. Result file is added separately.' },
        nonGoals: { type: 'array', items: { type: 'string' }, description: 'Explicit exclusions that agy must not reinterpret.' },
        proofCommands: { type: 'array', items: { type: 'string' }, description: 'Commands agy must run or report as unavailable.' },
        forbiddenPatterns: { type: 'array', items: { type: 'string' }, description: 'Regex/text patterns that must not appear in touched files.' },
        resultFile: { type: 'string', description: 'Optional namespaced result path. Defaults to .centurion/agents_results/<orderId>/AGY_RESULT.json.' }
      },
      required: ['task', 'orderId']
    }
  },
  {
    name: 'external_skill_sources',
    description: 'Return the curated external Antigravity skill source catalog and safety posture.',
    inputSchema: {
      type: 'object',
      properties: {
        filter: { type: 'string', description: 'Optional text filter for the catalog.' }
      }
    }
  },
  {
    name: 'external_skill_intake',
    description: 'Return a safe intake recommendation for a curated external Antigravity repository.',
    inputSchema: {
      type: 'object',
      properties: {
        repository: { type: 'string', description: 'Repository name such as owner/name. Omit to list all candidates.' },
        decision: { type: 'string', description: 'Optional safety decision filter: adapt-only, reference-only, needs-approval, blocked, or accept.' }
      }
    }
  },
  {
    name: 'frontend_sources',
    description: 'Return the curated frontend, landing, motion, and iGaming source catalog.',
    inputSchema: {
      type: 'object',
      properties: {
        filter: { type: 'string', description: 'Optional text filter for the frontend catalog.' }
      }
    }
  },
  {
    name: 'frontend_source_intake',
    description: 'Return a safe intake recommendation for a curated frontend, landing, motion, or iGaming repository.',
    inputSchema: {
      type: 'object',
      properties: {
        category: { type: 'string', description: 'Optional category filter: agent-skill, landing-template, motion-catalog, component-catalog, or igaming-reference.' },
        repository: { type: 'string', description: 'Repository name such as owner/name. Omit to list all matching candidates.' },
        decision: { type: 'string', description: 'Optional safety decision filter: adapt-only, reference-only, needs-approval, blocked, or accept.' }
      }
    }
  },
  {
    name: 'frontend_reference_search',
    description: 'Search implemented frontend page, block, template, and product-flow references for a user request.',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Natural-language UI request, such as SaaS pricing landing or admin dashboard.' },
        pageType: { type: 'string', description: 'Optional page/screen type: landing, dashboard, auth, settings, ecommerce, onboarding, mobile-app, igaming, etc.' },
        stack: { type: 'string', description: 'Optional preferred stack: React, Next.js, Tailwind, shadcn, Vue, HTML, etc.' },
        style: { type: 'string', description: 'Optional style direction: clean, SaaS, premium, animated, admin, ecommerce, etc.' },
        limit: { type: 'number', description: 'Maximum references to return. Default 5.' }
      },
      required: ['query']
    }
  },
  {
    name: 'content_sources',
    description: 'Return the curated content, UX writing, product language, and conversion-copy source catalog.',
    inputSchema: {
      type: 'object',
      properties: {
        filter: { type: 'string', description: 'Optional text filter for the content/copy catalog.' }
      }
    }
  },
  {
    name: 'content_source_intake',
    description: 'Return a safe intake recommendation for a curated content, UX writing, product language, or copywriting repository.',
    inputSchema: {
      type: 'object',
      properties: {
        category: { type: 'string', description: 'Optional category filter such as content-style-guide, content-design-system, brand-voice-system, accessibility-copy, experimentation-copy, agent-copy-skill, copywriting-reference, or prompt-copy-reference.' },
        repository: { type: 'string', description: 'Repository name such as owner/name. Omit to list all matching candidates.' },
        decision: { type: 'string', description: 'Optional safety decision filter: adapt-only, reference-only, needs-approval, blocked, or accept.' }
      }
    }
  }
];

const keywordRoutes = [
  { re: /capabilit|what can.*centurion|available skills|commands|help|способност|что уме|команд|легионер.*список|список.*легионер/i, primary: 'CAPABILITIES', handoffs: [
    { name: 'OPTIO', trigger: 'the capability question becomes a routed work request' },
    { name: 'CURATOR', trigger: 'the answer needs skill-surface or context-load optimization' }
  ] },
  { re: /\bgit\b|commit|branch|merge|rebase|conflict|pull request|\bpr\b|changelog|release note|коммит|ветк|конфликт|пуш|пулл.?реквест/i, primary: 'SIGNIFER', handoffs: [
    { name: 'REVIEWER', trigger: 'a risky diff needs review before commit or PR' },
    { name: 'TESTER', trigger: 'the commit or PR needs proof commands captured' }
  ] },
  { re: /context token load|token load|token budget|skill surface|context load|drift|duplicate skill|surface audit|оптимизац.*контекст|контекст.*оптимизац|токен.*контекст|пересеч.*скил|дрифт/i, primary: 'CURATOR', handoffs: [
    { name: 'OPTIO', trigger: 'context findings change routing or task ownership' },
    { name: 'TESTER', trigger: 'skill-surface or drift checks need deterministic evals' }
  ] },
  { re: /private key|credential|secret|prod(?:uction)? deploy|production auth|payment flow|kyc|signing|custody|destructive command|sudo|rm -rf|приватн.*ключ|секрет|деплой.*прод|прод.*деплой|платеж|kyc|подписан|кастоди/i, primary: 'GUARDIAN', handoffs: [
    { name: 'QUAESTOR', trigger: 'crypto wallet, token, pool, or on-chain domain facts are required for the security decision' },
    { name: 'PONTIFEX', trigger: 'production deployment, service, database, or runtime ownership proof is required' },
    { name: 'CENSOR', trigger: 'risk acceptance or safety assumptions need adversarial verification' },
    { name: 'TESTER', trigger: 'mitigation needs deterministic proof, smoke, or regression coverage' }
  ] },
  { re: /phantom1225|scamnet|sniper|dump timing|bonding curve|pump.?dump|live pool|мемкоин|памп|дамп|снайпер.*пул/i, primary: 'AUGUR', handoffs: [
    { name: 'QUAESTOR', trigger: 'pool behavior needs broader DEX/token/on-chain analysis' },
    { name: 'CENSOR', trigger: 'combat-intelligence conclusions need adversarial challenge' }
  ] },
  { re: /dex|token|on.?chain|pool|wallet|trading risk|contract address|liquidity|ohlc|crypto|крипто|он.?чейн|токен|ликвидност|кошелек/i, primary: 'QUAESTOR', handoffs: [
    { name: 'AUGUR', trigger: 'analysis focuses on Phantom1225, ScamNet, pump/dump, or sniper behavior' },
    { name: 'GUARDIAN', trigger: 'wallet, private-key, signing, scam, or custody risk appears' }
  ] },
  { re: /prompt|ears|requirements|acceptance criteria|system prompt|domain framing|rewrite prompt|промпт|требован|критер.*прием|спецификац/i, primary: 'INTERPRES', handoffs: [
    { name: 'OPTIO', trigger: 'the prompt spec must become a routed execution plan' },
    { name: 'TESTER', trigger: 'requirements need deterministic eval cases' }
  ] },
  { re: /refactor|technical debt|clean code|behavior.preserving|без изменени.*поведен|рефактор|техдолг|декомпози.*код/i, primary: 'FABER', handoffs: [
    { name: 'TESTER', trigger: 'behavior preservation needs regression proof' },
    { name: 'REVIEWER', trigger: 'the refactor diff needs regression-oriented review' }
  ] },
  { re: /debug|stack trace|traceback|crash|panic|runtime error|error logs?|stack logs?|exception|flaky|repro|ошибк|(?:^|\W)лог(?:и|ов|ам|ах)?(?:$|\W)|стектрейс|падает|краш|воспроизвед/i, primary: 'DEBUGGER', handoffs: [
    { name: 'CODER', trigger: 'root cause is proven and implementation is required' },
    { name: 'TESTER', trigger: 'the bug needs a regression test or reproducible eval' }
  ] },
  { re: /todo|task list|roadmap|milestone|backlog|sequence|durable memory|worklog|план работ|список задач|роадмап|майлстоун|беклог/i, primary: 'LIBRARIUS', handoffs: [
    { name: 'OPTIO', trigger: 'the plan needs active Legionary routing and handoff control' },
    { name: 'SCRIBA', trigger: 'the plan must be published as project documentation' }
  ] },
  { re: /optio|orchestrat|routing|route task|mission plan|маршрут|маршрутизац|составь план|состави план|план.*без реализац|декомпоз|sequenc/i, primary: 'OPTIO', handoffs: [
    { name: 'EXPLORATOR', trigger: 'the plan needs repository, documentation, web, or reference facts first' },
    { name: 'PRAEMONITOR', trigger: 'the plan needs premortem tripwires before execution' },
    { name: 'GUARDIAN', trigger: 'security, MCP, dependency, plugin, or secret risk appears' },
    { name: 'TESTER', trigger: 'the plan needs deterministic proof or eval coverage' }
  ] },
  { re: /adversarial verification|censor|red team|critique|challenge assumptions|assumption.*verification|проведи.*adversarial|верификац.*(предполож|assumption)|проверь.*предполож|оспорь|сломай.*план|разбей.*план/i, primary: 'CENSOR', handoffs: [
    { name: 'PRAEMONITOR', trigger: 'the critique must become a premortem with warning signs and tripwires' },
    { name: 'REVIEWER', trigger: 'the adversarial finding concerns a concrete code diff or regression' },
    { name: 'GUARDIAN', trigger: 'the adversarial finding concerns security, MCP, secrets, or dependency risk' },
    { name: 'TESTER', trigger: 'a claim needs deterministic reproduction or an eval' }
  ] },
  { re: /premortem|pre-mortem|failure forecast|failure mode|tripwire|warning sign|риск.*план|прогноз.*сбо|сбо.*прогноз/i, primary: 'PRAEMONITOR', handoffs: [
    { name: 'CENSOR', trigger: 'the winning plan needs adversarial verification' },
    { name: 'ARCHITECTUS', trigger: 'failure analysis exposes architecture-boundary changes' },
    { name: 'TESTER', trigger: 'failure scenarios must become deterministic checks or evals' }
  ] },
  { re: /ui design system|component system|design system.*(ui|frontend|component|dashboard)|dashboard component.*design|screen structure|visual hierarchy|ux architecture|accessibility.*(design|component)|компонентн.*систем|дизайн.?систем/i, primary: 'AEDILIS', handoffs: [
    { name: 'PICTOR', trigger: 'the design-system decision must become frontend code' },
    { name: 'NOMENCLATOR', trigger: 'labels, helper text, CTA, or state copy constrain the UX' },
    { name: 'TESTER', trigger: 'component states, accessibility, or responsive proof is required' }
  ] },
  { re: /telegram mini app.*game|mini app game|game concept|core loop|game loop|screen map|reward model|игров.*цикл|концепт.*игр|telegram.*игр|мини.?апп.*игр/i, primary: 'LUDIFEX', handoffs: [
    { name: 'PRAECO', trigger: 'Telegram Mini App platform, Bot API, payments, or client constraints appear' },
    { name: 'ALEATOR', trigger: 'progression, rewards, retention, or dark-pattern risk appears' },
    { name: 'PICTOR', trigger: 'game screens must be implemented in frontend' }
  ] },
  { re: /telegram bot|bot api|mini apps sdk|grammy|inline keyboard|callback_data|telegram payments|webapp|web app data|praeco|бот.*telegram|mini apps|мини.?апп|клавиатур.*telegram/i, primary: 'PRAECO', handoffs: [
    { name: 'LUDIFEX', trigger: 'the Telegram work is game-product architecture' },
    { name: 'GUARDIAN', trigger: 'payments, auth, sessions, webapp data, or abuse risk appears' },
    { name: 'TESTER', trigger: 'Bot API callbacks, payments, or Mini App flows need proof' }
  ] },
  { re: /i18n|l10n|locali[sz]ation|locale|plural|pluralization|rtl|right.to.left|placeholder|translation key|glossary|text expansion|локализац|перевод|плейсхолдер|плюрал|глоссар|расширени.*текст/i, primary: 'GLOSSATOR', handoffs: [
    { name: 'NOMENCLATOR', trigger: 'localized strings need source-copy or naming decisions first' },
    { name: 'AEDILIS', trigger: 'text expansion or RTL affects layout, hierarchy, or component fit' },
    { name: 'PICTOR', trigger: 'i18n decisions must be wired into frontend components' },
    { name: 'TESTER', trigger: 'locale behavior, placeholders, or RTL need proof' }
  ] },
  { re: /social|thread|tweet|x post|caption|hashtags|content calendar|community|short.form|reels|пост|тред|соцсет|подпис|хэштег|контент.?план/i, primary: 'ORATOR', handoffs: [
    { name: 'MERCATOR', trigger: 'channel content needs positioning, audience, funnel, or campaign strategy' },
    { name: 'NOMENCLATOR', trigger: 'social copy must align with product language or UI terminology' },
    { name: 'CENSOR', trigger: 'claims, urgency, or sensitive-domain wording needs challenge' }
  ] },
  { re: /conversion|funnel|offer|value prop|value proposition|positioning|pricing strategy|cta strategy|go.to.market|campaign|воронк|оффер|позиционир|конверси/i, primary: 'MERCATOR', handoffs: [
    { name: 'NOMENCLATOR', trigger: 'strategy must become source UI copy' },
    { name: 'AEDILIS', trigger: 'offer hierarchy or CTA placement needs interface design' },
    { name: 'CENSOR', trigger: 'conversion claims or urgency need adversarial review' }
  ] },
  { re: /(созда|create|forge|package|pack|упак|собер|сдела).*(agentskill|agent skill|skill\.md|скил|skill)|(?:agentskill|agent skill|skill\.md).*(созда|create|package|упак|migrat|мигр)/i, primary: 'ARTIFEX', handoffs: [
    { name: 'GUARDIAN', trigger: 'the skill imports external code, MCP, dependencies, secrets, or broad permissions' },
    { name: 'OPTIO', trigger: 'the new skill changes Legion routing or ownership' },
    { name: 'TESTER', trigger: 'the skill needs evals or installer validation' },
    { name: 'SCRIBA', trigger: 'the skill needs user-facing docs or migration notes' }
  ] },
  { re: /((созда|сдела|постро|сверста|реализ|разработ|нарису|build|create|make|implement|develop).*(reference|references|inspiration|template|templates|blocks|examples|gallery|page flow|mobbin|pageflows|готов(ые|ую)|референс|рефы|пример|примеры|каталог|шаблон|страниц))|((reference|references|inspiration|template|templates|blocks|examples|gallery|page flow|mobbin|pageflows|готов(ые|ую)|референс|рефы|пример|примеры|каталог|шаблон|страниц).*(созда|сдела|постро|сверста|реализ|разработ|нарису|build|create|make|implement|develop))/i, primary: 'PICTOR', handoffs: [
    { name: 'EXPLORATOR', trigger: 'implemented references must be found before building' },
    { name: 'AEDILIS', trigger: 'reference choices must become layout, flow, or component-system decisions' },
    { name: 'GUARDIAN', trigger: 'external code, license, paid template, wallet, payment, or iGaming risk appears' },
    { name: 'NOMENCLATOR', trigger: 'reference copy must become product-specific UI text' },
    { name: 'TESTER', trigger: 'a runnable UI needs browser, responsive, or screenshot proof' }
  ] },
  { re: /((созда|сдела|постро|сверста|реализ|разработ|build|create|make|implement|develop).*(casino|igaming|gambling|betting|slot|jackpot|bonus|odds|rtp))|((casino|igaming|gambling|betting|slot|jackpot|bonus|odds|rtp).*(ui|frontend|interface|landing|page|screen|lobby|сверста|созда|сдела|постро|реализ|build|create|make|implement|develop))/i, primary: 'PICTOR', handoffs: [
    { name: 'ALEATOR', trigger: 'iGaming mechanics, rewards, odds, or dark-pattern risk must be judged' },
    { name: 'GUARDIAN', trigger: 'wallet, payment, deposit, withdrawal, KYC, affiliate, or abuse risk appears' },
    { name: 'NOMENCLATOR', trigger: 'odds, bonus, limits, terms, or risk copy must be written' },
    { name: 'TESTER', trigger: 'a runnable iGaming UI needs browser, responsive, or screenshot proof' }
  ] },
  { re: /external skill|github skill|third.party|findskills|skill catalog|скил.*github|github.*скил|найди.*скил|найди.*skill|искать.*скил|искать.*skill/i, primary: 'ARMARIUS', handoffs: [
    { name: 'GUARDIAN', trigger: 'a candidate needs safety, license, dependency, MCP, or install review' },
    { name: 'ARTIFEX', trigger: 'an accepted source must be migrated into a local skill, workflow, or rule' },
    { name: 'CENSOR', trigger: 'the acquisition decision or assumptions need adversarial verification' },
    { name: 'OPTIO', trigger: 'the intake changes Legion routing or task ownership' }
  ] },
  { re: /reference|references|inspiration|template|templates|blocks|examples|gallery|page flow|mobbin|pageflows|готов(ые|ую)|референс|рефы|пример|примеры|каталог|шаблон|страниц/i, primary: 'EXPLORATOR', handoffs: [
    { name: 'AEDILIS', trigger: 'selected references must become layout, flow, or component-system decisions' },
    { name: 'PICTOR', trigger: 'the task moves from reference brief to frontend implementation' },
    { name: 'GUARDIAN', trigger: 'external code, license, paid template, wallet, payment, or iGaming risk appears' },
    { name: 'NOMENCLATOR', trigger: 'reference copy must become product-specific UI text' },
    { name: 'TESTER', trigger: 'a runnable UI needs browser, responsive, or screenshot proof' }
  ] },
  { re: /seo|schema|core web vital|cwv|indexability|metadata/i, primary: 'INDAGATOR', handoffs: [
    { name: 'PICTOR', trigger: 'SEO recommendations require frontend implementation' },
    { name: 'NOMENCLATOR', trigger: 'headings, descriptions, FAQ, or page copy must be rewritten' },
    { name: 'TESTER', trigger: 'metadata, schema, or Core Web Vitals proof is needed' }
  ] },
  { re: /copy|content|ux writing|microcopy|naming|name|cta|button|tooltip|hint|description|headline|offer|value prop|pricing|empty state|error state|success state|onboarding|section title|label|placeholder|selling|sales copy|продающ|текст|назван|кнопк|подсказ|описан|раздел/i, primary: 'NOMENCLATOR', handoffs: [
    { name: 'MERCATOR', trigger: 'positioning, audience, funnel, offer, or conversion hypothesis is unresolved' },
    { name: 'AEDILIS', trigger: 'copy placement, hierarchy, accessibility, or component fit constrains wording' },
    { name: 'GLOSSATOR', trigger: 'localization, placeholders, pluralization, or text expansion risk appears' },
    { name: 'CENSOR', trigger: 'claims, urgency, scarcity, legal, finance, health, betting, or iGaming wording needs challenge' },
    { name: 'PICTOR', trigger: 'approved copy must be wired into UI components or validated for responsive fit' }
  ] },
  { re: /\blanding\b|\blp\b|\bhero\b|animation|motion|framer|gsap|frontend|\bui\b|\breact\b|\bcss\b|layout|responsive|accessib/i, primary: 'PICTOR', handoffs: [
    { name: 'AEDILIS', trigger: 'screen structure, component system, accessibility, or visual hierarchy is not settled' },
    { name: 'NOMENCLATOR', trigger: 'labels, CTA, state text, or page copy must be authored' },
    { name: 'INDAGATOR', trigger: 'public page SEO, schema, metadata, or Core Web Vitals matter' },
    { name: 'MERCATOR', trigger: 'landing offer, funnel, or conversion hypothesis is missing' },
    { name: 'TESTER', trigger: 'browser, responsive, interaction, or screenshot proof is required' }
  ] },
  { re: /casino|igaming|gambling|betting|slot|jackpot|bonus|odds|rtp|responsible.gaming/i, primary: 'ALEATOR', handoffs: [
    { name: 'PICTOR', trigger: 'approved iGaming mechanics or guardrails need UI implementation' },
    { name: 'GUARDIAN', trigger: 'wallet, payment, deposit, withdrawal, KYC, affiliate, or abuse risk appears' },
    { name: 'NOMENCLATOR', trigger: 'odds, bonus, limits, terms, or risk copy must be written' },
    { name: 'CENSOR', trigger: 'dark-pattern or misleading-claim risk needs adversarial challenge' }
  ] },
  { re: /import skill|install skill|skill migrat|skill creator|catalog/i, primary: 'GUARDIAN', handoffs: [
    { name: 'ARMARIUS', trigger: 'a missing capability requires external skill discovery' },
    { name: 'ARTIFEX', trigger: 'an accepted source must be migrated into a local skill, workflow, or rule' },
    { name: 'CENSOR', trigger: 'the safety decision or assumptions need adversarial verification' },
    { name: 'OPTIO', trigger: 'the import changes Legion routing or task ownership' }
  ] },
  { re: /security|secret|token|auth|mcp|permission|vulnerab|audit/i, primary: 'GUARDIAN', handoffs: [
    { name: 'CENSOR', trigger: 'security claims or risk acceptance need adversarial verification' },
    { name: 'REVIEWER', trigger: 'a code diff needs regression-oriented review after security fixes' }
  ] },
  { re: /test|coverage|regression|smoke|proof|verify/i, primary: 'TESTER', handoffs: [
    { name: 'CODER', trigger: 'a failing proof requires implementation changes' },
    { name: 'REVIEWER', trigger: 'test results expose regression risk in changed code' }
  ] },
  { re: /architecture|module|boundary|adr|system/i, primary: 'ARCHITECTUS', handoffs: [
    { name: 'OPTIO', trigger: 'the architecture decision must become a routed task plan' },
    { name: 'PRAEMONITOR', trigger: 'the plan needs premortem tripwires before commitment' }
  ] },
  { re: /\bdocs?\b|\bdocumentation\b|\breadme\b|\bapi context\b|\bmanual\b|\bguide\b|докум|ридми/i, primary: 'SCRIBA', handoffs: [
    { name: 'CODER', trigger: 'documentation reveals code or contract changes are required' },
    { name: 'REVIEWER', trigger: 'docs must be checked against a risky implementation diff' }
  ] },
  { re: /deploy|docker|postgres|database|runtime|service|ci|cd/i, primary: 'PONTIFEX', handoffs: [
    { name: 'GUARDIAN', trigger: 'secrets, permissions, public exposure, or dependency risk appears' },
    { name: 'TESTER', trigger: 'release, migration, health, or rollback proof must be designed' }
  ] },
  { re: /recon|port scan|nmap|http headers|attack surface|fingerprint|exposed file|разведк|скан.*порт|заголовк.*http|поверхност.*атак/i, primary: 'VELITES', handoffs: [
    { name: 'GUARDIAN', trigger: 'recon findings need security risk triage' },
    { name: 'SICARIUS', trigger: 'a finding needs controlled exploit verification' }
  ] },
  { re: /sast|static analysis|sql injection|xss|rce|dangerous pattern|secret sink|уязвим.*код|статическ.*анализ|инъекц|секрет.*код/i, primary: 'HARUSPEX', handoffs: [
    { name: 'SICARIUS', trigger: 'a vulnerability candidate needs exploit verification' },
    { name: 'GUARDIAN', trigger: 'findings need remediation priority or policy decision' }
  ] },
  { re: /exploit|poc|prove vulnerability|browser automation.*vulnerability|verify exploit|эксплойт|провер.*уязвим|доказ.*уязвим|poc/i, primary: 'SICARIUS', handoffs: [
    { name: 'HARUSPEX', trigger: 'PoC needs static source tracing first' },
    { name: 'GUARDIAN', trigger: 'exploit proof needs risk handling and remediation gate' }
  ] },
  { re: /delegate.*opus|external model|evocate|tmux.*model|ask.*model|внешн.*модель|делегир.*модел|opus.*делег/i, primary: 'EVOCATUS', handoffs: [
    { name: 'OPTIO', trigger: 'delegation scope needs routing or acceptance criteria' },
    { name: 'CENSOR', trigger: 'external-model output needs adversarial verification' }
  ] },
  { re: /report|table|chart|html report|publish|dashboard report|tiny notepad|таблиц|отчет|график|html.?отчет|публикац/i, primary: 'TABULARIUS', handoffs: [
    { name: 'SCRIBA', trigger: 'published report must become project documentation' },
    { name: 'INDAGATOR', trigger: 'public report needs search visibility or schema' }
  ] },
  { re: /review|diff|pr|regression|code review|bug-risk/i, primary: 'REVIEWER', handoffs: [
    { name: 'TESTER', trigger: 'a finding requires focused regression proof' },
    { name: 'CENSOR', trigger: 'the review conclusion or risk acceptance needs adversarial challenge' }
  ] }
];

function routeTask(task) {
  const match = keywordRoutes.find((route) => route.re.test(task));
  if (match) return match;
  return { primary: 'CODER', handoffs: [
    { name: 'TESTER', trigger: 'the change needs focused proof or a regression test' },
    { name: 'REVIEWER', trigger: 'the diff is risky enough to need independent review' }
  ] };
}

function legionaryByName(name) {
  return LEGIONARIES.find((legionary) => legionary.name === name);
}

function listMarkdownFiles(directory) {
  if (!fs.existsSync(directory)) return [];
  return fs.readdirSync(directory)
    .filter((file) => file.endsWith('.md'))
    .sort();
}

function summarizeAgentPack() {
  return {
    root: AGENT_ROOT,
    rules: listMarkdownFiles(path.join(AGENT_ROOT, 'rules')).length,
    workflows: listMarkdownFiles(path.join(AGENT_ROOT, 'workflows')).length,
    skills: listMarkdownFiles(path.join(AGENT_ROOT, 'skills')).length
  };
}

function readSkillBrief(skill) {
  const normalized = String(skill || '').trim().toLowerCase().replace(/^\//, '');
  const file = path.join(CANONICAL_SKILL_ROOT, normalized, 'SKILL.md');
  if (!fs.existsSync(file)) {
    return `Skill '${normalized}' was not found under ${CANONICAL_SKILL_ROOT}.`;
  }
  const text = fs.readFileSync(file, 'utf8');
  const firstSections = text.split('\n').slice(0, 80).join('\n');
  return firstSections.length < text.length ? `${firstSections}\n\n[truncated: load the file for full instructions]` : firstSections;
}

function textContent(text) {
  return { content: [{ type: 'text', text }] };
}

function resolveHandoffs(handoffs = []) {
  return handoffs
    .map((handoff) => {
      const name = typeof handoff === 'string' ? handoff : handoff.name;
      const legionary = legionaryByName(name);
      if (!legionary) return null;
      return { ...legionary, trigger: typeof handoff === 'string' ? 'call only when this capability is required' : handoff.trigger };
    })
    .filter(Boolean);
}

function formatHandoffs(handoffs = []) {
  const resolved = resolveHandoffs(handoffs);
  if (!resolved.length) return '- none';
  return resolved.map((handoff) => `- ${handoff.name} / ${handoff.slug}: ${handoff.trigger}`).join('\n');
}

function intakeOwner(entry, fallback) {
  return entry.intake?.owner || fallback;
}

function intakeHandoffs(entry) {
  if (Array.isArray(entry.intake?.handoffs)) return entry.intake.handoffs;
  return [];
}

function readExternalCatalog(filter = '') {
  const file = path.join(KIT_ROOT, 'docs', 'EXTERNAL_CATALOG.md');
  if (!fs.existsSync(file)) return 'External catalog is not installed.';
  const text = fs.readFileSync(file, 'utf8');
  const needle = String(filter || '').trim().toLowerCase();
  if (!needle) return text;
  const lines = text.split('\n').filter((line) => line.toLowerCase().includes(needle) || line.startsWith('| Repository') || line.startsWith('| ---'));
  return lines.length ? lines.join('\n') : `No external catalog entries matched '${filter}'.`;
}

function readExternalCatalogData() {
  if (!fs.existsSync(CATALOG_JSON_PATH)) {
    return { error: `External catalog JSON is not installed at ${CATALOG_JSON_PATH}. Run npm run catalog:refresh.` };
  }
  return JSON.parse(fs.readFileSync(CATALOG_JSON_PATH, 'utf8'));
}

function readFrontendCatalog(filter = '') {
  const file = path.join(KIT_ROOT, 'docs', 'FRONTEND_CATALOG.md');
  if (!fs.existsSync(file)) return 'Frontend catalog is not installed.';
  const text = fs.readFileSync(file, 'utf8');
  const needle = String(filter || '').trim().toLowerCase();
  if (!needle) return text;
  const lines = text.split('\n').filter((line) => line.toLowerCase().includes(needle) || line.startsWith('| Repository') || line.startsWith('| ---'));
  return lines.length ? lines.join('\n') : `No frontend catalog entries matched '${filter}'.`;
}

function readFrontendCatalogData() {
  if (!fs.existsSync(FRONTEND_CATALOG_JSON_PATH)) {
    return { error: `Frontend catalog JSON is not installed at ${FRONTEND_CATALOG_JSON_PATH}. Run npm run frontend-catalog:refresh.` };
  }
  return JSON.parse(fs.readFileSync(FRONTEND_CATALOG_JSON_PATH, 'utf8'));
}

function readFrontendReferenceIndexData() {
  if (!fs.existsSync(FRONTEND_REFERENCE_INDEX_JSON_PATH)) {
    return { error: `Frontend reference index JSON is not installed at ${FRONTEND_REFERENCE_INDEX_JSON_PATH}. Run npm run frontend-reference:refresh.` };
  }
  return JSON.parse(fs.readFileSync(FRONTEND_REFERENCE_INDEX_JSON_PATH, 'utf8'));
}

function readContentCatalog(filter = '') {
  const file = path.join(KIT_ROOT, 'docs', 'CONTENT_COPY_CATALOG.md');
  if (!fs.existsSync(file)) return 'Content copy catalog is not installed.';
  const text = fs.readFileSync(file, 'utf8');
  const needle = String(filter || '').trim().toLowerCase();
  if (!needle) return text;
  const lines = text.split('\n').filter((line) => line.toLowerCase().includes(needle) || line.startsWith('| Repository') || line.startsWith('| ---'));
  return lines.length ? lines.join('\n') : `No content copy catalog entries matched '${filter}'.`;
}

function readContentCatalogData() {
  if (!fs.existsSync(CONTENT_CATALOG_JSON_PATH)) {
    return { error: `Content copy catalog JSON is not installed at ${CONTENT_CATALOG_JSON_PATH}. Run npm run content-catalog:refresh.` };
  }
  return JSON.parse(fs.readFileSync(CONTENT_CATALOG_JSON_PATH, 'utf8'));
}

function externalSkillIntake(args = {}) {
  const catalog = readExternalCatalogData();
  if (catalog.error) return catalog.error;

  const repository = String(args.repository || '').trim().toLowerCase();
  const decision = String(args.decision || '').trim().toLowerCase();
  let entries = catalog.entries || [];

  if (repository) {
    entries = entries.filter((entry) => entry.repository.toLowerCase() === repository);
  }
  if (decision) {
    entries = entries.filter((entry) => entry.decision.toLowerCase() === decision);
  }
  if (!entries.length) {
    return `No external catalog entries matched repository='${args.repository || ''}' decision='${args.decision || ''}'.`;
  }

  const lines = [
    `Catalog: v${catalog.version} generated ${catalog.generatedAt}`,
    `Policy: installAllowlist=${catalog.policy?.installAllowlist === true ? 'true' : 'false'}; requiredWorkflow=${catalog.policy?.requiredWorkflow || 'external-skill-audit'}`,
    ''
  ];

  for (const entry of entries) {
    lines.push(
      `Repository: ${entry.repository}`,
      `Decision: ${entry.decision}`,
      `Type: ${entry.type}`,
      `License: ${entry.license}`,
      `Useful assets: ${entry.useful}`,
      `Action: ${entry.intake?.action || 'audit before use'}`,
      `Owner: ${intakeOwner(entry, 'GUARDIAN')}`,
      'Conditional handoffs:',
      formatHandoffs(intakeHandoffs(entry)),
      `Blockers: ${(entry.intake?.blockers || ['audit exact files before use']).join('; ')}`,
      `Next workflow: ${entry.intake?.nextWorkflow || 'external-skill-audit -> skill-migrator -> smoke'}`,
      ''
    );
  }

  return lines.join('\n').trimEnd();
}

function frontendSourceIntake(args = {}) {
  const catalog = readFrontendCatalogData();
  if (catalog.error) return catalog.error;

  const repository = String(args.repository || '').trim().toLowerCase();
  const decision = String(args.decision || '').trim().toLowerCase();
  const category = String(args.category || '').trim().toLowerCase();
  let entries = catalog.entries || [];

  if (repository) {
    entries = entries.filter((entry) => entry.repository.toLowerCase() === repository);
  }
  if (decision) {
    entries = entries.filter((entry) => entry.decision.toLowerCase() === decision);
  }
  if (category) {
    entries = entries.filter((entry) => entry.category.toLowerCase() === category);
  }
  if (!entries.length) {
    return `No frontend catalog entries matched repository='${args.repository || ''}' category='${args.category || ''}' decision='${args.decision || ''}'.`;
  }

  const lines = [
    `Frontend catalog: v${catalog.version} generated ${catalog.generatedAt}`,
    `Policy: installAllowlist=${catalog.policy?.installAllowlist === true ? 'true' : 'false'}; requiredWorkflow=${catalog.policy?.requiredWorkflow || 'frontend-landing-igaming'}; safetyGate=${catalog.policy?.safetyGate || 'external-skill-audit'}`,
    ''
  ];

  for (const entry of entries) {
    lines.push(
      `Repository: ${entry.repository}`,
      `Category: ${entry.category}`,
      `Decision: ${entry.decision}`,
      `License: ${entry.license}`,
      `Useful assets: ${entry.useful}`,
      `Action: ${entry.intake?.action || 'audit before use'}`,
      `Owner: ${intakeOwner(entry, 'PICTOR')}`,
      'Conditional handoffs:',
      formatHandoffs(intakeHandoffs(entry)),
      `Blockers: ${(entry.intake?.blockers || ['audit exact files before use']).join('; ')}`,
      `Next workflow: ${entry.intake?.nextWorkflow || 'frontend-landing-igaming -> quality-gate'}`,
      ''
    );
  }

  return lines.join('\n').trimEnd();
}

const REFERENCE_QUERY_SYNONYMS = {
  saas: ['startup', 'b2b', 'software', 'product', 'subscription'],
  лендинг: ['landing', 'hero', 'marketing', 'saas'],
  посадочная: ['landing', 'hero', 'marketing'],
  кабинет: ['dashboard', 'admin', 'settings', 'sidebar-app'],
  дашборд: ['dashboard', 'admin', 'analytics', 'metrics'],
  админка: ['admin', 'dashboard', 'application-ui'],
  авторизация: ['auth', 'login', 'signup'],
  форма: ['forms', 'input', 'validation'],
  цена: ['pricing', 'plans', 'subscription'],
  тарифы: ['pricing', 'plans', 'subscription'],
  магазин: ['ecommerce', 'checkout', 'product page'],
  казино: ['igaming', 'casino', 'game', 'telegram-mini-app'],
  игра: ['game', 'igaming', 'interactive-sections'],
  мобильный: ['mobile-app', 'mobile', 'responsive'],
  анимация: ['animated', 'motion', 'interactive-sections'],
  premium: ['premium', 'polished', 'high-end'],
  minimal: ['clean', 'simple', 'neutral']
};

function normalizeSearchText(value) {
  return String(value || '').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
}

function referenceTokensFor(query) {
  const tokens = normalizeSearchText(query).split(/\s+/).filter(Boolean);
  const expanded = new Set(tokens);
  for (const token of tokens) {
    for (const synonym of REFERENCE_QUERY_SYNONYMS[token] || []) expanded.add(normalizeSearchText(synonym));
  }
  return [...expanded].filter(Boolean);
}

function referenceHaystack(source) {
  return normalizeSearchText([
    source.id,
    source.name,
    source.url,
    source.repository || '',
    source.sourceType,
    source.decision,
    (source.stacks || []).join(' '),
    (source.pageTypes || []).join(' '),
    (source.styles || []).join(' '),
    (source.patterns || []).join(' '),
    source.bestFor || '',
    source.adaptNotes || ''
  ].join(' '));
}

function scoreReferenceSources(sources, args = {}) {
  const queryTokens = referenceTokensFor(args.query || '');
  const pageTokens = referenceTokensFor(args.pageType || '');
  const stackTokens = referenceTokensFor(args.stack || '');
  const styleTokens = referenceTokensFor(args.style || '');
  const noFilters = !queryTokens.length && !pageTokens.length && !stackTokens.length && !styleTokens.length;

  return (sources || []).map((source) => {
    const haystack = referenceHaystack(source);
    const reasons = [];
    let score = noFilters ? 1 : 0;

    for (const token of queryTokens) {
      if (haystack.includes(token)) {
        score += 2;
        reasons.push(`query:${token}`);
      }
    }
    for (const token of pageTokens) {
      if ((source.pageTypes || []).some((value) => normalizeSearchText(value).includes(token)) || haystack.includes(token)) {
        score += 5;
        reasons.push(`page:${token}`);
      }
    }
    for (const token of stackTokens) {
      if ((source.stacks || []).some((value) => normalizeSearchText(value).includes(token)) || haystack.includes(token)) {
        score += 4;
        reasons.push(`stack:${token}`);
      }
    }
    for (const token of styleTokens) {
      if ((source.styles || []).some((value) => normalizeSearchText(value).includes(token)) || haystack.includes(token)) {
        score += 3;
        reasons.push(`style:${token}`);
      }
    }

    return { ...source, score, matchReasons: [...new Set(reasons)] };
  })
    .filter((source) => source.score > 0)
    .sort((left, right) => right.score - left.score || left.id.localeCompare(right.id));
}

function frontendReferenceSearch(args = {}) {
  const index = readFrontendReferenceIndexData();
  if (index.error) return index.error;

  const limit = Math.max(1, Math.min(10, Number(args.limit || 5)));
  const matches = scoreReferenceSources(index.sources, args).slice(0, limit);
  if (!matches.length) {
    return `No frontend references matched query='${args.query || ''}' pageType='${args.pageType || ''}' stack='${args.stack || ''}' style='${args.style || ''}'.`;
  }

  const lines = [
    `Frontend reference index: v${index.version} generated ${index.generatedAt}`,
    `Policy: installAllowlist=${index.policy?.installAllowlist === true ? 'true' : 'false'}; requiredWorkflow=${index.policy?.requiredWorkflow || 'frontend-reference-search'}; safetyGate=${index.policy?.safetyGate || 'frontend_source_intake'}`,
    `Search: query='${args.query || ''}' pageType='${args.pageType || ''}' stack='${args.stack || ''}' style='${args.style || ''}'`,
    ''
  ];

  for (const source of matches) {
    lines.push(
      `Reference: ${source.name} (${source.id})`,
      `URL: ${source.url}`,
      `Type: ${source.sourceType}`,
      `Decision: ${source.decision}`,
      `Score: ${source.score}`,
      `Match reasons: ${source.matchReasons.length ? source.matchReasons.join(', ') : 'default'}`,
      `Page types: ${(source.pageTypes || []).join(', ')}`,
      `Stacks: ${(source.stacks || []).join(', ')}`,
      `Best for: ${source.bestFor}`,
      `Adaptation: ${source.adaptNotes}`,
      ''
    );
  }

  lines.push(
    'Next steps:',
    '- Owner: EXPLORATOR selects 3-5 references with distinct roles: structure, component/block, visual direction, flow.',
    '- Conditional handoff to AEDILIS only after references must become layout, flow, or component-system decisions.',
    '- Conditional handoff to PICTOR only when the reference brief moves to implementation.',
    '- Use frontend_source_intake or GUARDIAN review before copying external code.',
    '- Rebuild in the target stack and design system; do not copy assets, screenshots, brand identity, or copy.'
  );

  return lines.join('\n').trimEnd();
}

function contentSourceIntake(args = {}) {
  const catalog = readContentCatalogData();
  if (catalog.error) return catalog.error;

  const repository = String(args.repository || '').trim().toLowerCase();
  const decision = String(args.decision || '').trim().toLowerCase();
  const category = String(args.category || '').trim().toLowerCase();
  let entries = catalog.entries || [];

  if (repository) {
    entries = entries.filter((entry) => entry.repository.toLowerCase() === repository);
  }
  if (decision) {
    entries = entries.filter((entry) => entry.decision.toLowerCase() === decision);
  }
  if (category) {
    entries = entries.filter((entry) => entry.category.toLowerCase() === category);
  }
  if (!entries.length) {
    return `No content copy catalog entries matched repository='${args.repository || ''}' category='${args.category || ''}' decision='${args.decision || ''}'.`;
  }

  const lines = [
    `Content copy catalog: v${catalog.version} generated ${catalog.generatedAt}`,
    `Policy: installAllowlist=${catalog.policy?.installAllowlist === true ? 'true' : 'false'}; requiredWorkflow=${catalog.policy?.requiredWorkflow || 'content-copy-system'}; safetyGate=${catalog.policy?.safetyGate || 'external-skill-audit'}`,
    ''
  ];

  for (const entry of entries) {
    lines.push(
      `Repository: ${entry.repository}`,
      `Category: ${entry.category}`,
      `Decision: ${entry.decision}`,
      `License: ${entry.license}`,
      `Useful assets: ${entry.useful}`,
      `Action: ${entry.intake?.action || 'audit before use'}`,
      `Owner: ${intakeOwner(entry, 'NOMENCLATOR')}`,
      'Conditional handoffs:',
      formatHandoffs(intakeHandoffs(entry)),
      `Blockers: ${(entry.intake?.blockers || ['audit exact files and claims before use']).join('; ')}`,
      `Next workflow: ${entry.intake?.nextWorkflow || 'content-copy-system -> quality-gate'}`,
      ''
    );
  }

  return lines.join('\n').trimEnd();
}

function qualityChecks(changeType = 'code') {
  const checks = {
    code: ['targeted test', 'typecheck/build when configured', 'git diff review'],
    docs: ['link/path check', 'command examples checked', 'install path verified'],
    frontend: ['build', 'responsive/browser smoke when available', 'no layout overlap in touched view'],
    backend: ['unit/integration test', 'live route or handler smoke', 'contract docs updated'],
    infra: ['dry-run or status command', 'rollback path', 'secret scan'],
    security: ['secret scan', 'permission review', 'dependency/install source review'],
    'agent-config': ['schema validation', 'MCP stdio smoke', 'rules/workflows inventory', 'secret scan']
  };
  return checks[String(changeType || 'code').toLowerCase()] || checks.code;
}

function agyDelegationFit(task) {
  const text = String(task || '');
  const strongFit = /frontend|ui\b|landing|animation|motion|responsive|react|css|layout|copy|microcopy|cta|tooltip|docs?|readme|reference|референс|лендинг|интерфейс|анимац|кнопк|подсказ|описан/i.test(text);
  const conditionalFit = /test|coverage|refactor|debug|bug|typescript|component|schema|migration|smoke|провер|тест|рефактор|ошибк/i.test(text);
  const blocked = /secret|private key|credential|prod(uction)? deploy|database migration|payment|wallet|withdraw|deposit|kyc|exploit|poc|destructive|rm -rf|sudo|секрет|приватн|деплой|платеж|кошелек|вывод|депозит|эксплойт/i.test(text);
  if (blocked) return { verdict: 'owner-only', reason: 'high-risk secrets, production, payment, wallet, exploit, or destructive surface requires local Legion control' };
  if (strongFit) return { verdict: 'good-fit', reason: 'bounded UI, copy, docs, reference, or frontend execution is a strong agy delegation target' };
  if (conditionalFit) return { verdict: 'conditional', reason: 'agy may help if the owner gives narrow files, exact proof commands, and review boundaries' };
  return { verdict: 'conditional', reason: 'delegate only after the owner narrows scope and defines deterministic acceptance proof' };
}

function stringList(value, fallback = []) {
  if (Array.isArray(value)) return value.map((item) => String(item).trim()).filter(Boolean);
  if (typeof value === 'string' && value.trim()) return value.split(/[\n,]+/).map((item) => item.trim()).filter(Boolean);
  return fallback;
}

function formatList(values, fallback) {
  const items = values.length ? values : fallback;
  return items.map((item) => `- ${item}`).join('\n');
}

function agyDelegationBrief(args = {}) {
  const task = String(args.task || '').trim();
  const route = routeTask(task);
  const routedOwner = legionaryByName(route.primary);
  const explicitOwner = String(args.owner || '').trim().toUpperCase();
  const owner = legionaryByName(explicitOwner) || routedOwner;
  const workspace = String(args.workspace || process.cwd());
  const orderId = validateOrderId(args.orderId);
  const resultFileArg = args.resultFile === undefined ? undefined : String(args.resultFile);
  const controlPaths = deriveControlPaths(workspace, orderId, {
    requireWorkspace: false,
    resultPath: resultFileArg
  });
  const changeType = String(args.changeType || (/frontend|ui\b|landing|animation|responsive|react|css|layout|интерфейс|лендинг/i.test(task) ? 'frontend' : 'code')).toLowerCase();
  const fit = agyDelegationFit(task);
  const checks = qualityChecks(changeType);
  const resultFile = controlPaths.resultRelative;
  const snapshotFile = controlPaths.snapshotRelative;
  const requestedAllowedPaths = stringList(args.allowedPaths, ['<exact files/directories allowed>']);
  for (const allowedPath of requestedAllowedPaths) {
    const normalized = allowedPath.replace(/\\/g, '/');
    if (normalized === CONTROL_NAMESPACE_ROOT || normalized.startsWith(`${CONTROL_NAMESPACE_ROOT}/`)) {
      if (normalized !== controlPaths.namespaceRelative && !normalized.startsWith(`${controlPaths.namespaceRelative}/`)) {
        throw new Error(`allowedPaths must keep controller files inside ${controlPaths.namespaceRelative}`);
      }
    }
    const baseName = normalized.split('/').pop();
    if (baseName === AGY_RESULT_FILE && normalized !== resultFile) throw new Error(`allowedPaths cannot place ${AGY_RESULT_FILE} outside ${controlPaths.namespaceRelative}`);
    if (baseName === AGY_SNAPSHOT_FILE && normalized !== snapshotFile) throw new Error(`allowedPaths cannot place ${AGY_SNAPSHOT_FILE} outside ${controlPaths.namespaceRelative}`);
  }
  const allowedPaths = [...new Set(requestedAllowedPaths.concat(resultFile, snapshotFile))];
  const nonGoals = stringList(args.nonGoals, ['no package/dependency changes unless explicitly allowed', 'no external network unless explicitly allowed', 'no edits outside allowed paths']);
  const proofCommands = stringList(args.proofCommands, ['<proof command 1>', '<proof command 2>']);
  const forbiddenPatterns = stringList(args.forbiddenPatterns, ['<forbidden regex/text pattern when applicable>']);

  return [
    `AUXILIUM AGY delegation brief`,
    `Task: ${task}`,
    `Legion owner remains: ${owner.name} / ${owner.slug}`,
    `Delegation verdict: ${fit.verdict}`,
    `Reason: ${fit.reason}`,
    `Workspace: ${workspace}`,
    `AGY orderId: ${orderId}`,
    `Control namespace: ${controlPaths.namespaceRelative}`,
    `Controller artifacts: ${snapshotFile}, ${resultFile}`,
    '',
    'Delegate to agy only if:',
    '- The owner can specify exact files, target behavior, non-goals, and proof commands.',
    '- The task is isolated enough that agy can work without production secrets or broad system authority.',
    '- The owner can review the resulting diff, logs, screenshots, or written artifact before reporting victory.',
    '',
    'Do not delegate to agy when:',
    '- The task touches secrets, credentials, production deploys, destructive commands, wallet/payment/KYC flows, or exploit execution.',
    '- The task requires final architectural, security, legal, or product-risk judgment.',
    '- The user asked for exact local state proof that only the primary owner can verify.',
    '',
    'AGY_ORDER v1 prompt shape:',
    '```text',
    `You are AUXILIUM AGY working for ${owner.name}.`,
    'Controller: CENTURION. Authority: obey this AGY_ORDER exactly.',
    `Task: ${task}`,
    `Workspace: ${workspace}`,
    'Allowed paths:',
    formatList(allowedPaths, ['- <exact files/directories allowed>']),
    'Non-goals / forbidden initiative:',
    formatList(nonGoals, ['- <explicit exclusions>']),
    'Forbidden content patterns:',
    formatList(forbiddenPatterns, ['- <forbidden regex/text pattern when applicable>']),
    'Proof commands:',
    formatList(proofCommands, ['- <proof command>']),
    '',
    'Controller artifact rules:',
    `- Write AGY control artifacts only under ${controlPaths.namespaceRelative}/ for this exact orderId.`,
    `- Snapshot path: ${snapshotFile}. Result path: ${resultFile}.`,
    '- Never create or read root-level AGY_RESULT.json or snapshot files.',
    '',
    'Owner snapshot command:',
    `node ${path.join(KIT_ROOT, 'scripts', 'agy-order-guard.mjs')} snapshot --workspace ${workspace} --order-id ${orderId} --out ${snapshotFile}`,
    '',
    'Hard-stop rules:',
    '- If a needed action is outside Allowed paths, stop and write status=blocked. Do not improvise.',
    '- If a Non-goal conflicts with the task, stop and write status=blocked. Do not reinterpret the order.',
    '- Do not add dependencies, network calls, scripts, broad discovery, or extra files unless explicitly listed in Allowed paths.',
    '- Read only files needed to satisfy the order and proof. Do not browse unrelated workspace files.',
    '- If proof fails, fix only within Allowed paths and rerun proof. If still failing, report blocked.',
    '',
    `Write ${resultFile} as JSON with this canonical default schema:`,
    '{',
    '  "resultVersion": "AGENT_RESULT_JSON_V1",',
    `  "orderId": "${orderId}",`,
    '  "executor": "agy",',
    '  "status": "done|blocked|failed",',
    '  "summary": "...",',
    '  "filesChanged": [{"path":"relative/path","action":"added|modified|deleted|renamed|none"}],',
    '  "artifacts": [{"path":"relative/path","exists":true,"type":"...","note":"..."}],',
    '  "proof": [{"command":"...","cwd":"...","status":"pass|fail|not_run","exitCode":0,"summary":"..."}],',
    '  "selfReview": {"performed":true,"findings":[],"fixesApplied":[]},',
    '  "scopeDeviations": [],',
    '  "forbiddenPatternHits": [],',
    '  "remainingRisks": [],',
    '  "questions": [],',
    '  "errors": [],',
    '  "stdoutSummary": "",',
    '  "stderrSummary": ""',
    '}',
    '',
    'Legacy compatibility only (--allow-legacy; not the default):',
    `- To accept the previous AGY_ORDER_V1 result shape, pass --allow-legacy to agy-order-guard verify for this exact namespaced ${resultFile}.`,
    '- Do not emit legacy fields or hybrid payloads in the default result.',
    '{ "orderVersion": "AGY_ORDER_V1", "owner": "<OWNER>", "status": "done|blocked", "filesChanged": ["relative/path"], "proof": [{"command":"...","result":"passed|failed|not_run","summary":"..."}], "selfReviewFixed": "yes|no", "scopeViolations": [], "forbiddenPatternHits": [], "remainingRisks": [] }',
    '',
    'Final stdout must contain only:',
    `AGY_RESULT_FILE=${resultFile}`,
    'STATUS=<done|blocked|failed>',
    'SELF_REVIEW_PERFORMED=<true|false>',
    '```',
    '',
    'Acceptance by CENTURION/owner:',
    `- Validate ${resultFile} as AGENT_RESULT_JSON_V1 by default; prefer it over stdout because CLI models may add narration.`,
    '- Confirm agy output includes files/artifacts changed, proof commands, self-review findings, fixes applied, scope violations, forbidden-pattern hits, and residual risk.',
    '- Inspect the diff or artifact directly; do not accept prose claims alone.',
    `- Suggested scope guard: node ${path.join(KIT_ROOT, 'scripts', 'agy-order-guard.mjs')} verify --workspace ${workspace} --order-id ${orderId} --before ${snapshotFile} --allowed ${allowedPaths.join(',')} --result ${resultFile}`,
    ...checks.map((check) => `- Run owner proof: ${check}`),
    '- Call TESTER for failing/fragile proof, REVIEWER for risky diffs, GUARDIAN for security or external-source risk, and CENSOR for claim-sensitive decisions.',
    '- Final report must state: owner, whether AUXILIUM AGY was used, agy proof, owner proof, and residual risk.'
  ].join('\n');
}

function handleToolCall(name, args = {}) {
  if (name === 'mission_prep') {
    const task = String(args.task || '').trim();
    const route = routeTask(task);
    const primary = legionaryByName(route.primary);
    const pack = summarizeAgentPack();
    return textContent([
      `Mission: ${task}`,
      `Workspace: ${args.workspace || process.cwd()}`,
      `Owner: ${primary.name} / ${primary.slug} (${primary.use})`,
      'Conditional handoffs:',
      formatHandoffs(route.handoffs),
      `Antigravity pack: ${pack.rules} rules, ${pack.workflows} workflows, ${pack.skills} skill briefs at ${pack.root}`,
      '',
      'Plan:',
      '1. Recon: read local instructions, git state, and relevant files.',
      '2. Action: owner executes the narrowest change that satisfies the task.',
      '3. Probatio: run the smallest meaningful proof command.',
      '4. Report: state files changed, proof, and residual risk.'
    ].join('\n'));
  }

  if (name === 'select_legionary') {
    const task = String(args.task || '').trim();
    const route = routeTask(task);
    const owner = legionaryByName(route.primary);
    const handoffs = resolveHandoffs(route.handoffs);
    return textContent(JSON.stringify({ task, owner, handoffs }, null, 2));
  }

  if (name === 'load_skill_brief') {
    return textContent(readSkillBrief(args.skill));
  }

  if (name === 'war_room') {
    const topic = String(args.topic || '').trim();
    const horizon = args.horizon || '6 months';
    return textContent([
      `Target: ${topic}`,
      `Horizon: ${horizon}`,
      '',
      'PROSECUTOR:',
      '- Attack the plan for unsupported assumptions, hidden coupling, missing proof, unsafe permissions, and maintenance drag.',
      '',
      'ADVOCATE:',
      '- Defend the smallest reversible implementation that uses Antigravity rules/workflows/MCP before any IDE patching.',
      '',
      'JUDGE:',
      '- Approve only a slice with clear install, smoke validation, rollback, and no hardcoded secrets.',
      '',
      'Required proof:',
      '- Validate rule/workflow files exist.',
      '- Validate MCP JSON config shape.',
      '- Start the MCP server or run a stdio initialize smoke.',
      '- Confirm no broad destructive command is exposed.'
    ].join('\n'));
  }

  if (name === 'quality_gate') {
    return textContent(qualityChecks(args.changeType).map((check) => `- ${check}`).join('\n'));
  }

  if (name === 'agy_delegation_brief') {
    return textContent(agyDelegationBrief(args));
  }

  if (name === 'external_skill_sources') {
    return textContent(readExternalCatalog(args.filter));
  }

  if (name === 'external_skill_intake') {
    return textContent(externalSkillIntake(args));
  }

  if (name === 'frontend_sources') {
    return textContent(readFrontendCatalog(args.filter));
  }

  if (name === 'frontend_source_intake') {
    return textContent(frontendSourceIntake(args));
  }

  if (name === 'frontend_reference_search') {
    return textContent(frontendReferenceSearch(args));
  }

  if (name === 'content_sources') {
    return textContent(readContentCatalog(args.filter));
  }

  if (name === 'content_source_intake') {
    return textContent(contentSourceIntake(args));
  }

  return textContent(`Unknown tool: ${name}`);
}

function send(message) {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}

function handleRequest(message) {
  const { id, method, params } = message;
  if (method === 'initialize') {
    send({
      jsonrpc: '2.0',
      id,
      result: {
        protocolVersion: params?.protocolVersion || '2024-11-05',
        capabilities: { tools: {} },
        serverInfo: { name: 'centurion-legion', version: '0.2.1' }
      }
    });
    return;
  }

  if (method === 'tools/list') {
    send({ jsonrpc: '2.0', id, result: { tools: TOOLS } });
    return;
  }

  if (method === 'tools/call') {
    const result = handleToolCall(params?.name, params?.arguments || {});
    send({ jsonrpc: '2.0', id, result });
    return;
  }

  if (method === 'ping') {
    send({ jsonrpc: '2.0', id, result: {} });
    return;
  }

  if (id !== undefined) {
    send({ jsonrpc: '2.0', id, error: { code: -32601, message: `Method not found: ${method}` } });
  }
}

let buffer = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  buffer += chunk;
  while (buffer.includes('\n')) {
    const newlineIndex = buffer.indexOf('\n');
    const line = buffer.slice(0, newlineIndex).trim();
    buffer = buffer.slice(newlineIndex + 1);
    if (!line) continue;
    try {
      handleRequest(parseStrictJson(line, 'JSON-RPC request'));
    } catch (error) {
      send({ jsonrpc: '2.0', error: { code: -32700, message: error.message } });
    }
  }
});
