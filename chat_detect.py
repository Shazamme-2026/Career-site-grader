"""Live chat / chatbot widget detection.

Two passes, in order:

1. Vendor signatures — name the product when we recognise the embed.
2. Generic structural signals — catch everything else: in-house widgets,
   white-label builds, and vendors that shipped after this list was written.

Only *markup* counts as evidence: script/iframe sources, element ids and
classes, custom tag names, widget config attributes and the label on the
launcher control itself. Visible copy ("come and chat to our team", a "Let's
chat" heading) is deliberately never enough — that wording is on half the
recruitment sites on the web and none of it means a chatbot is installed.

The input is every crawled page concatenated, so it runs to megabytes and
speed is part of the design. Nothing here sweeps the whole document with an
expensive pattern: vendor hosts are plain substrings checked against the URLs
harvested in one cheap pass, and the structural rules only ever run on the
markup immediately around a "chat" or "messenger" needle, found with str.find.
"""

import re
from typing import Dict, List, NamedTuple, Optional, Tuple

# Where the embed loads from. Matched against the URLs harvested out of the
# page, which is both faster and tighter than scanning the whole document:
# "drift.com" in a blog sentence is not a Drift install.
VENDOR_HOSTS: Dict[str, Tuple[str, ...]] = {
    'Zammenow':           ('zammenow.com',),
    'Intercom':           ('intercom.io', 'intercomcdn.com'),
    'Drift':              ('drift.com', 'driftt.com'),
    'Crisp':              ('crisp.chat',),
    'Tawk.to':            ('tawk.to',),
    'Zendesk':            ('zendesk.com', 'zdassets.com'),
    'LiveChat':           ('livechatinc.com', 'livechat.com'),
    'Tidio':              ('tidio.co',),
    'Freshchat':          ('freshchat.com',),
    'LivePerson':         ('liveperson.net', 'lpsnmedia.net'),
    'Olark':              ('olark.com',),
    'Smartsupp':          ('smartsupp.com',),
    'Genesys':            ('genesys.com', 'genesyscloud.com'),
    'Qualified':          ('qualified.com',),
    'HubSpot Chat':       ('js.usemessages.com', 'hubspot.com/conversations'),
    'Chatra':             ('chatra.io', 'chatra.com'),
    'JivoChat':           ('jivosite.com', 'jivochat.com'),
    'Userlike':           ('userlike.com',),
    'HelpCrunch':         ('helpcrunch.com',),
    'Kommunicate':        ('kommunicate.io',),
    'Landbot':            ('landbot.io',),
    'ManyChat':           ('manychat.com',),
    'Chatfuel':           ('chatfuel.com',),
    'Botpress':           ('botpress.cloud', 'botpress.com', 'bpcontent.cloud'),
    'Ada':                ('ada.support', 'adasupport.com'),
    'Dialogflow':         ('dialogflow.com',),
    'Paradox (Olivia)':   ('paradox.ai', 'olivia.paradox'),
    'Sendbird':           ('sendbird.com',),
    'Comm100':            ('comm100.com',),
    'SnapEngage':         ('snapengage.com',),
    'Pure Chat':          ('purechat.com',),
    'Respond.io':         ('respond.io', 'rocketbots.io'),
    'Zoho SalesIQ':       ('salesiq.zoho',),
    'Gorgias':            ('gorgias.chat',),
    'Front':              ('chat.frontapp.com',),
    'Kustomer':           ('kustomerapp.com', 'kustomer.com'),
    'Gladly':             ('gladly.com',),
    'Dixa':               ('dixa.io', 'dixa.com'),
    'Re:amaze':           ('reamaze.com', 'reamaze.io'),
    'Trengo':             ('trengo.com', 'trengo.net'),
    'Chaport':            ('chaport.com',),
    'Chatwoot':           ('chatwoot.com',),
    'Podium':             ('podium.com/widget', 'connect.podium'),
    'Birdeye':            ('birdeye.com/webchat',),
    'Tars':               ('hellotars.com',),
    'Haptik':             ('haptik.ai', 'haptikapi.com'),
    'Verloop':            ('verloop.io',),
    'WATI':               ('wati.io',),
    'HighLevel Chat':     ('leadconnectorhq.com/loader.js',),
    'Copilot Studio':     ('copilotstudio.microsoft.com', 'powerva.microsoft.com'),
    'Facebook Messenger': ('customerchat.js',),
    'ElevenLabs ConvAI':  ('elevenlabs.io/convai',),
    'Voiceflow':          ('voiceflow.com',),
    'Tiledesk':           ('tiledesk.com',),
    'Twilio Flex':        ('flex.twilio.com',),
}

