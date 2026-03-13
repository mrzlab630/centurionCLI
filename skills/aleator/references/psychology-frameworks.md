# ALEATOR — Psychology Frameworks Reference

> Source: Yu-kai Chou (Octalysis), Nir Eyal (Hooked), Csikszentmihalyi (Flow),
> Deci & Ryan (SDT), Skinner (Operant Conditioning), Cialdini (Influence), Fogg (BJ Fogg)

## 1. Octalysis Framework (Yu-kai Chou)

8 Core Drives of human motivation, organized as octagon:

| # | Core Drive | Type | Description | Game Mechanic Examples |
|---|---|---|---|---|
| 1 | **Epic Meaning & Calling** | White Hat | Being part of something bigger than yourself | Narrative, lore, "chosen one" feeling, mission statements |
| 2 | **Development & Accomplishment** | White Hat | Sense of progress, mastering skills | Points, badges, progress bars, levels, skill trees |
| 3 | **Empowerment of Creativity** | White Hat | Creative expression, experimentation | Sandbox modes, user-generated content, customization |
| 4 | **Ownership & Possession** | White Hat | Owning something, wanting to improve/protect it | Collections, virtual goods, profile building, inventory |
| 5 | **Social Influence & Relatedness** | — | Social pressure, mentorship, competition, envy | Leaderboards, teams, gifting, social proof, mentoring |
| 6 | **Scarcity & Impatience** | Black Hat | Wanting something because you can't have it yet | Limited editions, cooldown timers, appointment mechanics |
| 7 | **Unpredictability & Curiosity** | Black Hat | Not knowing what happens next | Mystery boxes, random rewards, variable outcomes |
| 8 | **Loss & Avoidance** | Black Hat | Avoiding negative outcomes | Streak loss, countdown to expiration, progress decay |

### White Hat vs Black Hat
- **White Hat (1-3):** Makes users feel GOOD — meaning, mastery, creativity. Sustainable but weak urgency.
- **Black Hat (6-8):** Creates URGENCY — scarcity, unpredictability, fear of loss. Powerful but causes burnout.
- **Best design:** White Hat core + Black Hat sparingly for activation moments.

### Octalysis Score
Rate each drive 0-10 for your product. Balanced octagon = healthy engagement. Skewed toward Black Hat = addiction risk.

---

## 2. Hook Model (Nir Eyal)

4-phase habit-forming loop:

```
┌─────────────────────────────────────┐
│  1. TRIGGER                         │
│     External: notification, email   │
│     Internal: emotion (boredom,     │
│     loneliness, uncertainty)        │
│              │                      │
│              ▼                      │
│  2. ACTION                          │
│     Simplest behavior in            │
│     anticipation of reward          │
│     (Fogg: B = MAP)                │
│              │                      │
│              ▼                      │
│  3. VARIABLE REWARD                 │
│     Tribe: social validation        │
│     Hunt: resources, information    │
│     Self: mastery, completion       │
│              │                      │
│              ▼                      │
│  4. INVESTMENT                      │
│     User puts something in:         │
│     data, content, reputation,      │
│     followers, skill                │
│     (increases value for next       │
│      cycle → loads next trigger)    │
└──────────── ↩ back to TRIGGER ──────┘
```

### Key Insights
- **Internal triggers** are the goal — external triggers just bootstrap the habit
- **Variable rewards** must vary or they become boring (hedonic adaptation)
- **Investment** phase is critical — it creates switching costs and loads the next trigger
- **Moral question:** Does the product materially improve the user's life? (Eyal's "Manipulation Matrix")

---

## 3. Flow Theory (Mihaly Csikszentmihalyi)

Optimal experience = being "in the zone."

### Flow Channel
```
Anxiety ↑
         \   FLOW
          \  ZONE  /
Challenge  ────────
          /        \
         /
Boredom ↓
         Skill →
```

- **Too much challenge, low skill** → Anxiety → user quits
- **Low challenge, high skill** → Boredom → user leaves
- **Challenge matches skill** → FLOW → deep engagement

### 9 Components of Flow
1. Challenge-skill balance
2. Action-awareness merging
3. Clear goals
4. Immediate feedback
5. Concentration on task
6. Sense of control
7. Loss of self-consciousness
8. Time distortion
9. Autotelic experience (intrinsically rewarding)

### Application
- **Onboarding:** Start easy, escalate gradually (tutorial → beginner → intermediate → expert)
- **Difficulty curves:** Ramp challenge WITH user skill growth
- **Feedback loops:** Instant feedback keeps users in flow (no waiting, no ambiguity)
- **GameFlow model:** 8 criteria — concentration, challenge, skills, control, goals, feedback, immersion, social

