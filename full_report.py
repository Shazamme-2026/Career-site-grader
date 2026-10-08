"""
Server-rendered technical "Website Grade Report" — the full on-screen report as
a consistent A4 PDF: every pillar, every check, Core Web Vitals, competitor
benchmark, recommendations, Shazamme advantage, coverage. Same brand and
renderer as the client report (client_report.render_pdf).
"""

import html as _html
import os
from datetime import date

PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL',
                                 'https://career-site-grader-production.up.railway.app')
MAX_ITEMS = 8


def _e(v) -> str:
    return _html.escape(str(v if v is not None else ''), quote=True)


def _colour(score) -> str:
    try:
        s = float(score)
    except (TypeError, ValueError):
        return '#64748b'
    if s >= 85: return '#059669'
    if s >= 65: return '#0891b2'
    if s >= 45: return '#d97706'
    return '#e11d48'


def _safe_colour(c) -> str:
    c = str(c or '')
    return c if len(c) == 7 and c.startswith('#') and all(ch in '0123456789abcdefABCDEF' for ch in c[1:]) else '#6366f1'


_STATUS = {'pass': ('✓', '#059669', 'Pass'), 'warn': ('!', '#d97706', 'Needs work'),
           'fail': ('✕', '#e11d48', 'Fail')}
_PRIORITY = {'critical': '#e11d48', 'high': '#d97706', 'medium': '#0891b2', 'low': '#64748b'}
_RATING = {'FAST': ('Good', '#059669'), 'AVERAGE': ('Needs work', '#d97706'), 'SLOW': ('Poor', '#e11d48')}

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Inter', system-ui, -apple-system, sans-serif; color: #0f172a; font-size: 11px;
       line-height: 1.5; background: #fff; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
