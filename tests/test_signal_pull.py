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


MOCK_REDDIT_JSON = {
    "data": {
        "children": [
            {
                "data": {
                    "title": "Is Fort Worth still affordable for first-time buyers?",
                    "score": 342,
                    "num_comments": 87,
                    "permalink": "/r/FortWorth/comments/abc123/test/",
                    "selftext": "Looking at homes in Saginaw area...",
                    "stickied": False,
                }
            },
            {
                "data": {
                    "title": "Sticky announcement",
                    "score": 1,
                    "num_comments": 0,
                    "permalink": "/r/FortWorth/comments/xyz/sticky/",
                    "selftext": "",
                    "stickied": True,
                }
            }
        ]
    }
}


class TestParseRedditResponse(unittest.TestCase):
    def test_parses_non_stickied_threads(self):
        result = sp.parse_reddit_response(MOCK_REDDIT_JSON, 'FortWorth')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], 'Is Fort Worth still affordable for first-time buyers?')

    def test_thread_has_required_fields(self):
        result = sp.parse_reddit_response(MOCK_REDDIT_JSON, 'FortWorth')
        for field in ['title', 'score', 'num_comments', 'url', 'subreddit', 'selftext_preview']:
            self.assertIn(field, result[0])

    def test_url_includes_reddit_domain(self):
        result = sp.parse_reddit_response(MOCK_REDDIT_JSON, 'FortWorth')
        self.assertTrue(result[0]['url'].startswith('https://reddit.com'))

    def test_skips_stickied_posts(self):
        result = sp.parse_reddit_response(MOCK_REDDIT_JSON, 'FortWorth')
        titles = [t['title'] for t in result]
        self.assertNotIn('Sticky announcement', titles)

    def test_empty_children_returns_empty_list(self):
        result = sp.parse_reddit_response({'data': {'children': []}}, 'FortWorth')
        self.assertEqual(result, [])


