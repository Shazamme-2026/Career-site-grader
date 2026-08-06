# AI Readiness — Help-Text & How-To Backlog

Working backlog for the team to expand the grader's in-app guidance from one-line
tips into full "what it means + how to fix it" help articles.

## How help text works in the grader

Each check renders three things to the user:

1. **Detail line** — the pass/fail breakdown (the grey text under the heading).
   Generated inline where the check is scored, e.g. AEO at
   [`grader.py:2050-2073`](../grader.py#L2050-L2073).
2. **Lightbulb tip** — the purple hint box. Comes from the `HELP` dict at
   [`grader.py:3559`](../grader.py#L3559).
3. **Reference links** — "Verify / Example" links. From the `EXAMPLES` dict at
   [`grader.py:3641`](../grader.py#L3641).

To improve a check: edit its `HELP` string (short, in-product) and — for anything
that needs real steps — write a full how-to below and link it. Keep the `HELP`
one-liner; the how-to is the long form for our team / client-facing docs.

## Contributing

- Status per check: `[ ]` = not started, `[~]` = help text drafted, `[x]` = help + how-to done.
- Each how-to should answer: **What it means → Why it matters → How to fix (generic) → How to fix on Duda/Shazamme → How to verify.**
- Prioritise the AI cluster (AEO, Entity & Authority, AI Crawler Access, llms.txt, Crawlable Content, FAQ schema) — that's the differentiator vs generic SEO tools.

---

# Priority 1 — worked exemplars

These three are fully drafted as the template for the rest. Scoring math is taken
straight from the grader so the team can explain any number a client sees.

## AEO / Answer-Engine Readiness — scored /20

**What it grades** ([`grader.py:2031-2074`](../grader.py#L2031-L2074)): whether the
richest content page is *shaped* for AI engines (ChatGPT, Perplexity, AI Overviews)
to quote. Five signals:

| Signal | Points | How it's detected |
|---|---|---|
| Summary / TL;DR block | 5 | Regex for `tl;dr`, `key takeaway`, `in summary`, `at a glance`, `quick answer`, `the short answer` |
| Question-style headings | 6 (≥3) / 3 (≥1) | H2/H3 starting with how/what/why/when/where/which/who/can/should/does/do/are/is, or ending `?` |
| Comparison table(s) | 4 | Any `<table>` element |
| Quotable stats/figures | 3 | ≥3 matches of `%`, `£/$/€` amounts |
| Freshness signal | 2 | "last updated / updated on / reviewed on", or `dateModified`/`datePublished` in Article schema |

**Why it matters:** AI engines extract and cite *packaged* answers. Rich content
that isn't shaped for extraction gets skipped even when it's authoritative.

**How to fix:**
1. Add a **TL;DR/summary block** in the first screenful — 2-3 sentences that
   directly answer the page's core question.
2. Reword subheadings as the **questions people actually ask** ("How much do
   nurses earn in 2026?"). Get to **≥3** to bank the full 6 points.
3. Answer in the **first sentence** under each heading (don't bury the lede).
4. Add at least one **comparison table** (salary by role, location by demand).
5. Show a visible **"Last updated: [date]"** and set `dateModified` in schema.

**On Duda/Shazamme:** add a summary text widget at the top of sector/blog pages;
convert accordion/FAQ headings to question form; insert a Table widget; add a
dynamic "Last updated" field or bake `dateModified` into the page's JSON-LD.

**Verify:** re-run the grader; check the AEO detail line shows ✓ on each signal.

## Entity & Authority — identity layer

**What it grades:** whether AI engines can confirm *who the brand is* and *whether
to trust it* — Organization schema, `sameAs` links, consistent NAP, named
people/bios, accreditations, plus off-page authority (DataForSEO domain rank,
referring domains, backlinks).

**Why it matters:** backlinks give you *reputation*; schema + `sameAs` give you an
*identity* to attach that reputation to. Without the identity layer you're an
island the Knowledge Graph can't connect.

**How to fix:**
1. Add **Organization schema** (sitewide/homepage) with logo, description, NAP.
2. Add a **`sameAs`** array pointing to LinkedIn, Crunchbase, socials, and
   ideally **Wikidata/Wikipedia** — every URL must be live and name/logo-consistent.
3. Keep **NAP identical** on the site, in schema, and on every `sameAs` profile.
4. Publish an **About/Team page** with named people and bios (E-E-A-T).
5. Display **accreditations** (REC, APSCo, ISO).

```html
<script type="application/ld+json">
{ "@context":"https://schema.org","@type":"Organization",
  "name":"Brand","url":"https://www.site.com","logo":"https://www.site.com/logo.png",
  "sameAs":["https://www.linkedin.com/company/...","https://www.crunchbase.com/organization/...","https://www.wikidata.org/wiki/Q..."] }
</script>
```

**On Duda/Shazamme:** Site → Settings → Head HTML (same pattern as the form-capture KB).
**Verify:** Google Rich Results Test + schema.org validator.

## Mobile Readiness — scored /12 (main path)

**What it grades** ([`grader.py:2152-2166`](../grader.py#L2152-L2166)): the viewport
meta tag.

| Condition | Points |
|---|---|
| `width=device-width` present | 12 |
| …but `user-scalable=no` or `maximum-scale=1-4` (blocks pinch-zoom, fails WCAG 1.4.4) | ×0.7 → ~8 |
| Viewport present **without** `width=device-width` | 6 (amber "not optimal") |
| No viewport meta | 0 |

**Reading the example card** (`initial-scale=1, minimum-scale=1, maximum-scale=5,
viewport-…`): it landed on the **6/12 "not optimal"** branch, which means the
substring `width=device-width` is **absent** from the content string. `maximum-scale=5`
is fine (the pinch-zoom penalty only triggers on 1-4), so the *only* problem is the
missing `width=device-width`.

**How to fix:** set the viewport to include `width=device-width`:
```html
<meta name="viewport" content="width=device-width, initial-scale=1">
```
Takes the score from 6 → 12. Avoid `user-scalable=no` / `maximum-scale=1-4`.

**On Duda/Shazamme:** builders usually emit this automatically — if a custom
viewport tag was hand-added, correct it in Head HTML.
**Verify:** PageSpeed Insights (mobile) / view-source the viewport tag.

---

# Backlog — remaining checks

Grouped by pillar. Tick as help text + how-to land. Full source list of tips:
[`HELP` dict, grader.py:3559-3636](../grader.py#L3559-L3636).

## AI / AEO / Entity (highest priority)
- [ ] AI Crawler Access — GPTBot/ClaudeBot/PerplexityBot allowed in robots.txt
- [ ] llms.txt File
- [ ] llm-info File (`/.well-known/llm-info`)
- [ ] FAQ & Q&A Schema (FAQPage JSON-LD)
- [ ] Content Structure (H2 sections, short paras, lists)
- [ ] Crawlable Content (JS-render) — content in raw HTML, not client-only
- [ ] Content Depth (800-1,000+ words on key pages)

## Structured data
- [ ] Schema / Structured Data (Organization / StaffingAgency / JobPosting)
- [ ] Structured Data Validity (JobPosting required fields, WebSite+SearchAction)
- [ ] Local / Location Schema (LocalBusiness per office, geo, areaServed)

## Core on-page SEO
- [ ] Title Tag
- [ ] Meta Description
- [ ] H1 Heading
- [ ] Heading Hierarchy / Heading Structure
- [ ] Canonical URL
- [ ] Indexability (noindex)
- [ ] Open Graph / Social Tags
- [ ] Sitemap.xml / XML Sitemap
- [ ] robots.txt Health
- [ ] Internal Linking
- [ ] External Links
- [ ] Structured Content (lists/tables)
- [ ] FAQ Content

## Recruitment-specific
- [ ] Recruitment Content Streams (employer + jobseeker per sector)
- [ ] Industry & Sector Pages
- [ ] Apply Flow & Job Search
- [ ] ATS Platform Detection
- [ ] Job Search & Filters / Search Functionality
- [ ] Job Alerts & Lead Capture / Lead Capture / Newsletter
- [ ] EVP & Pay Transparency

## Performance
- [ ] Core Web Vitals
- [ ] Lighthouse Performance
- [ ] Page Speed (TTFB) / Server Response (TTFB)
- [ ] Content Compression
- [ ] Caching Strategy
- [ ] Resource Hints
- [ ] Render-Blocking Scripts
- [ ] HTTP/2+
- [ ] Image Optimization / Image Dimensions / Font Loading

## Accessibility
- [ ] Accessibility (WCAG)
- [ ] Semantic HTML & ARIA
- [ ] Image Alt Text

## Security & privacy
- [ ] HTTPS / SSL / HTTPS Trust Signal
- [ ] Mixed Content
- [ ] Strict-Transport-Security
- [ ] Content-Security-Policy
- [ ] X-Content-Type-Options
- [ ] X-Frame-Options
- [ ] Referrer-Policy
- [ ] Permissions-Policy
- [ ] Privacy & Cookie Policy

## Conversion & UX
- [ ] Call-to-Action Strength
- [ ] Form Usability
- [ ] Live Chat & Chatbot
- [ ] Navigation & Structure
- [ ] Analytics & Tracking

## Brand, social & trust
- [ ] Social Sharing & Referrals / Social Links & Sharing
- [ ] Social Proof & Reviews
- [ ] Social Presence
- [ ] Visual Brand Assets
- [ ] Video Content
- [ ] Culture & Team Content
- [ ] Employee Stories & Testimonials
- [ ] DE&I Commitment
