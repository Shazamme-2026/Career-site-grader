"""Live chat / chatbot widget detection.

Two passes, in order:

1. Vendor signatures — name the product when we recognise the embed.
2. Generic structural signals — catch everything else: in-house widgets,
   white-label builds, and vendors that shipped after this list was written.

Only *markup* counts as evidence: script/iframe sources, element ids and
classes, custom tag names, widget config globals and accessibility labels on
controls. Visible copy ("come and chat to our team", a "Let's chat" heading)
is deliberately never enough — that wording is on half the recruitment sites
on the web and none of it means a chatbot is installed.
"""

import re
from typing import Dict, List, NamedTuple

# Vendor embeds we can name. Keyed on the host/global that actually ships in
# the page, not on the marketing name.
VENDOR_PATTERNS: Dict[str, str] = {
    'Zammenow':           r'zammenow\.com|zmn-chat-root',
    'Intercom':           r'intercom\.io|intercomcdn\.com|widget\.intercom|window\.intercom',
    'Drift':              r'drift\.com|driftt\.com',
    'Crisp':              r'crisp\.chat',
    'Tawk.to':            r'tawk\.to|tawk_api',
    'Zendesk':            r'zendesk\.com|zdassets\.com|zopim',
    'LiveChat':           r'livechatinc\.com|livechat\.com',
    'Tidio':              r'tidio\.co|tidiochat',
    'Freshchat':          r'freshchat\.com|wchat\.freshchat',
    'LivePerson':         r'liveperson\.net|lpsnmedia\.net',
    'Olark':              r'olark\.com',
    'Smartsupp':          r'smartsupp\.com|smartsuppchat',
    'Genesys':            r'genesys\.com|genesyscloud\.com',
    'Qualified':          r'qualified\.com',
    'HubSpot Chat':       r'hubspot[^"\']{0,60}(?:conversations|messages)|hubspot-messages-iframe',
    'Chatra':             r'chatra\.io|chatra\.com',
    'JivoChat':           r'jivosite\.com|jivochat\.com',
    'Userlike':           r'userlike\.com',
    'HelpCrunch':         r'helpcrunch\.com',
    'Kommunicate':        r'kommunicate\.io',
    'Landbot':            r'landbot\.io',
    'ManyChat':           r'manychat\.com',
    'Chatfuel':           r'chatfuel\.com',
    'Botpress':           r'botpress\.(?:cloud|com)|bpcontent\.cloud',
    'Ada':                r'ada\.support|adasupport\.com',
    'Dialogflow':         r'df-messenger|dialogflow\.com',
    'Paradox (Olivia)':   r'paradox\.ai|olivia\.paradox',
    'Sendbird':           r'sendbird\.com',
    'Comm100':            r'comm100\.com|comm100vue',
    'SnapEngage':         r'snapengage\.com',
    'Pure Chat':          r'purechat\.com',
    'Respond.io':         r'respond\.io|rocketbots\.io',
    'Zoho SalesIQ':       r'salesiq\.zoho',
    'Gorgias':            r'gorgias\.chat',
    'Front':              r'chat\.frontapp\.com',
    'Kustomer':           r'kustomerapp\.com|kustomer\.com',
    'Gladly':             r'gladly\.com',
    'Dixa':               r'dixa\.(?:io|com)',
    'Re:amaze':           r'reamaze\.(?:com|io)',
    'Trengo':             r'trengo\.(?:com|net)',
    'Chaport':            r'chaport\.com',
    'Chatwoot':           r'chatwoot',
    'Podium':             r'podium\.com/widget|connect\.podium',
    'Birdeye':            r'birdeye\.com/webchat|birdeye_?webchat',
    'Tars':               r'hellotars\.com',
    'Haptik':             r'haptik\.ai|haptikapi\.com',
    'Verloop':            r'verloop\.io',
    'WATI':               r'wati\.io',
    'HighLevel Chat':     r'leadconnectorhq\.com/loader\.js',
    'Copilot Studio':     r'copilotstudio\.microsoft\.com|powerva\.microsoft\.com',
    'Facebook Messenger': r'fb-customerchat|customerchat\.js',
    'ElevenLabs ConvAI':  r'elevenlabs-convai|convai-widget',
    'Voiceflow':          r'voiceflow\.com',
    'Tiledesk':           r'tiledesk\.com',
    'Twilio Flex':        r'flex\.twilio\.com',
}

# "chat" as a whole token, plus the compounds that spell a widget. The trailing
# guard is what keeps "chateau", "chatter" and "chatham" out.
_CHAT_WORD = (
    r'(?<![a-z])'
    r'(?:live[-_]?chat|web[-_]?chat|chat[-_]?bots?|chat[-_]?widget|chat[-_]?box|'
    r'chat[-_]?window|chat[-_]?launcher|chat[-_]?bubble|chat[-_]?root|chat[-_]?frame|'
    r'chat[-_]?container|chat[-_]?button|chat[-_]?icon|chat[-_]?app|messenger|chat)'
    r'(?![a-z])'
)

