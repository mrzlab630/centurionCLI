# INDAGATOR — Crypto/Web3 SEO Reference

> Source: victoriaolsina.com, coldchain.agency, lkiconsulting.io, Search Engine Journal

## YMYL Classification

Google classifies crypto content as **YMYL (Your Money Your Life)** — maximum E-E-A-T scrutiny.

### What This Means
- Content quality bar is HIGHER than non-YMYL niches
- Author expertise signals are MANDATORY (bios, credentials, links to experience)
- Factual accuracy is critical — one error can tank trust
- External authority signals matter more (backlinks from CoinDesk, CoinTelegraph, etc.)
- Google Quality Raters specifically evaluate YMYL content (E-E-A-T mentioned 186x in guidelines)

### E-E-A-T for Crypto Projects
| Signal | How to Demonstrate |
|---|---|
| **Experience** | Real trading screenshots (NFA), user testimonials, live product demos |
| **Expertise** | Technical documentation, whitepaper, GitHub activity, dev team bios |
| **Authoritativeness** | Backlinks from crypto media, partnerships, audit reports, TVL data |
| **Trustworthiness** | HTTPS, privacy policy, transparent tokenomics, open-source code, contact info |

---

## Keyword Strategy for Crypto

### Keyword Categories
| Category | Examples | Intent | Priority |
|---|---|---|---|
| **Tool/Product** | "solana trading bot", "defi portfolio tracker" | Transactional | HIGH |
| **Tutorial** | "how to swap tokens on solana", "how to use uniswap" | Informational | HIGH |
| **Comparison** | "phantom vs backpack wallet", "best solana dex 2026" | Commercial | HIGH |
| **Problem** | "solana transaction failed", "slippage too high defi" | Informational | MEDIUM |
| **Ecosystem** | "solana defi tools", "ethereum L2 comparison" | Informational | MEDIUM |
| **Token-specific** | "$SOL staking guide", "meme coin analysis" | Mixed | MEDIUM |

### Long-Tail Focus
Crypto users search VERY specifically:
- "hardware wallet with multisig support for DAOs" (not "crypto wallet")
- "cheapest way to bridge USDC from Ethereum to Solana" (not "crypto bridge")
- "raydium vs orca liquidity comparison" (not "solana dex")

**RULE:** Long-tail keywords = lower competition + higher conversion intent.

### Keyword Research Tools
- Ahrefs / Semrush — traditional keyword data
- Nansen / Dune — on-chain trends → keyword opportunities
- Google Trends — crypto search trends (very volatile)
- Reddit/Twitter — community language = real search terms
- "People Also Ask" — Google's own keyword expansion

---

## Content Strategy for Crypto SEO

### Content Types (by impact)
| Type | SEO Value | Effort | Example |
|---|---|---|---|
| **Comparison pages** | HIGHEST | Medium | "Trojan vs BullX vs Photon: 2026 Comparison" |
| **Tutorial/How-to** | HIGH | Medium | "How to Stake SOL: Complete Guide" |
| **Glossary/Wiki** | HIGH | Low | "DeFi Glossary: 100+ Terms Explained" |
| **Landing pages** | HIGH | High | Product-specific SEO landing pages |
| **Blog/Analysis** | MEDIUM | High | Weekly market analysis, feature deep dives |
| **Case studies** | MEDIUM | Medium | "DeFi Yield Farming Results: 6-Month Study (NFA)" |
| **Changelog** | LOW-MED | Low | Dev updates — E-E-A-T signal for "build in public" |

### Topic Cluster Model
```
Pillar: "Solana DeFi: Complete Guide 2026"
  ├── Cluster: "Best Solana DEXs Compared"
  ├── Cluster: "How to Stake SOL: Step by Step"
  ├── Cluster: "Solana Wallet Comparison"
  ├── Cluster: "Understanding Solana Transaction Fees"
  ├── Cluster: "Solana NFT Marketplaces Guide"
  └── Cluster: "Solana vs Ethereum: DeFi Comparison"
```
All cluster pages link to pillar AND each other. Pillar links to all clusters.