# What the embed leaves behind in the page — a JS global, a mount node, a
# custom element. These are matched against the whole document, so keep the
# list short and each entry unmistakable.
VENDOR_MARKERS: Dict[str, Tuple[str, ...]] = {
    'Zammenow':           ('zmn-chat-root',),
    'Intercom':           ('window.intercom',),
    'Tawk.to':            ('tawk_api',),
    'Zendesk':            ('zopim',),
    'Tidio':              ('tidiochat',),
    'Smartsupp':          ('smartsuppchat',),
    'Freshchat':          ('wchat.freshchat',),
    'HubSpot Chat':       ('hubspot-messages-iframe',),
    'Comm100':            ('comm100vue',),
    'Dialogflow':         ('df-messenger',),
    'Chatwoot':           ('chatwoot',),
    'Birdeye':            ('birdeyewebchat',),
    'Facebook Messenger': ('fb-customerchat',),
    'ElevenLabs ConvAI':  ('elevenlabs-convai', 'convai-widget'),
}

# The compounds that spell a widget. The guards on both ends are what keep
# "chateau", "chatter" and "chatham" out.
_WIDGET_COMPOUND = (
    r'(?<![a-z])'
    r'(?:live[-_]?chat|web[-_]?chat|chat[-_]?bots?|chat[-_]?widget|chat[-_]?box|'
    r'chat[-_]?window|chat[-_]?launcher|chat[-_]?bubble|chat[-_]?root|chat[-_]?frame|'
    r'chat[-_]?container|chat[-_]?button|chat[-_]?icon|chat[-_]?app)'
    r'(?![a-z])'
)

# In a script/iframe URL, bare "chat" is allowed as a filename stem (chat.js)
# but not as a path word — /blog/lets-chat-about-hiring is an article.
_SRC_CHAT = (_WIDGET_COMPOUND +
             r'|(?<![a-z])(?:chat|messenger)(?=\.(?:min\.)?js\b)')

# A hyphenated tag name is already proof of a web component, so "messenger"
# alone is safe there — unlike in a class, where it is a social icon.
_ELEMENT_CHAT = _WIDGET_COMPOUND + r'|(?<![a-z])messenger(?![a-z])'

GENERIC_PATTERNS: Dict[str, str] = {
    # A script or iframe whose URL is about chat. Only src — an <a href> to
    # /lets-chat is a page, not an embed. Nothing after the token is required:
    # a widget URL can carry a hundred characters of query string, and asking
    # for the closing quote would lose it.
    'chat script/iframe embed':
        r'<(?:script|iframe)\b[^>]{0,800}?\bsrc\s*=\s*["\'][^"\'<>]{0,600}(?:' + _SRC_CHAT + r')',
    # A container the widget mounts into, or the whole value being just "chat".
    'chat widget container':
        r'\b(?:id|class|data-widget|data-testid)\s*=\s*["\'][^"\'<>]{0,600}(?:' +
        _WIDGET_COMPOUND + r')'
        r'|\b(?:id|class)\s*=\s*["\']\s*chat\s*["\']',
    # Config the embed reads before it boots. data-chat, data-chatbot-id — but
    # not data-chateau.
    'chat widget config':
        r'\bdata-chat(?:bots?|widget|box)?(?:-[a-z][a-z-]*)?\s*=|'
        r'\bchat[_-]?widget[_-]?(?:settings|config|id|key)\b|'
        r'window\.[a-z_$]*chat(?:bot|widget)[a-z_$]*\s*=',
    # The launcher control's own label. aria-label only: title= is a tooltip,
    # and "Chat with us now" on a link to the contact page is not a widget.
    # The keywords are whole words, so "Em[ai]l or chat" does not qualify.
    'chat launcher control':
        r'(?<![-a-z])aria-label\s*=\s*["\'][^"\']{0,40}'
        r'(?:(?<![a-z])(?:open|close|toggle|start|launch|live|ai|support)(?![a-z])'
        r'[^"\']{0,20}(?<![a-z])chat(?![a-z])'
        r'|(?<![a-z])chat(?![a-z])[^"\']{0,20}(?:widget|window|bot|assistant|with us|now))',
}


