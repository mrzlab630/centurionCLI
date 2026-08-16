# ALEATOR — Ethical Gamification Guidelines

> Source: EU Digital Services Act, FTC Dark Pattern Guidelines, UK Gambling Commission,
> Deceptive Design (deceptivedesign.org), Ethical Design Handbook (Smashing Magazine)

## Dark Patterns Classification

### What Are Dark Patterns?
User interface designs that trick users into doing things they didn't intend. Term coined by Harry Brignull (2010).

### Dark Pattern Types (Relevant to Gamification)

| Pattern | Description | Example | Severity |
|---|---|---|---|
| **Confirm-shaming** | Guilt-tripping users who decline | "No thanks, I don't want to save money" | 🔴 HIGH |
| **Fake urgency** | False countdown timers that reset | Timer shows "2 hours left" but resets daily | 🔴 HIGH |
| **Fake scarcity** | Lying about limited availability | "Only 2 left!" when unlimited | 🔴 HIGH |
| **Forced continuity** | Hidden auto-renewals, hard to cancel | Free trial → paid, cancel buried 5 menus deep | 🔴 HIGH |
| **Roach motel** | Easy to enter, hard to leave | Simple signup, impossible account deletion | 🔴 HIGH |
| **Bait and switch** | Promising one thing, delivering another | "Free rewards!" → requires purchase | 🔴 HIGH |
| **Hidden costs** | Revealing fees only at checkout | $0.99 item → $5.99 with "processing fees" | 🔴 HIGH |
| **Nagging** | Persistent, repeated requests | "Rate us!" popup on every session | 🟡 MEDIUM |
| **Obstruction** | Making undesired action difficult | Unsubscribe requires calling a phone number | 🔴 HIGH |
| **Trick question** | Confusing UI to cause unintended action | Double negatives in opt-out checkboxes | 🔴 HIGH |
| **Sneak into basket** | Adding items without consent | Pre-checked "add insurance" at checkout | 🔴 HIGH |
| **Social proof manipulation** | Fake reviews, inflated numbers | "10,000 users online!" (actually 50) | 🔴 HIGH |

---

## Ethical Framework: The FAIR Test

Every gamification mechanic MUST pass:

### F — Freedom
**Does the user have genuine freedom to opt out?**
- Can they disable the mechanic without penalty?
- Is the opt-out as easy as the opt-in?
- Are they fully informed before opting in?

### A — Authenticity
**Is the mechanic honest?**
- Are all numbers real? (scarcity counts, timers, social proof)
- Are odds disclosed? (for any random/variable rewards)
- Is the value proposition truthful?

### I — Impact
**What is the worst-case impact on a vulnerable user?**
- Could this trigger problem gambling behavior?
- Could a minor be harmed?
- Could someone with addiction tendencies be exploited?
- Would you be comfortable if the user's therapist saw this design?

### R — Respect
**Does this treat users as autonomous adults?**
- No infantilizing, no guilt-tripping, no manipulation
- Users' time and attention are respected
- Natural stopping points are provided
- Clear information for informed decisions

---

## Regulatory Landscape (2026)

### EU Digital Services Act (DSA)
- **Effective:** February 2024+
- **Scope:** All digital services available in EU
- **Key provisions:**
  - Ban on dark patterns in user interfaces
  - Transparency requirements for algorithmic recommendations
  - Prohibition on targeting ads to minors using personal data
  - Obligation to assess systemic risks (including addictive design)
- **Enforcement:** Up to 6% of global annual turnover

### FTC (US Federal Trade Commission)
- **Staff report (2022):** "Bringing Dark Patterns to Light"
- **Key positions:**
  - Dark patterns that manipulate consumers are deceptive/unfair practices
  - Companies can face enforcement action for dark patterns
  - Special scrutiny for children-targeted products
  - Auto-renewal and subscription traps under active enforcement
- **Enforcement:** Civil penalties, consent decrees

### Loot Box Legislation
| Country | Status | Key Rule |
|---|---|---|
| **Belgium** | Banned (2018) | Paid loot boxes = illegal gambling |
| **Netherlands** | Restricted | Paid random items with real value = gambling |
| **UK** | Under review | Gambling Commission studying classification |
| **Australia** | Under review | Senate inquiry recommended regulation |
| **China** | Regulated | Must disclose odds, spending limits for minors |
| **Japan** | Self-regulated | "Kompu gacha" (complete gacha) banned by industry |
| **US** | Proposed bills | Several state-level proposals, no federal law yet |

### COPPA (Children's Online Privacy Protection Act)
- **Scope:** Products directed at children under 13 (US)
- **Requirements:**
  - Parental consent for data collection
  - No behavioral targeting
  - No gamification designed to extend screen time (under FTC scrutiny)

### GDPR (EU General Data Protection Regulation)
- Behavioral profiling for gamification purposes requires explicit consent
- Users have right to know how their behavioral data is used
- Right to deletion includes gamification progress data

---

## Responsible Design Checklist

### Before Launch
- [ ] FAIR test passed for every mechanic
- [ ] Odds disclosed for all variable reward mechanics
- [ ] Opt-out mechanism for each gamification feature
- [ ] Natural stopping points in all engagement loops
- [ ] Age verification if targeting under-18 audience
- [ ] Spending caps implemented for monetized mechanics
- [ ] Session time tracking with break suggestions
- [ ] All scarcity/urgency mechanics verified as genuine
- [ ] No confirm-shaming in any opt-out flow
- [ ] Dark pattern audit by independent reviewer

### After Launch
- [ ] Monitor for addiction patterns (excessive session times, spending spikes)
- [ ] Track opt-out rates (if high → mechanic may be annoying/manipulative)
- [ ] Watch for edge cases (users exploiting mechanics in harmful ways)
- [ ] Respond to user complaints about manipulative design
- [ ] Regular ethical audit (quarterly minimum)

---

## Ethical Alternatives to Dark Patterns

| Instead of... | Use... |
|---|---|
| Fake urgency | Real time-limited events with genuine value |
| Fake scarcity | Genuine limited editions or seasonal content |
| Nagging popups | Contextual, dismissable suggestions |
| Confirm-shaming | Neutral language ("No thanks" / "Maybe later") |
| Hidden auto-renewal | Clear renewal notice 7 days before charge |
| Infinite scroll | Pagination or "You're all caught up!" message |
| Addictive notifications | User-controlled notification preferences |
| Pay-to-win | Pay-for-cosmetics (aesthetic, not competitive advantage) |
| Hidden odds | Transparent probability tables |
| Loss-chasing mechanics | Cool-down periods, spending summaries |

---

## Decision Tree: Is This Mechanic Ethical?

```
START: New gamification mechanic proposed
  │
  ├─ Does it pass the FAIR test?
  │   NO → REJECT or REDESIGN
  │   YES ↓
  │
  ├─ Could it harm vulnerable users (minors, addiction-prone)?
  │   YES → Add mandatory safeguards (caps, breaks, age-gate)
  │   NO ↓
  │
  ├─ Does it use Black Hat Octalysis drives (6/7/8)?
  │   YES → Add time limits, opt-out, transparent mechanics
  │   NO ↓
  │
  ├─ Is there a variable reward component?
  │   YES → Disclose odds, add pity timers, cap spending
  │   NO ↓
  │
  ├─ Does it use loss aversion?
  │   YES → Add recovery mechanisms (streak shields, grace periods)
  │   NO ↓
  │
  └─ APPROVE — mark as GREEN in ethical spectrum
```
