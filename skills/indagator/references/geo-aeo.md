# INDAGATOR — GEO/AEO Reference (AI Search Optimization)

> Source: Gartner 2026, aurametrics.io, lkiconsulting.io, AICMO research, Search Engine Journal

## The 2026 Landscape

**Key stat:** Gartner predicts 25% drop in traditional search traffic by 2026 due to AI chatbots.

### AI Search Platforms
| Platform | How It Works | Optimization Priority |
|---|---|---|
| **Google AI Overviews** | AI-generated summary at top of SERP | HIGH — largest search share |
| **ChatGPT Web Search** | Browses web, synthesizes answer | HIGH — growing rapidly |
| **Perplexity** | Research-focused, always cites sources | MEDIUM — quality audience |
| **Claude** | Can browse via tools/MCP | MEDIUM — developer audience |
| **Bing Copilot** | AI-powered Bing integration | MEDIUM — enterprise users |

### What Changed
- Traditional SEO: optimize for blue links → user clicks → visits site
- GEO/AEO: optimize for AI citation → AI mentions your brand/content → user trusts recommendation
- **Both are needed.** GEO supplements, does not replace, traditional SEO.

---

## CITE Framework (Content for AI Citation)

### C — Credible
- Link to authoritative sources (research papers, official docs, verified data)
- Display author credentials and experience signals
- Include publication dates and update timestamps
- Reference verifiable data (not opinions)

### I — Instructive
- Clear structure: H1 → H2 → H3 hierarchy
- Step-by-step formats where applicable
- Tables for comparative data (LLMs love structured comparisons)
- FAQ sections with Q&A format
- Bullet points and numbered lists (easy for LLMs to parse)

### T — Transparent
- Cite your data sources explicitly
- Show methodology for any analysis
- Disclose limitations and caveats
- For crypto: NFA/DYOR where applicable

### E — Expert
- First-hand experience signals (screenshots, real data, personal insights)
- Technical depth appropriate to topic
- Cross-reference with industry standards
- Demonstrate domain knowledge through specificity (not generic advice)

---

## AI Crawler Management

### Known AI Crawlers (2026)
| Crawler | User-Agent | Owner |
|---|---|---|
| GPTBot | `GPTBot/1.0` | OpenAI |
| ChatGPT-User | `ChatGPT-User` | OpenAI (live browsing) |
| ClaudeBot | `ClaudeBot` | Anthropic |
| PerplexityBot | `PerplexityBot` | Perplexity |
| Google-Extended | `Google-Extended` | Google (AI training) |
| Bytespider | `Bytespider` | ByteDance |
| CCBot | `CCBot/2.0` | Common Crawl |

### robots.txt for AI
```
# Allow AI crawlers for GEO visibility
User-agent: GPTBot
Allow: /blog/
Allow: /docs/
Disallow: /api/
Disallow: /app/

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /
```

**Decision:** Block AI crawlers = invisible in AI search. Allow = potential citations. For most sites: **ALLOW.**

### Markdown-for-Bots Pattern
Emerging tactic (from `agent-seo` by pontiggia):
- Detect AI crawlers by User-Agent
- Serve clean Markdown instead of HTML (85% token reduction for LLMs)
- HTML to humans, Markdown to bots
- Generate `/llms.txt` directory (llmstxt.org spec)

---

## Content Optimization for AI Search

### What Gets Cited by LLMs
1. **Direct answers** — clear, concise answers to specific questions
2. **Structured data** — tables, lists, step-by-step guides
3. **Unique data** — original research, proprietary analysis, first-hand experience
4. **Authoritative sources** — well-known domains, established brands
5. **Recent content** — freshness signals matter for AI search too

### What Gets Ignored
1. Thin content (under 300 words with no unique value)
2. Heavy promotional copy (LLMs filter marketing speak)
3. Paywalled content (bots can't access it)
4. JavaScript-only content (many AI crawlers don't execute JS)
5. Content without clear structure (walls of text)

### Optimizing Existing Content for GEO
1. **Add FAQ section** — Q&A format that LLMs love to cite
2. **Add data tables** — comparative info in structured format
3. **Add TL;DR** — summary at top for quick extraction
4. **Add last-updated date** — freshness signal
5. **Add author info** — E-E-A-T for credibility
6. **Add schema markup** — machine-readable structure

---

## Brand Mention Monitoring in AI

### What to Track
- Does ChatGPT mention your brand when asked about your niche?
- Does Perplexity cite your website as a source?
- Does Google AI Overview include your content?
- What context/sentiment surrounds mentions?
- Which competitors get mentioned instead of you?

### How to Monitor
1. **Manual testing** — regularly query AI platforms with target keywords
2. **AICMO** (open-source) — automated brand visibility tracking across AI platforms
3. **LLM citation APIs** — some SEO tools now track AI mentions (Nightwatch, Search Atlas)

### Improving AI Mentions
1. **Be the definitive source** — comprehensive, authoritative content on your topic
2. **Get cited by Wikipedia** — LLMs weight Wikipedia sources heavily
3. **Earn editorial backlinks** — from sites LLMs trust (news, industry publications)
4. **Structured data** — help LLMs understand your entity and offerings
5. **Content freshness** — regularly update key pages

---

## Google AI Overviews (SGE) Specifics

### How AI Overviews Work
- AI-generated summary appears above organic results
- Pulls from multiple sources, sometimes citing them
- Triggered by informational queries, definitions, how-to, comparisons
- Less common for transactional queries (buying keywords)

### Optimization Tactics
1. **Target question keywords** — "how to", "what is", "best way to"
2. **Provide concise answers** — 40-60 word summary near the top of content
3. **Use structured headers** — match the question in H2, answer immediately below
4. **Include comparative tables** — AI Overviews love pulling table data
5. **Be cited, not replaced** — add unique angles that AI can't summarize away

---

## YMYL Niche GEO Specifics

LLMs are cautious with YMYL content — E-E-A-T signals even more critical for AI citations.

**Crypto/Web3:**
- On-chain data references (Dune, block explorers) add credibility
- Open-source code references (GitHub) boost trust signals
- "Build in public" content = first-hand experience = E-E-A-T

**Finance/Investing:**
- Cite regulatory sources (SEC, FCA), verified market data
- Author credentials (CFA, financial licenses) improve citation chances

**Health/Medical:**
- Cite PubMed, WHO, peer-reviewed studies
- Author medical credentials mandatory for AI citation

**Legal:**
- Cite jurisdiction-specific statutes, court decisions
- Bar membership / legal credentials increase trust

---

## Anti-Patterns
- Blocking all AI crawlers (zero AI search visibility)
- Keyword stuffing for AI (LLMs detect and deprioritize)
- Generating mass AI content without unique value (Google Helpful Content Update penalizes)
- Ignoring AI search entirely ("it's a fad") — 25% traffic shift is not a fad
- Cloaking (different content for bots vs humans) — detectable, penalizable
