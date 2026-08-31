import asyncio, csv, json, os, sys, time

REPO = "/Users/rickmare/Code/career-site-grader"
sys.path.insert(0, REPO)
os.chdir(REPO)
os.environ.setdefault("PSI_RUNS", "1")  # 1 PSI run per site (speed); real key set via `railway run`

import grader  # noqa: E402

SP = "/private/tmp/claude-501/-Users-rickmare-Code/7347f4fd-d2a1-46a7-a9fa-8bed88d085d5/scratchpad/run2"
OUTDIR = os.path.join(SP, "reports")
os.makedirs(OUTDIR, exist_ok=True)
PILLARS = ["seo", "geo", "cx", "brand", "technical", "conversion"]


def slug(url):
    return (url.replace("https://", "").replace("http://", "")
               .replace("www.", "").strip("/").replace("/", "_"))


async def grade_one(row, sem):
    url, mode = row["url"].strip(), row["mode"].strip()
    sg = slug(url)
    async with sem:
        t0 = time.time()
        print(f">>> START {mode:11} {url}", flush=True)
        try:
            final = None
            g = grader.CareerSiteGrader(url, mode=mode)
            async def run():
                nonlocal final
                async for ev in g.grade():
                    if ev.get("type") == "complete":
                        final = ev
            await asyncio.wait_for(run(), timeout=300)
            if not final:
                raise RuntimeError("no complete event")
            with open(os.path.join(OUTDIR, f"{sg}.json"), "w") as f:
                json.dump(final, f)
            pil = final.get("pillars", {}) or {}
            rec = {
                "slug": sg, "mode": mode,
                "provider": row.get("website_provider", ""), "ats": row.get("ats", ""),
                "url": url, "notes": row.get("notes", ""),
                "overall": final.get("overall_score"), "grade": final.get("grade"),
                "platform": final.get("platform", ""),
                "status": final.get("status_code", ""),
                "resp_s": final.get("response_time", ""),
            }
            for p in PILLARS:
                rec[p] = (pil.get(p) or {}).get("score", "")
            dt = round(time.time() - t0)
            print(f"<<< DONE  {mode:11} {url}  overall={rec['overall']} grade={rec['grade']} ({dt}s)", flush=True)
            return rec
        except Exception as e:
            dt = round(time.time() - t0)
            print(f"!!! FAIL  {mode:11} {url}  {type(e).__name__}: {e} ({dt}s)", flush=True)
            return {"slug": sg, "mode": mode, "provider": row.get("website_provider", ""),
                    "ats": row.get("ats", ""), "url": url, "notes": row.get("notes", ""),
                    "overall": "", "grade": "FAIL", "platform": "", "status": "",
                    "resp_s": "", **{p: "" for p in PILLARS}}


async def main():
    with open(os.path.join(SP, "sites.csv")) as f:
        rows = list(csv.DictReader(f))
    sem = asyncio.Semaphore(3)
    results = await asyncio.gather(*[grade_one(r, sem) for r in rows])
    order = {r["url"].strip(): i for i, r in enumerate(rows)}
    results.sort(key=lambda x: order.get(x["url"], 999))
    cols = ["slug", "mode", "provider", "ats", "url", "overall", "grade",
            *PILLARS, "platform", "status", "resp_s", "notes"]
    with open(os.path.join(SP, "results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow(r)
    ok = sum(1 for r in results if r["grade"] != "FAIL")
    print(f"=== DONE {ok}/{len(results)} graded ===", flush=True)


asyncio.run(main())
