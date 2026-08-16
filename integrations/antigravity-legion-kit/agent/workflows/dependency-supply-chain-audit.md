---
description: Audit dependencies, lockfiles, install scripts, MCP/tool configs, and external skills before trusting or releasing them.
---

# Dependency Supply-Chain Audit Workflow

1. Inspect manifest and lockfile diffs.
2. Identify new packages, changed versions, install/postinstall scripts, and binary downloads.
3. Run project audit command where available.
4. Inspect MCP/agent/tool config permissions if harness files changed.
5. Block remote shell installers, obfuscated scripts, broad permissions, and secret exposure.
6. Report risk level, evidence, and safer alternative or approval conditions.
