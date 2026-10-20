# Optional domain recipes

Examples apply only within the current order and core authority.

## Commit Message Format

### Standard Format (Conventional Commits)
```
<type>(<scope>): <subject>

<body>

<footer>

Co-Authored-By: Codex <noreply@anthropic.com>
```

### Extended Format (with Release Notes)
```
package: imperative title without period

Detailed explanation of what changed, why it changed, and
how it impacts users. Explain the problem that existed
before and how this commit solves it.

Include context about alternate approaches considered and
any side effects or consequences.

Resolves: #123
Epic: PROJ-357
See also: #456, #789

Release note (category): Description of user-facing change
in past or present tense explaining what changed.
```

### Commit Types

| Type | When to Use | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(auth): add JWT refresh` |
| `fix` | Bug fix | `fix(api): handle null response` |
| `docs` | Documentation | `docs: update API guide` |
| `style` | Formatting | `style: fix indentation` |
| `refactor` | Code restructure | `refactor(user): extract validation` |
| `perf` | Performance | `perf(db): add query index` |
| `test` | Tests | `test: add auth unit tests` |
| `chore` | Maintenance | `chore: update dependencies` |
| `ci` | CI/CD | `ci: add deploy workflow` |
| `revert` | Revert commit | `revert: feat(auth)...` |

### Release Note Categories

| Category | When to Use |
|----------|-------------|
| `bug fix` | Problem fixes |
| `performance improvement` | Speed/resource optimization |
| `security update` | Security changes |
| `backward-incompatible change` | Breaking changes |
| `sql change` | Database/SQL changes |
| `ui change` | Interface changes |
| `cli change` | Command-line changes |
| `ops change` | Operations/DevOps changes |
| `general change` | Other changes |
| `None` | Internal changes only |

### Issue References

```bash
Resolves: #123       # Auto-closes issue on merge
Fixes: #456          # Alternative to Resolves
See also: #789       # Cross-reference
Epic: PROJ-357       # Link to epic/project
Part of: #101        # Partial implementation
```

---
