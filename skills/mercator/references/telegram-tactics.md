# MERCATOR — Telegram Bot Engagement Tactics

> Specific tactics for Telegram bot user engagement, retention, and growth.
> Based on research from InviteMember, Hashmeta, MiloAgent, and industry best practices.

---

## User Lifecycle in Telegram Bot

```
DISCOVERY → FIRST OPEN → ONBOARDING → FIRST VALUE → HABITUAL USE → ADVOCACY
                ↓              ↓             ↓              ↓
             [BOUNCE]      [DROP-OFF]    [DORMANT]      [CHURN]
```

Each stage has different tactics. ALWAYS diagnose the stage before recommending.

---

## Stage 1: Discovery → First Open

### Acquisition Channels (Crypto Trading Bot)
| Channel | Effectiveness | Cost | Notes |
|---|---|---|---|
| **Telegram groups/channels** | HIGH | Free-Low | Organic sharing, alpha groups |
| **Twitter/X** | HIGH | Free | Crypto-native audience, thread virality |
| **Referral program** | HIGHEST | Revenue share | K-factor potential, trust-based |
| **KOL partnerships** | MEDIUM-HIGH | Paid | Pick carefully, verify audience quality |
| **Reddit** | MEDIUM | Free | r/solana, r/cryptocurrency — value-first |
| **YouTube tutorials** | MEDIUM | Free-Low | Evergreen, SEO value |
| **Paid ads (Telegram Ads)** | LOW-MEDIUM | High | Expensive, low conversion for complex products |

### Referral Program Design
```
Inviter Reward:  % of referee's trading fees (lifetime or 90 days)
Referee Reward:  Reduced fees for first X trades / bonus feature
Tracking:        Unique invite link per user (/start?ref=USER_ID)
Viral Mechanic:  "Share your P&L card" with invite link watermark
```

---

## Stage 2: Onboarding (First 5 Minutes = Make or Break)

### Welcome Sequence (5 messages max)
```
Message 1 (Instant): Welcome + ONE sentence value prop + "Let's get started" button
Message 2 (After button): Wallet setup or connect
Message 3 (After wallet): "Try your first feature" — guided action
Message 4 (After first action): Celebrate! "🎉 You just [did X]! Here's what else you can do..."
Message 5 (24h later): "Need help? Here are our most popular features" + community link
```

### Critical Rules
- **Time-to-value < 60 seconds** — user must see value FAST
- **ONE action per message** — never overwhelm with 10 features
- **Progressive disclosure** — reveal complexity gradually
- **Skip option** — let advanced users skip onboarding
- **Measure:** Onboarding completion rate, time-to-first-trade

---

## Stage 3: Activation → First Value Moment

### "Aha Moment" for Trading Bots
The moment user realizes "this is worth using":
- **Copy-trading:** First auto-trade executes successfully
- **Manual trading:** Trade completes faster than alternatives
- **Alerts:** First relevant alert arrives at the right time
- **Portfolio:** Seeing all holdings in one clean view

### Activation Tactics
1. **Pre-configured defaults** — don't force setup before value
2. **Demo mode** — show what a successful trade looks like
3. **Guided first trade** — step-by-step with safety guardrails
4. **Instant feedback** — "Trade executed in 0.3s!" (speed as feature)

---

## Stage 4: Retention → Habitual Use

### Daily Engagement Triggers
| Trigger | Type | Example |
|---|---|---|
| **Morning summary** | Scheduled | "📊 Market overnight: SOL +5%, your portfolio +$X" |
| **Wallet activity** | Event-based | "🔔 Tracked wallet bought TOKEN — view details?" |
| **P&L milestone** | Event-based | "🎉 You hit $100 total profit!" |
| **New feature** | One-time | "✨ New: Copy-trade Meteora pools — try it" |
| **Community highlight** | Weekly | "🏆 Top traders this week: ..." |

### Gamification Elements (Pick 2-3 max)
```
🏅 Trader Ranks:    Recruit → Soldier → Centurion → Imperator
                    (based on trade count or volume)
🔥 Streaks:         "7-day trading streak! Keep it going!"
🏆 Achievements:    First Trade, 100 Trades, First Referral, Diamond Hands (held 24h+)
📊 Weekly Report:   Personal stats vs community averages
```

### Retention Mechanics
1. **Sunk cost** — trade history, saved settings, tracked wallets = switching cost
2. **Personalization** — bot learns user preferences over time
3. **Community** — group chat, alpha sharing, collective intelligence
4. **Exclusive access** — beta features for active users
5. **Performance reports** — weekly/monthly P&L summaries

---

## Stage 5: Dormant User Re-engagement

### Dormancy Detection
```
Level 1 (Cooling):  3-7 days inactive → light nudge
Level 2 (Dormant):  7-14 days inactive → value-driven message
Level 3 (At-risk):  14-30 days inactive → "we miss you" + incentive
Level 4 (Churned):  30+ days inactive → win-back campaign or archive
```

### Re-engagement Message Templates

**Level 1 — Light Nudge (Day 3-7):**
```
Hey! While you were away:
• SOL moved X%
• Your tracked wallet [name] made Y trades
• New feature: [one-liner]

[Check it out →]
```

**Level 2 — Value-Driven (Day 7-14):**
```
📊 Your weekly snapshot:
• Market: [brief summary]
• Tracked wallets: [key activity]
• Opportunity: [specific trade/alert they would have caught]

Don't miss the next one → [Set alerts]
```

**Level 3 — Incentive (Day 14-30):**
```
We noticed you've been away. Here's what's changed:
✅ [New feature 1]
✅ [New feature 2]
✅ [Performance improvement]

Come back and get [incentive: reduced fees / bonus feature / exclusive access]

[Start trading →]
```

**Level 4 — Win-Back (Day 30+):**
```
Quick question: what made you stop using [bot name]?
1️⃣ Found a better tool
2️⃣ Too complicated
3️⃣ Lost money
4️⃣ Just forgot about it
5️⃣ Other

Your feedback helps us improve for everyone.
```

---

## Broadcast Best Practices

### DO:
- Segment recipients (don't blast everyone with everything)
- Time-zone aware sending (or pick universal peak: 14:00-18:00 UTC)
- Include value in EVERY message (not just "hey use our bot")
- A/B test subject/hook with 10% of audience before full send
- Track: delivered, opened (link clicks), actioned (trades made)
- Respect frequency: max 2-3 broadcasts per week

### DON'T:
- Spam daily — users will mute/block
- Send at night (user's timezone)
- Use ALL CAPS or excessive emoji 🚀🚀🚀
- Promise unrealistic returns
- Forget unsubscribe/mute option
- Send identical message to all segments

---

## Metrics to Track

### Primary (North Star)
**Daily Active Traders (DAT)** — users who executed ≥1 trade today

### Secondary
| Metric | Formula | Good Benchmark |
|---|---|---|
| Stickiness | DAU / MAU | >20% for trading bots |
| D1 Retention | Users active day after signup / total signups | >40% |
| D7 Retention | Users active 7 days after signup / total signups | >20% |
| D30 Retention | Users active 30 days after signup / total signups | >10% |
| Activation Rate | Users who completed first trade / total signups | >30% |
| Referral Rate | Users who invited ≥1 friend / total users | >5% |
| Power User Ratio | Users with ≥10 trades/week / total active users | >10% |

---

*These tactics are guidelines, not rules. Always A/B test before scaling.*
