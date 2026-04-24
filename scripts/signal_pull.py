import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from xml.etree import ElementTree

SUBREDDITS = ['FortWorth', 'DFW', 'realestate', 'TexasRealEstate', 'landlord']
LOCAL_SUBREDDITS = {'FortWorth', 'DFW'}
LOCAL_RSS_SOURCES = {'FortWorthReport', 'PaperCity', 'WFAA', 'NBCDFW', 'FWWeekly'}

RE_TITLE_KEYWORDS = {
    'rent', 'rental', 'renting', 'lease', 'landlord', 'tenant', 'tenants',
    'property', 'properties', 'home', 'homes', 'house', 'houses', 'housing',
    'apartment', 'apartments', 'condo', 'townhome', 'townhouse',
    'mortgage', 'buy', 'buying', 'sell', 'selling', 'sold', 'listing',
    'market', 'closing', 'realtor', 'realty', 'agent', 'broker',
    'invest', 'investment', 'investor', 'flip', 'flipping',
    'evict', 'eviction', 'hoa', 'neighbor', 'neighborhood', 'suburb',
    'development', 'builder', 'built', 'construction', 'zoning',
    'afford', 'affordable', 'price', 'prices', 'cost', 'costs',
    'move', 'moving', 'relocat',
}


NON_TX_STATE_CODES = {
    'AK','AL','AR','AZ','CA','CO','CT','DC','DE','FL','GA','HI','IA','ID',
    'IL','IN','KS','KY','LA','MA','MD','ME','MI','MN','MO','MS','MT','NC',
    'ND','NE','NH','NJ','NM','NV','NY','OH','OK','OR','PA','RI','SC','SD',
    'TN','UT','VA','VT','WA','WI','WV','WY',
}


def is_re_relevant(title):
    """Return True if the post title contains at least one real-estate keyword."""
    words = title.lower().replace('-', ' ').replace('/', ' ').split()
    return any(any(w.startswith(kw) for kw in RE_TITLE_KEYWORDS) for w in words)


def is_out_of_state(title):
    """Return True if the title explicitly references a non-TX US state (e.g. [Landlord-US-IN])."""
    for code in NON_TX_STATE_CODES:
        if f'-{code}]' in title or f'[{code}]' in title or f'({code})' in title:
            return True
    return False

