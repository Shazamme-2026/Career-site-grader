# Benchmark — Recruitment/staffing vs. corporate career sites

**Date:** 2026-08-31
**Tool:** Google Lighthouse (CLI), mobile emulation, single cold run per URL
**Sites:** 24 (17 recruitment/staffing agency sites + 7 corporate career sites)
**Test list:** [`../sites/recruitment-vs-career.csv`](../sites/recruitment-vs-career.csv)

## Files

| File | What it is |
|------|-----------|
| `results.csv` | Parsed scores per site (`slug\|provider\|url\|perf\|access\|bp\|seo\|fcp_s\|lcp_s\|tbt_ms\|cls\|si_s\|status`) |
| `report.pdf` | Shareable report — platform summary, ranked detail, analysis |
| `report.html` | Source of the PDF (self-contained; open in a browser) |
| `graded.xlsx` | Workbook — ranked results tab + by-provider tab (RAG-shaded) |
| `run_lighthouse.sh` | The batch runner used to produce `results.csv` |
| `raw-lighthouse-json.zip` | Full per-site Lighthouse JSON (audit evidence) |

## Headline findings

1. **Performance is the differentiator.** Cohort SEO (90 avg) and accessibility (86 avg) are healthy; performance (52 avg) is where sites bleed — 14 of 24 score under 60.
2. **The two Shazamme sites win performance outright** — sutherland **93**, tollgroup **91**, the only sites in the 90s, with sub-100ms TBT and near-zero CLS.
3. **Volcanic is the worst platform** (perf avg 27): sharpandcarter 17 (LCP 16s, CLS 0.52), ambition 37 (LCP 19s).
4. **Worst offenders** — TBT: bhp 10.1s, dunhill 7.4s, smiggle 6.1s. LCP: camino 27s, ambition 19s. CLS: scrhired 0.77, sharpandcarter 0.52, pearlrec 0.40.
5. **Link-out apply/job-board sites cluster at the bottom;** embedded-ATS sites (Shazamme, Applyflow TRS) top the table.

## Reproduce

```bash
# requires: node, Google Chrome, npx
# reads sites, runs Lighthouse on each, writes results.csv + reports/*.json
bash run_lighthouse.sh
```

> Note: `run_lighthouse.sh` here reads a flat `urls.txt` (`slug|provider|url`). The canonical
> source of truth is `../sites/recruitment-vs-career.csv`; regenerate `urls.txt` from it if the
> list changes. Lab perf scores vary ±5–10 run-to-run — treat category scores as directional and
> the LCP/TBT/CLS diagnostics as the reliable signal.
