# Context Optimizer — Advanced Reference

## Token Compression Techniques

### 1. LLMLingua-Style Compression

```yaml
principle: "Remove low-information tokens while preserving semantics"

techniques:
  perplexity_filtering:
    description: "Remove tokens with low perplexity (predictable)"
    example:
      before: "I would like to kindly request that you please help me"
      after: "Help me"
      reduction: "80%"

  semantic_preservation:
    keep:
      - Nouns (entities)
      - Verbs (actions)
      - Key modifiers
    remove:
      - Filler words
      - Redundant articles
      - Excessive politeness

  context_chunking:
    description: "Split context into chunks, score relevance"
    process:
      1: "Divide into semantic chunks"
      2: "Score each chunk for task relevance"
      3: "Keep top-k relevant chunks"
      4: "Discard or summarize rest"
```

### 2. Hierarchical Summarization

```yaml
levels:
  level_0_raw:
    description: "Original full content"
    use: "Never in context directly"

  level_1_detailed:
    description: "Key points with examples"
    compression: "50%"
    use: "When deep understanding needed"

  level_2_summary:
    description: "Main concepts only"
    compression: "80%"
    use: "Default for background context"

  level_3_reference:
    description: "Just title/location"
    compression: "95%"
    use: "For dormant context"

implementation:
  on_load: "Start at level_2"
  on_request: "Expand to level_1"
  after_use: "Collapse to level_3"
  on_clear: "Remove entirely"
```

### 3. Selective Context Loading

```yaml
analysis_phase:
  extract_from_prompt:
    - Keywords (nouns, technical terms)
    - Intent (action verbs)
    - Domain (skill area)
    - Scope (file, module, project)

  match_to_context:
    exact_match: "Load full context"
    partial_match: "Load summary only"
    no_match: "Skip loading"

loading_strategies:
  eager:
    when: "Explicitly requested"
    what: "Full content"

  lazy:
    when: "Might be needed"
    what: "Summary + load trigger"

  deferred:
    when: "Rarely needed"
    what: "Reference only, load on demand"
```

---

## Skill Structure Optimization

### Ideal Skill Architecture

```
skill-name/
├── SKILL.md           # Core instructions (max 500 lines)
├── REFERENCE.md       # Extended patterns (on-demand)
├── MEMORY.md          # Learned patterns (auto-updated)
├── references/
│   ├── api.md         # API documentation
│   ├── patterns.md    # Pattern library
│   ├── examples.md    # Extended examples
│   └── troubleshooting.md
└── scripts/
    ├── validate.sh    # Validation automation
    ├── generate.py    # Code generation
    └── analyze.js     # Analysis tools
```

### SKILL.md Template (Optimized)

```markdown
---
name: skill-name
description: One-line description for activation matching
allowed-tools: [minimal set]
model: haiku  # Use smallest sufficient model
---

# SKILL-NAME — Brief Title

## Identity (5 lines max)
Core purpose and victory condition.

## Quick Reference (table format)
| Trigger | Action | Output |
|---------|--------|--------|
| ... | ... | ... |

## Core Workflow (20 lines max)
Essential steps only. Details in REFERENCE.md.

## Output Format (10 lines max)
Expected output structure.

---
See REFERENCE.md for: [list of detailed topics]
```

### Reference Loading Markers

```markdown
<!-- LOAD:ON_DEMAND -->
## Detailed Section
This section loads only when explicitly needed.
<!-- /LOAD:ON_DEMAND -->

<!-- LOAD:NEVER (for search only) -->
## Searchable Archive
Contains historical patterns for Grep, never loads into context.
<!-- /LOAD:NEVER -->

<!-- LOAD:CONDITIONAL skill:security -->
## Security Patterns
Loads only when security skill is also active.
<!-- /LOAD:CONDITIONAL -->
```

---

## Context Window Management

### Capacity Planning

```yaml
typical_session:
  system_prompt: "~5%"
  claude_md: "~5%"
  active_skills: "~10%"
  conversation: "~40%"
  tool_outputs: "~30%"
  reserve: "~10%"

optimization_targets:
  skills: "Reduce to 5% via progressive disclosure"
  tool_outputs: "Summarize, reduce to 15%"
  conversation: "Compact old turns, keep at 30%"
  result: "50% more capacity for actual work"
```

### Compaction Strategies

```yaml
conversation_compaction:
  keep:
    - Last 3 turns (full)
    - Key decisions (summarized)
    - Error resolutions (brief)
  remove:
    - Exploration outputs
    - Superseded plans
    - Successful tool outputs (keep result only)

tool_output_compaction:
  file_reads:
    before: "Full file content (500 lines)"
    after: "Summary: config file with 12 settings, see path/to/file"

  grep_results:
    before: "All 50 matches with context"
    after: "Found 50 matches in 8 files. Key: file.ts:42, file.ts:89"

  command_outputs:
    before: "Full npm install log (200 lines)"
    after: "npm install: success, 0 vulnerabilities"
```

