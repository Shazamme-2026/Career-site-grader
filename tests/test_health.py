"""/health has to name the build, or a release cannot be verified.

Run: python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server  # noqa: E402


class Health(unittest.TestCase):

    def setUp(self):
        self.client = server.app.test_client()
        self.original = os.environ.get('RAILWAY_GIT_COMMIT_SHA')

    def tearDown(self):
        if self.original is None:
            os.environ.pop('RAILWAY_GIT_COMMIT_SHA', None)
        else:
            os.environ['RAILWAY_GIT_COMMIT_SHA'] = self.original

    def test_reports_the_deployed_commit(self):
        os.environ['RAILWAY_GIT_COMMIT_SHA'] = 'a1b2c3d4e5f6'
        body = self.client.get('/health').get_json()
        self.assertEqual('ok', body['status'])
        self.assertEqual('a1b2c3d4e5f6', body['commit'])

    def test_says_unknown_off_railway(self):
        os.environ.pop('RAILWAY_GIT_COMMIT_SHA', None)
        self.assertEqual('unknown', self.client.get('/health').get_json()['commit'])
