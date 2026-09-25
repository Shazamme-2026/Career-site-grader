"""Chat/chatbot detection — real embed snippets in, verdict out.

Run: python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat_detect import VENDOR_HOSTS, VENDOR_MARKERS, detect_chat  # noqa: E402


class SignatureCoverage(unittest.TestCase):
    """Hosts are matched against harvested URLs and markers against the whole
    document, so a signature filed under the wrong one silently never fires.
    These two tests are what make adding a vendor safe."""

    def test_every_host_is_found_in_a_script_src(self):
        for vendor, hosts in VENDOR_HOSTS.items():
            for host in hosts:
                found = detect_chat(f'<script src="https://{host}/embed.js"></script>').vendors
                self.assertIn(vendor, found, f'{vendor}: host {host} not matched')

    def test_every_marker_is_found_in_plain_markup(self):
        for vendor, markers in VENDOR_MARKERS.items():
            for marker in markers:
                found = detect_chat(f'<div class="{marker}"></div>').vendors
                self.assertIn(vendor, found, f'{vendor}: marker {marker} not matched')


class VendorEmbeds(unittest.TestCase):
    """Named vendors — the snippet each one actually ships."""

    def assert_vendor(self, html, vendor):
        result = detect_chat(html)
        self.assertTrue(result.found, f'{vendor} embed not detected: {html[:80]}')
        self.assertIn(vendor, result.vendors)

    def test_zammenow_on_method_recruitment(self):
        # Verbatim from methodrecruitment.com.au, the site that scored 0/20.
        self.assert_vendor(
            '<script src="https://www.zammenow.com/widget.js" '
            'data-tenant-id="method-recruitment" crossorigin="anonymous" defer></script>',
            'Zammenow')

    def test_zammenow_rendered_dom_container(self):
        self.assert_vendor('<div id="zmn-chat-root-v8"></div>', 'Zammenow')

    def test_intercom(self):
        self.assert_vendor(
            '<script>window.intercomSettings={app_id:"ab12cd34"};'
            's.src="https://widget.intercom.io/widget/ab12cd34";</script>',
            'Intercom')

    def test_tawk_to(self):
        self.assert_vendor(
            "<script>var Tawk_API=Tawk_API||{};"
            "s1.src='https://embed.tawk.to/5f0/default';</script>",
            'Tawk.to')

    def test_zendesk(self):
        self.assert_vendor(
            '<script id="ze-snippet" src="https://static.zdassets.com/ekr/snippet.js?key=x">'
            '</script>',
            'Zendesk')

    def test_dialogflow_messenger(self):
        self.assert_vendor('<df-messenger chat-title="Careers Bot"></df-messenger>',
                           'Dialogflow')

    def test_highlevel_chat_widget(self):
        self.assert_vendor(
            '<script src="https://widgets.leadconnectorhq.com/loader.js" '
            'data-resources-url="https://widgets.leadconnectorhq.com/chat-widget/loader.js">'
            '</script>',
            'HighLevel Chat')

    def test_copilot_studio_iframe(self):
        # Verbatim from artech.com — a live bot the old vendor list missed.
        self.assert_vendor(
            '<iframe src="https://copilotstudio.microsoft.com/environments/Default-c6b1/'
            'bots/cr662_copilotNew/webchat?__version__=2"></iframe>',
            'Copilot Studio')

    def test_loader_snippet_assigning_a_protocol_relative_src(self):
        self.assert_vendor(
            '<script>var s=document.createElement("script"); '
            's.src = "//widget.intercom.io/widget/abc123"; document.body.appendChild(s);</script>',
            'Intercom')

    def test_case_is_irrelevant(self):
        self.assert_vendor(
            '<SCRIPT SRC="https://WWW.Zammenow.COM/widget.js"></SCRIPT>', 'Zammenow')

    def test_reports_every_vendor_it_finds(self):
        result = detect_chat(
            '<script src="https://www.zammenow.com/widget.js"></script>'
            '<script src="https://embed.tawk.to/5f0/default"></script>')
        self.assertEqual(['Zammenow', 'Tawk.to'], result.vendors)


class GenericWidgets(unittest.TestCase):
    """Anything we cannot name still has to score."""

    def assert_generic(self, html):
        result = detect_chat(html)
        self.assertTrue(result.found, f'not detected: {html[:80]}')
        self.assertEqual([], result.vendors)

    def test_self_hosted_chat_script(self):
        self.assert_generic('<script src="/assets/js/chat-widget.min.js"></script>')

    def test_iframe_embed(self):
        self.assert_generic('<iframe src="https://bots.acme.io/webchat/v2?id=9"></iframe>')

    def test_mount_container(self):
        self.assert_generic('<div id="chat-root"></div>')

    def test_container_class(self):
        self.assert_generic('<div class="fixed bottom-4 right-4 chat-launcher"></div>')

    def test_custom_element(self):
        self.assert_generic('<acme-chatbot tenant="9"></acme-chatbot>')

    def test_hyphenated_custom_element_with_attributes(self):
        self.assert_generic('<chat-widget location-id="abc123"></chat-widget>')

    def test_chat_js_filename(self):
        self.assert_generic('<script src="/js/chat.js"></script>')

    def test_bare_chat_container_id(self):
        self.assert_generic('<div id="chat"></div>')

    def test_widget_config_attribute(self):
        self.assert_generic('<div data-chatbot-id="42"></div>')

    def test_launcher_aria_label(self):
        self.assert_generic('<button aria-label="Open live chat"><svg/></button>')

    def test_floating_whatsapp_widget(self):
        result = detect_chat(
            '<a class="whatsapp-float" href="https://wa.me/61400000000">Chat</a>')
        self.assertTrue(result.found)
        self.assertEqual(['WhatsApp'], result.vendors)

    def test_container_class_with_a_long_utility_list(self):
        # The window around the needle must not cut the attribute short.
        self.assert_generic(
            '<div class="chat-widget fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center '
            'justify-center rounded-full bg-indigo-600 text-white shadow-lg transition '
            'hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-offset-2"></div>')

    def test_script_src_with_a_long_query_string(self):
        self.assert_generic(
            '<script src="/assets/chat-widget.js?v=8&amp;site=acme&amp;region=au&amp;'
            'theme=dark&amp;locale=en-AU&amp;build=20260925&amp;cachebust=1758777600"></script>')

    def test_floating_iframe_with_a_long_attribute_list(self):
        # Real embeds carry title/allow/sandbox/loading/style before src, which
        # pushes the tag start far back from the "chat" in the URL.
        style = ('position:fixed;bottom:20px;right:20px;width:60px;height:60px;border:none;'
                 'z-index:999999;box-shadow:0 5px 40px rgba(0,0,0,.16);border-radius:50%;'
                 'transition:all .3s ease-in-out;background:#fff;overflow:hidden;'
                 'pointer-events:auto;-webkit-transform:translateZ(0);will-change:transform;')
        self.assert_generic(
            f'<iframe title="Support widget" allow="microphone; camera" '
            f'sandbox="allow-scripts allow-same-origin allow-popups allow-forms" '
            f'loading="lazy" allowtransparency="true" frameborder="0" scrolling="no" '
            f'style="{style}" src="https://bots.acme.io/webchat/v2?id=9"></iframe>')

    def test_floating_whatsapp_button_on_a_wrapper(self):
        # The plugin shape in the wild: the wrapper positions it, the anchor
        # carries nothing but the link.
        result = detect_chat(
            '<div class="whatsapp-float-button" style="position:fixed;bottom:20px;right:20px">'
            '<a href="https://wa.me/61400000000"><img src="/wa-icon.svg" alt="WhatsApp"></a></div>')
        self.assertTrue(result.found)
        self.assertEqual(['WhatsApp'], result.vendors)

    def test_summary_names_the_signal(self):
        self.assertIn('unrecognised provider', detect_chat('<div id="chat-root"></div>').summary)


class NotChat(unittest.TestCase):
    """Copy about chatting is not a chatbot. These are the false positives
    that would hand a site 20 points and a wrong recommendation."""

    def assert_not_chat(self, html):
        self.assertFalse(detect_chat(html).found, f'false positive: {html[:80]}')

    def test_empty(self):
        self.assert_not_chat('')

    def test_prose_and_heading_slug(self):
        self.assert_not_chat(
            '<h2 id="lets-chat">Let\'s chat</h2>'
            '<p>Come and chat with our team about your next role.</p>'
            '<a href="/lets-chat">Chat to us</a>')

    def test_words_containing_chat(self):
        # Every one of these goes through a rule that WOULD fire on a bare
        # "chat" substring: script src, iframe src, class attribute.
        self.assert_not_chat(
            '<script src="/js/chatterbox-tracker.js"></script>'
            '<iframe src="/tours/chateau-estate"></iframe>'
            '<div class="chatter-feed" id="chatham-house"></div>')

    def test_snapchat(self):
        # The social pixel every other recruitment site loads.
        self.assert_not_chat(
            '<script src="/js/snapchat.js"></script>'
            '<a class="social-icon snapchat" href="https://snapchat.com/add/acme">Snapchat</a>')

    def test_compound_glued_into_a_longer_word(self):
        # "chatbox"/"livechat" only count as whole words.
        self.assert_not_chat(
            '<div class="chatboxing-club" id="livechatterbox"></div>'
            '<script src="/js/prechatbotic.js"></script>')

    def test_footer_whatsapp_social_icon(self):
        self.assert_not_chat(
            '<ul class="social-links"><li><a href="https://wa.me/61400000000">WhatsApp</a></li>'
            '<li><a href="https://facebook.com/acme">Facebook</a></li></ul>')

    def test_ai_inside_another_word_is_not_a_launcher(self):
        # "Em[ai]l or chat" — the launcher keywords have to be whole words.
        self.assert_not_chat('<a href="/contact" title="Email or chat to a consultant">Contact</a>')

    def test_marketing_copy_in_a_data_attribute(self):
        # Only a control's own label counts, not every attribute ending in "title".
        self.assert_not_chat(
            '<div data-subtitle="Live chat support for every client"></div>')

    def test_footer_messenger_social_icon(self):
        self.assert_not_chat(
            '<ul class="social"><li><a class="social-icon messenger" href="https://m.me/acme">'
            'Messenger</a></li></ul>')

    def test_blog_post_iframe_slug(self):
        self.assert_not_chat('<iframe src="/blog/lets-chat-about-hiring"></iframe>')

    def test_data_attribute_starting_with_chat(self):
        self.assert_not_chat('<div data-chateau="loire" data-chatham="house"></div>')

    def test_whatsapp_link_and_prose_on_different_pages(self):
        # detect_chat is handed every crawled page concatenated. A plain footer
        # link on the homepage plus unrelated prose five pages later is not a
        # floating widget.
        footer = ('<footer><ul class="social-links">'
                  '<li><a href="https://wa.me/61400000000">WhatsApp</a></li></ul></footer>')
        blog = ('<article><p>A floating contact widget is popular, and many firms '
                'link to WhatsApp instead of building a chat stack.</p></article>')
        self.assert_not_chat(footer + ' ' + blog)

    def test_link_to_a_vendor_the_site_merely_mentions(self):
        # A help-centre link and a blog mention are not installs.
        self.assert_not_chat(
            '<a href="https://acme.zendesk.com/hc/en-au">Help centre</a>'
            '<p>We compared <a href="https://drift.com/blog/pricing">Drift</a> and Chatwoot.</p>')

    def test_bootstrap_float_utility_on_a_whatsapp_link(self):
        self.assert_not_chat(
            '<a class="float-end sticky-top" href="https://wa.me/61400000000">WhatsApp</a>')

    def test_contact_link_with_a_tooltip(self):
        self.assert_not_chat('<a class="btn" href="/contact" title="Chat with us now">Contact</a>')

    def test_messenger_in_a_path(self):
        self.assert_not_chat(
            '<iframe src="/blog/facebook-messenger-for-recruiters"></iframe>'
            '<script src="/js/messenger-share.js"></script>')

    def test_whatsapp_social_icon_with_prefilled_message(self):
        # The ?text= pre-fill routinely contains the word "chat".
        self.assert_not_chat(
            '<ul class="social-links"><li><a class="social-icon" '
            'href="https://wa.me/61400000000?text=Hi%2C%20I%27d%20like%20to%20chat%20about%20a%20role">'
            'WhatsApp</a></li></ul>')

    def test_ordinary_recruitment_page(self):
        self.assert_not_chat(
            '<html><head><title>Jobs</title>'
            '<script src="https://www.googletagmanager.com/gtag/js?id=G-X"></script></head>'
            '<body><h1>Search jobs</h1><a href="/apply">Apply now</a></body></html>')


if __name__ == '__main__':
    unittest.main()
