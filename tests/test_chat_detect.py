"""Chat/chatbot detection — real embed snippets in, verdict out.

Run: python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat_detect import detect_chat  # noqa: E402


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

    def test_footer_whatsapp_social_icon(self):
        self.assert_not_chat(
            '<ul class="social-links"><li><a href="https://wa.me/61400000000">WhatsApp</a></li>'
            '<li><a href="https://facebook.com/acme">Facebook</a></li></ul>')

    def test_ordinary_recruitment_page(self):
        self.assert_not_chat(
            '<html><head><title>Jobs</title>'
            '<script src="https://www.googletagmanager.com/gtag/js?id=G-X"></script></head>'
            '<body><h1>Search jobs</h1><a href="/apply">Apply now</a></body></html>')


if __name__ == '__main__':
    unittest.main()