---

## 4. Self-Determination Theory (Deci & Ryan)

3 innate psychological needs for intrinsic motivation:

| Need | Definition | In Gamification | Example |
|---|---|---|---|
| **Autonomy** | Feeling of choice and self-direction | Multiple paths, opt-in features, customization | Choose your challenge, pick your reward |
| **Competence** | Feeling effective and capable | Skill progression, clear feedback, achievable goals | Level system, skill badges, mastery indicators |
| **Relatedness** | Feeling connected to others | Teams, communities, social features, mentorship | Guilds, friend challenges, social sharing |

### Critical Warning: Overjustification Effect
Adding EXTERNAL rewards (money, points) to an activity someone already enjoys INTERNALLY can REDUCE their intrinsic motivation. The external reward replaces the internal drive.

**Rule:** For activities users already enjoy → enhance with competence/autonomy/relatedness signals, NOT points/money.
**Rule:** For activities users DON'T enjoy → external rewards are appropriate bootstrapping, then fade them out.

---

## 5. Skinner's Reinforcement Schedules

B.F. Skinner's operant conditioning — how timing of rewards shapes behavior:

| Schedule | Definition | Response Rate | Extinction Rate | Real-World Example |
|---|---|---|---|---|
| **Fixed Ratio (FR)** | Reward after N actions | High, steady | Fast when stopped | "Buy 10, get 1 free" |
| **Variable Ratio (VR)** | Reward after random N actions | Highest, steady | Very slow | Slot machines, loot boxes |
| **Fixed Interval (FI)** | Reward after set time | Scalloped (surge near time) | Fast when stopped | Daily login bonus |
| **Variable Interval (VI)** | Reward after random time | Moderate, steady | Slow | Random app notifications with reward |

### Key Insight
**Variable Ratio is the most powerful and most addictive schedule.** Slot machines, loot boxes, and gacha games all use VR. The unpredictability creates constant anticipation.

**Ethical rule:** VR schedules in products MUST have:
- Pity timers (guaranteed reward after N attempts)
- Spending caps
- Transparency about odds
- Natural stopping points

---

## 6. Cialdini's 7 Principles of Influence

Robert Cialdini's persuasion principles (Influence, 1984 + Pre-Suasion, 2016):

| Principle | Mechanism | Gamification Application |
|---|---|---|
| **Reciprocity** | Give first → people feel obligated to return | Free trial, bonus reward → user feels "I should give back" |
| **Commitment & Consistency** | Small yes → larger yes | Micro-commitments: profile setup → first action → first purchase |
| **Social Proof** | People follow what others do | "10,000 users chose this", live activity feeds, testimonials |
| **Authority** | Trust experts | Expert badges, verified status, partnership logos |
| **Liking** | Trust people you like | Personalized experience, friendly tone, shared values |
| **Scarcity** | Less available = more valuable | Limited editions, countdown timers, exclusive access |
| **Unity** | Shared identity/belonging | "We" language, tribe identity, community membership |

---

## 7. Fogg Behavior Model (BJ Fogg)

**B = MAP** (Behavior = Motivation × Ability × Prompt)

All three MUST be present for behavior to occur:

```
Motivation ↑
            │  ╱ Action Line
            │ ╱   (above = behavior happens)
            │╱
            ┼──────────── Ability →
```

| Factor | Increase By | Example |
|---|---|---|
| **Motivation** | Pleasure/pain, hope/fear, social acceptance/rejection | "Unlock exclusive reward" (hope) |
| **Ability** | Reduce friction: time, money, effort, cognitive load | One-click action, pre-filled forms |
| **Prompt** | Trigger at the right moment | Push notification when motivation is high |

### Fogg's Tiny Habits
Start with the SMALLEST possible behavior → build from there.
- "Open the app" (not "complete a workout")
- "Read one headline" (not "read the full article")
- "Claim daily reward" (not "play for 30 minutes")

---

## Quick Reference: When to Use Which Framework

| Situation | Best Framework |
|---|---|
| Designing a new feature | Hook Model (complete loop design) |
| Auditing existing engagement | Octalysis (8-drive scoring) |
| Balancing difficulty | Flow Theory (challenge-skill balance) |
| Understanding user motivation | SDT (autonomy/competence/relatedness) |
| Designing reward timing | Skinner Schedules (FR/VR/FI/VI) |
| Writing persuasive copy/UX | Cialdini Principles |
| Reducing friction | Fogg Model (increase ability) |
| Checking for manipulation | Octalysis Black Hat + Eyal Manipulation Matrix |
