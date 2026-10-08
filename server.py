import asyncio
import json
import os
import queue
import threading
import re
import time
import secrets
import sys
from collections import defaultdict, deque
from flask import Flask, request, Response, send_from_directory, jsonify
from grader import CareerSiteGrader
import db
import emailer
import client_report
import full_report
import competitors

app = Flask(__name__, static_folder='public')
db.init_db()

VALID_MODES = ('recruitment', 'career_site', 'general')
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL',
                                 'https://career-site-grader-production.up.railway.app')

# --- Simple in-memory per-IP rate limiting (per worker) ---
_rl = defaultdict(deque)
_rl_lock = threading.Lock()


def _client_ip():
    fwd = request.headers.get('X-Forwarded-For', '')
    return fwd.split(',')[0].strip() if fwd else (request.remote_addr or 'unknown')


def _rate_ok(bucket: str, limit: int, window: int = 3600) -> bool:
    now = time.time()
    key = f'{bucket}:{_client_ip()}'
    with _rl_lock:
        dq = _rl[key]
        while dq and dq[0] < now - window:
            dq.popleft()
        if not dq and key in _rl and len(dq) == 0:
            pass
        if len(dq) >= limit:
            return False
        dq.append(now)
        # opportunistic cleanup so spoofed-IP keys don't accumulate forever
        if len(_rl) > 5000:
            for k in [k for k, d in list(_rl.items()) if not d or d[-1] < now - window]:
                _rl.pop(k, None)
        return True


def _target_host(url: str) -> str:
    from urllib.parse import urlparse as _up
    u = url if url.lower().startswith(('http://', 'https://')) else 'https://' + url
    try:
        return _up(u).hostname or ''
    except ValueError:
        return ''


def _report_link(report_id):
    return f'{PUBLIC_BASE_URL}/r/{report_id}' if report_id else PUBLIC_BASE_URL


def _admin_token():
    return os.environ.get('ADMIN_TOKEN', '') or os.environ.get('CRON_TOKEN', '')


def _bypass_requested():
    """Super-admin cache bypass: ?fresh=1&token=ADMIN_TOKEN (or CRON_TOKEN)."""
    if request.args.get('fresh', '') not in ('1', 'true', 'yes'):
        return False
    tok = (request.args.get('token') or '').strip()
    expected = _admin_token()
    return bool(expected) and secrets.compare_digest(tok, expected)


def _pillar_scores(complete_event):
    return {k: v['score'] for k, v in complete_event.get('pillars', {}).items()}


def _persist_and_enrich(event, fallback_url, mode, bypass=False):
    """Save the grade, attach benchmark, and cache / restore Core Web Vitals.
    Best-effort: never raises into the grading path."""
    domain = event.get('domain', '')
    graded_url = event.get('url', fallback_url)
    try:
        prior = db.history(domain, mode)
        db.save_grade(graded_url, domain, mode, event.get('overall_score', 0),
                      event.get('grade', ''), _pillar_scores(event))
        bench = db.percentile(mode, event.get('overall_score', 0), event.get('domain', ''))
        if bench:
            event['benchmark'] = bench
        if prior:
            event['history'] = prior
    except Exception:
        pass
    # Core Web Vitals: cache a good result, or fall back to the last good one.
    try:
        cwv = event.get('core_web_vitals')
        if cwv and cwv.get('perf_score') is not None:
            db.save_cwv(graded_url, mode, cwv)
        elif event.get('cwv_attempted') and not bypass:
            cached = db.get_cwv(graded_url, mode)
            if cached:
                event['core_web_vitals'] = cached
    except Exception:
        pass
    if not event.get('report_id'):
        event['report_id'] = secrets.token_urlsafe(8)
    if not event.get('_owner'):
        event['_owner'] = secrets.token_urlsafe(16)  # lets the grader change the comparison later
    return event


def _public(report):
    """Stored report without server-only fields."""
    return {k: v for k, v in (report or {}).items() if not k.startswith('_')}


