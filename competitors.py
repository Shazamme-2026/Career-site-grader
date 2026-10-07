"""
Competitor discovery and validation.

find_competitors(url, mode) asks Claude (with web search) for two direct
competitors of the graded site. parse_competitors / clean_urls are pure and
shared by the AI path and manual entry so both produce the same clean list.

Env:
  ANTHROPIC_API_KEY   — enables the AI finder (enabled() is False without it)
  COMPETITOR_MODEL    — default claude-opus-5-5
"""

import ipaddress
import json
import os
import re
import socket
import sys
from urllib.parse import urlparse

MODEL = os.environ.get('COMPETITOR_MODEL', 'claude-opus-5-5')
MAX_COMPETITORS = 2

# Aggregators and platforms that are never a "competitor agency" (registrable
# domain or label prefix; matched on label boundaries, so apex.com != x.com).
_BLOCKED_DOMAINS = (
    'seek.com.au', 'seek.co.nz', 'indeed', 'linkedin.com', 'glassdoor', 'jora', 'adzuna',
    'reed.co.uk', 'totaljobs.com', 'cv-library.co.uk', 'monster', 'ziprecruiter', 'careerone',
    'jobstreet', 'facebook.com', 'instagram.com', 'twitter.com', 'x.com', 'youtube.com',
    'google', 'wikipedia.org', 'crunchbase.com', 'trustpilot', 'yelp', 'bing.com',
)
MAX_URL_LEN = 253


def _blocked(host: str) -> bool:
    labels = host.lower().split('.')
    for b in _BLOCKED_DOMAINS:
        bl = b.split('.')
        for i in range(len(labels) - len(bl) + 1):
            if labels[i:i + len(bl)] == bl:
                return True
    return False


def is_public_host(host: str) -> bool:
    """SSRF guard: every address the host resolves to must be public."""
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False
    if not infos:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            return False
    return True

SYSTEM = (
    'You are a market analyst for recruitment and staffing businesses. Given a company website, '
    'you identify its two closest direct competitors: businesses that recruit in the same sectors '
    'or specialisms, in the same country or region, of a broadly similar size. Never return job '
    'boards, aggregators, social networks, directories or the company itself. Prefer independent '
    'agencies over global giants unless the target is itself a large multinational. Verify each '
    'competitor website exists and is the company\'s own site.'
)


def enabled() -> bool:
    return bool(os.environ.get('ANTHROPIC_API_KEY', ''))


def _log(msg):
    print(f'[competitors] {msg}', file=sys.stderr, flush=True)


def _host(url: str) -> str:
    try:
        host = urlparse(url).hostname or ''
    except ValueError:
        return ''
    host = host.lower()
    return host[4:] if host.startswith('www.') else host


def _normalise(raw) -> str:
    raw = str(raw or '').strip().strip('<>"\'`.,;)')
    if not raw or len(raw) > MAX_URL_LEN:
        return ''
    if not re.match(r'^https?://', raw, re.I):
        if re.match(r'^[a-z]+:', raw, re.I):
            return ''  # javascript:, mailto:, etc.
        raw = 'https://' + raw
    try:
        p = urlparse(raw)
        host = p.hostname
    except ValueError:
        return ''
    if p.scheme not in ('http', 'https') or not host or '.' not in host:
        return ''
    if _blocked(host):
        return ''
    return f'{p.scheme}://{host}'


def clean_urls(raw_urls, target_domain: str, check_dns: bool = True) -> list:
    """Normalise, drop blanks, junk, aggregators, the target, duplicates and any host
    that resolves to a private address; cap at MAX_COMPETITORS. Shared by the AI path
    and manual entry so both produce the same clean list."""
    if not isinstance(raw_urls, (list, tuple)):
        return []
    target = _host('//' + str(target_domain or ''))
    out, seen = [], set()
    for raw in list(raw_urls)[:10]:
        if not isinstance(raw, str):
            continue
        url = _normalise(raw)
        if not url:
            continue
        host = _host(url)
        if host == target or host in seen:
            continue
        if check_dns and not is_public_host(urlparse(url).hostname):
            continue
        seen.add(host)
        out.append(url)
        if len(out) >= MAX_COMPETITORS:
            break
    return out


