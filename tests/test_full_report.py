"""Server-rendered technical report: complete, escaped, and robust to sparse data.

Run: python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import full_report  # noqa: E402


def sample(**over):
    base = {
        'report_id': 'abc123', 'url': 'https://www.example-recruit.com', 'domain': 'www.example-recruit.com',
        'overall_score': 58, 'grade': 'C+', 'grade_label': 'Below Average', 'mode': 'recruitment',
        'response_time': 0.42, 'word_count': 1200, 'status_code': 200,
        'pages_scanned': ['homepage', '/jobs', '/about'],
        'pillars': {
            'seo': {'name': 'SEO & Discoverability', 'score': 57, 'grade': 'C+', 'color': '#6366f1', 'icon': 'search',
                    'summary': 'Several SEO gaps.', 'checks': [
                        {'name': 'Title Tag', 'status': 'pass', 'score': 13, 'max': 15, 'detail': 'Title is 68 chars',
                         'value': 'Example <b>Recruit</b>'},
                        {'name': 'H1 Heading', 'status': 'warn', 'score': 7, 'max': 10,
                         'detail': 'H1 present on 25 of 34 pages', 'help': 'Use exactly one <h1>.',
                         'items': ['/a', '/b', '/c', '/d', '/e', '/f', '/g', '/h', '/i', '/j']},
                        {'name': 'XML Sitemap', 'status': 'fail', 'score': 0, 'max': 8, 'detail': 'No sitemap'},
                    ]},
            'geo': {'name': 'GEO & AI Visibility', 'score': 41, 'grade': 'C', 'color': '#8b5cf6', 'icon': 'bolt',
                    'summary': 'Weak.', 'checks': []},
        },
        'executive_summary': {'verdict': 'Meaningful value is being left on the table.',
                              'strengths': ['Candidate Experience'],
                              'top_opportunities': [{'title': 'Recruitment Content Streams', 'pillar': 'SEO & Discoverability',
                                                     'why_it_matters': 'Owns both sides of search.',
                                                     'how_to_fix': 'Build sector pages.'}]},
        'recommendations': [{'priority': 'critical', 'pillar': 'SEO & Discoverability', 'pillar_color': '#6366f1',
                             'check': 'Recruitment Content Streams', 'score': 0, 'max': 15, 'detail': 'None found',
                             'impact': 'Highest-traffic asset', 'how_to_fix': 'Build sector pages.',
                             'value': None, 'items': None, 'links': [{'label': 'Verify robots.txt', 'url': 'https://x/robots.txt'}]}],
        'core_web_vitals': {'perf_score': 52, 'runs': 2, 'has_field': False,
                            'field': {'lcp': {'p75': None, 'rating': None}},
                            'lab': {'lcp_ms': 4100.4, 'fcp_ms': 2100, 'cls': 0.12, 'tbt_ms': 300, 'si_ms': 5000, 'ttfb_ms': 500},
                            'issues': [{'title': 'Reduce unused JavaScript', 'display': 'Est savings of 893 KiB', 'savings_ms': 3000}]},
        'benchmark': {'average': 68, 'beats_pct': 16, 'percentile': 16, 'sample': 157, 'ready': True},
        'authority': {'rank': 151, 'referring_domains': 119, 'backlinks': 1983, 'provider': 'DataForSEO'},
        'history': [{'at': 1791415434.6, 'grade': 'C+', 'overall': 59}],
        'platform': {'platform': 'Squarespace', 'category': 'proprietary'},
        'tech_stack_summary': {'headline': 'On Squarespace.', 'body': 'Locked down.', 'platform': 'Squarespace'},
        'coverage': {'content_pages': 34, 'total_pages': 136, 'job_pages': 0, 'crawl_capped': True,
                     'h1_missing': ['/a'], 'duplicate_headings': {'cross_page': [{'text': 'x'}], 'same_page': []}},
        'shazamme_advantage': [{'gap': 'No chatbot', 'feature': 'AI Recruitment Chatbot',
                                'description': 'Answers 24/7.', 'stat': 'Reduces drop-off by up to 40%'}],
        'comparison': {'target': {'domain': 'www.example-recruit.com', 'overall_score': 58, 'grade': 'C+',
                                  'pillars': {'seo': 57, 'geo': 41}},
                       'competitors': [{'url': 'https://a.com', 'domain': 'a.com', 'overall_score': 71, 'grade': 'B',
                                        'pillars': {'seo': 70, 'geo': 50}},
                                       {'url': 'https://b.com', 'domain': 'b.com', 'error': 'HTTP 403'}],
                       'rank': 2, 'field_size': 2},
    }
    base.update(over)
    return base


class Html(unittest.TestCase):
    def test_every_section_is_present(self):
        html = full_report.build_html(sample())
        for text in ('Executive Summary', 'Pillar Scores', 'Competitor Benchmark', 'Core Web Vitals',
                     'Detailed Findings', 'Priority Recommendations', 'Shazamme Advantage', 'Coverage',
                     'Title Tag', 'H1 Heading', 'XML Sitemap', 'Recruitment Content Streams',
                     'Reduce unused JavaScript', 'a.com', 'Beats', '16%', 'Squarespace', '/r/abc123'):
            self.assertIn(text, html, text)

    def test_untrusted_text_is_escaped(self):
        html = full_report.build_html(sample(domain='<script>alert(1)</script>'))
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertNotIn('<b>Recruit</b>', html)      # check value
        self.assertIn('&lt;h1&gt;', html)              # help text

    def test_long_item_lists_are_capped(self):
        html = full_report.build_html(sample())
        self.assertIn('+2 more', html)

    def test_sparse_report_does_not_crash(self):
        html = full_report.build_html({'overall_score': 40, 'domain': 'x.com', 'pillars': {}})
        self.assertIn('40', html)
        self.assertNotIn('Core Web Vitals', html)
        self.assertNotIn('Competitor Benchmark', html)

    def test_odd_values_do_not_crash_and_are_escaped(self):
        rep = sample(overall_score='n/a', history=[{'overall': None}, {'overall': 'x'}])
        rep['pillars']['seo']['score'] = 'bad'
        rep['pillars']['seo']['checks'][0]['status'] = ['weird']
        rep['pillars']['seo']['checks'][0]['score'] = '<img onerror=1>'
        rep['pillars']['seo']['checks'][0]['value'] = 'v' * 2000
        rep['comparison']['competitors'][0]['overall_score'] = '<b>'
        html = full_report.build_html(rep)
        self.assertNotIn('<img onerror=1>', html)
        self.assertNotIn('v' * 400, html)

    def test_priority_order_and_check_counts(self):
        html = full_report.build_html(sample())
        self.assertIn('3 checks', html)
        self.assertLess(html.index('Executive Summary'), html.index('Detailed Findings'))
        self.assertLess(html.index('Detailed Findings'), html.index('Priority Recommendations'))


if __name__ == '__main__':
    unittest.main()