async def _grade_competitor(url: str, mode: str) -> dict:
    """Light grade (no PageSpeed) of a competitor — returns headline + pillar scores."""
    try:
        host = _target_host(url)
        if not host or not competitors.is_public_host(host):
            return {'url': url, 'domain': host, 'error': 'Could not analyse this site'}
        g = CareerSiteGrader(url, mode=mode, light=True)
        final = None
        async for ev in g.grade():
            if ev.get('type') == 'error':
                return {'url': url, 'domain': g.parsed.netloc, 'error': ev.get('message', 'failed')}
            if ev.get('type') == 'complete':
                final = ev
        if not final:
            return {'url': url, 'domain': g.parsed.netloc, 'error': 'no result'}
        return {
            'url': url,
            'domain': final['domain'],
            'overall_score': final['overall_score'],
            'grade': final['grade'],
            'pillars': {k: v['score'] for k, v in final['pillars'].items()},
            'authority': final.get('authority'),
        }
    except Exception as e:
        print(f'[compare] {url}: {type(e).__name__}: {e}', file=sys.stderr, flush=True)
        return {'url': url, 'domain': _target_host(url), 'error': 'Could not analyse this site'}


async def _build_comparison(competitor_urls, mode, target_event) -> dict:
    results = await asyncio.gather(*[_grade_competitor(u, mode) for u in competitor_urls])
    target = {
        'domain': target_event['domain'],
        'overall_score': target_event['overall_score'],
        'grade': target_event['grade'],
        'pillars': {k: v['score'] for k, v in target_event['pillars'].items()},
        'authority': target_event.get('authority'),
    }
    scored = [r for r in results if 'overall_score' in r]
    rank = 1 + sum(1 for r in scored if r['overall_score'] > target['overall_score'])
    return {'target': target, 'competitors': results, 'rank': rank, 'field_size': len(scored) + 1}


