export const EXPECTED_SKILLS = Object.freeze([
  'aedilis',
  'aleator',
  'architect',
  'artifex',
  'augur',
  'capabilities',
  'censor',
  'coder',
  'context-optimizer',
  'documenter',
  'error-handler',
  'evocate-ad-opus',
  'git-master',
  'glossator',
  'haruspex',
  'indagator',
  'ludifex',
  'mercator',
  'nomenclator',
  'orator',
  'orchestrator',
  'pictor',
  'planner',
  'pontifex',
  'praeco',
  'praemonitor',
  'prompt-engineer',
  'quaestor',
  'refactorer',
  'researcher',
  'reviewer',
  'security',
  'sicarius',
  'skill-quartermaster',
  'tabularius',
  'tester',
  'velites'
]);

export const EXPECTED_SKILL_COUNT = EXPECTED_SKILLS.length;
export const SHARED_CAPABILITIES = Object.freeze(['open-design-producer']);

const IGNORED_GENERATED_DIRS = new Set([
  '.git',
  '.next',
  '.venv',
  'build',
  'coverage',
  'dist',
  'node_modules',
  'reports',
  'vendor'
]);

export function isIgnoredGeneratedDir(name) {
  return IGNORED_GENERATED_DIRS.has(name);
}
