# censor optional domain recipes

Select only the technique needed for the approved question. Examples and section
numbers are reference material, never an instruction to perform all phases or
expand scope. Core authority, current project facts and mission budget govern.

#### A. Mathematical Attack
```yaml
checks:
  - Re-derive all calculations from raw data
  - Check unit consistency (SOL vs lamports, seconds vs ms)
  - Verify boundary conditions (what if min? max? zero? negative?)
  - Check for off-by-one errors
  - Verify percentage calculations sum correctly
  - Check for integer overflow / precision loss
```

#### B. Logical Attack
```yaml
checks:
  - Does conclusion follow from premises? (formal logic)
  - Are there unstated assumptions? (hidden premises)
  - Is this correlation mistaken for causation?
  - Does the argument work in reverse? (contrapositive test)
  - Are there alternative explanations the author ignored?
  - Is there survivorship bias in the data?
```

#### C. Empirical Attack
```yaml
checks:
  - Can the claim be verified against actual data? (DB query, logs, API)
  - Has the author measured or merely estimated?
  - Is the sample size sufficient?
  - Is the time window representative?
  - Are there edge cases not covered by the data?
```

#### D. Adversarial Scenario Attack
```yaml
checks:
  - What if the opponent adapts? (game theory)
  - What if load is 10x expected?
  - What if a dependency fails?
  - What is the blast radius of a false positive?
  - What is the blast radius of a false negative?
  - What if timing assumptions are wrong by 2x?
```

#### E. Architecture Attack
```yaml
checks:
  - Does this introduce coupling that limits future changes?
  - Are there race conditions in concurrent execution?
  - Memory/resource leaks under sustained load?
  - Does this respect existing rate limits and quotas?
  - Is error handling complete (not just happy path)?
```


### Data Verification
```bash
# Always verify numbers against the actual source
# Example: "15K addresses in DB" → run the query yourself
psql -c "SELECT COUNT(*) FROM bot_network.addresses"

# Example: "42 TX/sec" → measure yourself
# Don't trust the plan's numbers — re-derive them
```

### Cross-Reference Check
```
For every "X is Y" claim:
1. Find where X is defined in the codebase
2. Verify Y matches the actual implementation
3. Check if there are other places where X is used differently
```

### Edge Case Generation
```
For every threshold/boundary:
- What happens at exactly the boundary value?
- What happens at boundary ± 1?
- What happens with 0 input?
- What happens with negative input?
- What happens with MAX_INT input?
```

### Contradiction Detection
```
Scan the document for:
- Claim A says X, but claim B implies NOT X
- Section 1 assumes Y, but Section 3 requires NOT Y
- Constants defined with value V, but logic requires V' ≠ V
```

---
