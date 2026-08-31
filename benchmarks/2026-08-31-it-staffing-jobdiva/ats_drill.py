import asyncio, os, re, sys
from playwright.async_api import async_playwright

SP = os.path.dirname(os.path.abspath(__file__))
_arg = sys.argv[1] if len(sys.argv) > 1 else ""
if _arg and os.path.isfile(_arg):
    UNKNOWNS = [l.strip() for l in open(_arg) if l.strip()]
else:
    UNKNOWNS = sys.argv[1:]

CAREER_PATHS = ["/careers", "/jobs", "/job-search", "/search-jobs", "/careers/jobs",
                "/careers/job-search", "/job-openings", "/candidates", "/find-a-job",
                "/current-openings", "/open-positions", "/careers/current-openings",
                "/careers/open-positions", "/join-us", "/work-with-us"]

ATS = {
    "JobDiva": r"jobdiva|divainit|jdcloud|www1\.jobdiva",
    "Bullhorn": r"bullhorn|bhcloud|bullhornstaffing|talentrackr",
    "Ceipal": r"ceipal",
    "Workday": r"myworkdayjobs|workdayjobs|wd\d+\.myworkday",
    "Greenhouse": r"greenhouse\.io|boards\.greenhouse|grnhse",
    "Lever": r"jobs\.lever\.co|lever\.co/",
    "iCIMS": r"icims\.com",
    "SmartRecruiters": r"smartrecruiters",
    "Jobvite": r"jobvite",
    "JazzHR": r"applytojob|jazzhr",
    "Workable": r"workable\.com|apply\.workable",
    "ADP": r"workforcenow\.adp|recruiting\.adp|myjobs\.adp",
    "Taleo": r"taleo\.net|tbe\.taleo",
    "SuccessFactors": r"successfactors|sfcareers|jobs\.sap",
    "Ashby": r"ashbyhq",
    "Recruitee": r"recruitee",
    "Avionte": r"avionte|myavionte",
    "Sense": r"sensehq",
    "Crelate": r"crelate",
    "JobScore": r"jobscore",
    "BambooHR": r"bamboohr",
    "UKG": r"ultipro|ukg\.com|\.ulti\.",
    "Oracle": r"oraclecloud.*hcm|oraclerecruiting",
    "Zoho Recruit": r"zohorecruit|recruit\.zoho",
    "Shazamme": r"shazamme",
}
JOB_HREF = re.compile(r'job|/req|position|opening|vacan|apply|career.*\d|/id[=/]?\d', re.I)


def scan(text):
    low = text.lower()
    return {n for n, p in ATS.items() if re.search(p, low)}


async def harvest(page):
    try:
        return await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    except Exception:
        return []


async def snapshot(page, net):
    try:
        html = await page.content()
    except Exception:
        html = ""
    frames = " ".join(f.url for f in page.frames)
    return scan(html + " " + frames + " " + " ".join(net))


async def detect(browser, domain):
    net = []
    ctx = await browser.new_context(user_agent=(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"))
    ctx.set_default_timeout(22000)
    page = await ctx.new_page()
    page.on("request", lambda r: net.append(r.url))
    page.on("popup", lambda p: net.append("POPUP:" + p.url))
    found = set()
    root = "https://www." + domain + "/"
    career_links = []
    try:
        await page.goto(root, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        found |= await snapshot(page, net)
        hrefs = await harvest(page)
        career_links = [h for h in hrefs if re.search(r'career|/job|opening|talent|join', h, re.I)]
    except Exception:
        pass
    candidates = career_links[:5] + ["https://www." + domain + p for p in CAREER_PATHS]
    seen = {root}
    job_links = []
    for u in candidates:
        if found - {"Shazamme"}:
            break
        if u in seen:
            continue
        seen.add(u)
        net.clear()
        try:
            await page.goto(u, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
        except Exception:
            continue
        found |= await snapshot(page, net)
        hrefs = await harvest(page)
        job_links += [h for h in hrefs if JOB_HREF.search(h) and h not in seen]
    for j in job_links[:6]:
        if found - {"Shazamme"}:
            break
        if j in seen:
            continue
        seen.add(j)
        net.clear()
        try:
            await page.goto(j, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
        except Exception:
            continue
        found |= await snapshot(page, net)
        try:
            btn = page.locator("a,button", has_text=re.compile("apply", re.I)).first
            if await btn.count():
                async with page.expect_navigation(wait_until="domcontentloaded", timeout=8000):
                    await btn.click()
                await page.wait_for_timeout(2500)
                found |= await snapshot(page, net)
        except Exception:
            found |= scan(" ".join(net))
    await ctx.close()
    other = sorted(a for a in found if a not in ("JobDiva", "Shazamme"))
    return domain, ("JobDiva" in found), ",".join(other)


async def main():
    results = {}
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        sem = asyncio.Semaphore(4)

        async def guarded(d):
            async with sem:
                try:
                    return await asyncio.wait_for(detect(browser, d), timeout=180)
                except Exception as e:
                    return d, False, f"ERR:{type(e).__name__}"
        for coro in asyncio.as_completed([guarded(d) for d in UNKNOWNS]):
            dom, jd, other = await coro
            results[dom] = (jd, other)
            tag = "JobDiva" if jd else (other or "—")
            print(f"{'JD' if jd else '  '} {dom:22} {tag}", flush=True)
        await browser.close()
    import csv
    with open(os.path.join(SP, "ats_drill.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["site", "jobdiva", "other_ats"])
        for d in UNKNOWNS:
            jd, other = results.get(d, (False, "MISS"))
            w.writerow([d, jd, other])
    jd = [d for d in UNKNOWNS if results.get(d, (False,))[0]]
    print(f"\n=== drill JobDiva: {len(jd)}/{len(UNKNOWNS)} === {jd}")


asyncio.run(main())
