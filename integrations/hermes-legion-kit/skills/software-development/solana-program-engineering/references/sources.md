# Source Ledger

Retrieved: 2026-08-16 (Europe/Moscow). URLs and repository heads were checked live in this run. Solana, Anchor, Rust, SPL, Pinocchio, Surfpool, test harnesses, and verification tooling evolve quickly; re-open the relevant primary page and inspect installed `--version`/`--help` output before relying on exact APIs or commands.

## Primary And Official Sources

| Source | Live status on 2026-08-16 | Use and currentness caveat |
|---|---|---|
| [Solana: Developing Programs in Rust](https://solana.com/docs/programs/rust) | HTTP 200 | Native Rust entrypoint/build overview. The page showed snapshot examples such as `solana-program` 2.2.0; never turn example pins into project defaults. |
| [Solana: Core Programs](https://solana.com/docs/core/programs) | HTTP 200 | Runtime/core-program model and program identities. Recheck loader and built-in details against the active cluster/toolchain. |
| [Solana: Rust Program Structure](https://solana.com/docs/programs/rust/program-structure) | HTTP 200 | Entrypoint, state/instruction/processor/error organization, manual validation, serialization, and CPI concepts. |
| [Solana: Official Rust SDKs](https://solana.com/docs/clients/official/rust) | HTTP 200 | Current client SDK direction. Client crate splits and compatibility are version-sensitive. |
| [Solana: Accounts](https://solana.com/docs/core/accounts) | HTTP 200 | Owner, lamports, data, executable and rent/account-model fundamentals. Runtime limits and rent behavior must be verified live. |
| [Solana: Transactions](https://solana.com/docs/core/transactions) | HTTP 200 | Transaction/instruction/account metadata and atomic execution model. |
| [Solana: Program Derived Addresses](https://solana.com/docs/core/pda) | HTTP 200 | PDA derivation and bump concepts. Security requirements in this skill add relationship and canonical-domain review. |
| [Solana: Cross Program Invocation](https://solana.com/docs/core/cpi) | HTTP 200 | CPI and PDA-signed invocation fundamentals. Exact SDK APIs change. |
| [Solana: Tokens](https://solana.com/docs/tokens) | HTTP 200 | Token/mint/account/ATA fundamentals and official token documentation entry point. |
| [Solana: Token Extensions](https://solana.com/docs/tokens/extensions) | HTTP 200 | Token-2022 extension overview. Extension availability and semantics must be checked against the accepted token program and crates. |
| [Solana: Deploying Programs](https://solana.com/docs/programs/deploying) | HTTP 200 | Deployment and loader workflow. All real network writes remain approval-gated. |
| [Solana: Verified Builds](https://solana.com/docs/programs/verified-builds) | HTTP 200 | Official verification workflow entry point. Confirm current `solana-verify` syntax and image/tool versions live. |
| [Anchor documentation](https://www.anchor-lang.com/docs) | HTTP 200 | Anchor concepts, CLI, testing, tokens, constraints, footguns, and release notes. Match docs to the pinned Anchor crate/CLI version. |
| [Anchor: Account Constraints](https://www.anchor-lang.com/docs/references/account-constraints) | HTTP 200 | Constraint vocabulary for signers, owners, addresses, PDAs, relationships, lifecycle, and tokens. Constraints do not replace business-invariant review. |
| [Anchor: Security Exploits](https://www.anchor-lang.com/docs/references/security-exploits) | HTTP 200 | Current official security-exploit examples route observed from Anchor navigation. Use as examples, not an exhaustive checklist. |
| [Anchor: Footguns](https://www.anchor-lang.com/docs/footguns) | HTTP 200 | Version-aware framework hazards and design cautions. |
| [Anchor: Zero Copy](https://www.anchor-lang.com/docs/features/zero-copy) | HTTP 200 | Zero-copy facilities and constraints. Pair with Rust layout/unsafe review. |
| [Anchor: Verifiable Builds](https://www.anchor-lang.com/docs/references/verifiable-builds) | HTTP 200 | `anchor build --verifiable` and `anchor verify` were documented on retrieval; verify live help before execution. |
| [Anchor: LiteSVM](https://www.anchor-lang.com/docs/testing/litesvm) | HTTP 200 | In-process testing overview for Rust/TS/Python. Supported runtime features depend on the installed release. |
| [Anchor: Mollusk](https://www.anchor-lang.com/docs/testing/mollusk) | HTTP 200 | Lightweight Rust program/instruction test guidance. Check current APIs and runtime fidelity. |
| [Anchor: Token Extensions](https://www.anchor-lang.com/docs/tokens/extensions) | HTTP 200 | Anchor interfaces for Token-2022 and extension examples. Validate exact crate/macro behavior for the project version. |
| [The Rust Programming Language](https://doc.rust-lang.org/book/) | HTTP 200 | Primary language guide for ownership, borrowing, lifetimes, errors, testing, Cargo, and safe abstractions. Edition/compiler behavior remains toolchain-specific. |
| [The Rustonomicon](https://doc.rust-lang.org/nomicon/) | HTTP 200 | Primary advanced/unsafe Rust reference. It is not a recipe to introduce unsafe code; isolate and prove every unsafe invariant. |
| [Pinocchio upstream](https://github.com/anza-xyz/pinocchio) | HTTP 200 | Upstream source for current performance-oriented framework APIs. Treat all recommendations as version-aware and project-specific. |
| [Solana Verifiable Build upstream](https://github.com/solana-foundation/solana-verifiable-build) | HTTP 200 after redirect from the historical Ellipsis Labs URL | Upstream `solana-verify` implementation and release notes. Prefer tagged/current official instructions over remembered syntax. |
| [Surfpool upstream](https://github.com/solana-foundation/surfpool) | HTTP 200 after redirect from the historical txtx URL | Upstream local-network/forking tooling. Confirm current capabilities, safety, and CLI before use. |
| [Trident upstream](https://github.com/Ackee-Blockchain/trident) | HTTP 200 | Upstream fuzz/integration framework. Confirm maintenance, compatibility, and exact invocation live. |

### Explicit source drift

The order-listed URL `https://www.anchor-lang.com/docs/references/security` returned HTTP 404 on 2026-08-16. The current Anchor navigation exposed `https://www.anchor-lang.com/docs/references/security-exploits`, plus `account-constraints`, `footguns`, and `zero-copy`; those live pages were used instead. Recheck this mapping on future runs.

## Community And Comparative Sources

Community sources informed organization and audit coverage only. They were not installed, executed, or copied wholesale, and they do not override primary documentation or repository evidence.

| Source | Observed revision/state | Adopted lessons and rejected assumptions |
|---|---|---|
| [Solana Foundation solana-dev-skill](https://github.com/solana-foundation/solana-dev-skill) | `e66e32711d0cd7c263812c8208ef3092846d562a`, default branch `main`, observed 2026-08-16 | Useful progressive disclosure, compatibility matrix, explicit program/security/testing references, and transaction guardrails. Did not copy its broad dApp/client/MCP scope, auto-install behavior, fixed default versions, or framework preferences; this skill is bounded to on-chain program engineering/audit and forbids unapproved installs/network writes. |
| [Trail of Bits Solana vulnerability scanner](https://github.com/trailofbits/skills/tree/main/plugins/building-secure-contracts/skills/solana-vulnerability-scanner) | `4db88ee79db0a68bbe049fe827e272ee2bc19510`, default branch `main`, observed 2026-08-16 | Useful platform-specific audit categories such as arbitrary CPI, PDA validation, signer/owner checks, sysvars, and instruction introspection. Expanded beyond its six-pattern scanner and rejected keyword scanning as proof of exploitability. |
| [safe-solana-builder](https://github.com/Frankcastleauditor/safe-solana-builder) | `9e94436dcf4b5dfd6d837eb70cf88b9048e72e5d`, default branch `main`, observed 2026-08-16 | Useful security-first design-before-code and negative-test emphasis across Anchor/native/Pinocchio. Did not import its prompt or rule inventory wholesale; all claims in this skill are reconciled with primary sources and a finding-evidence model. |
| [solana-ai-kit](https://github.com/solanabr/solana-ai-kit) | `d4f6143fc4b0b9b1c07c6e56db9845f897e932eb`, default branch `main`, observed 2026-08-16 | Useful evidence that modern Solana workflows span specialized architecture, implementation, QA, security, testing, and tooling. Rejected its very broad agent/plugin/MCP/install surface and version-labeled "modern stack" as a timeless baseline. |

## Source-Use Rules

1. Prefer repository-pinned manifests, lockfiles, generated IDL, deployed accounts, installed tool help, and current official docs over this ledger's remembered detail.
2. Record retrieval date, URL or revision, and whether a claim was observed, inferred, or unverified.
3. Treat community source text as leads and comparative design input. Re-derive security claims from code/runtime behavior and primary documentation.
4. Do not execute installers, fetched scripts, MCP setup, plugins, third-party skills, deploy commands, or transaction examples from any source without separate explicit authority.
5. When primary sources conflict or a page moved, record the conflict and stop the affected version-sensitive action until resolved.
