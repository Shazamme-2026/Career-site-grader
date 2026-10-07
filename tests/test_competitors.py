"""AI competitor finder: parsing/validation is pure and tested; the Claude call is not.

Run: python3 -m unittest discover -s tests
"""

import ipaddress
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import competitors  # noqa: E402
from unittest import mock  # noqa: E402


def _fake_dns(private=()):
    """getaddrinfo stub: hosts in `private` resolve to 10.0.0.1, others to 93.184.216.34."""
    def fake(host, *a, **k):
        try:
            ip = str(ipaddress.ip_address(host))  # literals resolve to themselves
        except ValueError:
            ip = '10.0.0.1' if host in private else '93.184.216.34'
        return [(None, None, None, None, (ip, 0))]
    return mock.patch('competitors.socket.getaddrinfo', side_effect=fake)


class ParseCompetitors(unittest.TestCase):
    def test_parses_json_block_and_normalises_urls(self):
        text = ('Here you go:\n```json\n{"competitors": [{"url": "www.acme-recruit.com/", '
                '"name": "Acme", "reason": "Same sectors."}, {"url": "https://beta-talent.co.uk", '
                '"name": "Beta Talent", "reason": "Same region."}]}\n```')
        out = competitors.parse_competitors(text, 'www.target.com')
        self.assertEqual([c['url'] for c in out],
                         ['https://www.acme-recruit.com', 'https://beta-talent.co.uk'])
        self.assertEqual(out[0]['name'], 'Acme')
        self.assertEqual(out[1]['reason'], 'Same region.')

    def test_drops_target_and_duplicates_and_caps_at_two(self):
        text = ('{"competitors": [{"url": "https://target.com"}, {"url": "https://a.com"}, '
                '{"url": "http://www.a.com/jobs"}, {"url": "https://b.com"}, {"url": "https://c.com"}]}')
        out = competitors.parse_competitors(text, 'www.target.com')
        self.assertEqual([c['url'] for c in out], ['https://a.com', 'https://b.com'])

    def test_falls_back_to_bare_urls_in_prose(self):
        text = 'Two good matches are https://one.example and https://two.example/about.'
        out = competitors.parse_competitors(text, 'target.com')
        self.assertEqual([c['url'] for c in out], ['https://one.example', 'https://two.example'])

    def test_rejects_job_boards_and_junk(self):
        text = ('{"competitors": [{"url": "https://www.seek.com.au"}, {"url": "javascript:alert(1)"}, '
                '{"url": "https://www.linkedin.com/company/x"}, {"url": "https://real-agency.com"}]}')
        out = competitors.parse_competitors(text, 'target.com')
        self.assertEqual([c['url'] for c in out], ['https://real-agency.com'])

    def test_empty_when_nothing_usable(self):
        self.assertEqual(competitors.parse_competitors('no idea', 'target.com'), [])


class CleanUrls(unittest.TestCase):
    def test_clean_competitor_urls_for_manual_entry(self):
        with _fake_dns():
            out = competitors.clean_urls(['acme.com ', '', 'https://target.com', 'not a url', 'https://b.io/'],
                                         'www.target.com')
        self.assertEqual(out, ['https://acme.com', 'https://b.io'])

    def test_private_and_metadata_addresses_are_rejected(self):
        with _fake_dns(private={'intranet.corp'}):
            out = competitors.clean_urls(['http://169.254.169.254', 'http://10.0.0.1', 'http://127.0.0.1',
                                          'http://[::1]', 'http://intranet.corp', 'https://public.example'],
                                         'target.com')
        self.assertEqual(out, ['https://public.example'])

    def test_unresolvable_host_is_rejected(self):
        with mock.patch('competitors.socket.getaddrinfo', side_effect=OSError('nope')):
            self.assertEqual(competitors.clean_urls(['https://does-not-exist.example'], 't.com'), [])

    def test_junk_input_shapes_do_not_crash(self):
        self.assertEqual(competitors.clean_urls(5, 't.com'), [])
        self.assertEqual(competitors.clean_urls('a.com,b.com', 't.com'), [])
        self.assertEqual(competitors.clean_urls([None, 7, {'u': 1}, 'https://['], 't.com', check_dns=False), [])
        self.assertEqual(competitors.clean_urls(['https://' + 'a' * 300 + '.com'], 't.com', check_dns=False), [])

    def test_blocklist_matches_on_label_boundaries(self):
        self.assertEqual(competitors.clean_urls(['https://apex.com', 'https://wix.com', 'https://x.com',
                                                 'https://www.seek.com.au', 'https://uk.indeed.com'],
                                                't.com', check_dns=False),
                         ['https://apex.com', 'https://wix.com'])

    def test_target_with_port_or_www_is_still_excluded(self):
        self.assertEqual(competitors.clean_urls(['https://target.com', 'https://www.target.com:8443'],
                                                'www.target.com:8443', check_dns=False), [])


if __name__ == '__main__':
    unittest.main()
