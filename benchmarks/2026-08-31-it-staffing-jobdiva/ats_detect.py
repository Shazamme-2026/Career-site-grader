import os, re, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

SP = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(SP, "sites.txt")) as f:
    DOMAINS = [l.strip() for l in f if l.strip()]

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CAREER_PATHS = ["/careers", "/careers/", "/jobs", "/jobs/", "/job-search",
                "/job-seekers", "/search-jobs", "/find-a-job", "/candidates",
                "/careers/job-search", "/open-jobs", "/job-openings", "/apply"]

ATS = {
    "JobDiva": r"jobdiva|www1\.jobdiva|divainit|jdcloud",
    "Bullhorn": r"bullhorn|bhcloud|bullhornstaffing",
    "Workday": r"myworkdayjobs|workdayjobs",
    "Greenhouse": r"greenhouse\.io|boards\.greenhouse|grnhse",
    "Lever": r"jobs\.lever\.co|lever\.co/",
    "iCIMS": r"icims\.com",
    "SmartRecruiters": r"smartrecruiters",
    "Jobvite": r"jobvite",
    "Ceipal": r"ceipal",
    "JazzHR": r"applytojob|jazzhr",
    "ADP": r"workforcenow\.adp|recruiting\.adp",
    "Taleo": r"taleo\.net",
    "SuccessFactors": r"successfactors|sfcareers",
    "Ashby": r"ashbyhq",
    "Recruitee": r"recruitee",
    "Avionte": r"avionte",
    "Shazamme": r"shazamme",
}


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read(600000).decode("utf-8", "ignore")
    except Exception as e:
        return f"ERR {type(e).__name__}"


def find_career_links(base, html):
    links = []
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html, re.I):
        h = m.group(1)
        if re.search(r'career|/job|apply|opening|vacan|talent|opportun', h, re.I):
            if h.startswith("http"):
                links.append(h)
            elif h.startswith("/"):
                links.append(base.rstrip("/") + h)
    out = []
    for l in links:
        if l not in out:
            out.append(l)
    return out[:10]


def scan(html):
    low = html.lower()
    return [name for name, pat in ATS.items() if re.search(pat, low)]


def detect(domain):
    root = "https://www." + domain + "/"
    pages = {}
    checked = 0
    html = fetch(root)
    career_urls = []
    if not html.startswith("ERR"):
        checked += 1
        h = scan(html)
        if h:
            pages[root] = h
        career_urls = find_career_links(root, html)
    for p in CAREER_PATHS:
        career_urls.append("https://www." + domain + p)
    seen = {root}
    for u in career_urls:
        if u in seen:
            continue
        seen.add(u)
        h = fetch(u)
        if not h.startswith("ERR"):
            checked += 1
            hh = scan(h)
            if hh:
                pages[u] = hh
        if any("JobDiva" in v for v in pages.values()):
            break
    hits = {}
    for u, hh in pages.items():
        for name in hh:
            hits.setdefault(name, u)
    other = [a for a in hits if a not in ("JobDiva", "Shazamme")]
    return {"site": domain, "jobdiva": "JobDiva" in hits,
            "jobdiva_url": hits.get("JobDiva", ""),
            "other_ats": ",".join(other), "pages_checked": checked}


results = {}
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = {ex.submit(detect, d): d for d in DOMAINS}
    for fu in as_completed(futs):
        r = fu.result()
        results[r["site"]] = r
        tag = "JOBDIVA" if r["jobdiva"] else (r["other_ats"] or "—")
        print(f"{'JD' if r['jobdiva'] else '  '} {r['site']:24} {tag}", flush=True)

import csv
with open(os.path.join(SP, "ats.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["site", "jobdiva", "jobdiva_url", "other_ats", "pages_checked"])
    w.writeheader()
    for d in DOMAINS:
        w.writerow(results[d])
jd = [d for d in DOMAINS if results[d]["jobdiva"]]
print(f"\n=== JobDiva static-detected: {len(jd)}/{len(DOMAINS)} ===")
print(jd)
