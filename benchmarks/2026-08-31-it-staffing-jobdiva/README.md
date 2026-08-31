# Benchmark — IT Staffing & Consulting (50 sites) + JobDiva ATS audit

**Date:** 2026-08-31
**Tool:** Shazamme Career Site Grader (this repo), production service (`webgrader.shazamme.com`)
**Mode:** `recruitment` for all 50 (discoverability-led weighting)
**Sites:** 50 IT-staffing / consulting / recruitment firms · **44 graded**, 6 WAF-blocked (HTTP 403)

Two things were produced from the same 50-domain list:

1. **Grades** — each site scored on the product's 6-pillar `recruitment` rubric.
2. **ATS audit** — "are these all JobDiva clients?" Answered by inspecting each site's
   careers / application page (static HTML → headless render → drill into a live job + Apply flow).

## Pillar weights (recruitment mode)

| SEO | GEO/AI | CX | Brand | Technical | Conversion |
|---:|---:|---:|---:|---:|---:|
| 22% | 20% | 22% | 14% | 13% | 9% |

## Grade headlines

- Only two **A**s: `nescoresource.com` **87** (Shazamme site) and `4cornerresources.com` **85**.
- Gradable average **65** (B/C+ border).
- **GEO/AI visibility** is the field-wide weak pillar — almost no one is optimised for AI answer engines.
- Rebuild candidates (bottom): ccpace 24, intelliswift 31, lancesoft 37, igiusa 44.
- **6 hard-block the crawler (403):** luxoft, dsainc, kellton, acsicorp, adventglobal, go2dynamic.

## ATS audit — NOT all JobDiva

Verdict on all 50 (`verdict.csv`):

| Bucket | Count | Sites |
|---|---:|---|
| **JobDiva** | 18 | aditiconsulting, ccpace, genesis10, intelliswift, agwtalent, talentburst, greeley, brick.work, lancesoft, rgbsi, nescoresource, 4cornerresources, lce, igiusa, vlinkinfo, v2soft, aurastaff · +jobdiva.com (vendor) |
| **Other ATS** | 18 | Workday: nttdata, dev-10, fev · Bullhorn: rcmt, acsicorp, ncstech, gotoagile · Oracle: artech, artechinfo.in · Greenhouse: eplus, dsainc · Ceipal: solugenix · UKG: damcogroup · JazzHR: infinite · Taleo: experis · ADP: sterlingsolutions · Ashby: chartis · Avionté/Workday: go2dynamic |
| **Undetermined** | 14 | softtek, luxoft, lhpes, lertechforce, acrocorp, speridian, rapscorp, freyrsolutions, kellton, improving, ionidea, apar, adventglobal, pixazo.ai |

**Bottom line:** 17 JobDiva clients (+ the vendor) vs **18 confirmed on a competing ATS**.
Even if all 14 undetermined turned out to be JobDiva, it'd top out at 32/50 — so the list is
definitely not all-JobDiva. "Undetermined" = board hidden behind a JS portal / external redirect
that headless couldn't resolve, or the crawl timed out; not confirmed either way.

## Files

| File | What |
|------|------|
| `graded.xlsx` | Final workbook — RAG-shaded grades + colour-coded `ATS (apply page)` column |
| `results.csv` | 50-row grades (`site,overall,grade,seo,geo,cx,brand,technical,conversion,platform,status,resp_s`) |
| `verdict.csv` | Final ATS verdict per site (`site,ats,evidence`) |
| `ats.csv` / `ats_headless.csv` / `ats_drill.csv` | Raw output of each detection pass |
| `sites.txt` | The 50-domain input list |
| `run.py` | Grader runner — all 50 via the production SSE endpoint, recruitment mode |
| `build.py` | Builds `graded.xlsx` from `results.csv` + `verdict.csv` |
| `ats_detect.py` | Pass 1 — static HTML careers-page scan for ATS signatures |
| `ats_headless.py` | Pass 2 — Playwright render of homepage + careers page |
| `ats_drill.py` | Pass 3 — drill into a live job posting + follow the Apply button |
| `raw-grader-json.zip` | Full per-site grader JSON (44 graded) |

## Reproduce

```bash
# grade all 50 (recruitment mode) via production
.venv/bin/python run.py
# ATS audit — three escalating passes
python3 ats_detect.py                 # static
.venv/bin/python ats_headless.py unknowns.txt   # rendered
.venv/bin/python ats_drill.py unknowns2.txt      # drill + apply follow
# build the workbook
.venv/bin/python build.py
```

> Single grade run per site — treat ±3–5 as noise. WAF-blocked hosts (403) can't be crawled by
> the tool or by AI crawlers. ATS detection reads only public front-end signals (rendered DOM,
> iframe hosts, network requests, apply-button targets) — it does not log into any ATS.