def parse_competitors(text: str, target_domain: str, check_dns: bool = False) -> list:
    """Turn Claude's answer into [{url, name, reason}] — JSON first, bare URLs as fallback."""
    items = []
    m = re.search(r'\{.*\}', text or '', re.S)
    if m:
        try:
            data = json.loads(m.group(0))
            for c in (data.get('competitors') or []):
                if isinstance(c, dict):
                    items.append({'url': c.get('url', ''), 'name': str(c.get('name') or ''),
                                  'reason': str(c.get('reason') or '')})
                elif isinstance(c, str):
                    items.append({'url': c, 'name': '', 'reason': ''})
        except (ValueError, AttributeError):
            items = []
    if not items:
        items = [{'url': u, 'name': '', 'reason': ''}
                 for u in re.findall(r'https?://[^\s<>"\'`)\]]+', text or '')]

    urls = clean_urls([str(i['url']) for i in items], target_domain, check_dns=check_dns)
    by_host = {_host(i['url'] if re.match(r'^https?://', str(i['url']), re.I) else 'https://' + str(i['url'])): i
               for i in items if i.get('url')}
    return [{'url': u, 'name': by_host.get(_host(u), {}).get('name', ''),
             'reason': by_host.get(_host(u), {}).get('reason', '')} for u in urls]


def find_competitors(url: str, mode: str) -> list:
    """Ask Claude (web search) for two direct competitors. Raises on API failure."""
    import anthropic  # lazy: only needed when the finder is enabled

    client = anthropic.Anthropic()
    kind = {'recruitment': 'recruitment / staffing agency',
            'career_site': 'employer career site',
            'general': 'business website'}.get(mode, 'business')
    url = url[:MAX_URL_LEN]
    target_domain = _host(url)
    prompt = (
        f'The target is the {kind} at {url}.\n\n'
        f'Find its {MAX_COMPETITORS} closest direct competitors (see the rules). Use web search to '
        f'confirm what the target does and where, then find and verify the competitors.\n\n'
        'Respond with JSON only, no commentary, in exactly this shape:\n'
        '{"competitors": [{"url": "https://example.com", "name": "Example Recruitment", '
        '"reason": "one short sentence on why it is a direct competitor"}]}'
    )
    tools = [{'type': 'web_search_20260209', 'name': 'web_search', 'max_uses': 5}]
    messages = [{'role': 'user', 'content': prompt}]
    base = dict(model=MODEL, max_tokens=4000, system=SYSTEM, tools=tools,
                output_config={'effort': 'low'})
    # Server-side refusal fallback (routes a declined request to another model).
    # Older SDKs don't know the kwarg; fall back to a plain call rather than fail.
    variants = [dict(base, betas=['server-side-fallback-2026-07-01'], fallbacks='default'), base]
    response = None
    for _ in range(3):  # initial request + at most two pause_turn continuations
        response = None
        for kwargs in variants:
            try:
                response = client.beta.messages.create(messages=messages, **kwargs)
                break
            except (TypeError, anthropic.BadRequestError) as e:
                _log(f'variant rejected ({type(e).__name__}); trying plain call')
                continue
        if response is None or response.stop_reason != 'pause_turn':
            break
        messages = [messages[0], {'role': 'assistant', 'content': response.content}]
    if response is None or response.stop_reason == 'refusal':
        _log(f'no answer for {url}: stop_reason={getattr(response, "stop_reason", None)}')
        return []
    text = ''.join(b.text for b in response.content if b.type == 'text')
    found = parse_competitors(text, target_domain, check_dns=True)
    _log(f'{url} -> {[c["url"] for c in found]}')
    return found
