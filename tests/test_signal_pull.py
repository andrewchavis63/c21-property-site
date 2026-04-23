import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import signal_pull as sp


class TestSkeleton(unittest.TestCase):
    def test_constants_defined(self):
        self.assertEqual(len(sp.SUBREDDITS), 5)
        self.assertIn('FortWorth', sp.SUBREDDITS)
        self.assertEqual(len(sp.RSS_FEEDS), 5)
        self.assertIn('Inman', sp.RSS_FEEDS)


if __name__ == '__main__':
    unittest.main()
