# INDAGATOR — Technical SEO Reference

> Source: Google Search Central 2026, web.dev, Lighthouse, Yoast, Screaming Frog

## Core Web Vitals (2026 Thresholds)

| Metric | Good | Needs Improvement | Poor | What It Measures |
|---|---|---|---|---|
| **LCP** (Largest Contentful Paint) | ≤2.5s | 2.5-4.0s | >4.0s | Loading performance |
| **INP** (Interaction to Next Paint) | ≤200ms | 200-500ms | >500ms | Interactivity (replaced FID) |
| **CLS** (Cumulative Layout Shift) | ≤0.1 | 0.1-0.25 | >0.25 | Visual stability |

### How to Measure
- **Lab data:** Lighthouse, PageSpeed Insights, WebPageTest
- **Field data:** Chrome UX Report (CrUX), Search Console Core Web Vitals report
- **RULE:** Field data > Lab data for ranking purposes. Google uses real user metrics.

---

## Crawlability Checklist

### robots.txt
```
User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/
Sitemap: https://example.com/sitemap.xml
```
- Check for accidental blocks (`Disallow: /` blocks everything)
- Allow AI crawlers explicitly if doing GEO: `User-agent: GPTBot`, `User-agent: ClaudeBot`

### XML Sitemap
- Maximum 50,000 URLs per sitemap, 50MB uncompressed
- Include `<lastmod>` dates (only if genuinely updated)
- Submit via Search Console AND robots.txt
- Separate sitemaps for content types: pages, blog, images, video

### Canonical Tags
- Every page MUST have `<link rel="canonical" href="...">` pointing to preferred URL
- Prevent duplicate content issues from URL parameters, HTTP/HTTPS, www/non-www
- Self-referencing canonicals are valid and recommended

### Indexation Control
| Tag | Purpose |
|---|---|
| `<meta name="robots" content="noindex">` | Prevent indexing |
| `<meta name="robots" content="nofollow">` | Don't follow links on page |
| `X-Robots-Tag: noindex` | HTTP header (for non-HTML resources) |
| `<link rel="canonical">` | Preferred URL version |

---

## Schema Markup (JSON-LD)

### Common Schemas (by priority)

**Organization** (MUST HAVE for any business):
```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Brand Name",
  "url": "https://example.com",
  "logo": "https://example.com/logo.png",
  "sameAs": ["https://x.com/brand", "https://t.me/brand"],
  "description": "Description for knowledge panel"
}
```

**WebApplication** (for software products, SaaS, tools):
```json
{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "App Name",
  "applicationCategory": "FinanceApplication",
  "operatingSystem": "Web",
  "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" }
}
```

**FAQPage** (high SERP real estate):
```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [{
    "@type": "Question",
    "name": "Question text?",
    "acceptedAnswer": { "@type": "Answer", "text": "Answer text." }
  }]
}
```

**HowTo** (for tutorials):
```json
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "How to...",
  "step": [{ "@type": "HowToStep", "text": "Step description" }]
}
```

### Validation
- Google Rich Results Test: https://search.google.com/test/rich-results
- Schema.org Validator: https://validator.schema.org
- **RULE:** Always validate before deployment. Invalid schema = no rich results + possible penalty.

---

## Mobile-First Indexing

- Google uses MOBILE version of content for indexing since March 2021
- **Check:** Same content on mobile and desktop (no hidden content)
- **Check:** Viewport meta tag: `<meta name="viewport" content="width=device-width, initial-scale=1">`
- **Check:** Touch targets ≥48px, font ≥16px, no horizontal scroll
- **Check:** No interstitials blocking content on mobile

---

## JavaScript & SPA Rendering

### The Problem
- SPAs (React, Vue, Svelte) render content via JavaScript
- Googlebot CAN render JS but with delays (seconds to days)
- Other crawlers (Bing, AI bots) may NOT render JS at all

### Solutions (by priority)
1. **SSR (Server-Side Rendering)** — best for SEO. Next.js, Nuxt, SvelteKit.
2. **SSG (Static Site Generation)** — best for performance. Pre-rendered HTML.
3. **Dynamic Rendering** — serve pre-rendered HTML to bots, SPA to users. Last resort.
4. **Hydration** — SSR + client-side JS takes over. Next.js default.

### SPA-Specific Notes
- Auth-gated / login-gated content is NOT indexable — provide ungated summary/preview
- Frequently changing data (dashboards, feeds) — use ISR (Incremental Static Regeneration)
- App-heavy products — create static SEO landing pages, link to dynamic app
- Web3 dApps — wallet-gated content invisible to crawlers, same pattern applies

---

## Internal Linking Strategy

### Principles
1. **Topic clusters:** Pillar page (broad topic) links to cluster pages (specific subtopics) and back
2. **Link depth:** Important pages should be ≤3 clicks from homepage
3. **Anchor text:** Descriptive, varied (not all exact-match keywords)
4. **Orphan pages:** Every page must be linked from at least one other page
5. **Link equity flow:** More internal links = more authority distribution

### Audit Checklist
- No broken internal links (404s)
- No redirect chains (A→B→C, max 1 redirect)
- No nofollow on internal links (wastes link equity)
- Footer/nav links count but carry less weight than contextual links

---

## Page Speed Optimization

### Quick Wins (by impact)
1. **Image optimization** — WebP/AVIF, compression, lazy loading, responsive sizes
2. **Caching** — browser cache headers, CDN, service workers
3. **Minification** — CSS, JS, HTML minification + gzip/brotli compression
4. **Critical CSS** — inline above-the-fold CSS, defer rest
5. **Font optimization** — font-display: swap, preload, subset
6. **Third-party scripts** — defer/async, remove unused, evaluate impact

### Delegation
- Image optimization → PICTOR
- Server caching/CDN → PONTIFEX
- Code minification/bundling → CODER
- Infrastructure (HTTP/2, Brotli) → PONTIFEX

---

## Redirects

| Type | When to Use |
|---|---|
| **301 (Permanent)** | Page permanently moved. Passes ~90-99% link equity. |
| **302 (Temporary)** | Temporary move. Does NOT pass link equity reliably. |
| **Redirect chain** | A→B→C — BAD. Fix to A→C direct. |
| **Redirect loop** | A→B→A — CRITICAL BUG. Breaks indexing. |

### Rules
- Maximum 1 redirect hop
- Update internal links to point to final URL (don't rely on redirects)
- After migration: monitor 404s in Search Console for 6+ months

---

## Anti-Patterns
- Blocking CSS/JS in robots.txt (Google needs to render pages)
- Missing canonical tags on paginated content
- Using `noindex` AND `disallow` together (Google can't see noindex if disallowed)
- Soft 404s (page exists but shows "not found" content with 200 status)
- Hreflang without self-referencing tags
- Schema markup that doesn't match visible page content (cloaking risk)
