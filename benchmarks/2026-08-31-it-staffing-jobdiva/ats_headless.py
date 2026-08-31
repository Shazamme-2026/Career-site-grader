import asyncio, os, re, sys
from playwright.async_api import async_playwright

SP = os.path.dirname(os.path.abspath(__file__))
_arg = sys.argv[1] if len(sys.argv) > 1 else ""
if _arg and os.path.isfile(_arg):
    with open(_arg) as _f:
        UNKNOWNS = [l.strip() for l in _f if l.strip()]
else:
    UNKNOWNS = sys.argv[1:]

CAREER_PATHS = ["/careers", "/jobs", "/job-search", "/search-jobs",
                "/careers/job-search", "/job-openings", "/candidates", "/find-a-job"]

ATS = {
    "JobDiva": r"jobdiva|divainit|jdcloud",
    "Bullhorn": r"bullhorn|bhcloud",
    "Workday": r"myworkdayjobs|workdayjobs",
    "Greenhouse": r"greenhouse\.io|boards\.greenhouse|grnhse",
    "Lever": r"jobs\.lever\.co",
    "iCIMS": r"icims\.com",
    "SmartRecruiters": r"smartrecruiters",
    "Jobvite": r"jobvite",
    "Ceipal": r"ceipal",
    "JazzHR": r"applytojob|jazzhr",
    "ADP": r"workforcenow\.adp|recruiting\.adp",
    "Taleo": r"taleo\.net",
    "SuccessFactors": r"successfactors|sfcareers",
    "Avionte": r"avionte",
    "Shazamme": r"shazamme",
}


def scan(text):
    low = text.lower()
    return [n for n, p in ATS.items() if re.search(p, low)]


async def check_url(page, url, net):
    try:
        await page.goto(url, timeout=25000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3500)
        html = await page.content()
        frames = " ".join(f.url for f in page.frames)
        return set(scan(html + " " + frames + " " + " ".join(net)))
    except Exception:
        return set()


async def detect(browser, domain):
    net = []
    ctx = await browser.new_context(user_agent=(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"))
    page = await ctx.new_page()
    page.on("request", lambda r: net.append(r.url))
    found = set()
    root = "https://www." + domain + "/"
    try:
        await page.goto(root, timeout=25000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        found |= set(scan(await page.content() + " " + " ".join(net)))
        hrefs = await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        care = [h for h in hrefs if re.search(r'career|/job|apply|opening|talent', h, re.I)]
    except Exception:
        care = []
    urls = care[:4] + ["https://www." + domain + p for p in CAREER_PATHS]
    seen = {root}
    for u in urls:
        if "JobDiva" in found:
            break
        if u in seen:
            continue
        seen.add(u)
        net.clear()
        found |= await check_url(page, u, net)
    await ctx.close()
    other = [a for a in found if a not in ("JobDiva", "Shazamme")]
    return domain, ("JobDiva" in found), ",".join(sorted(other))


async def main():
    results = {}
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        sem = asyncio.Semaphore(4)

        async def guarded(d):
            async with sem:
                try:
                    return await asyncio.wait_for(detect(browser, d), timeout=120)
                except Exception as e:
                    return d, False, f"ERR:{type(e).__name__}"
        for coro in asyncio.as_completed([guarded(d) for d in UNKNOWNS]):
            dom, jd, other = await coro
            results[dom] = (jd, other)
            print(f"{'JD' if jd else '  '} {dom:24} {other or '—'}", flush=True)
        await browser.close()
    import csv
    with open(os.path.join(SP, "ats_headless.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["site", "jobdiva", "other_ats"])
        for d in UNKNOWNS:
            jd, other = results.get(d, (False, "MISS"))
            w.writerow([d, jd, other])
    jd = [d for d in UNKNOWNS if results.get(d, (False,))[0]]
    print(f"\n=== headless JobDiva: {len(jd)}/{len(UNKNOWNS)} === {jd}")


asyncio.run(main())
