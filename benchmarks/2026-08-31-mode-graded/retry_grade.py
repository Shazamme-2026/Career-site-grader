import asyncio, csv, json, os, sys, time
REPO = "/Users/rickmare/Code/career-site-grader"
sys.path.insert(0, REPO); os.chdir(REPO)
os.environ.setdefault("PSI_RUNS", "1")
import grader  # noqa
SP = "/private/tmp/claude-501/-Users-rickmare-Code/7347f4fd-d2a1-46a7-a9fa-8bed88d085d5/scratchpad/run2"
OUTDIR = os.path.join(SP, "reports"); os.makedirs(OUTDIR, exist_ok=True)
PILLARS = ["seo","geo","cx","brand","technical","conversion"]

FAILS = [
    ("recruitment","Staffing Futures","","https://www.avidtr.com/",""),
    ("recruitment","Staffing Futures","","https://kofi-group.com/",""),
    ("recruitment","Shazamme","","https://www.aspectpersonnel.com.au/",""),
    ("career_site","","SuccessFactors","https://www.bhp.com/careers/global-careers/careers-in-australia",""),
    ("career_site","Shazamme","SmartRecruiters","https://www.jobs.sutherlandglobal.com/","Link out apply"),
    ("career_site","Shazamme","Workday","https://www.careers.tollgroup.com/","workday jb"),
]

def slug(u):
    return u.replace("https://","").replace("http://","").replace("www.","").strip("/").replace("/","_")

async def one(mode, prov, ats, url, notes):
    sg = slug(url); t0=time.time()
    for attempt in (1,2):
        final=None; last=None
        try:
            g = grader.CareerSiteGrader(url, mode=mode)
            async def run():
                nonlocal final,last
                async for ev in g.grade():
                    last=ev
                    if ev.get("type")=="complete": final=ev
            await asyncio.wait_for(run(), timeout=360)
            if final:
                json.dump(final, open(os.path.join(OUTDIR,f"{sg}.json"),"w"))
                rec={"slug":sg,"mode":mode,"provider":prov,"ats":ats,"url":url,"notes":notes,
                     "overall":final.get("overall_score"),"grade":final.get("grade"),
                     "platform":final.get("platform",""),"status":final.get("status_code",""),
                     "resp_s":final.get("response_time","")}
                for p in PILLARS: rec[p]=(final.get("pillars",{}).get(p) or {}).get("score","")
                print(f"<<< DONE {mode:11} {url} overall={rec['overall']} grade={rec['grade']} (att{attempt}, {round(time.time()-t0)}s)",flush=True)
                return rec
            else:
                print(f"... att{attempt} {url} ended on type={last.get('type') if last else None} msg={str(last.get('message','') if last else '')[:120]}",flush=True)
        except Exception as e:
            print(f"... att{attempt} {url} EXC {type(e).__name__}: {str(e)[:120]}",flush=True)
        await asyncio.sleep(3)
    print(f"!!! FAIL {mode:11} {url}",flush=True)
    return {"slug":sg,"mode":mode,"provider":prov,"ats":ats,"url":url,"notes":notes,
            "overall":"","grade":"FAIL","platform":"","status":"","resp_s":"",**{p:"" for p in PILLARS}}

async def main():
    out=[]
    for row in FAILS:
        out.append(await one(*row))
    cols=["slug","mode","provider","ats","url","overall","grade",*PILLARS,"platform","status","resp_s","notes"]
    with open(os.path.join(SP,"results_retry.csv"),"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore"); w.writeheader()
        for r in out: w.writerow(r)
    print(f"=== RETRY DONE {sum(1 for r in out if r['grade']!='FAIL')}/{len(out)} ===",flush=True)

asyncio.run(main())
