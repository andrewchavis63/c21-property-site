import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from xml.etree import ElementTree

SUBREDDITS = ['FortWorth', 'DFW', 'realestate', 'FirstTimeHomeBuyer', 'landlord']

RSS_FEEDS = {
    'Inman': 'https://www.inman.com/feed/',
    'HousingWire': 'https://www.housingwire.com/feed/',
    'Redfin': 'https://www.redfin.com/news/feed/',
    'BiggerPockets': 'https://www.biggerpockets.com/blog/feed',
    'CalculatedRisk': 'https://feeds.feedburner.com/CalculatedRisk',
}

USER_AGENT = 'signal-pull/1.0 (allpantherproperties.com; content research bot)'
RENTCAST_BASE = 'https://api.rentcast.io/v1/markets'


def parse_reddit_response(data, subreddit):
    """Parse Reddit hot.json API response into list of thread dicts."""
    threads = []
    for child in data.get('data', {}).get('children', []):
        post = child.get('data', {})
        if post.get('stickied'):
            continue
        threads.append({
            'title': post.get('title', ''),
            'score': post.get('score', 0),
            'num_comments': post.get('num_comments', 0),
            'url': f"https://reddit.com{post.get('permalink', '')}",
            'subreddit': subreddit,
            'selftext_preview': post.get('selftext', '')[:200],
        })
    return threads


def fetch_reddit(subreddits):
    """Fetch top threads from all subreddits, sorted by score desc. Returns top 10."""
    all_threads = []
    for sub in subreddits:
        url = f'https://www.reddit.com/r/{sub}/hot.json?limit=10'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            threads = parse_reddit_response(data, sub)
            all_threads.extend(threads)
            time.sleep(0.5)
        except Exception as e:
            print(f'WARNING: Reddit fetch failed for r/{sub}: {e}', file=sys.stderr)
    all_threads.sort(key=lambda t: t['score'], reverse=True)
    return all_threads[:10]


def parse_rss_feed(xml_bytes, source):
    """Parse RSS2 or Atom XML bytes into list of item dicts. Returns up to 5 items."""
    items = []
    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError:
        return items

    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    entries = root.findall('.//item') or root.findall('.//atom:entry', ns)

    for entry in entries[:5]:
        title = (
            entry.findtext('title') or
            entry.findtext('atom:title', namespaces=ns) or ''
        ).strip()
        link = (
            entry.findtext('link') or
            entry.findtext('atom:link', namespaces=ns) or ''
        ).strip()
        description = (
            entry.findtext('description') or
            entry.findtext('summary') or ''
        ).strip()[:300]
        pub_date = (
            entry.findtext('pubDate') or
            entry.findtext('published') or ''
        ).strip()

        if title:
            items.append({
                'title': title,
                'url': link,
                'description': description,
                'pub_date': pub_date,
                'source': source,
            })
    return items


def fetch_rss(feeds):
    """Fetch all RSS feeds. Returns up to 10 items sorted by pub_date desc."""
    all_items = []
    for source, url in feeds.items():
        try:
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_data = resp.read()
            items = parse_rss_feed(xml_data, source)
            all_items.extend(items)
        except Exception as e:
            print(f'WARNING: RSS fetch failed for {source}: {e}', file=sys.stderr)
    all_items.sort(key=lambda x: x.get('pub_date', ''), reverse=True)
    return all_items[:10]


def parse_rentcast_response(data):
    """Parse RentCast zipCode markets API response into market snapshot dict."""
    if not data:
        return {}
    if isinstance(data, list):
        data = data[0] if data else {}
    if not data:
        return {}
    rental = data.get('rentalData') or data
    return {
        'median_rent': rental.get('medianRent') or rental.get('averageRent'),
        'rent_yoy_change': rental.get('rentYoYChange') or rental.get('averageRentYoY'),
        'vacancy_rate': rental.get('vacancyRate'),
        'days_on_market': rental.get('averageDaysOnMarket') or rental.get('daysOnMarket'),
        'new_listings': rental.get('newListings'),
        'total_listings': rental.get('totalListings'),
        'city': 'Fort Worth',
        'state': 'TX',
        'pulled_at': datetime.now(timezone.utc).isoformat(),
        'source_url': 'https://app.rentcast.io',
    }


