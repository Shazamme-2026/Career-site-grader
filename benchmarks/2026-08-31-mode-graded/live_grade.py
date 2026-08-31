import json, sys, time, urllib.parse, urllib.request

BASE = "https://webgrader.shazamme.com/grade"
TARGETS = [
    ("recruitment","Staffing Futures","","https://www.avidtr.com/",""),
    ("recruitment","Staffing Futures","","https://kofi-group.com/",""),
    ("recruitment","Shazamme","","https://www.aspectpersonnel.com.au/",""),
    ("career_site","","SuccessFactors","https://www.bhp.com/careers/global-careers/careers-in-australia",""),
    ("career_site","Shazamme","SmartRecruiters","https://www.jobs.sutherlandglobal.com/","Link out apply"),
    ("career_site","Shazamme","SmartRecruiters","https://jobs.sutherlandglobal.com/","no-www"),
    ("career_site","Shazamme","Workday","https://www.careers.tollgroup.com/","workday jb"),
    ("career_site","Shazamme","Workday","https://careers.tollgroup.com/","no-www"),
]
PILL=["seo","geo","cx","brand","technical","conversion"]

def grade(mode,url):
    q=urllib.parse.urlencode({"url":url,"mode":mode})
    req=urllib.request.Request(BASE+"?"+q, headers={"Accept":"text/event-stream"})
    final=None; last_err=None
    with urllib.request.urlopen(req, timeout=240) as r:
        for raw in r:
            line=raw.decode("utf-8","ignore").strip()
            if not line.startswith("data:"): continue
            try: ev=json.loads(line[5:].strip())
            except: continue
            t=ev.get("type")
            if t=="complete": final=ev
            elif t=="error": last_err=ev.get("message","")
    return final,last_err

for mode,prov,ats,url,notes in TARGETS:
    t0=time.time()
    try:
        final,err=grade(mode,url)
    except Exception as e:
        final,err=None,f"{type(e).__name__}: {e}"
    dt=round(time.time()-t0)
    if final:
        pil={k:(final.get("pillars",{}).get(k) or {}).get("score") for k in PILL}
        plat=final.get("platform"); plat=plat.get("platform") if isinstance(plat,dict) else plat
        print(f"OK   {url}  overall={final.get('overall_score')} grade={final.get('grade')} plat={plat} pillars={pil} ({dt}s)",flush=True)
    else:
        print(f"FAIL {url}  {str(err)[:110]} ({dt}s)",flush=True)
