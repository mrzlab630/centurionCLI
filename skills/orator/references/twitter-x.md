# ORATOR — X/Twitter Platform Reference

> Source: twitter/the-algorithm (72K⭐), Sprout Social 2026, TweetArchivist, OpenTweet

## Algorithm Mechanics (2026)

### Feeds
- **For You** — algorithmic default, SimClusters-based relevance
- **Following** — reverse chronological
- **Explore** — trending with Grok AI summaries

### Ranking Signals (by weight)
| Signal | Weight vs Like (1x) | Notes |
|---|---|---|
| Repost | ~20x | Strongest signal — "I vouch for this" |
| Reply | ~13.5x | Conversation = quality content |
| Bookmark | ~10x | "Silent like" — saves without public engagement |
| Like | 1x | Baseline, weakest signal |

### Content Type Impact
- **Native video:** BOOSTED — 4/5 sessions include video
- **Threads:** 3x more engagement than single tweets
- **Images/GIFs/Polls:** Moderate boost
- **External links:** PENALIZED 50-90% — put link in FIRST REPLY

### Recency Decay
- Half-life: ~6 hours — visibility drops 50% every 6h
- First hour critical — engagement velocity determines virality

### X Premium (Critical)
- **2-4x reach boost** vs non-Premium
- Non-Premium + links = ~0% median engagement (since March 2026)
- Premium replies appear at top of threads
- **Verdict:** Virtually required for serious reach

---

## Content Formats

### Single Tweet (280 chars)
```
[Hook — provocative statement or question]
[1-2 supporting points]
[CTA or open question]
```
Best for: Quick takes, reactions, engagement bait (questions)

### Thread (3-15 tweets)
```
Tweet 1: [Hook + promise — "Here's what I learned..." / "🧵"]
Tweet 2-N: [One point per tweet, numbered or emoji-prefixed]
Last tweet: [Summary + CTA + "Follow for more" or link]
```
Best for: Deep content, tutorials, analyses, storytelling
**Rule:** Each tweet must stand alone AND flow as a chain

### Quote Tweet
Add commentary to someone else's post — shows thought leadership
**Rule:** Add value, don't just say "This 👆" — algorithm deprioritizes low-effort QTs

### Poll
4 options max, 24h-7 days duration
Drives engagement — voters come back to check results

---

## Crypto Twitter (CT) Specifics

**Full reference:** `references/crypto-social.md` — CT culture, vocabulary, KOL etiquette, compliance, FUD handling.

**X-specific crypto notes:**
- Cashtags ($SOL, $BTC) are native — use them instead of plain text
- Crypto hours = 24/7, but US/EU peak still dominates engagement
- Alpha threads are the #1 growth driver on CT

---

## Timing & Frequency

### Optimal Posting
- **Frequency:** 3-5 tweets/day + 2-3 threads/week
- **Peak engagement:** 8-10 AM EST, 12-2 PM EST, 6-8 PM EST
- **Crypto specifics:** 24/7 market, but US/EU awake hours peak
- **Consistency > Virality** — posting daily beats sporadic viral hits

### Reply Strategy
- Reply to EVERY comment in first 2 hours
- Thank reposters publicly
- Ask follow-up questions (drives reply chains → algorithm loves depth)
- Engage with larger accounts' posts (visibility through association)

---

## Anti-Patterns
- Links in main tweet body (50-90% reach penalty)
- More than 2 hashtags (looks spammy)
- ALL CAPS or excessive emoji (spam filter risk)
- Posting and disappearing (engagement velocity dies)
- Auto-DM on follow (instant mute/block)