RSS_FEEDS = {
    # Local Fort Worth
    'FortWorthReport': 'https://fortworthreport.org/feed/',
    'PaperCity': 'https://www.papercitymag.com/feed/',
    'WFAA': 'https://www.wfaa.com/feeds/syndication/rss/news/',
    'NBCDFW': 'https://www.nbcdfw.com/feed/',
    'FWWeekly': 'https://www.fwweekly.com/feed/',
    # National RE / mortgage
    'RealTrends': 'https://www.realtrends.com/feed/',
    'MortgageReports': 'https://themortgagereports.com/feed',
    'HousingWire': 'https://www.housingwire.com/feed/',
    'BiggerPockets': 'https://www.biggerpockets.com/blog/feed',
    'CalculatedRisk': 'https://feeds.feedburner.com/CalculatedRisk',
    'RealtorMag': 'https://magazine.realtor/rss',
    'Redfin': 'https://www.redfin.com/news/feed/',
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
    """Fetch top threads. Local subs (FortWorth, DFW) fill first 3 slots; national fills the rest."""
    local_threads = []
    national_threads = []
    for sub in subreddits:
        if sub in LOCAL_SUBREDDITS:
            url = f'https://www.reddit.com/r/{sub}/search.json?q=real+estate&sort=top&t=week&limit=10&restrict_sr=1'
        else:
            url = f'https://www.reddit.com/r/{sub}/hot.json?limit=10'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            threads = parse_reddit_response(data, sub)
            is_local = sub in LOCAL_SUBREDDITS
            for t in threads:
                t['is_local'] = is_local
            if is_local:
                local_threads.extend(t for t in threads if is_re_relevant(t['title']))
            else:
                national_threads.extend(threads)
            time.sleep(0.5)
        except Exception as e:
            print(f'WARNING: Reddit fetch failed for r/{sub}: {e}', file=sys.stderr)
    local_threads.sort(key=lambda t: t['score'], reverse=True)
    national_threads.sort(key=lambda t: t['score'], reverse=True)
    # Local threads always fill first 3 slots — national can't crowd them out
    return (local_threads[:3] + national_threads[:7])[:10]


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
    sale = data.get('saleData') or {}
    return {
        # Rental
        'median_rent': rental.get('medianRent') or rental.get('averageRent'),
        'rent_yoy_change': rental.get('rentYoYChange') or rental.get('averageRentYoY'),
        'rental_dom': rental.get('averageDaysOnMarket') or rental.get('daysOnMarket'),
        'rental_new_listings': rental.get('newListings'),
        'rental_total_listings': rental.get('totalListings'),
        # Sale
        'sale_median_price': sale.get('medianPrice'),
        'sale_avg_price': sale.get('averagePrice'),
        'sale_price_per_sqft': sale.get('medianPricePerSquareFoot') or sale.get('averagePricePerSquareFoot'),
        'sale_dom': sale.get('averageDaysOnMarket'),
        'sale_median_dom': sale.get('medianDaysOnMarket'),
        'sale_new_listings': sale.get('newListings'),
        'sale_total_listings': sale.get('totalListings'),
        'sale_updated': (sale.get('lastUpdatedDate') or '')[:10],
        # Meta
        'city': 'Fort Worth',
        'state': 'TX',
        'zip': '76179',
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
    Returns exactly 7 content angle dicts. Priority order — no engagement sort.

    Content pool (5 slots):
      P1: local Reddit — RE-keyword-filtered r/FortWorth and r/DFW posts (max 3)
      P2: FortWorthReport RSS — highest-signal local RE source (max 1)
      P3: other local RSS (PaperCity, WFAA, etc.) — local context (max 1)
      P4: national RSS (HousingWire, BiggerPockets, etc.) — industry context
      P5: national Reddit (TexasRealEstate, realestate, landlord) — last resort
    Slot 6: RentCast market angle (always)
    Slot 7: Evergreen (always)
    """
    angles = []

    local_reddit = [t for t in reddit_threads
                    if t.get('is_local', t.get('subreddit') in LOCAL_SUBREDDITS)]
    national_reddit = [t for t in reddit_threads
                       if not t.get('is_local', t.get('subreddit') in LOCAL_SUBREDDITS)
                       and not is_out_of_state(t['title'])]
    # Local RSS filtered by RE keywords — FortWorthReport publishes events/food too
    fw_report_rss = [i for i in rss_items
                     if i.get('source') == 'FortWorthReport' and is_re_relevant(i['title'])]
    other_local_rss = [i for i in rss_items
                       if i.get('source') in LOCAL_RSS_SOURCES
                       and i.get('source') != 'FortWorthReport'
                       and is_re_relevant(i['title'])]
    national_rss = [i for i in rss_items if i.get('source') not in LOCAL_RSS_SOURCES]

    # Build ordered content pool — priority determines position
    content_pool = []
    content_pool.extend(('local_reddit', t) for t in local_reddit[:3])
    content_pool.extend(('fw_report', i) for i in fw_report_rss[:1])
    content_pool.extend(('local_rss', i) for i in other_local_rss[:1])
    content_pool.extend(('national_rss', i) for i in national_rss[:3])
    content_pool.extend(('national_reddit', t) for t in national_reddit[:3])
    content_pool = content_pool[:5]

    for src_type, item in content_pool:
        if src_type in ('local_reddit', 'national_reddit'):
            t = item
            is_local = src_type == 'local_reddit'
            angles.append({
                'rank': 0,
                'headline': (f"Fort Worth: {t['title'][:90]}" if is_local
                             else f"What Fort Worth Buyers Should Know: {t['title'][:70]}"),
                'format': 'blog' if t['num_comments'] > 50 else 'social',
                'seo_keyword': 'fort worth real estate 2026' if is_local else 'fort worth real estate market 2026',
                'competition': 'low' if is_local else 'medium',
                'source_type': 'reddit',
                'source_title': t['title'],
                'source_url': t['url'],
                'engagement_score': t['score'] + t['num_comments'] * 2,
            })
        else:
            rss_item = item
            is_local_src = src_type in ('fw_report', 'local_rss')
            angles.append({
                'rank': 0,
                'headline': (f"Fort Worth: {rss_item['title'][:90]}" if is_local_src
                             else f"{rss_item['title'][:80]} — What It Means for Fort Worth"),
                'format': 'blog',
                'seo_keyword': ('fort worth real estate news 2026' if is_local_src
                                else 'fort worth real estate market 2026'),
                'competition': 'low' if is_local_src else 'medium',
                'source_type': 'rss',
                'source_title': rss_item['title'],
                'source_url': rss_item['url'],
                'engagement_score': 0,
            })

    # Slot 6: Market data
    if market_data.get('median_rent'):
        yoy = market_data.get('rent_yoy_change')
        yoy_str = f"{yoy:+.1f}%" if isinstance(yoy, (int, float)) else "shifting"
        angles.append({
            'rank': 0,
            'headline': f"Fort Worth Rental Market Update: Rents {yoy_str} YoY — Data and Analysis",
            'format': 'screen_recording',
            'seo_keyword': 'fort worth rental market 2026',
            'competition': 'low',
            'source_type': 'rentcast',
            'source_title': f"RentCast Tarrant County — pulled {market_data.get('pulled_at', '')[:10]}",
            'source_url': market_data.get('source_url', 'https://app.rentcast.io'),
            'engagement_score': 0,
        })
    else:
        angles.append({
            'rank': 0,
            'headline': 'Tarrant County Market Update: What Buyers and Renters Need to Know',
            'format': 'social',
            'seo_keyword': 'tarrant county real estate 2026',
            'competition': 'low',
            'source_type': 'fallback',
            'source_title': 'Market data unavailable this pull — verify before publishing',
            'source_url': '',
            'engagement_score': 0,
        })

    # Slot 7: Evergreen
    top_local = local_reddit[0]['subreddit'] if local_reddit else 'FortWorth'
    angles.append({
        'rank': 0,
        'headline': 'Why Fort Worth Is Still One of the Best Places to Buy in Texas Right Now',
        'format': 'youtube',
        'seo_keyword': 'fort worth real estate buy 2026',
        'competition': 'medium',
        'source_type': 'reddit',
        'source_title': f"r/{top_local} — top local discussions this week",
        'source_url': f"https://reddit.com/r/{top_local}",
        'engagement_score': 0,
    })

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

    def stat_box(value, label, color='#38bdf8'):
        return (
            f'<div style="background:#1e293b;border-radius:8px;padding:16px;text-align:center;">'
            f'<div style="color:{color};font-size:24px;font-weight:700;">{value}</div>'
            f'<div style="color:#64748b;font-size:11px;margin-top:4px;">{label}</div></div>'
        )

    if market.get('median_rent') or market.get('sale_median_price'):
        pulled = market.get('pulled_at', '')[:10]
        zipc = market.get('zip', '76179')

        rental_row = ''
        if market.get('median_rent'):
            yoy = market.get('rent_yoy_change')
            yoy_display = f'{yoy:+.1f}%' if isinstance(yoy, (int, float)) else 'N/A'
            yoy_color = '#4ade80' if isinstance(yoy, (int, float)) and yoy > 0 else '#f87171'
            rental_row = (
                f'<div style="margin-bottom:8px;color:#94a3b8;font-size:11px;font-weight:600;'
                f'text-transform:uppercase;letter-spacing:1px;">Rental Market</div>'
                f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:20px;">'
                + stat_box(f'${market["median_rent"]:,.0f}', 'Median Rent', '#38bdf8')
                + stat_box(yoy_display, 'YoY Change', yoy_color)
                + stat_box(f'{market.get("rental_dom") or "N/A"}d', 'Avg DOM', '#a78bfa')
                + stat_box(str(market.get('rental_new_listings') or 'N/A'), 'New Listings', '#fb923c')
                + '</div>'
            )

        sale_row = ''
        if market.get('sale_median_price'):
            sale_row = (
                f'<div style="margin-bottom:8px;color:#94a3b8;font-size:11px;font-weight:600;'
                f'text-transform:uppercase;letter-spacing:1px;">Sale Market</div>'
                f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;">'
                + stat_box(f'${market["sale_median_price"]:,.0f}', 'Median Sale Price', '#34d399')
                + stat_box(f'${market.get("sale_price_per_sqft") or 0:,.0f}/sqft', 'Price / SqFt', '#34d399')
                + stat_box(f'{market.get("sale_dom") or "N/A"}d', 'Avg DOM', '#a78bfa')
                + stat_box(str(market.get('sale_new_listings') or 'N/A'), 'New Listings', '#fb923c')
                + stat_box(str(market.get('sale_total_listings') or 'N/A'), 'Total Listings', '#64748b')
                + '</div>'
            )

        market_html = (
            rental_row + sale_row +
            f'<div style="color:#64748b;font-size:11px;margin-top:10px;">'
            f'Source: RentCast &middot; Zip {zipc} (NW Fort Worth / Saginaw) &middot; Pulled: {pulled}</div>'
        )
    else:
        market_html = (
            '<div style="color:#ef4444;padding:12px;background:#1e293b;border-radius:8px;">'
            '&#9888; RentCast data unavailable this pull &mdash; do not publish market stats '
            'until verified from another source.</div>'
        )

    angles_html = ''.join(angle_card(a) for a in angles)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SIGNAL &mdash; Weekly Brief &middot; {pulled_at[:10]}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#0a0f1e;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:32px 24px}}
  .container{{max-width:860px;margin:0 auto}}
  .section{{margin-bottom:36px}}
  .section-label{{font-size:11px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:2px;margin-bottom:14px}}
  .divider{{border:none;border-top:1px solid #1a2540;margin:28px 0}}
  code{{background:#131d35;border-radius:3px;padding:1px 5px;color:#38bdf8;font-size:11px}}
  a{{color:#60a5fa;text-decoration:none}}
  a:hover{{color:#93c5fd}}
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:36px;flex-wrap:wrap;gap:12px">
    <div>
      <div style="font-size:11px;font-weight:700;letter-spacing:3px;color:#38bdf8;text-transform:uppercase;margin-bottom:6px">All Panther Properties</div>
      <div style="font-size:32px;font-weight:800;color:#f8fafc;letter-spacing:-0.5px">&#9889; SIGNAL</div>
      <div style="color:#475569;font-size:13px;margin-top:5px">Fort Worth Content Intelligence &mdash; Week of {pulled_at[:10]}</div>
    </div>
  </div>

  <!-- Content Angles -->
  <div class="section">
    <div class="section-label">&#127919; Content Angles This Week</div>
    <div id="angles">{angles_html}</div>
  </div>

  <hr class="divider">

  <!-- Market Snapshot -->
  <div class="section">
    <div class="section-label">&#128202; Market Snapshot &mdash; Tarrant County / 76179</div>
    <div id="market">{market_html}</div>
  </div>

  <div style="color:#1e3050;font-size:11px;text-align:center;margin-top:48px;padding-top:16px;border-top:1px solid #1a2540">
    SIGNAL &middot; allpantherproperties.com &middot; Every stat is sourced and timestamped. Do not publish unverified data.
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
