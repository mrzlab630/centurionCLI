# Player Retention

Use this file for acquisition, activation, habit loops, progression, rewards, social mechanics, and ethical retention design for Telegram Mini App games.

## Retention Stages

| Stage | Goal | Good Mechanics | Metrics |
|---|---|---|---|
| D0 Activation | Player completes first meaningful action. | Starter reward, instant play, guided first upgrade, result screen. | first action rate, time to first reward, onboarding completion. |
| D1 Return | Player has a concrete reason to come back. | Daily reward, refill, unfinished upgrade, new task, friend response. | D1 retention, return source, reward claim rate. |
| D3 Understanding | Player understands progression and value. | visible next unlock, early collection set, 3-day quest chain. | D3 retention, upgrade rate, quest completion. |
| D7 Habit | Player has a routine or social tie. | weekly challenge, leaderboard period, team goal, streak with protection. | D7 retention, sessions per user, social actions. |
| Long-term | Player keeps goals beyond novelty. | seasons, events, mastery, collections, fair economy tuning. | D30 retention, economy sink/source balance, churn reasons. |

## Ethical Mechanics

| Mechanic | Use When | Guardrail |
|---|---|---|
| Daily bonus | The game has meaningful daily progress. | Do not punish missed days harshly. Offer catch-up or streak shield. |
| Energy/refill | Sessions need pacing or anti-abuse. | Show refill time and cap clearly. Avoid pushing paid refill pressure. |
| Streak | Repeated behavior is central. | Make the reward transparent. Avoid shame copy. Add recovery path. |
| Leaderboard | Competition motivates the audience. | Segment by league or cohort. Provide opt-out for public identity. |
| Referral reward | Social growth creates real player value. | Reward both sides where possible. Prevent self-referral and spam. |
| Variable reward | Cosmetic surprise or low-stakes delight. | Cap frequency, disclose odds when value matters, avoid paid random value. |
| Limited event | Real seasonal or event content. | Deadline must be real and visible. No resetting countdown deception. |

## Player Motivation Segments

| Segment | Wants | Give Them | Avoid |
|---|---|---|---|
| Achiever | Progress, levels, completion. | milestones, badges, clear next goal. | hidden rules and random-only advancement. |
| Explorer | Discovery, novelty, secrets. | unlockable areas, item lore, rotating events. | repetitive tap-only loops. |
| Socializer | Friends, teams, sharing. | team quests, invite benefits, cooperative goals. | spammy referral pressure. |
| Competitor | Rank, mastery, challenge. | fair leaderboard, leagues, duels, replays. | pay-to-win advantage without disclosure. |
| Collector | Ownership, sets, rarity. | collections, albums, cosmetic identity. | impossible completion or opaque paid odds. |

## Growth Loop Patterns

| Loop | Shape | Fit |
|---|---|---|
| Referral loop | Player earns value -> invites friend -> both gain progress -> friend repeats. | Casual/social games with low onboarding friction. |
| Result-sharing loop | Player gets score/reward -> shares proof -> others enter to beat/claim. | Skill, score, challenge, leaderboard games. |
| Team loop | Player joins group -> group target creates repeated action -> social obligation drives return. | Cooperative events and community games. |
| Content/event loop | New event/task appears -> player returns -> unlocks limited cosmetic/status. | Seasonal games and live ops. |

## Notification And Re-entry Rules

- Send or request notifications only after value is delivered.
- Tie every notification to a concrete player state: reward ready, friend moved, event ending, challenge result, energy full.
- Avoid generic reminders like "Come back now".
- Provide frequency control when possible.
- Use Telegram bot messages sparingly and coordinate with PRAECO for platform constraints.

## Metrics Checklist

Track by cohort and source:
- First action rate.
- Time to first reward.
- D1/D3/D7/D30 retention.
- Sessions per active user.
- Core action completion rate.
- Reward claim rate.
- Upgrade conversion.
- Invite sent, invite accepted, invited user retained.
- Task completion and verification failures.
- Economy source/sink balance.
- Fraud/abuse review rate.
- Language-specific drop-off after localization.

## Anti-Patterns

- Rewarding invites before the player understands the game.
- Showing ten currencies or systems on the first screen.
- Making the main loop depend on off-platform tasks.
- Using fake countdowns or unclear prize eligibility.
- Giving paid users undisclosed competitive advantage.
- Designing a daily loop with no natural stopping point.
- Making localization an afterthought after copy has already become unstructured.