MOCK_RSS_XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Mortgage rates hit 2026 low</title>
      <link>https://www.inman.com/2026/04/23/mortgage-rates/</link>
      <description>Rates dropped to 6.5% this week according to Freddie Mac</description>
      <pubDate>Wed, 23 Apr 2026 10:00:00 +0000</pubDate>
    </item>
    <item>
      <title>DFW housing inventory rises for third straight month</title>
      <link>https://www.inman.com/2026/04/22/dfw-inventory/</link>
      <description>More listings hitting the market in Tarrant County</description>
      <pubDate>Tue, 22 Apr 2026 09:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>'''


class TestParseRssFeed(unittest.TestCase):
    def test_parses_two_items(self):
        result = sp.parse_rss_feed(MOCK_RSS_XML, 'Inman')
        self.assertEqual(len(result), 2)

    def test_item_has_required_fields(self):
        result = sp.parse_rss_feed(MOCK_RSS_XML, 'Inman')
        for field in ['title', 'url', 'description', 'pub_date', 'source']:
            self.assertIn(field, result[0])

    def test_source_label_preserved(self):
        result = sp.parse_rss_feed(MOCK_RSS_XML, 'Inman')
        self.assertEqual(result[0]['source'], 'Inman')

    def test_first_item_title(self):
        result = sp.parse_rss_feed(MOCK_RSS_XML, 'Inman')
        self.assertEqual(result[0]['title'], 'Mortgage rates hit 2026 low')

    def test_invalid_xml_returns_empty(self):
        result = sp.parse_rss_feed(b'not valid xml <<<', 'TestFeed')
        self.assertEqual(result, [])


MOCK_RENTCAST_RESPONSE = {
    "averageRent": 1850,
    "rentYoYChange": 3.2,
    "vacancyRate": 0.04,
    "daysOnMarket": 18,
}


class TestParseRentcastResponse(unittest.TestCase):
    def test_parses_median_rent(self):
        result = sp.parse_rentcast_response(MOCK_RENTCAST_RESPONSE)
        self.assertEqual(result['median_rent'], 1850)

    def test_parses_yoy_change(self):
        result = sp.parse_rentcast_response(MOCK_RENTCAST_RESPONSE)
        self.assertAlmostEqual(result['rent_yoy_change'], 3.2)

    def test_result_has_city_and_state(self):
        result = sp.parse_rentcast_response(MOCK_RENTCAST_RESPONSE)
        self.assertEqual(result['city'], 'Fort Worth')
        self.assertEqual(result['state'], 'TX')

    def test_empty_dict_returns_empty_dict(self):
        result = sp.parse_rentcast_response({})
        self.assertEqual(result, {})

    def test_list_response_uses_first_item(self):
        result = sp.parse_rentcast_response([MOCK_RENTCAST_RESPONSE])
        self.assertEqual(result['median_rent'], 1850)

    def test_pulled_at_is_set(self):
        result = sp.parse_rentcast_response(MOCK_RENTCAST_RESPONSE)
        self.assertIn('pulled_at', result)
        self.assertTrue(result['pulled_at'].startswith('20'))


class TestGenerateAngles(unittest.TestCase):
    def setUp(self):
        self.reddit = [
            {
                'title': f'Fort Worth topic {i}',
                'score': 200 - i * 20,
                'num_comments': 60 - i * 5,
                'url': f'https://reddit.com/r/FortWorth/{i}',
                'subreddit': 'FortWorth',
                'selftext_preview': '',
            }
            for i in range(5)
        ]
        self.rss = [
            {
                'title': f'News item {i}',
                'url': f'https://inman.com/{i}',
                'description': '',
                'pub_date': '',
                'source': 'Inman',
            }
            for i in range(3)
        ]
        self.market = {
            'median_rent': 1850,
            'rent_yoy_change': 3.2,
            'vacancy_rate': 0.04,
            'days_on_market': 18,
            'pulled_at': '2026-04-23T05:00:00+00:00',
            'source_url': 'https://app.rentcast.io',
        }

    def test_returns_exactly_seven_angles(self):
        result = sp.generate_angles(self.reddit, self.rss, self.market)
        self.assertEqual(len(result), 7)

    def test_each_angle_has_required_fields(self):
        result = sp.generate_angles(self.reddit, self.rss, self.market)
        for angle in result:
            for field in ['rank', 'headline', 'format', 'seo_keyword',
                          'competition', 'source_type', 'source_title', 'source_url']:
                self.assertIn(field, angle, f"Missing field '{field}' in angle: {angle}")

    def test_ranks_are_1_through_7(self):
        result = sp.generate_angles(self.reddit, self.rss, self.market)
        ranks = sorted(a['rank'] for a in result)
        self.assertEqual(ranks, [1, 2, 3, 4, 5, 6, 7])

    def test_fallback_angle_when_no_market_data(self):
        result = sp.generate_angles(self.reddit[:3], self.rss[:2], {})
        self.assertEqual(len(result), 7)
        fallback = next((a for a in result if a['source_type'] == 'fallback'), None)
        self.assertIsNotNone(fallback)

    def test_format_values_are_valid(self):
        valid_formats = {'blog', 'social', 'youtube', 'screen_recording', 'fallback'}
        result = sp.generate_angles(self.reddit, self.rss, self.market)
        for angle in result:
            self.assertIn(angle['format'], valid_formats)

    def test_headlines_mention_fort_worth_or_tarrant(self):
        result = sp.generate_angles(self.reddit, self.rss, self.market)
        for angle in result:
            combined = (angle['headline'] + angle['seo_keyword']).lower()
            self.assertTrue(
                'fort worth' in combined or 'tarrant' in combined,
                f"Angle missing geo target: {angle['headline']}"
            )


SAMPLE_DATA = {
    'pulled_at': '2026-04-23T05:00:00+00:00',
    'reddit': [
        {'title': 'Fort Worth topic', 'score': 200, 'num_comments': 60,
         'url': 'https://reddit.com/r/FortWorth/1', 'subreddit': 'FortWorth',
         'selftext_preview': ''}
    ],
    'rss': [
        {'title': 'Mortgage rates drop', 'url': 'https://inman.com/1',
         'description': 'Rates fell this week', 'pub_date': 'Wed, 23 Apr 2026',
         'source': 'Inman'}
    ],
    'market': {
        'median_rent': 1850, 'rent_yoy_change': 3.2, 'vacancy_rate': 0.04,
        'days_on_market': 18, 'pulled_at': '2026-04-23T05:00:00+00:00',
        'source_url': 'https://app.rentcast.io'
    },
    'angles': [
        {
            'rank': 1, 'headline': 'Fort Worth Real Estate: Fort Worth topic',
            'format': 'blog', 'seo_keyword': 'fort worth forthworth 2026',
            'competition': 'low', 'source_type': 'reddit',
            'source_title': 'Fort Worth topic',
            'source_url': 'https://reddit.com/r/FortWorth/1',
            'engagement_score': 320
        }
    ],
}


class TestOutputFiles(unittest.TestCase):
    def test_write_data_json_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'data.json')
            sp.write_data_json(SAMPLE_DATA, path)
            self.assertTrue(os.path.exists(path))

    def test_write_data_json_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'data.json')
            sp.write_data_json(SAMPLE_DATA, path)
            with open(path) as f:
                loaded = json.load(f)
            self.assertEqual(loaded['pulled_at'], '2026-04-23T05:00:00+00:00')

    def test_generate_html_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'brief.html')
            sp.generate_html(SAMPLE_DATA, path)
            self.assertTrue(os.path.exists(path))

    def test_generate_html_contains_required_sections(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'brief.html')
            sp.generate_html(SAMPLE_DATA, path)
            with open(path) as f:
                html = f.read()
            self.assertIn('SIGNAL', html)
            self.assertIn('Content Angles', html)
            self.assertIn('Market Snapshot', html)
            self.assertIn('Reddit Hot Topics', html)
            self.assertIn('News Angles', html)

    def test_generate_html_includes_pulled_date(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'brief.html')
            sp.generate_html(SAMPLE_DATA, path)
            with open(path) as f:
                html = f.read()
            self.assertIn('2026-04-23', html)

    def test_generate_html_includes_market_rent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'brief.html')
            sp.generate_html(SAMPLE_DATA, path)
            with open(path) as f:
                html = f.read()
            self.assertIn('1,850', html)

    def test_generate_html_warns_when_no_market_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'brief.html')
            data = dict(SAMPLE_DATA, market={})
            sp.generate_html(data, path)
            with open(path) as f:
                html = f.read()
            self.assertIn('unavailable', html)


if __name__ == '__main__':
    unittest.main()
