# SOUL Runtime Model Rule

Hermes can report stale model names through persistent config/profile surfaces.
Keep this rule in `/home/mrz/.hermes/SOUL.md` under primary model fallback reliability:

```text
Runtime model evidence overrides stale profile summaries for the current session. If `config.yaml`, `hermes profile list`, or `hermes prompt-size` says one model while the active turn context/logs show an explicit runtime switch or live API calls with another model, treat it as a warning to report and audit, not as an identity conflict or automatic failure.
```

The default installer does not patch `SOUL.md`; apply this rule manually or through a separately reviewed control-plane edit.
