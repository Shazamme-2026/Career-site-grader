"""
Competitor discovery and validation.

find_competitors(url, mode) asks Claude (with web search) for two direct
competitors of the graded site. parse_competitors / clean_urls are pure and
shared by the AI path and manual entry so both produce the same clean list.

Env:
  ANTHROPIC_API_KEY   — enables the AI finder (enabled() is False without it)
  COMPETITOR_MODEL    — default claude-opus-5-5
"""

import json
import os
import re
import sys
from urllib.parse import urlparse

MODEL = os.environ.get('COMPETITOR_MODEL', 'claude-opus-5-5')
MAX_COMPETITORS = 2

# Aggregators and platforms that are never a "competitor agency".
_BLOCKED_HOSTS = (
    'seek.com', 'indeed.', 'linkedin.com', 'glassdoor.', 'jora.', 'adzuna.', 'reed.co.uk',
    'totaljobs.', 'cv-library.', 'monster.', 'ziprecruiter.', 'careerone.', 'jobstreet.',
    'facebook.com', 'instagram.com', 'twitter.com', 'x.com', 'youtube.com', 'google.',
    'wikipedia.org', 'crunchbase.com', 'trustpilot.', 'yelp.', 'bing.com',
)

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
    return (urlparse(url).hostname or '').lower().removeprefix('www.')


def _normalise(raw) -> str:
    raw = str(raw or '').strip().strip('<>"\'`.,;)')
    if not raw:
        return ''
    if not re.match(r'^https?://', raw, re.I):
        if re.match(r'^[a-z]+:', raw, re.I):
            return ''  # javascript:, mailto:, etc.
        raw = 'https://' + raw
    p = urlparse(raw)
    if p.scheme not in ('http', 'https') or not p.hostname or '.' not in p.hostname:
        return ''
    if any(b in p.hostname.lower() for b in _BLOCKED_HOSTS):
        return ''
    return f'{p.scheme}://{p.hostname}'


def clean_urls(raw_urls, target_domain: str) -> list:
    """Manual-entry path: normalise, drop blanks, junk, the target and duplicates; cap at 2."""
    target = (target_domain or '').lower().removeprefix('www.')
    out, seen = [], set()
    for raw in raw_urls or []:
        url = _normalise(raw)
        if not url:
            continue
        host = _host(url)
        if host == target or host in seen:
            continue
        seen.add(host)
        out.append(url)
        if len(out) >= MAX_COMPETITORS:
            break
    return out


def parse_competitors(text: str, target_domain: str) -> list:
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

    urls = clean_urls([i['url'] for i in items], target_domain)
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
    target_domain = _host(url)
    prompt = (
        f'The target is the {kind} at {url}.\n\n'
        f'Find its {MAX_COMPETITORS} closest direct competitors (see the rules). Use web search to '
        f'confirm what the target does and where, then find and verify the competitors.\n\n'
        'Respond with JSON only, no commentary, in exactly this shape:\n'
        '{"competitors": [{"url": "https://example.com", "name": "Example Recruitment", '
        '"reason": "one short sentence on why it is a direct competitor"}]}'
    )
    tools = [{'type': 'web_search_20260209', 'name': 'web_search', 'max_uses': 8}]
    messages = [{'role': 'user', 'content': prompt}]
    base = dict(model=MODEL, max_tokens=4000, system=SYSTEM, tools=tools,
                output_config={'effort': 'low'})
    # Server-side refusal fallback (routes a declined request to another model).
    # Older SDKs don't know the kwarg; fall back to a plain call rather than fail.
    variants = [dict(base, betas=['server-side-fallback-2026-07-01'], fallbacks='default'), base]
    response = None
    for _ in range(4):
        for kwargs in variants:
            try:
                response = client.beta.messages.create(messages=messages, **kwargs)
                break
            except TypeError:
                continue
        if response is None or response.stop_reason != 'pause_turn':
            break
        messages = [messages[0], {'role': 'assistant', 'content': response.content}]
    if response is None or response.stop_reason == 'refusal':
        _log(f'no answer for {url}: stop_reason={getattr(response, "stop_reason", None)}')
        return []
    text = ''.join(b.text for b in response.content if b.type == 'text')
    found = parse_competitors(text, target_domain)
    _log(f'{url} -> {[c["url"] for c in found]}')
    return found
