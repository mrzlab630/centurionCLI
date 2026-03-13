# Pipeline: {name}
Started: {YYYY-MM-DD HH:MM UTC}
Status: ACTIVE
Chain: {LEG1} → {LEG2} → {LEG3} → {LEG4}

## Steps

| # | Legionary | Status | Handoff |
|---|-----------|--------|---------|
| 1 | {LEG1} | ⏳ Pending | — |
| 2 | {LEG2} | ⏳ Pending | — |
| 3 | {LEG3} | ⏳ Pending | — |
| 4 | {LEG4} | ⏳ Pending | — |

## Status Legend
- ⏳ Pending — waiting for previous step
- 🔄 Active — legionary is working
- ✅ Done — completed with handoff
- ❌ Failed — failed after 3 retries
- ⏭️ Skipped — conditionally skipped

## Notes
<!-- Pipeline-level notes, blockers, decisions -->