h1 { font-size: 28px; font-weight: 800; letter-spacing: -.02em; line-height: 1.15; }
h2 { font-size: 17px; font-weight: 800; letter-spacing: -.01em; margin: 0 0 10px; padding-top: 6px;
     border-top: 2px solid #ede9fe; }
h3 { font-size: 12.5px; font-weight: 700; }
p { color: #334155; }
.muted { color: #64748b; }
.brand { font-weight: 900; font-size: 14px; letter-spacing: -.02em;
         background: linear-gradient(120deg, #6d28d9, #ec2baf 55%, #0891b2);
         -webkit-background-clip: text; background-clip: text; color: transparent; }
.topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; font-size: 10px; color: #64748b; }
.logo { height: 34px; max-width: 160px; object-fit: contain; margin-bottom: 14px; }
.kicker { font-size: 10px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: #6d28d9; margin-bottom: 4px; }
.sub { font-size: 12px; color: #475569; margin: 6px 0 16px; }
.hero { display: grid; grid-template-columns: 130px 1fr; gap: 20px; align-items: center; padding: 18px 22px; border-radius: 16px;
        background: linear-gradient(135deg, #f5f3ff, #fdf2f8 60%, #ecfeff); border: 1px solid rgba(15,23,42,.08); margin-bottom: 14px; }
.big { font-size: 58px; font-weight: 900; line-height: 1; letter-spacing: -.04em; white-space: nowrap; }
.big small { font-size: 16px; font-weight: 700; color: #64748b; letter-spacing: 0; }
.label { font-size: 16px; font-weight: 800; margin-bottom: 4px; }
.pills { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.pill { font-size: 10px; font-weight: 600; padding: 3px 9px; border-radius: 999px; background: #fff; border: 1px solid rgba(15,23,42,.1); color: #334155; }
.section { margin-top: 18px; break-inside: avoid-page; }
.section.flow { break-inside: auto; }
.card { border: 1px solid rgba(15,23,42,.1); border-radius: 12px; padding: 12px 14px; margin-bottom: 10px; break-inside: avoid; }
.verdict { font-size: 12.5px; color: #0f172a; margin-bottom: 8px; }
.opp { display: grid; grid-template-columns: 22px 1fr; gap: 8px; padding: 7px 0; border-top: 1px solid rgba(15,23,42,.07); }
.opp .n { width: 20px; height: 20px; border-radius: 6px; background: linear-gradient(135deg,#7c3aed,#ec2baf); color: #fff; font-weight: 800; font-size: 11px; display: flex; align-items: center; justify-content: center; }
.opp .t { font-weight: 700; }
.opp .pl { font-size: 9.5px; color: #6d28d9; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; margin-left: 6px; }
.fix { color: #334155; margin-top: 2px; }
.fix b { color: #0f172a; }
table { width: 100%; border-collapse: collapse; font-size: 10.5px; }
th, td { padding: 5px 8px; border-bottom: 1px solid rgba(15,23,42,.08); text-align: left; vertical-align: top; }
th { font-size: 9.5px; text-transform: uppercase; letter-spacing: .06em; color: #64748b; font-weight: 700; }
td.num, th.num { text-align: right; white-space: nowrap; }
tr.you td { background: #f5f3ff; }
td.best { font-weight: 800; color: #059669; }
.bar { height: 7px; background: #f1f5f9; border-radius: 999px; overflow: hidden; min-width: 90px; }
.bar i { display: block; height: 100%; border-radius: 999px; }
.pillar { break-inside: avoid-page; margin-bottom: 12px; }
.pillar-head { display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: center; padding: 9px 12px; border-radius: 10px 10px 0 0;
               background: #f8fafc; border: 1px solid rgba(15,23,42,.1); border-bottom: none; }
.pillar-head h3 { font-size: 13px; }
.pillar-head .s { font-size: 20px; font-weight: 900; }
.pillar-head .g { font-size: 10px; font-weight: 700; margin-left: 4px; }
.checks { border: 1px solid rgba(15,23,42,.1); border-radius: 0 0 10px 10px; }
.check { display: grid; grid-template-columns: 18px 1fr auto; gap: 8px; padding: 6px 12px; border-top: 1px solid rgba(15,23,42,.06); break-inside: avoid; }
.check:first-child { border-top: none; }
.check .ic { width: 16px; height: 16px; border-radius: 50%; color: #fff; font-size: 9px; font-weight: 900; display: flex; align-items: center; justify-content: center; margin-top: 2px; }
.check .nm { font-weight: 700; }
.check .dt { color: #475569; }
.check .val { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 9.5px; color: #64748b; background: #f8fafc; border: 1px solid rgba(15,23,42,.08); border-radius: 4px; padding: 1px 5px; display: inline-block; margin-top: 2px; max-width: 150mm; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.check ul { padding-left: 14px; color: #475569; font-size: 10px; margin-top: 2px; }
.check .help { margin-top: 3px; padding: 5px 8px; border-radius: 6px; background: #f5f3ff; color: #3b2a6b; font-size: 10px; }
.check .sc { font-weight: 700; color: #64748b; white-space: nowrap; }
.rec { display: grid; grid-template-columns: 58px 1fr; gap: 10px; padding: 9px 0; border-top: 1px solid rgba(15,23,42,.08); break-inside: avoid; }
.rec .pr { font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; color: #fff; border-radius: 6px; padding: 3px 0; text-align: center; height: fit-content; }
.rec .ck { font-weight: 700; font-size: 12px; }
.rec .pl { font-size: 9.5px; font-weight: 700; padding: 1px 7px; border-radius: 999px; margin-left: 6px; }
.rec .dt { color: #475569; }
.rec .im { color: #334155; margin-top: 2px; }
.rec .im b, .rec .fx b { color: #0f172a; }
.rec .fx { margin-top: 2px; padding: 5px 8px; border-radius: 6px; background: #f5f3ff; }
.rec .ev { font-size: 10px; color: #64748b; margin-top: 2px; }
.rec .ln { font-size: 10px; color: #6d28d9; margin-top: 2px; }
.cwv { display: grid; grid-template-columns: 110px 1fr; gap: 14px; align-items: start; }
.cwv .score { font-size: 40px; font-weight: 900; line-height: 1; letter-spacing: -.04em; }
.cwv .score small { font-size: 10px; display: block; color: #64748b; font-weight: 600; letter-spacing: 0; }
.metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.metric { border: 1px solid rgba(15,23,42,.08); border-radius: 8px; padding: 6px 8px; }
.metric .k { font-size: 9.5px; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
.metric .v { font-size: 14px; font-weight: 800; }
.metric .r { font-size: 9.5px; font-weight: 700; }
.adv { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.adv .card { margin: 0; }
.adv .gap { font-size: 9.5px; color: #e11d48; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }
.adv .st { font-weight: 800; color: #059669; margin-top: 3px; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.foot { margin-top: 16px; font-size: 9.5px; color: #94a3b8; }
"""


def _items_html(items):
    items = [str(i) for i in (items or []) if i is not None]
    if not items:
        return ''
    shown = ''.join(f'<li>{_e(i)}</li>' for i in items[:MAX_ITEMS])
    more = f'<li class="muted">+{len(items) - MAX_ITEMS} more</li>' if len(items) > MAX_ITEMS else ''
    return f'<ul>{shown}{more}</ul>'


def _hero(report, logo_src):
    score = int(report.get('overall_score') or 0)
    c = _colour(score)
    bench = report.get('benchmark') or {}
    auth = report.get('authority') or {}
    hist = report.get('history') or []
    plat = (report.get('platform') or {}).get('platform')
    pills = []
    if bench.get('ready'):
        pills.append(f'Beats <b>{int(bench.get("beats_pct") or 0)}%</b> of {int(bench.get("sample") or 0):,} graded sites')
        pills.append(f'Category average {int(bench.get("average") or 0)}')
    if auth.get('rank') is not None or auth.get('referring_domains') is not None:
        parts = []
        if auth.get('rank') is not None: parts.append(f'rank {int(auth["rank"])}')
        if auth.get('referring_domains') is not None: parts.append(f'{int(auth["referring_domains"]):,} referring domains')
        if auth.get('backlinks') is not None: parts.append(f'{int(auth["backlinks"]):,} backlinks')
        pills.append('Authority: ' + ' · '.join(parts))
    if len(hist) >= 2:
        delta = int(hist[-1].get('overall', 0)) - int(hist[0].get('overall', 0))
        pills.append(f'{"▲ +" if delta > 0 else "▼ " if delta < 0 else "–"}{delta if delta else ""} over {len(hist)} scans'.replace('– over', 'No change over'))
    if plat:
        pills.append(f'Platform: {_e(plat)}')
    pills_html = ''.join(f'<span class="pill">{p}</span>' for p in pills)
    logo = f'<img class="logo" src="{_e(logo_src)}" alt="">' if logo_src else ''
    mode = {'recruitment': 'Recruitment agency', 'career_site': 'Career site', 'general': 'Website'}.get(report.get('mode'), 'Website')
    return f"""
  {logo}
  <div class="kicker">{_e(mode)} grade report</div>
  <h1>{_e(report.get('domain') or report.get('url') or '')}</h1>
  <div class="sub">{_e(report.get('url') or '')} · graded {date.today().strftime('%-d %B %Y')}</div>
  <div class="hero">
    <div class="big" style="color:{c}">{score}<small> / 100</small></div>
    <div>
      <div class="label" style="color:{c}">{_e(report.get('grade') or '')} · {_e(report.get('grade_label') or '')}</div>
      <div class="pills">{pills_html}</div>
    </div>
  </div>"""


def _exec(report):
    es = report.get('executive_summary') or {}
    if not es:
        return ''
    opps = ''.join(
        f'<div class="opp"><div class="n">{i + 1}</div><div><span class="t">{_e(o.get("title"))}</span>'
        f'<span class="pl">{_e(o.get("pillar"))}</span><div class="muted">{_e(o.get("why_it_matters"))}</div>'
        f'<div class="fix"><b>How to fix:</b> {_e(o.get("how_to_fix"))}</div></div></div>'
        for i, o in enumerate(es.get('top_opportunities') or []))
    strengths = ' · '.join(_e(s) for s in (es.get('strengths') or []))
    return f"""
  <div class="section"><h2>Executive Summary</h2><div class="card">
    <div class="verdict">{_e(es.get('verdict'))}</div>
    {f'<div class="muted"><b>Working well:</b> {strengths}</div>' if strengths else ''}
    <h3 style="margin-top:8px">Top opportunities to fix first</h3>{opps}
  </div></div>"""


def _pillar_table(report):
    rows = ''
    for p in (report.get('pillars') or {}).values():
        s = int(p.get('score') or 0); c = _colour(s)
        rows += (f'<tr><td><b>{_e(p.get("name"))}</b><div class="muted">{_e(p.get("summary"))}</div></td>'
                 f'<td><div class="bar"><i style="width:{s}%;background:{_safe_colour(p.get("color"))}"></i></div></td>'
                 f'<td class="num" style="color:{c}"><b>{s}</b> {_e(p.get("grade"))}</td>'
                 f'<td class="num muted">{len(p.get("checks") or [])} checks</td></tr>')
    if not rows:
        return ''
    return f'<div class="section"><h2>Pillar Scores</h2><table><thead><tr><th>Pillar</th><th></th><th class="num">Score</th><th class="num"></th></tr></thead><tbody>{rows}</tbody></table></div>'


def _comparison(report):
    comp = report.get('comparison') or {}
    target, comps = comp.get('target'), comp.get('competitors') or []
    if not target or not comps:
        return ''
    keys = list((report.get('pillars') or {}).keys())
    names = {k: (report['pillars'][k].get('name') or k).split(' ')[0] for k in keys}
    rows_src = [target] + comps
    best = {k: max([(r.get('pillars') or {}).get(k) or 0 for r in rows_src if not r.get('error')] or [0]) for k in keys}
    best_overall = max([r.get('overall_score') or 0 for r in rows_src if not r.get('error')] or [0])
    head = ''.join(f'<th class="num">{_e(names[k])}</th>' for k in keys)
    body = ''
    for i, r in enumerate(rows_src):
        you = ' class="you"' if i == 0 else ''
        name = f'<b>{_e(r.get("domain"))} (you)</b>' if i == 0 else _e(r.get('domain') or r.get('url'))
        if r.get('error'):
            body += f'<tr{you}><td>{name}</td><td colspan="{len(keys) + 1}" class="muted"><i>Could not analyse: {_e(r["error"])}</i></td></tr>'
            continue
        ov = r.get('overall_score')
        cells = ''.join(
            f'<td class="num{" best" if (r.get("pillars") or {}).get(k) == best[k] and best[k] else ""}" style="color:{_colour((r.get("pillars") or {}).get(k))}">'
            f'{(r.get("pillars") or {}).get(k, "—")}</td>' for k in keys)
        body += (f'<tr{you}><td>{name}</td><td class="num{" best" if ov == best_overall and ov else ""}" style="color:{_colour(ov)}">'
                 f'<b>{ov}</b> {_e(r.get("grade"))}</td>{cells}</tr>')
    rank = (f'<p class="muted" style="margin-bottom:6px">You rank <b>#{int(comp["rank"])}</b> of {int(comp["field_size"])} on overall score. Bold marks the leader in each column.</p>'
            if comp.get('rank') and comp.get('field_size') else '')
    return (f'<div class="section"><h2>Competitor Benchmark</h2>{rank}<table><thead><tr><th>Site</th><th class="num">Overall</th>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


def _cwv_device(d, title):
    perf = d.get('perf_score')
    field, lab = d.get('field') or {}, d.get('lab') or {}
    metrics = ''
    if d.get('has_field'):
        for key, label, fmt in (('lcp', 'LCP', lambda v: f'{v / 1000:.1f}s'), ('inp', 'INP', lambda v: f'{int(v)}ms'),
                                ('cls', 'CLS', lambda v: f'{v:.2f}'), ('fcp', 'FCP', lambda v: f'{v / 1000:.1f}s')):
            m = field.get(key) or {}
            v = m.get('p75'); r = _RATING.get(m.get('rating'), ('—', '#64748b'))
            metrics += (f'<div class="metric"><div class="k">{label} (field)</div><div class="v">{fmt(v) if v is not None else "—"}</div>'
                        f'<div class="r" style="color:{r[1]}">{r[0]}</div></div>')
    for key, label, fmt in (('lcp_ms', 'LCP', lambda v: f'{v / 1000:.1f}s'), ('fcp_ms', 'FCP', lambda v: f'{v / 1000:.1f}s'),
                            ('cls', 'CLS', lambda v: f'{v:.3f}'), ('tbt_ms', 'TBT', lambda v: f'{int(v)}ms'),
                            ('si_ms', 'Speed Index', lambda v: f'{v / 1000:.1f}s'), ('ttfb_ms', 'TTFB', lambda v: f'{int(v)}ms')):
        v = lab.get(key)
        if v is not None:
            metrics += f'<div class="metric"><div class="k">{label} (lab)</div><div class="v">{fmt(float(v))}</div></div>'
    issues = ''
    for i in (d.get('issues') or [])[:MAX_ITEMS]:
        display = f' <span class="muted">{_e(i.get("display"))}</span>' if i.get('display') else ''
        issues += f'<li>{_e(i.get("title"))}{display}</li>'
    issues_html = f'<div style="margin-top:8px"><b>Improvements to raise this score</b><ul style="padding-left:14px;color:#475569">{issues}</ul></div>' if issues else ''
    pc = _colour(perf) if perf is not None else '#64748b'
    runs = f' · {int(d["runs"])} runs' if d.get('runs') else ''
    return (f'<div class="card"><h3 style="margin-bottom:6px">{title}</h3><div class="cwv">'
            f'<div class="score" style="color:{pc}">{perf if perf is not None else "—"}<small>Lighthouse performance{runs}</small></div>'
            f'<div class="metrics">{metrics}</div></div>{issues_html}</div>')


def _cwv(report):
    cwv = report.get('core_web_vitals') or {}
    if cwv.get('perf_score') is None and not cwv.get('has_field'):
        return ''
    html = _cwv_device(cwv, 'Mobile')
    d = cwv.get('desktop') or {}
    if d.get('perf_score') is not None or d.get('has_field'):
        html += _cwv_device(d, 'Desktop')
    return f'<div class="section flow"><h2>Core Web Vitals</h2>{html}</div>'


def _findings(report):
    out = ''
    for p in (report.get('pillars') or {}).values():
        s = int(p.get('score') or 0); c = _colour(s)
        checks = ''
        for ch in p.get('checks') or []:
            ic, col, _ = _STATUS.get(ch.get('status'), ('•', '#64748b', ''))
            val = f'<div class="val">{_e(ch.get("value"))}</div>' if ch.get('value') not in (None, '', 'None') else ''
            help_ = f'<div class="help">{_e(ch.get("help"))}</div>' if ch.get('help') else ''
            checks += (f'<div class="check"><div class="ic" style="background:{col}">{ic}</div><div>'
                       f'<div class="nm">{_e(ch.get("name"))}</div><div class="dt">{_e(ch.get("detail"))}</div>{val}'
                       f'{_items_html(ch.get("items"))}{help_}</div>'
                       f'<div class="sc">{ch.get("score", "")}/{ch.get("max", "")}</div></div>')
        out += (f'<div class="pillar"><div class="pillar-head"><div><h3>{_e(p.get("name"))}</h3>'
                f'<div class="muted">{_e(p.get("summary"))} · {len(p.get("checks") or [])} checks</div></div>'
                f'<div><span class="s" style="color:{c}">{s}</span><span class="g" style="color:{c}">{_e(p.get("grade"))}</span></div></div>'
                f'<div class="checks">{checks or "<div class=check><div></div><div class=muted>No checks recorded.</div></div>"}</div></div>')
    return f'<div class="section flow"><h2>Detailed Findings</h2>{out}</div>' if out else ''


def _recs(report):
    recs = report.get('recommendations') or []
    if not recs:
        return '<div class="section"><h2>Priority Recommendations</h2><p class="muted">No critical issues found.</p></div>'
    rows = ''
    for r in recs:
        pc = _PRIORITY.get(r.get('priority'), '#64748b'); plc = _safe_colour(r.get('pillar_color'))
        score = f' <span class="muted">{r["score"]}/{r["max"]}</span>' if r.get('score') is not None and r.get('max') else ''
        links = ' · '.join(f'{_e(l.get("label"))}: {_e(l.get("url"))}' for l in (r.get('links') or []) if isinstance(l, dict))
        evidence = f'<div class="ev">Detected: {_e(r["value"])}</div>' if r.get('value') else ''
        fix = f'<div class="fx"><b>How to fix:</b> {_e(r["how_to_fix"])}</div>' if r.get('how_to_fix') else ''
        links_html = f'<div class="ln">{links}</div>' if links else ''
        rows += (f'<div class="rec"><div class="pr" style="background:{pc}">{_e(r.get("priority"))}</div><div>'
                 f'<div class="ck">{_e(r.get("check"))}{score}<span class="pl" style="background:{plc}1a;color:{plc}">{_e(r.get("pillar"))}</span></div>'
                 f'<div class="dt">{_e(r.get("detail"))}</div>{evidence}{_items_html(r.get("items"))}'
                 f'<div class="im"><b>Why it matters:</b> {_e(r.get("impact"))}</div>{fix}{links_html}</div></div>')
    return f'<div class="section flow"><h2>Priority Recommendations</h2>{rows}</div>'


def _advantage(report):
    items = report.get('shazamme_advantage') or []
    if not items:
        return ''
    cards = ''.join(f'<div class="card"><div class="gap">{_e(a.get("gap"))}</div><h3>{_e(a.get("feature"))}</h3>'
                    f'<p>{_e(a.get("description"))}</p><div class="st">{_e(a.get("stat"))}</div></div>' for a in items)
    return f'<div class="section"><h2>Shazamme Advantage</h2><div class="adv">{cards}</div></div>'


def _coverage(report, link):
    cov = report.get('coverage') or {}
    ts = report.get('tech_stack_summary') or {}
    pages = report.get('pages_scanned') or []
    facts = []
    if cov.get('content_pages') is not None: facts.append(f'{int(cov["content_pages"])} content pages analysed' + (f' of {int(cov["total_pages"])} discovered' if cov.get('total_pages') else '') + (' (crawl capped)' if cov.get('crawl_capped') else ''))
    if cov.get('job_pages') is not None: facts.append(f'{int(cov["job_pages"])} job pages found')
    if cov.get('h1_missing'): facts.append(f'{len(cov["h1_missing"])} pages missing an H1')
    dh = cov.get('duplicate_headings') or {}
    if dh.get('cross_page') or dh.get('same_page'): facts.append(f'{len(dh.get("cross_page") or [])} headings duplicated across pages, {len(dh.get("same_page") or [])} within a page')
    if report.get('response_time') is not None: facts.append(f'Homepage responded in {float(report["response_time"]):.2f}s (HTTP {_e(report.get("status_code"))})')
    if report.get('word_count'): facts.append(f'{int(report["word_count"]):,} words on the homepage')
    facts_html = ''.join(f'<li>{f}</li>' for f in facts)
    pages_html = ', '.join(_e(p) for p in pages[:12]) + (f' +{len(pages) - 12} more' if len(pages) > 12 else '')
    tech = f'<div class="card"><h3>{_e(ts.get("headline"))}</h3><p>{_e(ts.get("body"))}</p></div>' if ts.get('headline') else ''
    return f"""
  <div class="section"><h2>Coverage &amp; Method</h2>
    <div class="two"><div class="card"><h3>What was analysed</h3><ul style="padding-left:14px;color:#475569">{facts_html}</ul>
      <p class="muted" style="margin-top:4px"><b>Pages scanned:</b> {pages_html}</p></div>{tech or '<div></div>'}</div>
    <div class="foot">Scores are weighted across the pillars above; methodology at {_e(PUBLIC_BASE_URL)}/methodology ·
      Live report: {_e(link)} · Generated by the Shazamme Website Grader, {date.today().strftime('%-d %B %Y')}</div>
  </div>"""


def build_html(report: dict, logo_src: str = None) -> str:
    report_id = report.get('report_id') or ''
    link = f'{PUBLIC_BASE_URL}/r/{report_id}' if report_id else PUBLIC_BASE_URL
    domain = report.get('domain') or report.get('url') or ''
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Website Grade Report · {_e(domain)}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>{_CSS}</style></head><body>
<div class="topbar"><span class="brand">shazamme</span><span>Website Grade Report · {_e(domain)}</span></div>
{_hero(report, logo_src)}
{_exec(report)}
{_pillar_table(report)}
{_comparison(report)}
{_cwv(report)}
{_findings(report)}
{_recs(report)}
{_advantage(report)}
{_coverage(report, link)}
</body></html>"""


FOOTER_TEMPLATE = (
    '<div style="width:100%;font-family:Inter,system-ui,sans-serif;font-size:8px;color:#94a3b8;'
    'padding:0 14mm;display:flex;justify-content:space-between">'
    '<span>Shazamme Website Grader · webgrader.shazamme.com</span>'
    '<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>')


def render_pdf(html: str) -> bytes:
    from client_report import render_pdf as _render
    return _render(html, margin={'top': '14mm', 'right': '12mm', 'bottom': '16mm', 'left': '12mm'},
                   footer_template=FOOTER_TEMPLATE)