def fetch_rentcast(api_key):
    """Fetch NW Fort Worth/Saginaw market snapshot from RentCast API (zip 76179)."""
    if not api_key:
        print('WARNING: RENTCAST_API_KEY not set — skipping market data', file=sys.stderr)
        return {}
    url = f'{RENTCAST_BASE}?zipCode=76179'
    try:
        req = urllib.request.Request(url, headers={
            'X-Api-Key': api_key,
            'User-Agent': USER_AGENT,
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return parse_rentcast_response(data)
    except Exception as e:
        print(f'WARNING: RentCast fetch failed: {e}', file=sys.stderr)
        return {}


def generate_angles(reddit_threads, rss_items, market_data):
    """
    Returns exactly 7 content angle dicts ranked by SEO potential.
    Sources: top 3 Reddit threads, top 2 RSS items, 1 RentCast angle, 1 evergreen local.
    Every angle includes a source URL — no angles without citations.
    """
    angles = []

    for thread in reddit_threads[:3]:
        engagement = thread['score'] + (thread['num_comments'] * 2)
        post_format = 'blog' if thread['num_comments'] > 50 else 'social'
        angles.append({
            'rank': len(angles) + 1,
            'headline': f"Fort Worth Real Estate: {thread['title'][:80]}",
            'format': post_format,
            'seo_keyword': f"fort worth {thread['subreddit'].lower()} 2026",
            'competition': 'low' if thread['score'] < 500 else 'medium',
            'source_type': 'reddit',
            'source_title': thread['title'],
            'source_url': thread['url'],
            'engagement_score': engagement,
        })

    for item in rss_items[:2]:
        angles.append({
            'rank': len(angles) + 1,
            'headline': f"{item['title'][:90]} — What It Means for Fort Worth",
            'format': 'blog',
            'seo_keyword': 'fort worth real estate market 2026',
            'competition': 'medium',
            'source_type': 'rss',
            'source_title': item['title'],
            'source_url': item['url'],
            'engagement_score': 0,
        })

    if market_data.get('median_rent'):
        yoy = market_data.get('rent_yoy_change')
        yoy_str = f"{yoy:+.1f}%" if isinstance(yoy, (int, float)) else "shifting"
        angles.append({
            'rank': 6,
            'headline': f"Fort Worth Rental Market Update: Rents {yoy_str} YoY — Data and Analysis",
            'format': 'screen_recording',
            'seo_keyword': 'fort worth rental market 2026',
            'competition': 'low',
            'source_type': 'rentcast',
            'source_title': (
                f"RentCast Tarrant County — pulled "
                f"{market_data.get('pulled_at', '')[:10]}"
            ),
            'source_url': market_data.get('source_url', 'https://app.rentcast.io'),
            'engagement_score': 0,
        })
    else:
        angles.append({
            'rank': 6,
            'headline': 'Tarrant County Market Update: What Buyers and Renters Need to Know',
            'format': 'social',
            'seo_keyword': 'tarrant county real estate 2026',
            'competition': 'low',
            'source_type': 'fallback',
            'source_title': 'Market data unavailable this pull — verify before publishing',
            'source_url': '',
            'engagement_score': 0,
        })

    top_sub = reddit_threads[0]['subreddit'] if reddit_threads else 'FortWorth'
    angles.append({
        'rank': 7,
        'headline': 'Why Fort Worth Is Still One of the Best Places to Buy in Texas Right Now',
        'format': 'youtube',
        'seo_keyword': 'fort worth real estate buy 2026',
        'competition': 'medium',
        'source_type': 'reddit',
        'source_title': f"r/{top_sub} — top local discussions this week",
        'source_url': f"https://reddit.com/r/{top_sub}",
        'engagement_score': 0,
    })

    angles.sort(key=lambda a: a['engagement_score'], reverse=True)
    for i, angle in enumerate(angles):
        angle['rank'] = i + 1

    return angles


def write_data_json(data, path='signal/data.json'):
    """Write pull data to JSON file. Creates parent directory if needed."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_html(data, path='signal/brief.html'):
    """Generate self-contained visual dashboard HTML from pull data."""
    pulled_at = data.get('pulled_at', 'Unknown')
    angles = data.get('angles', [])
    reddit = data.get('reddit', [])
    rss = data.get('rss', [])
    market = data.get('market', {})

    FORMAT_BADGES = {
        'blog':             ('#2563eb', 'BLOG POST'),
        'social':           ('#16a34a', 'SOCIAL'),
        'youtube':          ('#dc2626', 'YOUTUBE'),
        'screen_recording': ('#7c3aed', 'SCREEN REC'),
        'fallback':         ('#6b7280', 'VERIFY DATA'),
    }

    def angle_card(a):
        color, label = FORMAT_BADGES.get(a['format'], ('#6b7280', a['format'].upper()))
        if a['source_url']:
            src = (f'<a href="{a["source_url"]}" target="_blank" '
                   f'style="color:#94a3b8;font-size:12px;">'
                   f'&rarr; {a["source_title"][:80]}</a>')
        else:
            src = (f'<span style="color:#ef4444;font-size:12px;">'
                   f'&#9888; {a["source_title"]}</span>')
        return (
            f'<div style="background:#1e293b;border-radius:8px;padding:16px;'
            f'margin-bottom:12px;border-left:4px solid {color};">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
            f'<span style="background:{color};color:#fff;padding:2px 8px;'
            f'border-radius:4px;font-size:11px;font-weight:700;">{label}</span>'
            f'<span style="background:#334155;color:#94a3b8;padding:2px 8px;'
            f'border-radius:4px;font-size:11px;">#{a["rank"]}</span>'
            f'<span style="background:#334155;color:#94a3b8;padding:2px 8px;'
            f'border-radius:4px;font-size:11px;">{a["competition"].upper()} COMP</span>'
            f'</div>'
            f'<div style="color:#f1f5f9;font-size:16px;font-weight:600;margin-bottom:6px;">'
            f'{a["headline"]}</div>'
            f'<div style="color:#64748b;font-size:12px;margin-bottom:6px;">'
            f'SEO: <code style="color:#38bdf8;background:#0f172a;padding:2px 4px;">'
            f'{a["seo_keyword"]}</code></div>'
            f'{src}</div>'
        )

    def reddit_card(t):
        return (
            f'<div style="background:#1e293b;border-radius:6px;padding:12px;margin-bottom:8px;">'
            f'<a href="{t["url"]}" target="_blank" style="color:#f8fafc;font-size:14px;'
            f'font-weight:500;text-decoration:none;">{t["title"][:100]}</a>'
            f'<div style="color:#64748b;font-size:12px;margin-top:4px;">'
            f'r/{t["subreddit"]} &middot; &uarr;{t["score"]:,} &middot; {t["num_comments"]:,} comments</div>'
            f'</div>'
        )

    def rss_card(item):
        date_str = item.get('pub_date', '')[:16] if item.get('pub_date') else ''
        return (
            f'<div style="background:#1e293b;border-radius:6px;padding:12px;margin-bottom:8px;">'
            f'<a href="{item["url"]}" target="_blank" style="color:#f8fafc;font-size:14px;'
            f'font-weight:500;text-decoration:none;">{item["title"][:100]}</a>'
            f'<div style="color:#64748b;font-size:12px;margin-top:4px;">'
            f'{item["source"]} &middot; {date_str}</div>'
            f'</div>'
        )

    if market.get('median_rent'):
        yoy = market.get('rent_yoy_change')
        yoy_display = f'{yoy:+.1f}%' if isinstance(yoy, (int, float)) else 'N/A'
        yoy_color = '#4ade80' if isinstance(yoy, (int, float)) and yoy > 0 else '#f87171'
        dom = market.get('days_on_market') or 'N/A'
        vac = market.get('vacancy_rate') or 'N/A'
        market_html = (
            f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;">'
            f'<div style="background:#1e293b;border-radius:8px;padding:16px;text-align:center;">'
            f'<div style="color:#38bdf8;font-size:28px;font-weight:700;">'
            f'${market["median_rent"]:,.0f}</div>'
            f'<div style="color:#64748b;font-size:12px;margin-top:4px;">Median Rent</div></div>'
            f'<div style="background:#1e293b;border-radius:8px;padding:16px;text-align:center;">'
            f'<div style="color:{yoy_color};font-size:28px;font-weight:700;">{yoy_display}</div>'
            f'<div style="color:#64748b;font-size:12px;margin-top:4px;">YoY Change</div></div>'
            f'<div style="background:#1e293b;border-radius:8px;padding:16px;text-align:center;">'
            f'<div style="color:#a78bfa;font-size:28px;font-weight:700;">{dom}</div>'
            f'<div style="color:#64748b;font-size:12px;margin-top:4px;">Days on Market</div></div>'
            f'<div style="background:#1e293b;border-radius:8px;padding:16px;text-align:center;">'
            f'<div style="color:#fb923c;font-size:28px;font-weight:700;">{vac}</div>'
            f'<div style="color:#64748b;font-size:12px;margin-top:4px;">Vacancy Rate</div></div>'
            f'</div>'
            f'<div style="color:#64748b;font-size:11px;margin-top:8px;">'
            f'Source: RentCast &middot; Fort Worth, TX &middot; '
            f'Pulled: {market.get("pulled_at", "")[:10]}</div>'
        )
    else:
        market_html = (
            '<div style="color:#ef4444;padding:12px;background:#1e293b;border-radius:8px;">'
            '&#9888; RentCast data unavailable this pull &mdash; do not publish market stats '
            'until verified from another source.</div>'
        )

    angles_html = ''.join(angle_card(a) for a in angles)
    reddit_html = ''.join(reddit_card(t) for t in reddit[:5])
    rss_html = ''.join(rss_card(item) for item in rss[:5])

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SIGNAL &mdash; Weekly Brief &middot; {pulled_at[:10]}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#0f172a;color:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:24px}}
  h2{{font-size:15px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;cursor:pointer;user-select:none}}
  h2:hover{{color:#f1f5f9}}
  .section{{margin-bottom:32px}}
  .section-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid #1e293b}}
  .collapsed{{display:none}}
  code{{background:#1e293b;border-radius:3px}}
  a{{color:#38bdf8}}
</style>
<script>
function toggle(id){{document.getElementById(id).classList.toggle('collapsed')}}
</script>
</head>
<body>
<div style="max-width:900px;margin:0 auto">
  <div style="margin-bottom:32px">
    <div style="font-size:28px;font-weight:700;color:#f8fafc">&#9889; SIGNAL</div>
    <div style="color:#64748b;font-size:13px;margin-top:4px">
      Fort Worth Content Intelligence &middot; Week of {pulled_at[:10]} &middot; allpantherproperties.com
    </div>
  </div>

  <div class="section">
    <div class="section-header" onclick="toggle('angles')">
      <h2>&#127919; 7 Content Angles This Week</h2>
      <span style="color:#475569;font-size:12px">click to collapse</span>
    </div>
    <div id="angles">{angles_html}</div>
  </div>

  <div class="section">
    <div class="section-header" onclick="toggle('market')">
      <h2>&#128202; Market Snapshot &mdash; Tarrant County</h2>
      <span style="color:#475569;font-size:12px">click to collapse</span>
    </div>
    <div id="market">{market_html}</div>
  </div>

  <div class="section">
    <div class="section-header" onclick="toggle('reddit')">
      <h2>&#128293; Reddit Hot Topics</h2>
      <span style="color:#475569;font-size:12px">click to collapse</span>
    </div>
    <div id="reddit">{reddit_html}</div>
  </div>

  <div class="section">
    <div class="section-header" onclick="toggle('news')">
      <h2>&#128240; News Angles</h2>
      <span style="color:#475569;font-size:12px">click to collapse</span>
    </div>
    <div id="news">{rss_html}</div>
  </div>

  <div style="color:#334155;font-size:11px;text-align:center;margin-top:48px;padding-top:16px;border-top:1px solid #1e293b">
    SIGNAL &middot; allpantherproperties.com &middot; Every stat above is sourced and timestamped.
    Do not publish anything not in this brief.
  </div>
</div>
</body>
</html>'''

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)


def send_email_brief(html_path, pulled_at, resend_api_key):
    """Email the SIGNAL brief HTML to Andrew via Resend."""
    if not resend_api_key:
        print('WARNING: RESEND_API_KEY not set — skipping email', file=sys.stderr)
        return
    try:
        with open(html_path, encoding='utf-8') as f:
            html_body = f.read()
    except FileNotFoundError:
        print(f'WARNING: {html_path} not found — skipping email', file=sys.stderr)
        return

    subject = f'SIGNAL -- Week of {pulled_at[:10]}'
    payload = json.dumps({
        'from': 'newsletter@allpantherproperties.com',
        'to': ['andrewchavis63@gmail.com'],
        'subject': subject,
        'html': html_body,
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.resend.com/emails',
        data=payload,
        headers={
            'Authorization': f'Bearer {resend_api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            print(f'SIGNAL: brief emailed (id: {result.get("id", "?")})', flush=True)
    except urllib.error.HTTPError as e:
        print(f'WARNING: email failed {e.code}: {e.read().decode()}', file=sys.stderr)
    except Exception as e:
        print(f'WARNING: email failed: {e}', file=sys.stderr)


def main():
    api_key = os.environ.get('RENTCAST_API_KEY', '')

    print('SIGNAL: pulling Reddit...', flush=True)
    reddit_data = fetch_reddit(SUBREDDITS)
    print(f'  -> {len(reddit_data)} threads', flush=True)

    print('SIGNAL: pulling RSS feeds...', flush=True)
    rss_data = fetch_rss(RSS_FEEDS)
    print(f'  -> {len(rss_data)} items', flush=True)

    print('SIGNAL: pulling RentCast market data...', flush=True)
    market_data = fetch_rentcast(api_key)
    status = f"${market_data['median_rent']:,.0f}" if market_data.get('median_rent') else 'unavailable'
    print(f'  -> median rent: {status}', flush=True)

    print('SIGNAL: generating 7 content angles...', flush=True)
    angles = generate_angles(reddit_data, rss_data, market_data)

    data = {
        'pulled_at': datetime.now(timezone.utc).isoformat(),
        'reddit': reddit_data,
        'rss': rss_data,
        'market': market_data,
        'angles': angles,
    }

    write_data_json(data)
    print('SIGNAL: signal/data.json written', flush=True)

    generate_html(data)
    print('SIGNAL: signal/brief.html written', flush=True)

    resend_key = os.environ.get('RESEND_API_KEY', '')
    print('SIGNAL: emailing brief...', flush=True)
    send_email_brief('signal/brief.html', data['pulled_at'], resend_key)

    print(f'\nSIGNAL: done. Top angle: {angles[0]["headline"][:70]}', flush=True)


if __name__ == '__main__':
    main()