# WhatsApp click-to-chat counts only as a floating widget, and the proof has
# to be a class or id that names it — on the link or on the wrapper that
# positions it. Anything looser turns a footer social icon into a chat
# widget: Bootstrap's own "float-end" utility, or a wa.me link whose
# ?text= pre-fill happens to contain the word "chat".
_WHATSAPP_LINK = r'wa\.me/|api\.whatsapp\.com/send|web\.whatsapp\.com/send'
_WHATSAPP_TAG = r'<a\b[^<>]{0,200}(?:' + _WHATSAPP_LINK + r')[^<>]{0,200}>'
_WHATSAPP_WIDGET_MARKER = (
    r'\b(?:class|id)\s*=\s*["\'][^"\']{0,100}'
    r'(?:whatsapp[a-z0-9_-]{0,12}(?:float|fixed|sticky|widget|button|bubble|chat)'
    r'|(?:float|fixed|sticky|widget|bubble)[a-z0-9_-]{0,12}whatsapp)')
# How far back to look for the wrapper that carries that class.
_WHATSAPP_WRAPPER_LOOKBACK = 250


# Every structural rule needs one of these words next to it, and str.find is
# orders of magnitude cheaper than a regex sweep — so the words are located
# first and the rules only ever run on the markup around them.
_CHAT_NEEDLES = ('chat', 'messenger')

_VENDOR_NAMES = list(dict.fromkeys(list(VENDOR_HOSTS) + list(VENDOR_MARKERS)))

# Where the page loads things FROM: the markup around every "src" (which
# covers src=, data-src= and the `el.src = "//host/..."` form in a loader
# snippet) and every <link> tag, where a preconnect to a widget CDN shows up.
# Deliberately not <a href> or prose: a help-centre link to acme.zendesk.com
# is not an install. str.find keeps this to a couple of C-speed passes.
_RESOURCE_NEEDLES = (('src', 160), ('<link', 250))

# How much markup around a needle a rule can see. This has to exceed the
# embed rule's own reach — 800 characters of attributes plus 600 of URL or
# class list before the token — or a widget matches the rule but not the
# window it is scanned in.
_WINDOW_BEFORE = 1500
_WINDOW_AFTER = 120

# Work ceiling for the structural pass. A 6MB crawl of real sites produces
# ~100KB of chat-adjacent markup, so this is twenty times what a career site
# needs — deliberate headroom, because the rendered DOM is appended LAST and
# a budget spent on ordinary "chat to our team" copy would drop exactly the
# JS-injected widget this check exists to find. A page that still blows
# through it is pathological, and the grader is fed whatever URL a stranger
# typed into the public form.
_MAX_SCAN_BYTES = 2_000_000

_GENERIC_SIGNALS = list(GENERIC_PATTERNS)
_GENERIC_RX = re.compile(
    '|'.join(f'(?P<g{i}>{p})' for i, p in enumerate(GENERIC_PATTERNS.values())), re.I)

_CUSTOM_TAG_RX = re.compile(r'<((?:[a-z0-9]+-)+[a-z0-9]+)(?=[\s/>])', re.I)
_ELEMENT_CHAT_RX = re.compile(_ELEMENT_CHAT, re.I)
_WHATSAPP_LITERALS = ('wa.me/', 'api.whatsapp.com/send', 'web.whatsapp.com/send')
_WHATSAPP_TAG_RX = re.compile(_WHATSAPP_TAG, re.I)
_WHATSAPP_MARKER_RX = re.compile(_WHATSAPP_WIDGET_MARKER, re.I)


class ChatDetection(NamedTuple):
    """found: anything at all. vendors: the ones we could name. signal: why."""
    found: bool
    vendors: List[str]
    signal: str

    @property
    def summary(self) -> str:
        if not self.found:
            return 'No chat/chatbot found across scanned pages'
        if self.vendors:
            return f'Live chat / chatbot detected: {", ".join(self.vendors)} ✓'
        return f'Live chat / chatbot detected ✓ — {self.signal} (unrecognised provider)'


# A marker only counts inside markup or code. "We compared Chatwoot and
# Tidio" is a sentence about chat tools, not a chat tool — and the tell is
# that both of its neighbours are prose. One code neighbour is enough:
# class="woot-widget-holder chatwoot", /vendor/chatwoot/sdk.js, or
# <script>window.intercomSettings all qualify.
_CODE_NEIGHBOUR = set('"\'=/_-()[]{}:;?&#')


