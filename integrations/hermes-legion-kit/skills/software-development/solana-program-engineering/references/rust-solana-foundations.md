# Rust And Solana Foundations

Use this reference before designing or implementing a Solana program. Verify live crate, framework, CLI, and runtime versions against [sources.md](sources.md); examples in upstream documentation are version snapshots, not permanent pins.

## Contents

- [Rust correctness](#rust-correctness)
- [Constrained runtime engineering](#constrained-runtime-engineering)
- [Cargo and dependency discipline](#cargo-and-dependency-discipline)
- [Solana execution model](#solana-execution-model)
- [Accounts and lifecycle](#accounts-and-lifecycle)
- [Instructions and transactions](#instructions-and-transactions)
- [PDAs and seed domains](#pdas-and-seed-domains)
- [CPI and signed CPI](#cpi-and-signed-cpi)
- [Serialization and identity](#serialization-and-identity)
- [Sysvars and instruction introspection](#sysvars-and-instruction-introspection)
- [Compute and parallelism](#compute-and-parallelism)
- [Upgrades and program data](#upgrades-and-program-data)
- [Framework selection](#framework-selection)
- [SPL Token and Token-2022](#spl-token-and-token-2022)
- [Architecture and economics](#architecture-and-economics)

## Rust Correctness

### Ownership, borrowing, and lifetimes

- Make ownership boundaries match state and authority boundaries. Avoid cloning account or instruction data to silence borrow problems without measuring allocation and semantic cost.
- Keep mutable borrows narrow. Do not hold a mutable serialized view across CPI, realloc, close, or another operation that can invalidate assumptions.
- Treat `AccountInfo` and framework account lifetimes as proof obligations. A compiling lifetime relation does not prove that two account roles are distinct or that cached data remains current.
- Prefer slices and borrowed views for parsing, with explicit bounds before indexing. Avoid retaining references into buffers that may be resized or replaced.
- Use lifetimes to express real relationships, not to bypass them with broad `unsafe`, transmute, leaked allocations, or unchecked casts.

### Results and errors

- Use `Result` and propagate errors deliberately. Map expected invalid input to stable program errors; do not panic, unwrap, or expect on attacker-controlled data.
- Preserve enough error specificity for clients and tests without leaking secrets or relying on unstable internal strings.
- Distinguish parsing, authorization, account identity, arithmetic, state transition, CPI, token, oracle, and resource-limit failures.
- Test the exact failure before mutation and after any boundary where partial state assumptions could arise.

### Checked arithmetic and conversions

- Use checked add, subtract, multiply, divide, exponentiation, and conversions for balances, supply, fees, shares, timestamps, slots, basis points, and account sizes.
- Define units for every numeric field. Do not mix raw token amounts, decimal display values, prices, quote lots, basis points, slots, and Unix timestamps.
- Specify rounding direction and who benefits from it. For financial ratios, reason about multiply-before-divide, intermediate width, overflow, dust, and conservation.
- Reject division by zero, negative-to-unsigned conversion, truncation, wraparound, saturation used as a silent policy, and unbounded exponent/shift inputs.
- Test minimum, maximum, zero, one-less/one-more boundaries, decimal extremes, repeated rounding, and conservation across duplicate roles.

### Serialization and layout

- Treat wire and account layout as public interfaces. Document tags/discriminators, field order, endianness, lengths, optional fields, reserved bytes, and upgrade strategy.
- Validate data length before deserialization. Prefer exact length for fixed layouts and explicit upper bounds for variable layouts.
- Do not deserialize an account until owner and expected type identity have been validated.
- Avoid ABI-sensitive Rust layout assumptions unless the representation is explicit and audited. Never assume compiler field layout is a stable network format.
- For zero-copy or bytemuck-like approaches, prove alignment, padding, initialization, allowed bit patterns, aliasing, and version compatibility. Treat layout changes as migrations.

### Unsafe boundaries

- Default to safe Rust. Isolate every `unsafe` block or unsafe trait implementation in the smallest module possible.
- State the invariant in a nearby comment: valid length, alignment, initialization, aliasing, lifetime, ownership, and mutation assumptions.
- Add focused tests for malformed lengths, alignment edges, zeroed bytes, duplicate accounts, and lifecycle changes.
- Reject unsafe used only for convenience or micro-optimization without measured compute benefit and independent review.

## Constrained Runtime Engineering

- Solana programs execute under bounded compute, stack, heap, account-data, and transaction constraints. Measure the active runtime rather than hard-coding remembered limits.
- Keep stack frames small. Avoid large fixed arrays, deep recursion, large generic temporaries, and nested deserialization on the stack.
- Bound heap allocation and vector/string growth from instruction or account data. Preallocate only from validated limits.
- Minimize copies, formatting, logging, hashing, PDA derivation, serialization, and repeated account scans in hot paths.
- Treat logs as bounded observability, not control flow or proof. Never log secrets or attacker-sized strings.
- Avoid panic paths. A panic consumes compute and produces less controlled client behavior than a program error.
- `no_std` and dependency-free styles may reduce footprint, but they also remove conveniences and can enlarge manual-validation risk. Confirm framework and crate support before choosing them.
- Do not assume host Rust behavior, filesystem, threads, sockets, wall clock, entropy, or operating-system services exist on chain.

## Cargo And Dependency Discipline

- Read all workspace and program `Cargo.toml` files plus the lockfile before changing dependencies or features.
- Pin compatible major/minor versions according to repository policy. Verify the Solana SDK, Anchor, SPL, Pinocchio, serialization, testing, and client crate matrix live.
- Minimize default features. Confirm target compatibility for every enabled feature and separate host-only test/client features from on-chain features.
- Inspect duplicate versions, transitive dependency growth, build scripts, procedural macros, unsafe code, licenses, advisories, yanked releases, and unmaintained crates.
- Do not install or upgrade dependencies during a bounded audit unless explicitly authorized.
- Run repository-scoped format, clippy, unit, and documentation checks when authorized and available. Treat warnings, skipped targets, and feature combinations truthfully.
- Test relevant feature matrices, including `--no-default-features` or explicit on-chain/test features where the project supports them.

## Solana Execution Model

- A program is executable code invoked by an instruction. Persistent state and lamports live in accounts passed to the instruction.
- The runtime exposes only the accounts declared by the transaction. Programs must validate every account role rather than discover trusted state by name.
- Transactions are atomic at the runtime level, but correctness still depends on validation order, CPI effects, and invariant restoration.
- Instructions contain a program ID, ordered account metadata, and opaque data. Account order and duplication are attacker-controlled unless constrained.
- The scheduler can execute non-conflicting transactions in parallel. Writable account overlap serializes work and can create a throughput bottleneck.
- Programs are stateless between calls except for account state. Never rely on process memory, previous invocation locals, or log history.

## Accounts And Lifecycle

For every account, verify and test:

- public key or derivation when identity matters;
- expected owner before reading or writing typed data;
- signer status for the exact authority role;
- writable status before mutation or lamport movement;
- executable status and program ID for program accounts;
- relationship to other accounts, such as stored authority, mint, vault, market, pool, position, or parent state;
- expected data length, discriminator/tag, version, and initialized/uninitialized state;
- lamport sufficiency, rent-exemption requirements where applicable, and lawful lamport debit/credit behavior;
- uniqueness when two mutable roles must not alias;
- close destination, post-close state, discriminator clearing, and revival resistance;
- realloc payer, size bounds, rent delta, zeroing policy, stale-byte exposure, and serialization compatibility;
- reinitialization rules, including whether an account that once held state may be initialized again.

An account being a signer does not make it the correct signer. An account having the expected shape does not make it owned by the expected program.

## Instructions And Transactions

- Give each instruction a unique, stable discriminator/tag and bounded argument format.
- Validate account count and ordered roles before consuming accounts. Optional and remaining accounts require explicit schemas and maximum counts.
- Define preconditions, state transition, effects, events, and postconditions for each instruction.
- Bind deadlines to a verified clock/slot source and state whether the comparison is inclusive.
- Treat blockhash, fee payer, compute budget, address lookup tables, and transaction composition as client concerns that can still affect threat models and release proof.
- For introspection-dependent logic, bind to the correct transaction instruction and validate program ID, accounts, data, and relative position. Do not rely on a reusable absolute index alone.

## PDAs And Seed Domains

- Define a seed-domain prefix per account family. Avoid ambiguous concatenation and cross-type collisions.
- Include the minimum stable identity fields needed to bind the PDA to its parent, authority, mint, market, position, or epoch.
- Bound variable seed lengths and normalize only according to an explicit protocol rule.
- Derive with the current program ID unless a foreign-program PDA is intentionally and explicitly validated.
- Require the canonical bump unless the protocol intentionally stores and validates a different derivation scheme.
- Validate the PDA address, owner, discriminator, state relationship, and stored bump if present. Address derivation alone is insufficient.
- Use exactly the verified seeds and bump for signed CPI. Review whether PDA authority is scoped narrowly enough for the invoked action.
- Treat seed changes as address and migration changes, not refactors.

## CPI And Signed CPI

- Allowlist the invoked program ID. Validate the executable program account or use a framework type that does so.
- Map each CPI account to the intended role and validate ownership, signer/writable privileges, and relationships before invocation.
- Do not forward arbitrary remaining accounts or excessive privileges without an explicit callee schema.
- Prevent confused-deputy behavior: a valid PDA signer must not authorize a user-chosen target, mint, vault, recipient, or instruction.
- Confirm privilege propagation and whether the callee can mutate accounts later used by the caller.
- Reload or re-deserialize mutable accounts after CPI before using their balances, authorities, supply, status, or other data.
- Check CPI return data and errors where the interface requires it; do not infer success from logs.
- Include nested-CPI depth and compute consumption in resource analysis.

## Serialization And Identity

- Native programs must define and enforce instruction tags and account type tags/discriminators explicitly.
- Anchor discriminators and typed accounts help identify expected types, but custom/short discriminators, unchecked accounts, zero-copy, remaining accounts, manual serialization, and migrations require direct review.
- Prevent type cosplay by validating owner, discriminator/tag, length, version, relationship, and initialization state together.
- Reserve space or use explicit versions for compatible evolution. Reject unknown versions and malformed trailing bytes unless the protocol deliberately permits extensions.
- Keep IDL and client codecs synchronized with deployed behavior; hash and compare them for release proof.

## Sysvars And Instruction Introspection

- Prefer runtime-provided or checked sysvar access patterns supported by the current SDK/framework.
- If a sysvar account is supplied, validate its identity with current APIs before trusting its data.
- Treat Clock fields as protocol inputs with documented slot/time semantics and boundary tests.
- For instructions-sysvar parsing, validate the sysvar identity, index bounds, target instruction program ID, account metas, data discriminator, and relative ordering.
- Never let a caller substitute a lookalike account or reuse a prior instruction shape to satisfy an incomplete introspection check.

## Compute And Parallelism

- Measure compute units for representative success and worst-case failure paths. Record tool/runtime versions with measurements.
- Bound loops over instruction data, account data, remaining accounts, extension lists, and CPIs.
- Reject unbounded realloc, vector growth, sorting, hashing, or quadratic duplicate detection.
- Use efficient duplicate-account checks appropriate to the bounded maximum; always enforce semantic role separation.
- Minimize writable accounts and global hot PDAs. Partition state by user, market, mint, shard, or epoch where invariants allow parallel updates.
- Do not trade correctness for compute savings. Remove redundant work only after validation obligations remain explicit and tests cover the optimized path.
- Include compute exhaustion and account-lock contention in DoS and economic analysis.

## Upgrades And Program Data

- Identify the loader and derive/read the corresponding program-data account using current official tooling.
- Verify program executable state, deployed slot/version evidence, program-data address, and upgrade authority.
- Treat upgrade authority as a critical governance key. Document multisig/timelock/pause controls and compromise impact.
- Ensure declared program IDs, generated IDL/client IDs, local keypair public IDs, deployed IDs, and verification targets agree.
- A closed or immutable upgrade authority changes rollback options. Require an explicit governance decision and proof before any authority change.
- Preserve the previously verified artifact and a tested or explicitly untested rollback plan before upgrade.

## Framework Selection

### Native Rust

Choose native Solana Rust when the repository already uses it or requires direct parsing, custom ABI control, reduced framework surface, or measured optimization. Budget for manual checks of every account property, discriminator, relationship, PDA, CPI, serialization path, and error.

### Anchor

Use current Anchor account types and constraints to express signer, mutability, owner/address, PDA seeds/bump, `has_one`, custom constraints, initialization, realloc, close, token, mint, ATA, and program-interface rules. Then review what constraints do not express:

- cross-account economic relationships;
- state-machine transitions;
- remaining-account schemas and duplicates;
- arbitrary CPI and confused-deputy behavior;
- stale account data after CPI;
- custom serialization/discriminators and zero-copy invariants;
- Token-2022 extension semantics;
- oracle, fee, slippage, deadline, MEV, and governance assumptions.

Confirm exact macro/constraint behavior against the project's Anchor version. Do not assume a current documentation example compiles on a pinned older release.

### Pinocchio

Pinocchio is a performance-oriented, low-dependency program framework/ecosystem whose APIs and compatibility can change. Consider it only after live checks of:

- exact crate and companion-crate versions;
- supported Solana/platform-tools and Rust versions;
- entrypoint, account parsing, CPI, logging, allocation, and serialization APIs;
- repository precedent, maintenance state, audit coverage, and test-harness compatibility;
- measured compute/binary benefit versus increased manual-validation and migration cost.

Do not introduce Pinocchio into an Anchor/native task as an incidental optimization.

## SPL Token And Token-2022

For every token path, establish:

- exact token program identity: legacy SPL Token or Token-2022;
- mint account owner, mint address, decimals, supply assumptions, mint authority, freeze authority, and extension authorities;
- token account owner program, mint field, authority/owner field, amount, state, delegate, close authority, and native-token behavior when relevant;
- ATA derivation using the correct wallet, mint, and token program ID;
- source and destination relationship to protocol state and authority;
- checked transfer semantics that bind amount and decimals when supported;
- PDA signer seeds and the exact token authority being exercised;
- post-transfer balances or reloaded state when later logic depends on them.

Token-2022 requires extension-aware parsing and policy. Inventory all mint and account extensions before accepting the asset. Review transfer fees and withheld amounts, transfer hooks and extra-account resolution, permanent delegate, default account state, non-transferable behavior, interest-bearing/confidential features, CPI guard, memo requirements, metadata/group pointers, close authority, and extension-specific authorities as applicable.

For transfer hooks:

- validate the hook program identity and expected extra-account-meta state;
- treat hook CPIs and extra accounts as adversarial composition;
- include reentrancy-like sequencing, compute, failure, fee, and stale-state effects in the threat model;
- do not assume a nominal transfer amount equals the recipient's net amount.

## Architecture And Economics

### State machines

- Enumerate states and allowed transitions. Reject skipped, repeated, backward, or post-terminal transitions unless explicitly designed.
- Bind transition authority and time/oracle conditions to stored state.
- Ensure cancellation, settlement, liquidation, pause, close, and recovery paths preserve asset conservation.

### Authority model

- Separate user ownership, operator roles, protocol governance, emergency pause, fee authority, mint/freeze authority, oracle admin, and upgrade authority.
- Define delegation scope, expiry, nonce/replay policy, revocation, multisig/timelock, and key-compromise impact.
- Prefer least privilege and PDA capabilities scoped to one state domain and action.

### Account lifecycle

- Specify who pays initialization/realloc rent, who receives close lamports, maximum size, shrink/zero policy, and whether reinitialization is ever valid.
- Prevent close-and-revive, prefunded-address, stale discriminator, and partial initialization paths.

### Oracles, fees, and markets

- Allowlist oracle/feed identity and validate status, staleness, confidence, scale/exponent, aggregation, and acceptable divergence.
- Define fee base, rate units, caps, rounding, recipient, conservation, and interaction with Token-2022 transfer fees.
- Enforce minimum output or maximum input, explicit slippage units, and deadlines for price-sensitive actions.
- Model sandwiching, back-running, liquidation ordering, oracle manipulation, flash liquidity, stale quotes, transaction replay/composition, and writable-account contention where relevant.
- State which economic properties are assumptions and which are enforced on chain.
