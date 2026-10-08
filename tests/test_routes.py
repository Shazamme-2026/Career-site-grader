"""Every public route the front end and integrations depend on must stay registered."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server  # noqa: E402

REQUIRED = [
    '/', '/grade', '/health', '/api/logo', '/methodology', '/lead', '/api/history', '/api/cwv',
    '/api/grade', '/api/report/<report_id>', '/r/<report_id>', '/r/<report_id>/client',
    '/r/<report_id>/client.pdf', '/r/<report_id>/full', '/r/<report_id>/full.pdf',
    '/api/competitors', '/api/compare', '/cron/rescore', '/cron/seed', '/api/outcome',
    '/cron/calibrate', '/stats',
]


class Routes(unittest.TestCase):
    def test_required_routes_are_registered(self):
        rules = {r.rule for r in server.app.url_map.iter_rules()}
        missing = [r for r in REQUIRED if r not in rules]
        self.assertEqual(missing, [])


if __name__ == '__main__':
    unittest.main()