### Auto-Compaction Triggers

```yaml
time_based:
  - Every 10 turns: Light compaction
  - Every 25 turns: Medium compaction
  - Every 50 turns: Full compaction

usage_based:
  - At 40%: Enable compression mode
  - At 60%: Auto-compact conversation
  - At 80%: Critical compaction + warning

content_based:
  - After major task completion
  - After topic/skill switch
  - After error resolution
```

---

## Progress Preservation

### Dump Protocol

```yaml
when_to_dump:
  - Before /clear
  - Before /compact (if major work pending)
  - At 70% context usage
  - End of work session
  - Before switching projects

dump_location: ".claude/progress/"
filename_pattern: "progress-{date}-{task-slug}.md"

dump_contents:
  required:
    - Completed tasks
    - Current state
    - Next steps
    - Modified files
  optional:
    - Key decisions made
    - Problems encountered
    - Context restoration commands
```

### Restoration Protocol

```yaml
after_clear:
  1: "Read CLAUDE.md"
  2: "Read latest progress dump"
  3: "Read only files mentioned in 'next steps'"
  4: "Continue from documented state"

minimal_restoration:
  - CLAUDE.md
  - Current file being edited
  - Relevant test file

full_restoration:
  - Everything in minimal
  - All files in progress dump
  - Related skill references
```

---

## Skill-Specific Optimization

### High-Token Skills

```yaml
coder:
  problem: "Loads full code examples"
  solution:
    - Extract examples to references/examples.md
    - Use pattern names, not full code
    - Reference file:line instead of inline

reviewer:
  problem: "Verbose checklist in context"
  solution:
    - Single checklist in SKILL.md
    - Detailed items in REFERENCE.md
    - Load phase-specific sections only

tester:
  problem: "Test templates consume tokens"
  solution:
    - Templates in scripts/templates/
    - Generate on demand
    - Don't include in base context
```

### Low-Token Skill Patterns

```yaml
identity: "2-3 lines max"
  example: |
    Expert X. Victory: Y. Death: Z.

workflow: "Numbered steps, no prose"
  example: |
    1. Analyze
    2. Plan
    3. Execute
    4. Validate

output: "YAML template only"
  example: |
    ```yaml
    result:
      status: success|failure
      summary: "..."
    ```
```

---

## Metrics & Monitoring

### Token Efficiency Metrics

```yaml
skill_efficiency:
  formula: "value_delivered / tokens_consumed"
  good: "> 0.8"
  acceptable: "0.5 - 0.8"
  poor: "< 0.5"

context_utilization:
  formula: "active_context / loaded_context"
  good: "> 0.7"
  warning: "0.4 - 0.7"
  critical: "< 0.4"

compression_ratio:
  formula: "original_size / compressed_size"
  target: "> 3x"
```

### Optimization Tracking

```yaml
before_optimization:
  - Count lines per skill
  - Measure load time
  - Note context usage at activation

after_optimization:
  - Recount lines
  - Remeasure load time
  - Compare context usage

report:
  lines_reduced: "X%"
  load_time_improved: "Xms"
  context_saved: "X%"
```

---

## Troubleshooting

### Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Context bloat | Slow responses | Run /compact |
| Lost context | Missing info after clear | Check progress dumps |
| Skill not loading | Commands not recognized | Verify trigger words |
| Over-optimization | Missing necessary context | Expand reference loading |
| Circular references | Infinite loading | Break dependency cycle |

### Debug Commands

```yaml
check_context:
  command: "/context"
  shows: "Current usage percentage"

check_loaded:
  command: "What skills are active?"
  shows: "Currently loaded skills"

force_compact:
  command: "/compact"
  does: "Immediate context compression"

emergency_clear:
  command: "/clear"
  does: "Full context reset"
  warning: "Dump progress first!"
```

---

## Integration with Other Skills

### Orchestrator Integration

```yaml
context_budget_per_phase:
  research: "20%"
  planning: "15%"
  implementation: "40%"
  testing: "15%"
  review: "10%"

handoff_protocol:
  1: "Compact current phase context"
  2: "Generate summary for next phase"
  3: "Load next phase skill"
  4: "Pass summary as input"
```

### Skill Activation Optimization

```yaml
activation_order:
  1: "Load orchestrator (small)"
  2: "Analyze request"
  3: "Load primary skill only"
  4: "Load support skills on demand"

deactivation:
  - Unload skill after 5 turns of non-use
  - Keep summary in context
  - Full reload if needed again
```
