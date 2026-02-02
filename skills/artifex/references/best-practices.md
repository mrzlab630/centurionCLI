# Skill Building Best Practices

Derived from "The Complete Guide to Building Skills for Claude".

## 1. Core Principles
*   **Progressive Disclosure:** Keep `SKILL.md` concise (<500 lines). Move details to `references/`.
*   **Conciseness:** Do not explain things Claude already knows. Focus on *domain-specific* procedures.
*   **Composability:** Your skill should work alongside others.

## 2. File Structure
```
skill-name/
├── SKILL.md              # Required. High-level workflow.
├── scripts/              # Optional. Executable code (deterministic).
├── references/           # Optional. detailed docs, schemas.
└── assets/               # Optional. Templates, files for output.
```
**Critical:** Do NOT include `README.md` inside the skill folder.

## 3. Metadata (YAML Frontmatter)
*   **name:** `kebab-case` only. No spaces, no capitals.
*   **description:** Must contain **WHAT** it does + **WHEN** to use it (triggers).
    *   *Bad:* "Helps with projects."
    *   *Good:* "Manages Linear project workflows. Use when user mentions 'sprint', 'Linear tasks', or asks to 'create tickets'."
*   **Forbidden:** XML tags (`<`, `>`) in frontmatter.

## 4. Writing Instructions (SKILL.md)
*   Use imperative/infinitive form.
*   Use **Sequential Workflow** pattern for multi-step tasks:
    ```markdown
    -# Workflow: Task Name
    --# Step 1: Action
    --# Step 2: Action
    ```
*   Define **Success Criteria**: What does a good result look like?

## 5. Testing Checklist
*   [ ] Triggers on relevant queries?
*   [ ] Does NOT trigger on unrelated queries?
*   [ ] All API calls succeed?
*   [ ] Output matches style/format requirements?
