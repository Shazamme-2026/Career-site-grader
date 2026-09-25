"""The Live Chat & Chatbot check as the grader actually emits it.

Run: python3 -m unittest discover -s tests
"""

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bs4 import BeautifulSoup  # noqa: E402

from grader import CareerSiteGrader  # noqa: E402

PAGE = """<html><head><title>Method Recruitment</title>
{embed}
</head><body><h1>Find your next role</h1>
<a href="/jobs">Search jobs</a><a href="/apply">Apply now</a>
</body></html>"""

ZAMMENOW = ('<script src="https://www.zammenow.com/widget.js" '
            'data-tenant-id="method-recruitment" crossorigin="anonymous" defer></script>')


def chat_check(embed):
    grader = CareerSiteGrader('https://example.com', mode='recruitment', light=True)
    grader.html = PAGE.format(embed=embed)
    grader.soup = BeautifulSoup(grader.html, 'html.parser')
    pillar = asyncio.run(grader._analyze_conversion())
    return next(c for c in pillar['checks'] if c['name'] == 'Live Chat & Chatbot')


class LiveChatCheck(unittest.TestCase):

    def test_zammenow_site_scores_full_marks(self):
        check = chat_check(ZAMMENOW)
        self.assertEqual(20, check['score'])
        self.assertEqual('Zammenow', check['value'])
        self.assertIn('Zammenow', check['detail'])

    def test_site_without_chat_scores_zero(self):
        check = chat_check('')
        self.assertEqual(0, check['score'])
        self.assertIsNone(check['value'])
        self.assertIn('No chat/chatbot found', check['detail'])


if __name__ == '__main__':
    unittest.main()
