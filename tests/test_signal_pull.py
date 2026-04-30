import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import signal_pull as sp


class TestConstants(unittest.TestCase):
    def test_reddit_rss_feeds_defined(self):
        self.assertEqual(len(sp.REDDIT_RSS_FEEDS), 5)
        self.assertIn('FortWorth', sp.REDDIT_RSS_FEEDS)
        self.assertIn('landlord', sp.REDDIT_RSS_FEEDS)
        self.assertIn('realestate', sp.REDDIT_RSS_FEEDS)

    def test_rss_feeds_defined(self):
        self.assertEqual(len(sp.RSS_FEEDS), 12)
        self.assertIn('FortWorthReport', sp.RSS_FEEDS)
        self.assertIn('PaperCity', sp.RSS_FEEDS)
        self.assertIn('WFAA', sp.RSS_FEEDS)
        self.assertIn('NBCDFW', sp.RSS_FEEDS)
        self.assertIn('FWWeekly', sp.RSS_FEEDS)
        self.assertIn('RealTrends', sp.RSS_FEEDS)
        self.assertIn('Redfin', sp.RSS_FEEDS)

    def test_reddit_feeds_are_rss_urls(self):
        for sub, url in sp.REDDIT_RSS_FEEDS.items():
            self.assertIn('.rss', url, f"Expected .rss URL for r/{sub}")


MOCK_REDDIT_ATOM = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Is Fort Worth still affordable for first-time buyers?</title>
    <link rel="alternate" href="https://www.reddit.com/r/FortWorth/comments/abc123/test/"/>
    <published>2026-04-30T10:00:00+00:00</published>
  </entry>
  <entry>
    <title>Best neighborhoods for landlords in Saginaw</title>
    <link rel="alternate" href="https://www.reddit.com/r/FortWorth/comments/def456/test/"/>
    <published>2026-04-29T08:00:00+00:00</published>
  </entry>