---

## Technical SEO for Web3

### SPA/dApp Challenges
- Most Web3 frontends are React/Next.js SPAs — require SSR for SEO
- Wallet-gated content = invisible to crawlers → create ungated SEO versions
- Dynamic data (prices, TVL) → use ISR (Incremental Static Regeneration)
- RPC calls in frontend → pre-render results for crawlers

### Telegram Bot → Web Funnel
Telegram bots are walled gardens (not indexed). Strategy:
1. **Create SEO-optimized web landing pages** for each major feature
2. **Blog content** targeting keywords → drives organic traffic
3. **CTAs on web** → "Start trading → Open in Telegram" funnel
4. **Repurpose Telegram content** → index-friendly FAQ/guide pages
5. **Bot deep links** from web: `https://t.me/BotName?start=feature`

### Schema for Crypto Projects
Priority schema types:
1. **Organization** — brand entity in knowledge graph
2. **WebApplication** — bot/dApp listing with category "FinanceApplication"
3. **FAQPage** — common crypto questions (high SERP real estate)
4. **HowTo** — setup guides, tutorials
5. **Article** — blog posts with author, date, publisher

---

## Link Building for Crypto

### Ethical Strategies
| Strategy | Difficulty | Impact | How |
|---|---|---|---|
| **Crypto media PR** | HIGH | HIGH | Pitch to CoinDesk, CoinTelegraph, The Block, Decrypt |
| **Guest posts** | MEDIUM | MEDIUM | Write for crypto blogs, DeFi publications |
| **Ecosystem directories** | LOW | MEDIUM | List on ecosystem pages (Solana, Ethereum), DeFi aggregators |
| **Open-source contributions** | LOW | LOW-MED | GitHub activity → linked from other repos/docs |
| **Data/Research** | HIGH | HIGH | Original research (on-chain analysis) → natural citations |
| **Community mentions** | LOW | LOW | Reddit, forums, StackExchange answers |

### What NOT to Do
- Buy links from "crypto SEO" services (spam, potential penalty)
- PBN (Private Blog Network) links (Google detects, penalizes)
- Excessive reciprocal linking (obvious to Google)
- Directory spam (low-quality directories hurt more than help)

---

## Compliance & Legal

### Content Rules
- **MUST:** Add NFA/DYOR disclaimers on trading-related content
- **MUST:** Disclose if content discusses your own product
- **MUST:** Be factually accurate about tokenomics, features, performance
- **MUST NOT:** Promise returns, profits, or specific outcomes
- **MUST NOT:** Fabricate testimonials or P&L screenshots
- **MUST NOT:** Mislead about risks

### Google Ads for Crypto (if applicable)
- Pre-approval required for crypto advertising
- Must comply with local regulations
- Certified advertisers only in most regions
- Organic SEO often more effective and cheaper than paid for crypto

---

## Benchmarks

### Typical Crypto SEO Timelines
| Goal | Timeline | Notes |
|---|---|---|
| Technical fixes impact | 2-4 weeks | After crawl/index cycle |
| New content ranking | 2-6 months | Depends on domain authority |
| Keyword position improvement | 3-6 months | Consistent content + links |
| Top 3 ranking | 6-12 months | Competitive keywords |
| Domain authority growth | 6-12 months | Link building dependent |

**RULE:** Set realistic expectations. SEO is a compounding investment, not instant gratification.

---

## Anti-Patterns
- Creating content for every crypto keyword (thin content penalty)
- Ignoring Telegram→Web funnel (biggest missed opportunity for bot projects)
- Using AI to mass-generate low-quality crypto content (Helpful Content Update)
- Neglecting E-E-A-T signals on YMYL crypto pages
- Focusing only on Google — missing GEO/AEO opportunity
- "SEO is dead" mindset — organic search is still 50%+ of web traffic
