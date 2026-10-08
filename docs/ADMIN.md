# Admin / Operations

## Super-admin cache bypass (`fresh=1`)

The grader caches per-domain **Core Web Vitals** and **backlink authority** so
repeat grades, monitoring and competitor lookups don't re-measure / re-charge.
Admins can force a completely fresh run with a token-protected override.

### Usage

Append `&fresh=1&token=<ADMIN_TOKEN>` to any grade endpoint:

```
# Streaming grade (UI / SSE)
/grade?url=https://example.com&mode=recruitment&fresh=1&token=<TOKEN>

# JSON grade (Client Portal / integrations)
/api/grade?url=https://example.com&mode=recruitment&fresh=1&token=<TOKEN>

# Force a fresh Core Web Vitals measurement
/api/cwv?url=https://example.com&mode=recruitment&fresh=1&token=<TOKEN>
```

What it bypasses:
- **Authority cache** — forces a fresh backlink-provider (DataForSEO/Moz) lookup
  instead of the 7-day cached value.
- **Core Web Vitals cache** — forces a fresh PageSpeed run and skips the cached
  fallback.

### Token

`fresh=1` is honoured only when `token` matches the `ADMIN_TOKEN` env var, or
`CRON_TOKEN` if `ADMIN_TOKEN` is unset. Without a valid token the `fresh` flag is
ignored, so public traffic can never bust the cache or drive up provider spend.

Set a dedicated admin token on the master (`web`) service:

```
railway variables --set "ADMIN_TOKEN=<random-secret>"
```

## Services

- **Master:** `web` service → https://webgrader.shazamme.com (volume `/data`,
  PageSpeed key, seeded benchmark). Deploy with:
  `railway link --project "Career Site Grader" --service web && railway up`
- **Scratch/test:** `career-site-grader` service. Use for risky changes via
  `railway up` (no GitHub push = master untouched).

## Relevant env vars (master)

| Var | Purpose |
|-----|---------|
| `DATA_DIR=/data` | SQLite persistence on the Railway volume |
| `PAGESPEED_API_KEY` | Google PageSpeed Insights (Core Web Vitals) |
| `CRON_TOKEN` | Auth for `/cron/rescore`, `/cron/seed`, and cache bypass |
| `ADMIN_TOKEN` | (optional) dedicated token for the cache bypass |
| `ENABLE_HEADLESS=1` | Playwright headless render (kill switch: `0`) |
| `DATAFORSEO_LOGIN` / `DATAFORSEO_PASSWORD` | Backlink authority (DataForSEO) |
| `MOZ_TOKEN` | Backlink authority (Moz, alternative) |
| `SENDGRID_API_KEY` | Report / monitor-digest emails |
| `ANTHROPIC_API_KEY` | "Find with AI" competitor finder (Claude + web search). Without it the button returns 503 and manual entry still works |
| `COMPETITOR_MODEL` | (optional) model for the finder, default `claude-opus-5-5` |
| `CLIENT_PDF_RENDER_SLOTS` | (optional) concurrent Chromium renders per worker for the client PDF, default 2 |

## Client opportunity report (PDF)

Every stored report has a short, plain-English, client-facing version built
from the same grade (`client_report.py`):

```
/r/<report_id>/client        print-ready HTML (add ?print=1 to auto-open the print dialog)
/r/<report_id>/client.pdf    A4 PDF rendered with Chromium, served as a download
```

The "Client report" button in the results header calls the PDF route and falls
back to the HTML view if Chromium is unavailable. PDFs are cached in memory per
report (reports are immutable) and the route is rate-limited at 20/hour/IP.
Branding comes from `BRAND_SITE` / `BRAND_EMAIL` (defaults: shazamme.com,
hello@shazamme.com). The check-name → plain-English copy lives in
`client_report.CHECKS` and `client_report.ADVANTAGE`.

## Full technical report (PDF)

The **Full PDF** button downloads a server-rendered A4 version of the complete
on-screen report (`full_report.py`): executive summary, pillar scores,
competitor benchmark, Core Web Vitals, every check in every pillar,
recommendations, Shazamme advantage, coverage. Same Chromium renderer, cache,
semaphore and rate limit as the client report.

```
/r/<report_id>/full          print-ready HTML (add ?print=1 for the print dialog)
/r/<report_id>/full.pdf      A4 PDF download
```

The browser print dialog remains the fallback when there is no stored report
or Chromium is unavailable.

## Competitor comparison

Two competitors can be added before grading (hero) or after it (results screen),
by hand or with **Find with AI** (`GET /api/competitors?url=&mode=` → two direct
competitors with a one-line reason; cached per domain). After a grade,
`POST /api/compare {report_id, competitors:[…]}` light-grades the competitors,
attaches `comparison` to the stored report and clears that report's client-PDF
cache. The table shows in the results, prints in the Full PDF, and appears as
"How you compare" on page 2 of the client report.