</feed>'''


class TestParseRedditRss(unittest.TestCase):
    def test_parses_two_posts(self):
        result = sp.parse_reddit_rss(MOCK_REDDIT_ATOM, 'FortWorth')
        self.assertEqual(len(result), 2)

    def test_post_has_required_fields(self):
        result = sp.parse_reddit_rss(MOCK_REDDIT_ATOM, 'FortWorth')
        for field in ['title', 'url', 'subreddit', 'pub_date', 'is_local', 'score', 'num_comments']:
            self.assertIn(field, result[0])

    def test_url_extracted_from_href(self):
        result = sp.parse_reddit_rss(MOCK_REDDIT_ATOM, 'FortWorth')
        self.assertTrue(result[0]['url'].startswith('https://www.reddit.com'))

    def test_local_flag_set_for_fortworth(self):
        result = sp.parse_reddit_rss(MOCK_REDDIT_ATOM, 'FortWorth')
        self.assertTrue(result[0]['is_local'])

    def test_local_flag_false_for_national(self):
        result = sp.parse_reddit_rss(MOCK_REDDIT_ATOM, 'landlord')
        self.assertFalse(result[0]['is_local'])

    def test_invalid_xml_returns_empty(self):
        result = sp.parse_reddit_rss(b'not valid xml <<<', 'FortWorth')
        self.assertEqual(result, [])

    def test_subreddit_field_set(self):
        result = sp.parse_reddit_rss(MOCK_REDDIT_ATOM, 'FortWorth')
        self.assertEqual(result[0]['subreddit'], 'FortWorth')


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
    'averageRent': 1850,
    'rentYoYChange': 3.2,
    'vacancyRate': 0.04,
    'daysOnMarket': 18,
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


def _make_reddit_posts(n=5, subreddit='FortWorth'):
    return [
        {
            'title': f'Fort Worth real estate topic {i}',
            'score': 200 - i * 20,
            'num_comments': 60 - i * 5,
            'url': f'https://reddit.com/r/{subreddit}/{i}',
            'subreddit': subreddit,
            'is_local': subreddit in sp.LOCAL_SUBREDDITS,
            'pub_date': '',
        }
        for i in range(n)
    ]


def _make_rss_items(n=3):
    return [
        {
            'title': f'Housing market news item {i}',
            'url': f'https://inman.com/{i}',
            'description': '',
            'pub_date': '',
            'source': 'Inman',
        }
        for i in range(n)
    ]


SAMPLE_MARKET = {
    'median_rent': 1850,
    'rent_yoy_change': 3.2,
    'rental_dom': 18,
    'rental_new_listings': 289,
    'rental_total_listings': 748,
    'sale_median_price': 355000,
    'sale_avg_price': 545781,
    'sale_price_per_sqft': 177.58,
    'sale_dom': 56.71,
    'sale_median_dom': 30,
    'sale_new_listings': 204,
    'sale_total_listings': 712,
    'sale_updated': '2026-04-23',
    'city': 'Fort Worth',
    'state': 'TX',
    'zip': '76179',
    'pulled_at': '2026-04-23T05:00:00+00:00',
    'source_url': 'https://app.rentcast.io',
}

SAMPLE_DATA = {
    'pulled_at': '2026-04-23T05:00:00+00:00',
    'reddit': _make_reddit_posts(1),
    'rss': _make_rss_items(1),
    'market': SAMPLE_MARKET,
    'angles': [
        {
            'rank': 1,
            'headline': 'Fort Worth: Fort Worth real estate topic 0',
            'format': 'blog',
            'seo_keyword': 'fort worth real estate 2026',
            'competition': 'low',
            'source_type': 'local_reddit',
            'source_title': 'Fort Worth real estate topic 0',
            'source_url': 'https://reddit.com/r/FortWorth/0',
            'engagement_score': 320,
            'business_lens': 'both',
            'urgency': 'now',
            'priority_score': 7.5,
            'action': 'Post this to FB Story.',
        }
    ],
}


class TestGenerateAngles(unittest.TestCase):
    def setUp(self):
        self.reddit = _make_reddit_posts(5)
        self.rss    = _make_rss_items(3)
        self.market = SAMPLE_MARKET

    def test_returns_exactly_seven_angles(self):
        result = sp.generate_angles(self.reddit, self.rss, self.market)
        self.assertEqual(len(result), 7)

    def test_each_angle_has_required_fields(self):
        result = sp.generate_angles(self.reddit, self.rss, self.market)
        for angle in result:
            for field in ['rank', 'headline', 'format', 'seo_keyword',
                          'competition', 'source_type', 'source_title', 'source_url',
                          'business_lens', 'urgency', 'priority_score', 'action']:
                self.assertIn(field, angle, f"Missing field '{field}' in: {angle.get('headline')}")

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

    def test_business_lens_values_are_valid(self):
        result = sp.generate_angles(self.reddit, self.rss, self.market)
        for angle in result:
            self.assertIn(angle['business_lens'], {'pm', 'sales', 'both'})

    def test_urgency_values_are_valid(self):
        result = sp.generate_angles(self.reddit, self.rss, self.market)
        for angle in result:
            self.assertIn(angle['urgency'], {'now', 'this_week', 'evergreen'})

    def test_priority_score_in_range(self):
        result = sp.generate_angles(self.reddit, self.rss, self.market)
        for angle in result:
            self.assertGreaterEqual(angle['priority_score'], 0)
            self.assertLessEqual(angle['priority_score'], 10)

    def test_rentcast_angle_has_now_urgency(self):
        result = sp.generate_angles(self.reddit, self.rss, self.market)
        rc = next((a for a in result if a['source_type'] == 'rentcast'), None)
        self.assertIsNotNone(rc)
        self.assertEqual(rc['urgency'], 'now')

    def test_rentcast_angle_business_lens_is_both(self):
        result = sp.generate_angles(self.reddit, self.rss, self.market)
        rc = next((a for a in result if a['source_type'] == 'rentcast'), None)
        self.assertEqual(rc['business_lens'], 'both')

    def test_evergreen_angle_present(self):
        result = sp.generate_angles(self.reddit, self.rss, self.market)
        ev = next((a for a in result if a['urgency'] == 'evergreen'), None)
        self.assertIsNotNone(ev)


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
            sp.generate_html(SAMPLE_DATA, None, path)
            self.assertTrue(os.path.exists(path))

    def test_generate_html_contains_required_sections(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'brief.html')
            sp.generate_html(SAMPLE_DATA, None, path)
            with open(path) as f:
                html = f.read()
            self.assertIn('SIGNAL', html)
            self.assertIn('Action Board', html)
            self.assertIn('Market Snapshot', html)

    def test_generate_html_includes_pulled_date(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'brief.html')
            sp.generate_html(SAMPLE_DATA, None, path)
            with open(path) as f:
                html = f.read()
            self.assertIn('2026-04-23', html)

    def test_generate_html_includes_market_rent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'brief.html')
            sp.generate_html(SAMPLE_DATA, None, path)
            with open(path) as f:
                html = f.read()
            self.assertIn('1,850', html)

    def test_generate_html_warns_when_no_market_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'brief.html')
            data = dict(SAMPLE_DATA, market={})
            sp.generate_html(data, None, path)
            with open(path) as f:
                html = f.read()
            self.assertIn('unavailable', html)

    def test_generate_html_renders_llm_sections_when_analysis_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'brief.html')
            analysis = {
                'owner_lead_signals': 'Landlords complaining about vacancies.',
                'reddit_friction': [{'pattern': 'Slow leases', 'category': 'lease-up delay', 'example': 'Why is it so slow?'}],
                'content_angles': [{'rank': 1, 'topic': 'Fort Worth vacancy trends', 'format': 'blog', 'seo_keyword': 'fort worth rental market 2026', 'source': 'r/landlord', 'why': 'Landlords are searching for answers.'}],
                'action_board': 'Review lease pricing on current vacancies.',
                'data_quality': 'All feeds pulled clean.',
            }
            sp.generate_html(SAMPLE_DATA, analysis, path)
            with open(path) as f:
                html = f.read()
            self.assertIn('Landlords complaining', html)
            self.assertIn('Fort Worth vacancy trends', html)
            self.assertIn('lease-up delay', html)


class TestWriteBriefMd(unittest.TestCase):
    def test_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'brief.md')
            sp.write_brief_md(SAMPLE_DATA, {}, path)
            self.assertTrue(os.path.exists(path))

    def test_contains_all_sections(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'brief.md')
            sp.write_brief_md(SAMPLE_DATA, {}, path)
            with open(path) as f:
                md = f.read()
            for section in ['# SIGNAL Weekly Brief', 'Owner Lead Signals',
                            'NW Fort Worth', 'Reddit Community Friction',
                            'Content Angles', 'Action Board', 'Data Quality Notes']:
                self.assertIn(section, md, f"Missing section: {section}")

    def test_contains_market_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'brief.md')
            sp.write_brief_md(SAMPLE_DATA, {}, path)
            with open(path) as f:
                md = f.read()
            self.assertIn('1,850', md)

    def test_renders_llm_content_angles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'brief.md')
            analysis = {
                'content_angles': [
                    {'rank': 1, 'topic': 'Fort Worth vacancy spike', 'format': 'blog',
                     'seo_keyword': 'fort worth rental market 2026', 'source': 'r/landlord',
                     'why': 'High search volume.'}
                ]
            }
            sp.write_brief_md(SAMPLE_DATA, analysis, path)
            with open(path) as f:
                md = f.read()
            self.assertIn('Fort Worth vacancy spike', md)

    def test_stale_market_flagged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'signal', 'brief.md')
            data = dict(SAMPLE_DATA, market=dict(SAMPLE_MARKET, _stale=True, _cache_note='Cached'))
            sp.write_brief_md(data, {}, path)
            with open(path) as f:
                md = f.read()
            self.assertIn('cached', md.lower())


class TestWriteArchive(unittest.TestCase):
    def test_creates_archive_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            brief_path   = os.path.join(tmpdir, 'brief.md')
            archive_dir  = os.path.join(tmpdir, 'archive')
            with open(brief_path, 'w') as f:
                f.write('# Test brief')
            sp.write_archive(brief_path, archive_dir)
            files = os.listdir(archive_dir)
            self.assertEqual(len(files), 1)
            self.assertTrue(files[0].endswith('-brief.md'))

    def test_archive_content_matches_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            brief_path  = os.path.join(tmpdir, 'brief.md')
            archive_dir = os.path.join(tmpdir, 'archive')
            with open(brief_path, 'w') as f:
                f.write('# SIGNAL content')
            sp.write_archive(brief_path, archive_dir)
            archive_file = os.path.join(archive_dir, os.listdir(archive_dir)[0])
            with open(archive_file) as f:
                self.assertEqual(f.read(), '# SIGNAL content')


if __name__ == '__main__':
    unittest.main()
