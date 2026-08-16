# Product Language System

Use this file for product voice, tone, naming governance, word lists, glossary, and product language standards.

## Table Of Contents

- Product Language Layers
- Voice And Tone
- Naming Governance
- Word List
- Glossary
- Claims Discipline
- Localization Readiness
- Output Template

## Product Language Layers

| Layer | Purpose | Owner |
|---|---|---|
| Voice | Stable product personality. | NOMENCLATOR + product owner. |
| Tone | Situation-specific delivery. | NOMENCLATOR. |
| Glossary | Meaning of product terms. | NOMENCLATOR + GLOSSATOR. |
| Word list | Preferred/avoid terms and mechanics. | NOMENCLATOR. |
| UI copy patterns | CTA, labels, states, errors. | NOMENCLATOR + AEDILIS. |
| Localization notes | Terms, placeholders, plural risk. | GLOSSATOR. |

## Voice And Tone

Define voice with 3-5 stable adjectives and operational rules.

Example:

| Voice Attribute | Means | Does Not Mean |
|---|---|---|
| Clear | Names the action and result. | Oversimplified or vague. |
| Calm | Handles errors without panic. | Emotionless or dismissive. |
| Direct | Uses short, useful sentences. | Abrupt or rude. |

Tone shifts by context:

| Context | Tone | Rule |
|---|---|---|
| Onboarding | Welcoming, specific. | Show first value fast. |
| CTA | Direct, action-oriented. | Verb first; avoid vague “Continue” when state is unclear. |
| Error | Calm, recoverable. | Problem + next step. |
| Success | Confirming, concise. | Say what changed. |
| Empty | Helpful, not apologetic. | Explain state + next useful action. |
| Payment/prize/legal | Precise, conservative. | No exaggerated claims. |

## Naming Governance

Good names are:

- Specific enough to predict what happens.
- Short enough for navigation and buttons.
- Stable enough to become glossary terms.
- Distinct from nearby concepts.
- Easy to translate or document.

Naming process:

1. Define the thing in one sentence.
2. List adjacent/confusable terms.
3. Choose naming pattern: noun, verb phrase, status, role, reward, object.
4. Generate variants.
5. Score for clarity, specificity, tone, length, localization, legal risk.
6. Pick one recommended name and rejected patterns.

## Word List

Maintain preferred and avoided terms.

| Use | Avoid | Reason |
|---|---|---|
| Sign in | Log in / Login mixed randomly | Keep one account action. |
| Claim reward | Get money | “Money” can imply withdrawable value. |
| Try again | Failed | Gives recovery action. |
| Not enough energy | You cannot play | Names the specific blocker. |
| View rules | Learn more | Better for eligibility/legal details. |

## Glossary

For each term:

| Field | Example |
|---|---|
| Term | Energy |
| Definition | Resource spent to start a game session. |
| Use in UI | “Not enough energy” / “Energy refills in {timeLeft}” |
| Avoid | “Power”, “fuel” unless product chooses that metaphor. |
| Translate? | Yes, with GLOSSATOR-approved target terms. |
| Notes | Do not imply paid currency unless it is purchasable. |

## Claims Discipline

Interface copy must not invent:

- Guaranteed rewards.
- Scarcity or deadlines.
- Eligibility.
- Payment/refund outcomes.
- Security/privacy guarantees.
- Performance claims.

If product logic does not prove it, mark the phrase as `needs product/legal decision`.

## Localization Readiness

- Prefer complete sentences over fragments.
- Avoid idioms and puns in core UI.
- Use placeholders by meaning: `{amount}`, `{currency}`, `{timeLeft}`.
- Add translator notes for invented terms, rewards, roles, ranks, and metaphors.
- Avoid UI text that depends on English word order.

## Output Template

```
Product Language System: [project/feature]

Voice:
| Attribute | Do | Avoid |
|---|---|---|

Tone By Context:
| Context | Tone | Example |
|---|---|---|

Glossary:
| Term | Meaning | Use | Avoid | Notes |
|---|---|---|---|---|

Word List:
| Preferred | Avoid | Reason |
|---|---|---|
```