def run_grader_in_thread(url: str, mode: str, competitors, q: queue.Queue, bypass=False):
    """Run the async grader in a background thread and push events to queue."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def collect():
        grader = CareerSiteGrader(url, mode=mode, bypass_cache=bypass)
        async for event in grader.grade():
            if event.get('type') == 'complete':
                _persist_and_enrich(event, url, mode, bypass=bypass)
                if competitors:
                    q.put({'type': 'status', 'message': f'Benchmarking against {len(competitors)} competitor(s)...', 'progress': 99})
                    try:
                        event['comparison'] = await _build_comparison(competitors, mode, event)
                    except Exception:
                        pass
                try:
                    db.save_report(event['report_id'], event.get('url', url), mode, event)
                except Exception:
                    pass
            q.put(event)
        q.put(None)  # sentinel

    try:
        loop.run_until_complete(collect())
    except Exception as e:
        q.put({'type': 'error', 'message': str(e)})
        q.put(None)
    finally:
        loop.close()


@app.route('/')
def index():
    return send_from_directory('public', 'index.html')


@app.route('/grade')
def grade():
    url = (request.args.get('url') or '').strip()
    if not url:
        return jsonify({'error': 'URL parameter required'}), 400

    mode = (request.args.get('mode') or '').strip()
    if mode not in VALID_MODES:
        return jsonify({'error': f'mode parameter required. Must be one of: {", ".join(VALID_MODES)}'}), 400

    if not _rate_ok('grade', limit=40):
        return jsonify({'error': 'Rate limit reached — please try again later.'}), 429

    # Optional competitor benchmarking (comma-separated URLs, max 3)
    raw_comp = (request.args.get('competitors') or '').strip()
    competitors_list = competitors.clean_urls(raw_comp.split(','), _target_host(url)) if raw_comp else []

    bypass = _bypass_requested()

    def generate():
        q: queue.Queue = queue.Queue()
        t = threading.Thread(target=run_grader_in_thread, args=(url, mode, competitors_list, q, bypass), daemon=True)
        t.start()

        while True:
            try:
                item = q.get(timeout=120)
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Timeout waiting for analysis'})}\n\n"
                break

            if item is None:
                break

            yield f"data: {json.dumps(item)}\n\n"

        t.join(timeout=5)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*',
        },
    )


@app.route('/health')
def health():
    # Feature flags and the NAMES (never values) of Anthropic-related env vars,
    # so a mis-named or mis-placed key can be diagnosed from outside.
    anthropic_vars = sorted(k for k in os.environ if 'anthropic' in k.lower())
    return jsonify({'status': 'ok', 'service': 'Shazamme Career Site Grader',
                    'ai_finder': competitors.enabled(),
                    'anthropic_env_names': anthropic_vars,
                    'pagespeed': bool(os.environ.get('PAGESPEED_API_KEY')),
                    'email': emailer.enabled()})


def _fetch_image(src: str, max_bytes: int = 3 * 1024 * 1024):
    """SSRF-guarded image fetch. Returns (content_type, bytes) or None."""
    import urllib.request, ipaddress, socket
    from urllib.parse import urlparse as _up
    p = _up(src or '')
    if p.scheme not in ('http', 'https') or not p.hostname:
        return None
    try:
        for info in socket.getaddrinfo(p.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast):
                return None
    except Exception:
        return None

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None  # block redirects (metadata-endpoint SSRF via 30x)
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        req = urllib.request.Request(src, headers={'User-Agent': 'Mozilla/5.0 (ShazammeGrader)'})
        with opener.open(req, timeout=8) as r:
            ctype = (r.headers.get('content-type') or '').split(';')[0].strip()
            if not ctype.startswith('image/'):
                return None
            data = r.read(max_bytes + 1)
        if len(data) > max_bytes:
            return None
        return ctype, data
    except Exception:
        return None


@app.route('/api/logo')
def api_logo():
    """Image proxy so a client's logo always loads and downloads in the report,
    regardless of hotlink protection or CORS on the origin."""
    src = (request.args.get('url') or '').strip()
    if not src:
        return ('', 400)
    fetched = _fetch_image(src)
    if not fetched:
        return ('', 502)
    ctype, data = fetched
    resp = Response(data, mimetype=ctype)
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


_logo_cache = {}
_client_pdf_cache = {}
_client_pdf_locks = {}
_client_pdf_lock = threading.Lock()
_RENDER_SLOTS = int(os.environ.get('CLIENT_PDF_RENDER_SLOTS', '2'))
_render_sem = threading.BoundedSemaphore(_RENDER_SLOTS)


def _bounded_put(cache: dict, key, value, cap: int = 50):
    """FIFO-bounded insert. Caller holds _client_pdf_lock."""
    if len(cache) >= cap:
        cache.pop(next(iter(cache)))
    cache[key] = value


def _logo_data_uri(report_id, report):
    """Client logo as a data URI so the PDF never depends on a third-party host.
    Cached per report so the HTML and PDF routes fetch the origin at most once."""
    import base64
    with _client_pdf_lock:
        if report_id in _logo_cache:
            return _logo_cache[report_id]
    uri = None
    src = (report or {}).get('client_logo')
    fetched = _fetch_image(src) if src else None
    if fetched:
        ctype, data = fetched
        uri = f'data:{ctype};base64,' + base64.b64encode(data).decode('ascii')
    with _client_pdf_lock:
        _bounded_put(_logo_cache, report_id, uri)
    return uri


def _per_report_lock(report_id):
    with _client_pdf_lock:
        lock = _client_pdf_locks.get(report_id)
        if lock is None:
            if len(_client_pdf_locks) >= 200:
                _client_pdf_locks.clear()
            lock = _client_pdf_locks[report_id] = threading.Lock()
        return lock


@app.route('/r/<report_id>/client')
def client_report_html(report_id):
    """Client-facing opportunity report as a print-ready page (fallback when
    server-side PDF rendering is unavailable: the browser's Save as PDF)."""
    report = db.get_report(report_id)
    if not report:
        return jsonify({'error': 'not found'}), 404
    if not _rate_ok('client_html', limit=60):
        return jsonify({'error': 'Rate limit reached — please try again later.'}), 429
    html = client_report.build_html(report, logo_src=_logo_data_uri(report_id, report))
    if request.args.get('print') == '1':
        html = html.replace('</body>', '<script>window.onload=function(){window.print()}</script></body>')
    return Response(html, mimetype='text/html')


_PDF_KINDS = {
    'client': (client_report.build_html, client_report.render_pdf, '-opportunity-report.pdf'),
    'full': (full_report.build_html, full_report.render_pdf, '-grade-report.pdf'),
}


def _serve_pdf(report_id, kind):
    report = db.get_report(report_id)
    if not report:
        return jsonify({'error': 'not found'}), 404
    build, render, suffix = _PDF_KINDS[kind]
    key = (report_id, kind)
    fallback = f'/r/{report_id}/{kind}?print=1'
    with _client_pdf_lock:
        pdf = _client_pdf_cache.get(key)
    if pdf is None:
        if not _rate_ok('client_pdf', limit=30):
            return jsonify({'error': 'Rate limit reached — please try again later.'}), 429
        # Same report: one render, the rest wait and reuse it (no stampede).
        with _per_report_lock(key):
            with _client_pdf_lock:
                pdf = _client_pdf_cache.get(key)
            if pdf is None:
                try:
                    html = build(report, logo_src=_logo_data_uri(report_id, report))
                except Exception as e:
                    print(f'[{kind}_report] build failed for {report_id}: {type(e).__name__}: {e}',
                          file=sys.stderr, flush=True)
                    return jsonify({'error': 'pdf unavailable', 'fallback': fallback}), 503
                # Cap concurrent Chromium processes across the worker.
                if not _render_sem.acquire(timeout=5):
                    return jsonify({'error': 'busy', 'fallback': fallback}), 503
                try:
                    pdf = render(html)
                except Exception as e:
                    print(f'[{kind}_report] pdf render failed for {report_id}: {type(e).__name__}: {e}',
                          file=sys.stderr, flush=True)
                    return jsonify({'error': 'pdf unavailable', 'fallback': fallback}), 503
                finally:
                    _render_sem.release()
                with _client_pdf_lock:
                    _bounded_put(_client_pdf_cache, key, pdf, cap=100)
    resp = Response(pdf, mimetype='application/pdf')
    domain = re.sub(r'[^a-z0-9.-]+', '-', (report.get('domain') or 'website').lower())
    resp.headers['Content-Disposition'] = f'attachment; filename="{domain}{suffix}"'
    resp.headers['Cache-Control'] = 'private, max-age=86400'
    return resp


@app.route('/r/<report_id>/client.pdf')
def client_report_pdf(report_id):
    """Client-facing opportunity report as a downloadable A4 PDF (Chromium)."""
    return _serve_pdf(report_id, 'client')


@app.route('/r/<report_id>/full')
def full_report_html(report_id):
    """Technical report as a print-ready page (fallback when Chromium is unavailable)."""
    report = db.get_report(report_id)
    if not report:
        return jsonify({'error': 'not found'}), 404
    if not _rate_ok('client_html', limit=60):
        return jsonify({'error': 'Rate limit reached — please try again later.'}), 429
    try:
        html = full_report.build_html(report, logo_src=_logo_data_uri(report_id, report))
    except Exception as e:
        print(f'[full_report] build failed for {report_id}: {type(e).__name__}: {e}', file=sys.stderr, flush=True)
        return jsonify({'error': 'report unavailable'}), 500
    if request.args.get('print') == '1':
        html = html.replace('</body>', '<script>window.onload=function(){window.print()}</script></body>')
    return Response(html, mimetype='text/html')


@app.route('/r/<report_id>/full.pdf')
def full_report_pdf(report_id):
    """Full technical report as a downloadable A4 PDF (Chromium)."""
    return _serve_pdf(report_id, 'full')


@app.route('/methodology')
def methodology():
    return send_from_directory('public', 'methodology.html')


@app.route('/lead', methods=['POST'])
def lead():
    """Capture an email for the full report and (optionally) monthly monitoring."""
    data = request.get_json(silent=True) or request.form
    email = (data.get('email') or '').strip().lower()
    url = (data.get('url') or '').strip()
    mode = (data.get('mode') or '').strip()
    overall = data.get('overall')
    want_monitor = str(data.get('monitor', '')).lower() in ('1', 'true', 'yes', 'on')
    if not _EMAIL_RE.match(email):
        return jsonify({'ok': False, 'error': 'Please enter a valid email address.'}), 400
    try:
        overall = int(overall) if overall is not None else None
    except (TypeError, ValueError):
        overall = None
    db.save_lead(email, url, mode, overall)
    monitoring = False
    if want_monitor and url and mode in VALID_MODES:
        monitoring = db.add_monitor(email, url, mode)

    # Email the report (best-effort; needs SENDGRID_API_KEY)
    emailed = False
    report_id = (data.get('report_id') or '').strip()
    grade = (data.get('grade') or '').strip()
    top_fixes = None
    if report_id:
        stored = db.get_report(report_id)
        if stored:
            overall = stored.get('overall_score', overall)
            grade = stored.get('grade', grade)
            es = stored.get('executive_summary') or {}
            top_fixes = es.get('top_opportunities')
    if emailer.enabled() and overall is not None:
        emailed = emailer.send_report_email(email, url, mode, overall, grade,
                                             _report_link(report_id), top_fixes)
    return jsonify({'ok': True, 'monitoring': monitoring, 'emailed': emailed})


@app.route('/api/history')
def api_history():
    domain = (request.args.get('domain') or '').strip()
    mode = (request.args.get('mode') or 'recruitment').strip()
    if not domain:
        return jsonify({'error': 'domain required'}), 400
    return jsonify({'domain': domain, 'mode': mode, 'history': db.history(domain, mode)})


_cwv_jobs = set()
_cwv_lock = threading.Lock()


def _measure_cwv_bg(url, mode):
    """Background Core Web Vitals measurement — runs the slow PageSpeed pass and
    caches the result so polling requests stay instant."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def run():
            g = CareerSiteGrader(url, mode=mode)
            g.psi_timeouts = (75, 55)
            await g._fetch_pagespeed()
            return g.pagespeed

        try:
            cwv = loop.run_until_complete(run())
        finally:
            loop.close()
        if cwv and cwv.get('perf_score') is not None:
            db.save_cwv(url, mode, cwv)
    except Exception:
        pass
    finally:
        with _cwv_lock:
            _cwv_jobs.discard((url, mode))


@app.route('/api/cwv')
def api_cwv():
    """Fast, poll-friendly Core Web Vitals. Returns cached data immediately if we
    have it; otherwise kicks off a background measurement and returns 'pending'
    so the browser can poll without holding a long connection open (which proxies
    and browsers cut off)."""
    url = (request.args.get('url') or '').strip()
    mode = (request.args.get('mode') or 'recruitment').strip()
    if not url:
        return jsonify({'error': 'url required'}), 400

    cached = None if _bypass_requested() else db.get_cwv(url, mode)
    # A cached blob missing its desktop reading is incomplete (an earlier
    # desktop-drop poisoned it): keep serving the mobile data we have, but kick a
    # background re-measure to backfill desktop so the card heals on next view.
    needs_measure = (cached is None) or (not cached.get('desktop'))
    status = 'ready' if cached else 'pending'
    if needs_measure:
        # Only spawn a (billable) PageSpeed job for URLs that were actually graded,
        # rate-limited at spawn time — prevents anonymous PSI-cost abuse via ?url=.
        if not db.url_graded(url, mode):
            if not cached:
                status = 'unavailable'
        else:
            key = (url, mode)
            with _cwv_lock:
                if key in _cwv_jobs:
                    pass  # already measuring — keep polling
                elif _rate_ok('cwv', limit=60):
                    _cwv_jobs.add(key)
                    threading.Thread(target=_measure_cwv_bg, args=(url, mode), daemon=True).start()
                elif not cached:
                    status = 'unavailable'
    resp = jsonify({'status': status, 'core_web_vitals': cached})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@app.route('/api/grade')
def api_grade():
    """Non-streaming JSON grade — for the Client Portal and integrations."""
    url = (request.args.get('url') or '').strip()
    mode = (request.args.get('mode') or 'recruitment').strip()
    if not url:
        return jsonify({'error': 'url required'}), 400
    if mode not in VALID_MODES:
        return jsonify({'error': f'mode must be one of: {", ".join(VALID_MODES)}'}), 400

    bypass = _bypass_requested()
    raw_comp = (request.args.get('competitors') or '').strip()
    comp_urls = competitors.clean_urls(raw_comp.split(','), _target_host(url)) if raw_comp else []
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run():
        grader = CareerSiteGrader(url, mode=mode, bypass_cache=bypass)
        final = None
        async for ev in grader.grade():
            if ev.get('type') == 'error':
                return {'error': ev.get('message', 'failed')}
            if ev.get('type') == 'complete':
                final = ev
        if final and comp_urls:
            try:
                final['comparison'] = await _build_comparison(comp_urls, mode, final)
            except Exception:
                pass
        return final

    try:
        result = loop.run_until_complete(run())
    finally:
        loop.close()
    if not result or 'error' in (result or {}):
        return jsonify(result or {'error': 'no result'}), 502
    _persist_and_enrich(result, url, mode, bypass=bypass)
    try:
        db.save_report(result['report_id'], result.get('url', url), mode, result)
    except Exception:
        pass
    resp = jsonify(result)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


# --- Competitors -------------------------------------------------------------

_competitor_cache = {}


@app.route('/api/competitors')
def api_competitors():
    """AI competitor finder: two direct competitors for a site (Claude + web search)."""
    url = (request.args.get('url') or '').strip()[:competitors.MAX_URL_LEN]
    mode = (request.args.get('mode') or 'recruitment').strip()
    if not url or mode not in VALID_MODES:
        return jsonify({'error': 'url and a valid mode are required'}), 400
    if not url.lower().startswith(('http://', 'https://')):
        url = 'https://' + url
    if not competitors.enabled():
        return jsonify({'error': 'AI competitor finder is not configured (ANTHROPIC_API_KEY). '
                                 'Enter competitor websites manually.'}), 503
    key = (competitors._host(url), mode)
    with _client_pdf_lock:
        cached = _competitor_cache.get(key)
    if cached is not None:
        found, ts = cached
        if found or time.time() - ts < 600:  # empty answers are cached for 10 minutes
            return jsonify({'competitors': found, 'cached': True})
    if not _rate_ok('competitors', limit=15):
        return jsonify({'error': 'Rate limit reached — please try again later.'}), 429
    try:
        found = competitors.find_competitors(url, mode)
    except Exception as e:
        print(f'[competitors] finder failed for {url}: {type(e).__name__}: {e}', file=sys.stderr, flush=True)
        return jsonify({'error': 'Could not find competitors right now. Enter them manually.'}), 502
    with _client_pdf_lock:
        _bounded_put(_competitor_cache, key, (found, time.time()))
    return jsonify({'competitors': found})


@app.route('/api/compare', methods=['POST'])
def api_compare():
    """Attach a competitor comparison (up to 2) to an existing stored report."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'JSON object required'}), 400
    report_id = data.get('report_id')
    if not isinstance(report_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{4,64}', report_id):
        return jsonify({'error': 'report not found'}), 404
    report = db.get_report(report_id)
    if not report:
        return jsonify({'error': 'report not found'}), 404
    # Only the browser that ran the grade may change its comparison (reports made
    # before owner tokens existed stay editable).
    owner = report.get('_owner')
    if owner and not secrets.compare_digest(str(data.get('owner') or ''), owner):
        return jsonify({'error': 'Only the person who ran this grade can change its comparison.'}), 403
    raw = data.get('competitors')
    if not isinstance(raw, list) or len(raw) > 5:
        return jsonify({'error': 'competitors must be a list of up to 5 websites.'}), 400
    urls = competitors.clean_urls(raw, report.get('domain', ''))
    if not urls:
        return jsonify({'error': 'Enter at least one competitor website that can be reached.'}), 400
    if not _rate_ok('compare', limit=20):
        return jsonify({'error': 'Rate limit reached — please try again later.'}), 429
    mode = report.get('mode') or 'recruitment'
    with _per_report_lock(report_id):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            comparison = loop.run_until_complete(_build_comparison(urls, mode, report))
        except Exception as e:
            print(f'[compare] failed for {report_id}: {type(e).__name__}: {e}', file=sys.stderr, flush=True)
            return jsonify({'error': 'Could not analyse the competitors. Please try again.'}), 502
        finally:
            loop.close()
        db.set_report_comparison(report_id, comparison)
        with _client_pdf_lock:
            for kind in _PDF_KINDS:  # both PDFs now carry a comparison table
                _client_pdf_cache.pop((report_id, kind), None)
    resp = jsonify({'ok': True, 'comparison': comparison})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@app.route('/api/report/<report_id>')
def api_report(report_id):
    report = db.get_report(report_id)
    if not report:
        return jsonify({'error': 'not found'}), 404
    resp = jsonify(_public(report))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@app.route('/r/<report_id>')
def shared_report(report_id):
    # Serves the SPA; the front-end detects /r/<id> and loads the stored report.
    return send_from_directory('public', 'index.html')


@app.route('/cron/rescore')
def cron_rescore():
    """Re-grade all active monitor subscriptions. Protect with ?token=CRON_TOKEN."""
    token = (request.args.get('token') or '').strip()
    expected = os.environ.get('CRON_TOKEN', '')
    if not expected or not secrets.compare_digest(token, expected):
        return jsonify({'error': 'unauthorized'}), 401

    monitors = db.active_monitors()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def rescore_all():
        out = []
        for m in monitors:
            try:
                domain = ''
                g = CareerSiteGrader(m['url'], mode=m['mode'], light=True)
                final = None
                async for ev in g.grade():
                    if ev.get('type') == 'complete':
                        final = ev
                if final:
                    domain = final.get('domain', '')
                    previous = db.last_overall(domain, m['mode'], before_latest=False)
                    db.save_grade(final.get('url', m['url']), domain, m['mode'],
                                  final.get('overall_score', 0), final.get('grade', ''),
                                  _pillar_scores(final))
                    db.mark_monitor_run(m['id'])
                    if emailer.enabled():
                        emailer.send_monitor_digest(
                            m['email'], m['url'], final.get('overall_score', 0),
                            final.get('grade', ''), previous, _report_link(None))
                    out.append({'url': m['url'], 'overall': final.get('overall_score')})
            except Exception as e:
                out.append({'url': m['url'], 'error': str(e)})
        return out

    try:
        results = loop.run_until_complete(rescore_all())
    finally:
        loop.close()
    return jsonify({'rescored': len(results), 'results': results})


SEED_SITES = [
    'roberthalf.com', 'hays.com', 'michaelpage.com', 'adecco.com', 'randstad.com',
    'manpower.com', 'kellyservices.com', 'roberthalf.co.uk', 'reed.co.uk', 'morganmckinley.com',
    'hudson.com', 'gartner.com/en/careers', 'pagepersonnel.co.uk', 'sthree.com', 'roberthalf.com.au',
    'hays.com.au', 'seek.com.au', 'allegisgroup.com', 'kornferry.com', 'spencerstuart.com',
    'aerotek.com', 'teksystems.com', 'experis.com', 'roberthalf.de', 'gigroom.com',
]


def _seed_bg(mode):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def seed():
        for site in SEED_SITES:
            try:
                g = CareerSiteGrader(site, mode=mode, light=True)
                final = None
                async for ev in g.grade():
                    if ev.get('type') == 'complete':
                        final = ev
                if final:
                    db.save_grade(final.get('url', site), final.get('domain', ''), mode,
                                  final.get('overall_score', 0), final.get('grade', ''),
                                  _pillar_scores(final))
            except Exception:
                pass
    try:
        loop.run_until_complete(seed())
    finally:
        loop.close()


@app.route('/cron/seed')
def cron_seed():
    """Populate the benchmark dataset by light-grading a curated list so
    percentile benchmarking becomes meaningful. Runs in the background (25 sites
    take several minutes). Protect with ?token=CRON_TOKEN."""
    token = (request.args.get('token') or '').strip()
    expected = os.environ.get('CRON_TOKEN', '')
    if not expected or not secrets.compare_digest(token, expected):
        return jsonify({'error': 'unauthorized'}), 401
    mode = (request.args.get('mode') or 'recruitment').strip()
    threading.Thread(target=_seed_bg, args=(mode,), daemon=True).start()
    return jsonify({'started': True, 'sites': len(SEED_SITES), 'mode': mode})


@app.route('/api/outcome', methods=['POST'])
def api_outcome():
    """Ingest a real-world outcome for a domain (token-protected) so pillar weights
    can be calibrated against reality. Body: {domain, mode, metric, value}."""
    token = (request.args.get('token') or '').strip()
    expected = _admin_token()
    if not expected or not secrets.compare_digest(token, expected):
        return jsonify({'error': 'unauthorized'}), 401
    d = request.get_json(silent=True) or {}
    domain = (d.get('domain') or '').strip().lower().lstrip('www.')
    mode = (d.get('mode') or 'recruitment').strip()
    metric = (d.get('metric') or 'gsc_clicks').strip()
    try:
        value = float(d.get('value'))
    except (TypeError, ValueError):
        return jsonify({'error': 'value must be numeric'}), 400
    if not domain or mode not in VALID_MODES:
        return jsonify({'error': 'domain + valid mode required'}), 400
    ok = db.save_outcome(domain, mode, metric, value)
    return jsonify({'ok': ok})


@app.route('/cron/calibrate')
def cron_calibrate():
    """Suggest pillar weights by correlating each pillar's score with a real
    outcome metric across domains that have both. Surfaces recommendations — does
    NOT auto-apply. Token-protected."""
    token = (request.args.get('token') or '').strip()
    expected = os.environ.get('CRON_TOKEN', '') or _admin_token()
    if not expected or not secrets.compare_digest(token, expected):
        return jsonify({'error': 'unauthorized'}), 401
    mode = (request.args.get('mode') or 'recruitment').strip()
    metric = (request.args.get('metric') or 'gsc_clicks').strip()
    rows = db.calibration_rows(mode, metric)
    n = len(rows)
    if n < 12:
        return jsonify({'mode': mode, 'metric': metric, 'samples': n,
                        'ready': False,
                        'note': f'Need >=12 domains with both a grade and a "{metric}" outcome; have {n}. '
                                'POST outcomes to /api/outcome (e.g. from GSC/GA4) to enable calibration.'})

    # Pearson correlation of each pillar score vs the outcome.
    pillars = sorted({k for r in rows for k in r['pillars'].keys()})
    outcomes = [r['outcome'] for r in rows]

    def pearson(xs, ys):
        m = len(xs)
        mx = sum(xs) / m; my = sum(ys) / m
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        dx = (sum((x - mx) ** 2 for x in xs)) ** 0.5
        dy = (sum((y - my) ** 2 for y in ys)) ** 0.5
        return (num / (dx * dy)) if dx and dy else 0.0

    corr = {}
    for p in pillars:
        xs = [r['pillars'].get(p, 0) for r in rows]
        corr[p] = round(pearson(xs, outcomes), 3)
    # Suggested weights = positive correlations, normalised to sum 1.
    pos = {p: max(c, 0) for p, c in corr.items()}
    tot = sum(pos.values()) or 1
    suggested = {p: round(v / tot, 3) for p, v in pos.items()}
    return jsonify({'mode': mode, 'metric': metric, 'samples': n, 'ready': True,
                    'correlations': corr, 'suggested_weights': suggested,
                    'note': 'Correlation of each pillar score with the outcome. Review before applying.'})


@app.route('/stats')
def stats():
    return jsonify(db.stats())


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7070))
    print(f"Shazamme Career Site Grader running on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