# Same, minus the bare "chat" — for attributes a page author writes for their
# own reasons. An <h2 id="lets-chat"> is a heading slug, not a widget.
_CHAT_WIDGET_WORD = (
    r'(?<![a-z])'
    r'(?:live[-_]?chat|web[-_]?chat|chat[-_]?bots?|chat[-_]?widget|chat[-_]?box|'
    r'chat[-_]?window|chat[-_]?launcher|chat[-_]?bubble|chat[-_]?root|chat[-_]?frame|'
    r'chat[-_]?container|chat[-_]?button|chat[-_]?icon|chat[-_]?app|messenger)'
    r'(?![a-z])'
)

GENERIC_PATTERNS: Dict[str, str] = {
    # A script or iframe whose URL is about chat. Only src — an <a href> to
    # /lets-chat is a page, not an embed.
    'chat script/iframe embed':
        r'<(?:script|iframe)\b[^>]*\bsrc\s*=\s*["\'][^"\']*' + _CHAT_WORD + r'[^"\']*["\']',
    # A container the widget mounts into, or the whole value being just "chat".
    'chat widget container':
        r'\b(?:id|class|data-widget|data-testid)\s*=\s*["\'][^"\']*' + _CHAT_WIDGET_WORD +
        r'[^"\']*["\']'
        r'|\b(?:id|class)\s*=\s*["\']\s*chat\s*["\']',
    # Config the embed reads before it boots.
    'chat widget config':
        r'\bdata-chat[a-z-]*\s*=|\bchat[_-]?widget[_-]?(?:settings|config|id|key)\b|'
        r'window\.[a-z_$]*chat(?:bot|widget)[a-z_$]*\s*=',
    # The launcher control itself.
    'chat launcher control':
        r'(?:aria-label|title)\s*=\s*["\'][^"\']{0,40}'
        r'(?:(?:open|close|toggle|start|launch|live|ai|support)[^"\']{0,20}chat|'
        r'chat[^"\']{0,20}(?:widget|window|bot|assistant|with us|now))',
}

# WhatsApp click-to-chat only counts when it is a floating widget, never when
# it is one more icon in a footer social row.
_WHATSAPP_LINK = r'wa\.me/|api\.whatsapp\.com/send|web\.whatsapp\.com/send'
_WHATSAPP_WIDGET_CONTEXT = (
    r'whatsapp[^"\'<>]{0,40}(?:widget|float|button|chat|bubble)|'
    r'(?:widget|float|sticky|fixed|chat|bubble)[^"\'<>]{0,40}whatsapp'
)

_COMPILED_VENDORS = [(name, re.compile(p, re.I)) for name, p in VENDOR_PATTERNS.items()]
_COMPILED_GENERIC = [(name, re.compile(p, re.I)) for name, p in GENERIC_PATTERNS.items()]
_COMPILED_WHATSAPP = (re.compile(_WHATSAPP_LINK, re.I), re.compile(_WHATSAPP_WIDGET_CONTEXT, re.I))

# Custom elements are matched on the tag NAME, not inline in the markup regex:
# a hyphenated name is already proof of a web component, so <chat-widget>,
# <df-messenger> and <zapier-interfaces-chatbot-embed> all land without the
# bare-"chat" looseness that a raw markup scan would need.
_CUSTOM_TAG_RX = re.compile(r'<((?:[a-z0-9]+-)+[a-z0-9]+)(?=[\s/>])', re.I)
_CHAT_WIDGET_RX = re.compile(_CHAT_WIDGET_WORD, re.I)


def _custom_chat_element(html: str) -> bool:
    return any(_CHAT_WIDGET_RX.search(tag) for tag in _CUSTOM_TAG_RX.findall(html))


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


def detect_chat(html: str) -> ChatDetection:
    """Detect a chat/chatbot widget in page markup.

    `html` is every scanned page's HTML concatenated, plus the rendered DOM
    when one was captured. Case does not matter.
    """
    if not html:
        return ChatDetection(False, [], '')

    vendors = [name for name, rx in _COMPILED_VENDORS if rx.search(html)]
    if vendors:
        return ChatDetection(True, vendors, 'vendor embed')

    for signal, rx in _COMPILED_GENERIC:
        if rx.search(html):
            return ChatDetection(True, [], signal)

    if _custom_chat_element(html):
        return ChatDetection(True, [], 'chat custom element')

    link_rx, context_rx = _COMPILED_WHATSAPP
    if link_rx.search(html) and context_rx.search(html):
        return ChatDetection(True, ['WhatsApp'], 'floating WhatsApp chat')

    return ChatDetection(False, [], '')
