import json, os, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

SP = os.path.dirname(os.path.abspath(__file__))
BASE = "https://webgrader.shazamme.com/grade"
MODE = "recruitment"
PILL = ["seo", "geo", "cx", "brand", "technical", "conversion"]

with open(os.path.join(SP, "sites.txt")) as f:
    DOMAINS = [l.strip() for l in f if l.strip()]


def grade(domain):
    url = "https://www." + domain + "/"
    q = urllib.parse.urlencode({"url": url, "mode": MODE})
    req = urllib.request.Request(BASE + "?" + q, headers={"Accept": "text/event-stream"})
    final = None; last_err = None
    with urllib.request.urlopen(req, timeout=300) as r:
        for raw in r:
            line = raw.decode("utf-8", "ignore").strip()
            if not line.startswith("data:"):
                continue
            try:
                ev = json.loads(line[5:].strip())
            except Exception:
                continue
            t = ev.get("type")
            if t == "complete":
                final = ev
            elif t == "error":
                last_err = ev.get("message", "")
    return final, last_err


def work(domain):
    t0 = time.time()
    try:
        final, err = grade(domain)
    except Exception as e:
        final, err = None, f"{type(e).__name__}: {e}"
    dt = round(time.time() - t0)
    if final:
        with open(os.path.join(SP, "raw", domain.replace("/", "_") + ".json"), "w") as f:
            json.dump(final, f)
        pil = final.get("pillars", {}) or {}
        plat = final.get("platform")
        plat = plat.get("platform") if isinstance(plat, dict) else plat
        rec = {"site": domain, "overall": final.get("overall_score"),
               "grade": final.get("grade"), "platform": plat or "",
               "status": final.get("status_code", ""), "resp_s": final.get("response_time", "")}
        for p in PILL:
            rec[p] = (pil.get(p) or {}).get("score", "")
        print(f"OK   {domain:26} overall={rec['overall']} grade={rec['grade']} plat={plat} ({dt}s)", flush=True)
        return rec
    print(f"FAIL {domain:26} {str(err)[:90]} ({dt}s)", flush=True)
    return {"site": domain, "overall": "", "grade": "BLOCKED", "platform": "",
            "status": "", "resp_s": "", **{p: "" for p in PILL}}


os.makedirs(os.path.join(SP, "raw"), exist_ok=True)
results = {}
with ThreadPoolExecutor(max_workers=6) as ex:
    futs = {ex.submit(work, d): d for d in DOMAINS}
    for fu in as_completed(futs):
        r = fu.result()
        results[r["site"]] = r

import csv
cols = ["site", "overall", "grade", *PILL, "platform", "status", "resp_s"]
with open(os.path.join(SP, "results.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for d in DOMAINS:
        w.writerow(results[d])
ok = sum(1 for d in DOMAINS if results[d]["grade"] != "BLOCKED")
print(f"=== DONE {ok}/{len(DOMAINS)} graded ===", flush=True)
