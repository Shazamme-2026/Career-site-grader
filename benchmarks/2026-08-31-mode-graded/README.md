# Benchmark — Recruitment vs. Career-site modes (mode-aware grading)

**Date:** 2026-08-31
**Tool:** Shazamme Career Site Grader (this repo), run per group in its **correct mode**
**Env:** production service (`webgrader.shazamme.com`) — PageSpeed + headless render enabled
**Sites:** 27 (20 recruitment/staffing, 7 corporate career) · **25 graded**, 2 WAF-blocked
**Test list:** [`../sites/recruitment-vs-career.csv`](../sites/recruitment-vs-career.csv) (now carries a `mode` column)

Supersedes the earlier generic Lighthouse pass (`../2026-08-31-recruitment-vs-career/`). That run scored
every site on one raw performance rubric; this one uses the product's real 6-pillar scoring with
mode-specific weights + checks, so the two groups are judged correctly and reported separately.

## Why two modes

Same 6 pillars, different weights and checks:

| Pillar | recruitment | career_site |
|---|---:|---:|
| SEO & Discoverability | 22% | 18% |
| GEO & AI Visibility | 20% | 15% |
| Candidate Experience | 22% | 25% |
| Employer Brand & Content | 14% | 25% |
| Technical Performance | 13% | 10% |
| Conversion & Engagement | 9% | 7% |

- **recruitment** = discoverability-led (SEO+GEO 42%); scores JobPosting / StaffingAgency schema + sector pages; DE&I intentionally not scored.
- **career_site** = brand + experience-led (Brand+CX 50%); adds Culture & Team content, DE&I, explicit Mobile Readiness.

## Headline findings

1. **Career sites are where Shazamme wins decisively.** sutherland **80** and tollgroup **78** are the only B+ in the career group; incumbent-ATS sites trail (svhm 67, linfox 62, smiggle 55, reece 54). Gap is largest on Brand (92/89 vs 33–71) and Technical (88/91 vs 62–78).
2. **Recruitment is tighter.** Shazamme designandbuild 81 / beaumontpeople 80 / aspectpersonnel 77 sit in a B+ cluster with SaaS rivals (trsresourcing 82, ambition 80). Shazamme edge = Brand + Technical; rivals win raw SEO.
3. **GEO/AI visibility is the industry-wide gap** — lowest pillar in both groups (recruitment 64, career 54 avg).
4. **2 sites hard-block the crawler (403):** kofi-group and BHP (Cloudflare-class WAF), on both local and prod. Same block also stops AI crawlers.

## Files

| File | What |
|------|------|
| `results.csv` | Final 27-row results (`mode,site,provider,ats,overall,grade,seo,geo,cx,brand,technical,conversion`) |
| `report.pdf` / `report.html` | Two-section report (recruitment + career) with analysis |
| `graded.xlsx` | Two-tab workbook, RAG-shaded, weights in headers |
| `batch_grade.py` | Primary runner — grades all sites concurrently in-process |
| `retry_grade.py` | Sequential retry + terminating-event diagnostics for failures |
| `live_grade.py` | Regrades WAF/TLS-blocked sites via the production SSE endpoint |
| `build_report.py` | Builds report.html + graded.xlsx from the final dataset |
| `raw-grader-json.zip` | Full per-site grader JSON (21 locally graded) |

## Reproduce

```bash
# grades every site in-process using the correct mode per row
railway run -- .venv/bin/python batch_grade.py
# WAF/TLS-blocked hosts fail locally — regrade via production:
python3 live_grade.py
```

> Local grading fails for hosts behind aggressive WAF/TLS (403 / TLSV1_ALERT) — the production
> service handles them, so blocked sites were regraded via `live_grade.py`. Single run per site;
> treat ±3–5 as noise.