def _code_side(text: str, at: int) -> bool:
    if not 0 <= at < len(text):
        return False
    char = text[at]
    if char.isalnum() or char in _CODE_NEIGHBOUR:
        return True
    # A dot is member access in code and a full stop in prose.
    return char == '.' and at + 1 < len(text) and text[at + 1].isalnum()


def _marker_in_markup(html: str, marker: str) -> bool:
    at = html.find(marker)
    while at != -1:
        if _code_side(html, at - 1) or _code_side(html, at + len(marker)):
            return True
        at = html.find(marker, at + len(marker))
    return False


def _resource_urls(html: str) -> str:
    """Just the markup that names something the page loads."""
    parts: List[str] = []
    for needle, span in _RESOURCE_NEEDLES:
        at = html.find(needle)
        while at != -1:
            # Stop at the end of this tag, or an <img src> would drag in the
            # <a href> that follows it.
            chunk = html[at:at + span]
            end = chunk.find('>')
            parts.append(chunk if end == -1 else chunk[:end])
            at = html.find(needle, at + len(needle))
    return ' '.join(parts)


def _vendors(html: str) -> List[str]:
    """Every vendor whose embed is present."""
    urls = _resource_urls(html)
    return [name for name in _VENDOR_NAMES
            if any(host in urls for host in VENDOR_HOSTS.get(name, ()))
            or any(_marker_in_markup(html, marker)
                   for marker in VENDOR_MARKERS.get(name, ()))]


def _windows(html: str) -> List[Tuple[int, int]]:
    """Merged spans of markup around every chat needle.

    Merging matters: a page that says "chat" a thousand times in a row would
    otherwise be scanned a thousand times over. Merged, the work is capped at
    one pass over the document however the needles are distributed.
    """
    starts: List[int] = []
    for needle in _CHAT_NEEDLES:
        at = html.find(needle)
        while at != -1:
            starts.append(at)
            at = html.find(needle, at + len(needle))
    if not starts:
        return []

    starts.sort()
    spans = [[max(0, starts[0] - _WINDOW_BEFORE), starts[0] + _WINDOW_AFTER]]
    for start in starts[1:]:
        low, high = max(0, start - _WINDOW_BEFORE), start + _WINDOW_AFTER
        if low <= spans[-1][1]:
            spans[-1][1] = max(spans[-1][1], high)
        else:
            spans.append([low, high])
    return [(low, high) for low, high in spans]


def _generic_signal(html: str) -> Optional[str]:
    """The first structural signal found, named for the report."""
    budget = _MAX_SCAN_BYTES
    for low, high in _windows(html):
        # Stop on a whole window rather than scanning half of one: a clipped
        # window can cut an attribute in two and lose a real match silently.
        if high - low > budget:
            break
        match = _GENERIC_RX.search(html[low:high])
        if match:
            return _GENERIC_SIGNALS[int(match.lastgroup[1:])]
        budget -= high - low
    return None


def _custom_chat_element(html: str) -> bool:
    return any(_ELEMENT_CHAT_RX.search(tag) for tag in _CUSTOM_TAG_RX.findall(html))


def _floating_whatsapp(html: str) -> bool:
    # The cheap literal scan gates the pricier tag scan: almost no page has a
    # WhatsApp link at all.
    if not any(literal in html for literal in _WHATSAPP_LITERALS):
        return False
    # The positioning class often sits on the wrapper, not the link itself.
    return any(_WHATSAPP_MARKER_RX.search(
        html[max(0, tag.start() - _WHATSAPP_WRAPPER_LOOKBACK):tag.end()])
        for tag in _WHATSAPP_TAG_RX.finditer(html))


def detect_chat(html: str) -> ChatDetection:
    """Detect a chat/chatbot widget in page markup.

    `html` is every scanned page's HTML concatenated, plus the rendered DOM
    when one was captured. Case does not matter.
    """
    if not html:
        return ChatDetection(False, [], '')

    # Vendor signatures are plain lowercase substrings, so normalise once.
    html = html.lower()

    vendors = _vendors(html)
    if vendors:
        return ChatDetection(True, vendors, 'vendor embed')

    signal = _generic_signal(html)
    if signal:
        return ChatDetection(True, [], signal)

    if _custom_chat_element(html):
        return ChatDetection(True, [], 'chat custom element')

    if _floating_whatsapp(html):
        return ChatDetection(True, ['WhatsApp'], 'floating WhatsApp chat')

    return ChatDetection(False, [], '')
