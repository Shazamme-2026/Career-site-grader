"""The client-facing opportunity report: plain English, no jargon, safe HTML.

Run: python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import client_report  # noqa: E402


def sample(**over):
    base = {
        'report_id': 'abc123',
        'url': 'https://www.example-recruit.com',
        'domain': 'www.example-recruit.com',
        'overall_score': 58,
        'grade': 'C+',
        'grade_label': 'Below Average',
        'mode': 'recruitment',
        'pillars': {
            'seo': {'name': 'SEO & Discoverability', 'score': 57},
            'geo': {'name': 'GEO & AI Visibility', 'score': 41},
            'cx': {'name': 'Candidate Experience', 'score': 87},
            'brand': {'name': 'Employer Brand & Content', 'score': 60},
            'technical': {'name': 'Technical Performance', 'score': 64},
            'conversion': {'name': 'Conversion & Engagement', 'score': 20},
        },
        'executive_summary': {
            'strengths': ['Candidate Experience'],
            'weakest_pillars': [{'name': 'Conversion & Engagement', 'score': 20}],
        },
        'recommendations': [
            {'priority': 'critical', 'pillar': 'SEO & Discoverability',
             'check': 'Recruitment Content Streams', 'detail': 'd', 'impact': 'i'},
            {'priority': 'critical', 'pillar': 'SEO & Discoverability',
             'check': 'Industry & Sector Pages', 'detail': 'd', 'impact': 'i'},
            {'priority': 'critical', 'pillar': 'Conversion & Engagement',
             'check': 'Live Chat & Chatbot', 'detail': 'd', 'impact': 'i'},
            {'priority': 'high', 'pillar': 'GEO & AI Visibility',
             'check': 'llms.txt File', 'detail': 'd', 'impact': 'i'},
            {'priority': 'high', 'pillar': 'Technical Performance',
             'check': 'Lighthouse Performance', 'detail': 'd', 'impact': 'i'},
            {'priority': 'medium', 'pillar': 'Candidate Experience',
             'check': 'Mobile Readiness', 'detail': 'd', 'impact': 'i'},
            {'priority': 'low', 'pillar': 'Candidate Experience',
             'check': 'Some Unknown Check <b>', 'detail': 'raw <detail>',
             'impact': 'raw impact'},
        ],
        'shazamme_advantage': [
            {'gap': 'No chatbot or live engagement', 'feature': 'AI Recruitment Chatbot',
             'description': 'Answers 24/7.', 'stat': 'Reduces drop-off by up to 40%'},
            {'gap': 'Missing or weak schema markup', 'feature': 'Auto Schema Engine',
             'description': 'Generates JobPosting, FAQPage and BreadcrumbList schema.',
             'stat': '3× higher CTR from rich snippets'},
            {'gap': 'Invisible to AI search engines', 'feature': 'GEO-Ready Out of the Box',
             'description': 'Ships llms.txt, llm-info and FAQPage schema.',
             'stat': 'Ranks in AI-generated job search answers'},
        ],
        'benchmark': {'average': 68, 'percentile': 16, 'sample': 157, 'ready': True},
    }
    base.update(over)
    return base


class OpportunityTranslation(unittest.TestCase):
    def test_known_checks_become_plain_english(self):
        opps = client_report.opportunities(sample())
        titles = [o['title'] for o in opps]
        self.assertIn('Pages for every sector you recruit in', titles)
        self.assertIn('Answering candidate questions instantly', titles)
        for o in opps:
            self.assertNotIn('schema', o['title'].lower())
            self.assertNotIn('llms', o['title'].lower())

    def test_duplicate_plain_titles_are_collapsed(self):
        # 'Recruitment Content Streams' and 'Industry & Sector Pages' are the
        # same opportunity to a client; they must appear once.
        opps = client_report.opportunities(sample())
        titles = [o['title'] for o in opps]
        self.assertEqual(len(titles), len(set(titles)))

    def test_capped_and_priority_ordered(self):
        opps = client_report.opportunities(sample(), limit=3)
        self.assertEqual(len(opps), 3)
        self.assertEqual(opps[0]['title'], 'Pages for every sector you recruit in')

    def test_unknown_check_falls_back_to_grader_text(self):
        recs = [{'priority': 'high', 'pillar': 'Candidate Experience',
                 'check': 'Some Unknown Check', 'detail': 'the detail',
                 'impact': 'the impact', 'how_to_fix': 'the fix'}]
        opps = client_report.opportunities(sample(recommendations=recs))
        self.assertEqual(opps[0]['title'], 'Some Unknown Check')
        self.assertEqual(opps[0]['why'], 'the impact')
        self.assertEqual(opps[0]['great'], 'the fix')

    def test_no_recommendations_yields_empty(self):
        self.assertEqual(client_report.opportunities(sample(recommendations=[])), [])


class PillarTranslation(unittest.TestCase):
    def test_pillars_are_renamed_and_ordered_weakest_first(self):
        rows = client_report.pillar_rows(sample())
        self.assertEqual(rows[0]['label'], 'Turning visitors into candidates and clients')
        self.assertEqual(rows[0]['score'], 20)
        self.assertEqual(rows[-1]['score'], 87)
        self.assertTrue(all('GEO' not in r['label'] for r in rows))


class Html(unittest.TestCase):
    def test_html_escapes_untrusted_report_text(self):
        html = client_report.build_html(sample(domain='<script>alert(1)</script>'))
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', html)
        # fallback text from an unknown check is escaped too
        self.assertNotIn('<detail>', html)

    def test_html_contains_the_story_not_the_jargon(self):
        html = client_report.build_html(sample())
        self.assertIn('58', html)
        self.assertIn('Below Average', html)
        self.assertIn('An AI assistant on every page', html)
        self.assertNotIn('rich snippets', html)
        self.assertIn('/r/abc123', html)
        for word in ('GEO', 'schema', 'llms.txt', 'Lighthouse', 'H1', 'JobPosting', 'FAQPage'):
            self.assertNotIn(word, html, word)

    def test_advantage_copy_is_translated(self):
        html = client_report.build_html(sample())
        self.assertIn('Rich Google job listings, automatically', html)
        self.assertIn('Recommended by ChatGPT and Google AI', html)

    def test_logo_data_uri_is_used_when_given(self):
        html = client_report.build_html(sample(), logo_src='data:image/png;base64,AAAA')
        self.assertIn('data:image/png;base64,AAAA', html)

    def test_minimal_report_does_not_crash(self):
        html = client_report.build_html({'overall_score': 40, 'domain': 'x.com'})
        self.assertIn('40', html)


if __name__ == '__main__':
    unittest.main()
