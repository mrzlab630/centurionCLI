# Bundled Legion Contracts

This directory makes the Antigravity Legion Kit standalone. The files below are byte-copied from the accepted shared core and must not fork its API:

- `lib/contracts.mjs`
- `scripts/legion-contract.mjs`

For AGY, the default result contract is `AGENT_RESULT_JSON_V1`. Validate it directly with the bundled CLI when needed:

```bash
node legion-contracts/scripts/legion-contract.mjs validate-agent-result \
  --file .centurion/agents_results/<orderId>/AGY_RESULT.json \
  --order-id <orderId> \
  --executor agy
```

Workspace snapshot, namespace, allowed-path, reported-scope, and forbidden-pattern enforcement remains the responsibility of `scripts/agy-order-guard.mjs`.

## `--allow-legacy` Compatibility

The previous `AGY_ORDER_V1` result payload is not the default. It is accepted only through `agy-order-guard.mjs verify --allow-legacy`; default guard verification rejects legacy-only and hybrid results.
