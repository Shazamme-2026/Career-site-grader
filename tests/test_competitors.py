"""AI competitor finder: parsing/validation is pure and tested; the Claude call is not.

Run: python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import competitors  # noqa: E402


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
        out = competitors.clean_urls(['acme.com ', '', 'https://target.com', 'not a url', 'https://b.io/'],
                                     'www.target.com')
        self.assertEqual(out, ['https://acme.com', 'https://b.io'])


if __name__ == '__main__':
    unittest.main()
