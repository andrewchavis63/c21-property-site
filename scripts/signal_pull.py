import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from xml.etree import ElementTree

# ── Constants ─────────────────────────────────────────────────────────────────

REDDIT_RSS_FEEDS = {
    'FortWorth':       'https://www.reddit.com/r/FortWorth/.rss',
    'DFW':             'https://www.reddit.com/r/DFW/.rss',
    'landlord':        'https://www.reddit.com/r/landlord/.rss',
    'realestate':      'https://www.reddit.com/r/realestate/.rss',
    'TexasRealEstate': 'https://www.reddit.com/r/TexasRealEstate/.rss',
}

LOCAL_SUBREDDITS = {'FortWorth', 'DFW'}
LOCAL_RSS_SOURCES = {'FortWorthReport', 'PaperCity', 'WFAA', 'NBCDFW', 'FWWeekly'}

RSS_FEEDS = {
    # Local Fort Worth
    'FortWorthReport': 'https://fortworthreport.org/feed/',
    'PaperCity':       'https://www.papercitymag.com/feed/',
    'WFAA':            'https://www.wfaa.com/feeds/syndication/rss/news/',
    'NBCDFW':          'https://www.nbcdfw.com/feed/',
    'FWWeekly':        'https://www.fwweekly.com/feed/',
    # National RE / mortgage
    'RealTrends':      'https://www.realtrends.com/feed/',
    'MortgageReports': 'https://themortgagereports.com/feed',
    'HousingWire':     'https://www.housingwire.com/feed/',
    'BiggerPockets':   'https://www.biggerpockets.com/blog/feed',
    'CalculatedRisk':  'https://feeds.feedburner.com/CalculatedRisk',
    'RealtorMag':      'https://magazine.realtor/rss',
    'Redfin':          'https://www.redfin.com/news/feed/',
}

RENTCAST_BASE       = 'https://api.rentcast.io/v1/markets'
RENTCAST_CACHE_PATH = 'signal/.rentcast-cache.json'
RENTCAST_BUDGET     = 40  # guard threshold; free tier = 50/month

USER_AGENT = 'signal-pull/1.0 (allpantherproperties.com; content research bot)'

# ── Keyword / filter helpers ───────────────────────────────────────────────────

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
    words = title.lower().replace('-', ' ').replace('/', ' ').split()
    return any(any(w.startswith(kw) for kw in RE_TITLE_KEYWORDS) for w in words)


def is_out_of_state(title):
    for code in NON_TX_STATE_CODES:
        if f'-{code}]' in title or f'[{code}]' in title or f'({code})' in title:
            return True
    return False


# ── Reddit RSS ────────────────────────────────────────────────────────────────

def parse_reddit_rss(xml_bytes, subreddit):
    """Parse Reddit Atom feed into list of post dicts."""
    posts = []
    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError:
        return posts

    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    entries = root.findall('atom:entry', ns)

    for entry in entries[:15]:
        title = (entry.findtext('atom:title', namespaces=ns) or '').strip()
        if not title:
            continue
        # Atom <link> is self-closing with href attribute, not text
        link_el = entry.find('atom:link', ns)
        url = link_el.get('href', '') if link_el is not None else ''
        pub_date = (
            entry.findtext('atom:published', namespaces=ns) or
            entry.findtext('atom:updated', namespaces=ns) or ''
        ).strip()
        posts.append({
            'title':    title,
            'url':      url,
            'subreddit': subreddit,
            'pub_date': pub_date,
            'is_local': subreddit in LOCAL_SUBREDDITS,
            'score':    0,
            'num_comments': 0,
        })
    return posts


def fetch_reddit_rss(feeds):
    """Fetch Reddit RSS. Local subs are keyword-filtered; national RE subs accepted as-is."""
    local_posts    = []
    national_posts = []

    for subreddit, url in feeds.items():
        try:
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_data = resp.read()
            posts = parse_reddit_rss(xml_data, subreddit)
            is_local = subreddit in LOCAL_SUBREDDITS
            for post in posts:
                if is_out_of_state(post['title']):
                    continue
                if is_local and not is_re_relevant(post['title']):
                    continue
                if is_local:
                    local_posts.append(post)
                else:
                    national_posts.append(post)
            time.sleep(0.5)
        except Exception as e:
            print(f'WARNING: Reddit RSS failed for r/{subreddit}: {e}', file=sys.stderr)

    # Local always fills first 3 slots; national fills rest
    return (local_posts[:3] + national_posts[:7])[:10]


# ── News RSS ──────────────────────────────────────────────────────────────────

def parse_rss_feed(xml_bytes, source):
    """Parse RSS2 or Atom XML bytes. Returns up to 5 items."""
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
                'title':       title,
                'url':         link,
                'description': description,
                'pub_date':    pub_date,
                'source':      source,
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


# ── RentCast ──────────────────────────────────────────────────────────────────

def parse_rentcast_response(data):
    if not data:
        return {}
    if isinstance(data, list):
        data = data[0] if data else {}
    if not data:
        return {}
    rental = data.get('rentalData') or data
    sale   = data.get('saleData') or {}
    return {
        'median_rent':          rental.get('medianRent') or rental.get('averageRent'),
        'rent_yoy_change':      rental.get('rentYoYChange') or rental.get('averageRentYoY'),
        'rental_dom':           rental.get('averageDaysOnMarket') or rental.get('daysOnMarket'),
        'rental_new_listings':  rental.get('newListings'),
        'rental_total_listings':rental.get('totalListings'),
        'sale_median_price':    sale.get('medianPrice'),
        'sale_avg_price':       sale.get('averagePrice'),
        'sale_price_per_sqft':  sale.get('medianPricePerSquareFoot') or sale.get('averagePricePerSquareFoot'),
        'sale_dom':             sale.get('averageDaysOnMarket'),
        'sale_median_dom':      sale.get('medianDaysOnMarket'),
        'sale_new_listings':    sale.get('newListings'),
        'sale_total_listings':  sale.get('totalListings'),
        'sale_updated':        (sale.get('lastUpdatedDate') or '')[:10],
        'city':       'Fort Worth',
        'state':      'TX',
        'zip':        '76179',
        'pulled_at':  datetime.now(timezone.utc).isoformat(),
        'source_url': 'https://app.rentcast.io',
    }


def load_rentcast_cache():
    try:
        with open(RENTCAST_CACHE_PATH, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'calls': [], 'last_response': {}}


def save_rentcast_cache(cache):
    os.makedirs(os.path.dirname(os.path.abspath(RENTCAST_CACHE_PATH)), exist_ok=True)
    with open(RENTCAST_CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2)


def fetch_rentcast(api_key):
    """Fetch NW Fort Worth/76179 market snapshot. Caches response, guards monthly call budget."""
    if not api_key:
        print('WARNING: RENTCAST_API_KEY not set — skipping market data', file=sys.stderr)
        return {}

    cache = load_rentcast_cache()
    now   = datetime.now(timezone.utc)
    month = now.strftime('%Y-%m')
    calls_this_month = sum(1 for c in cache.get('calls', []) if c.startswith(month))

    if calls_this_month >= RENTCAST_BUDGET:
        print(f'WARNING: RentCast at {calls_this_month}/{RENTCAST_BUDGET} calls this month — using cache',
              file=sys.stderr)
        cached = dict(cache.get('last_response', {}))
        if cached:
            cached['_stale']      = True
            cached['_cache_note'] = f'Cached response (budget limit: {calls_this_month} calls this month)'
        return cached

    url = f'{RENTCAST_BASE}?zipCode=76179'
    try:
        req = urllib.request.Request(url, headers={'X-Api-Key': api_key, 'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        result = parse_rentcast_response(data)
        cache['calls'] = cache.get('calls', []) + [now.isoformat()]
        cache['last_response'] = result
        save_rentcast_cache(cache)
        print(f'SIGNAL: RentCast call #{calls_this_month + 1} this month logged', flush=True)
        return result
    except Exception as e:
        print(f'WARNING: RentCast fetch failed: {e}', file=sys.stderr)
        cached = dict(cache.get('last_response', {}))
        if cached:
            cached['_stale']      = True
            cached['_cache_note'] = f'Cached response (live fetch failed: {e})'
        return cached


# ── Scoring (algorithmic layer — kept as fallback) ────────────────────────────

_OWNER_ACQ_KW = {
    'investor', 'invest', 'investment', 'portfolio', 'passive', 'income',
    'management', 'manage', 'landlord', 'cash', 'roi', 'cap',
    'appreciation', 'return', 'wealth', 'asset', 'owner',
}
_PM_KW = {
    'tenant', 'renter', 'lease', 'evict', 'eviction', 'maintenance',
    'repair', 'vacancy', 'vacant', 'rent', 'rental', 'deposit', 'screening',
    'turnover', 'application',
}
_SALES_KW = {
    'buyer', 'seller', 'closing', 'mortgage', 'listing', 'offer',
    'contract', 'price', 'equity', 'down', 'approved', 'sell', 'buy',
}


def _kw_hits(text, kw_set):
    words = text.lower().replace('-', ' ').replace('/', ' ').split()
    return sum(1 for w in words if w in kw_set)


def _priority_score(title, source_type, engagement_score):
    tl = title.lower()
    owner_score = min(_kw_hits(tl, _OWNER_ACQ_KW) * 2.5, 10)
    pm_score    = min(_kw_hits(tl, _PM_KW) * 2.5, 10)
    if source_type in ('local_reddit', 'fw_report', 'local_rss'):
        local_score = 10
    elif 'fort worth' in tl or 'tarrant' in tl:
        local_score = 7
    elif source_type == 'national_rss':
        local_score = 4
    else:
        local_score = 3
    if source_type == 'rentcast':
        content_score = 9
    elif engagement_score > 200:
        content_score = 10
    elif engagement_score > 100:
        content_score = 7
    elif engagement_score > 0:
        content_score = 4
    else:
        content_score = 4
    urgency_score = (9 if source_type in ('local_reddit', 'fw_report')
                     else 8 if source_type == 'rentcast'
                     else 7 if source_type == 'local_rss'
                     else 5 if source_type == 'national_rss'
                     else 3)
    raw = (owner_score * 0.30 + local_score * 0.25 + content_score * 0.20
           + pm_score * 0.15 + urgency_score * 0.10)
    return round(min(raw, 10.0), 1)


def _business_lens(title, source_type):
    if source_type in ('rentcast', 'fallback'):
        return 'both'
    tl = title.lower()
    pm_hits    = _kw_hits(tl, _PM_KW)
    sales_hits = _kw_hits(tl, _SALES_KW) + _kw_hits(tl, _OWNER_ACQ_KW)
    if pm_hits > 0 and sales_hits > 0:
        return 'both'
    if pm_hits > 0:
        return 'pm'
    if sales_hits > 0:
        return 'sales'
    return 'both'


def _urgency(source_type, engagement_score):
    if source_type in ('local_reddit', 'fw_report', 'rentcast'):
        return 'now'
    if source_type in ('local_rss', 'national_rss', 'national_reddit', 'fallback'):
        return 'this_week'
    return 'evergreen'


def _action_sentence(source_type, title, num_comments, market_data):
    if source_type == 'local_reddit':
        if num_comments and num_comments > 50:
            return (f"Write a blog post on this — {num_comments} comments signal "
                    "demand and your local answer will rank.")
        return ("Drop this in your FB Story with one local data point "
                "— it will outperform any polished post this week.")
    if source_type == 'fw_report':
        return ("Share to FB with one sentence of market context "
                "— FWR readers are your owner pipeline audience.")
    if source_type == 'local_rss':
        return ("Localize in one paragraph and post to IG "
                "— tie it to a specific neighborhood you manage.")
    if source_type == 'national_rss':
        return ("Use as blog intro hook — swap the national stat "
                "with your Tarrant County RentCast number before publishing.")
    if source_type == 'national_reddit':
        return ("Screenshot the top comment and overlay your local data "
                "— works as a Reel or IG carousel.")
    if source_type == 'rentcast':
        yoy = (market_data or {}).get('rent_yoy_change')
        if isinstance(yoy, (int, float)):
            direction = 'up' if yoy > 0 else 'down'
            return (f"Post a market reel — rents are {direction} {abs(yoy):.1f}% YoY "
                    "and both investors and renters want to know.")
        return ("Post the market numbers to FB with your read "
                "— data posts outperform opinion posts every time.")
    if source_type == 'fallback':
        return ("Market data unavailable this pull "
                "— do not publish rent stats until verified.")
    return ("Film a 60-second explainer — repurpose as YouTube Short, "
            "Reel, and FB video in one take.")


def _executive_summary(angles, market):
    parts = []
    yoy = market.get('rent_yoy_change')
    if isinstance(yoy, (int, float)):
        direction = 'up' if yoy > 0 else 'down'
        note = 'flag for owner renewals' if yoy > 2 else 'watch vacancy risk on new leases'
        parts.append(f"Rents {direction} {abs(yoy):.1f}% YoY in NW Fort Worth — {note}.")
    top = next((a for a in angles if a.get('urgency') == 'now'), angles[0] if angles else None)
    if top:
        lens = top.get('business_lens', 'both')
        lens_str = {'pm': 'PM-facing', 'sales': 'sales-facing', 'both': 'dual-use'}.get(lens, 'dual-use')
        parts.append(f"Lead with {lens_str}: {top['headline'][:70]}.")
    sale_dom = market.get('sale_dom')
    if isinstance(sale_dom, (int, float)):
        if sale_dom < 30:
            parts.append("Sale market is hot — prep buyers for fast decisions.")
        elif sale_dom < 60:
            parts.append(f"Sale DOM at {sale_dom:.0f}d — balanced, competitive listings win.")
        else:
            parts.append(f"Sale DOM at {sale_dom:.0f}d — buyers have leverage, price to move.")
    if not parts:
        parts.append("Pull complete — review Action Board below and verify market data before publishing.")
    return ' '.join(parts)


def generate_angles(reddit_posts, rss_items, market_data):
    """Generate 7 algorithmic content angle dicts (fallback if LLM unavailable)."""
    angles = []

    local_reddit    = [p for p in reddit_posts
                       if p.get('is_local', p.get('subreddit') in LOCAL_SUBREDDITS)]
    national_reddit = [p for p in reddit_posts
                       if not p.get('is_local', p.get('subreddit') in LOCAL_SUBREDDITS)
                       and not is_out_of_state(p['title'])]
    fw_report_rss   = [i for i in rss_items
                       if i.get('source') == 'FortWorthReport' and is_re_relevant(i['title'])]
    other_local_rss = [i for i in rss_items
                       if i.get('source') in LOCAL_RSS_SOURCES
                       and i.get('source') != 'FortWorthReport'
                       and is_re_relevant(i['title'])]
    national_rss    = [i for i in rss_items if i.get('source') not in LOCAL_RSS_SOURCES]

    raw_pool = []
    raw_pool.extend(('local_reddit',    p) for p in local_reddit[:3])
    raw_pool.extend(('fw_report',       i) for i in fw_report_rss[:1])
    raw_pool.extend(('local_rss',       i) for i in other_local_rss[:1])
    raw_pool.extend(('national_rss',    i) for i in national_rss[:5])
    raw_pool.extend(('national_reddit', p) for p in national_reddit[:5])

    _seen: set = set()
    content_pool = []
    for src_type, item in raw_pool:
        url = item.get('url', '')
        if url and url in _seen:
            continue
        if url:
            _seen.add(url)
        content_pool.append((src_type, item))
        if len(content_pool) == 5:
            break

    for src_type, item in content_pool:
        if src_type in ('local_reddit', 'national_reddit'):
            p = item
            is_local = src_type == 'local_reddit'
            eng = p['score'] + p['num_comments'] * 2
            title = p['title']
            angles.append({
                'rank': 0,
                'headline': (f"Fort Worth: {title[:90]}" if is_local
                             else f"What Fort Worth Buyers Should Know: {title[:70]}"),
                'format': 'blog' if p['num_comments'] > 50 else 'social',
                'seo_keyword': 'fort worth real estate 2026' if is_local else 'fort worth real estate market 2026',
                'competition': 'low' if is_local else 'medium',
                'source_type': src_type, 'source_title': title, 'source_url': p['url'],
                'engagement_score': eng,
                'business_lens': _business_lens(title, src_type),
                'urgency': _urgency(src_type, eng),
                'priority_score': _priority_score(title, src_type, eng),
                'action': _action_sentence(src_type, title, p['num_comments'], market_data),
            })
        else:
            rss_item = item
            is_local_src = src_type in ('fw_report', 'local_rss')
            title = rss_item['title']
            angles.append({
                'rank': 0,
                'headline': (f"Fort Worth: {title[:90]}" if is_local_src
                             else f"{title[:80]} — What It Means for Fort Worth"),
                'format': 'blog',
                'seo_keyword': ('fort worth real estate news 2026' if is_local_src
                                else 'fort worth real estate market 2026'),
                'competition': 'low' if is_local_src else 'medium',
                'source_type': src_type, 'source_title': title, 'source_url': rss_item['url'],
                'engagement_score': 0,
                'business_lens': _business_lens(title, src_type),
                'urgency': _urgency(src_type, 0),
                'priority_score': _priority_score(title, src_type, 0),
                'action': _action_sentence(src_type, title, 0, market_data),
            })

    # Slot 6: RentCast market
    if market_data.get('median_rent'):
        yoy = market_data.get('rent_yoy_change')
        yoy_str = f"{yoy:+.1f}%" if isinstance(yoy, (int, float)) else "shifting"
        mkt_headline = f"Fort Worth Rental Market Update: Rents {yoy_str} YoY — Data and Analysis"
        angles.append({
            'rank': 0, 'headline': mkt_headline, 'format': 'screen_recording',
            'seo_keyword': 'fort worth rental market 2026', 'competition': 'low',
            'source_type': 'rentcast',
            'source_title': f"RentCast Tarrant County — pulled {market_data.get('pulled_at', '')[:10]}",
            'source_url': market_data.get('source_url', 'https://app.rentcast.io'),
            'engagement_score': 0, 'business_lens': 'both', 'urgency': 'now',
            'priority_score': _priority_score(mkt_headline, 'rentcast', 0),
            'action': _action_sentence('rentcast', mkt_headline, 0, market_data),
        })
    else:
        angles.append({
            'rank': 0,
            'headline': 'Tarrant County Market Update: What Buyers and Renters Need to Know',
            'format': 'social', 'seo_keyword': 'tarrant county real estate 2026',
            'competition': 'low', 'source_type': 'fallback',
            'source_title': 'Market data unavailable this pull — verify before publishing',
            'source_url': '', 'engagement_score': 0, 'business_lens': 'both',
            'urgency': 'this_week', 'priority_score': 2.0,
            'action': _action_sentence('fallback', '', 0, market_data),
        })

    # Slot 7: Evergreen
    top_local = local_reddit[0]['subreddit'] if local_reddit else 'FortWorth'
    angles.append({
        'rank': 0,
        'headline': 'Why Fort Worth Is Still One of the Best Places to Buy in Texas Right Now',
        'format': 'youtube', 'seo_keyword': 'fort worth real estate buy 2026',
        'competition': 'medium', 'source_type': 'reddit',
        'source_title': f"r/{top_local} — top local discussions this week",
        'source_url': f"https://reddit.com/r/{top_local}",
        'engagement_score': 0, 'business_lens': 'sales', 'urgency': 'evergreen',
        'priority_score': 5.0,
        'action': _action_sentence('evergreen', '', 0, market_data),
    })

    angles.sort(key=lambda a: a['priority_score'], reverse=True)
    rc_idx = next((i for i, a in enumerate(angles) if a['source_type'] == 'rentcast'), None)
    if rc_idx is not None and rc_idx > 2 and angles[rc_idx]['priority_score'] >= 2.0:
        angles.insert(2, angles.pop(rc_idx))
    for i, angle in enumerate(angles):
        angle['rank'] = i + 1
    return angles


# ── Claude LLM analysis ───────────────────────────────────────────────────────

def call_claude(prompt, api_key, model='claude-sonnet-4-6'):
    """Call Claude API via stdlib urllib. Returns response text or None."""
    payload = json.dumps({
        'model': model,
        'max_tokens': 2000,
        'messages': [{'role': 'user', 'content': prompt}],
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'x-api-key':         api_key,
            'anthropic-version': '2023-06-01',
            'content-type':      'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
        return result['content'][0]['text']
    except Exception as e:
        print(f'WARNING: Claude API call failed: {e}', file=sys.stderr)
        return None


def run_llm_analysis(reddit_posts, rss_items, market_data, api_key):
    """
    Run Claude analysis over pulled data. Returns structured dict with brief sections.
    Falls back to empty dict if API key missing or call fails.
    """
    if not api_key:
        print('WARNING: ANTHROPIC_API_KEY not set — skipping LLM analysis', file=sys.stderr)
        return {}

    reddit_lines = [f"r/{p['subreddit']}: {p['title']}" for p in reddit_posts[:10]]
    rss_lines    = [f"{i['source']}: {i['title']}" for i in rss_items[:10]]

    if market_data.get('median_rent'):
        yoy = market_data.get('rent_yoy_change')
        yoy_str = f'{yoy:+.1f}%' if isinstance(yoy, (int, float)) else 'unknown'
        stale = ' (CACHED — may be stale)' if market_data.get('_stale') else ''
        market_line = (f"Median rent: ${market_data['median_rent']:,.0f} | "
                       f"YoY: {yoy_str} | DOM: {market_data.get('rental_dom', 'N/A')}d{stale}")
    else:
        market_line = 'RentCast data unavailable this pull'

    prompt = f"""You are the market intelligence engine for All Panther Properties — a property management and real estate company in Fort Worth / Saginaw, TX (Tarrant County).

Andrew Chavis is a REALTOR® and property manager with 75+ rental doors in NW Fort Worth. His audience: (1) burned-out DIY landlords who might hand over management, (2) remote investors, (3) buyers/sellers in Tarrant County.

Analyze this week's signal data and return a JSON object with EXACTLY these keys:

{{
  "owner_lead_signals": "2-3 bullet points identifying Reddit/news patterns that suggest landlord frustration, burnout, or remote management pain. Be specific — what are people actually saying, not generic observations.",
  "reddit_friction": [
    {{"pattern": "one-sentence description", "category": "one of: pricing confusion | lease-up delay | tenant screening pain | repair/vendor complaint | property tax anxiety | insurance anxiety | builder incentive skepticism | renter affordability complaint | landlord burnout | remote owner friction", "example": "exact or paraphrased post title"}}
  ],
  "content_angles": [
    {{"rank": 1, "topic": "specific content topic", "format": "blog|social|youtube", "seo_keyword": "specific keyword phrase", "source": "where this signal came from", "why": "one sentence on why this resonates with Andrew's audience"}}
  ],
  "action_board": "2-3 bullet points of anything requiring Andrew's attention this week. Fast-moving news, patterns matching a 75+ door NW Fort Worth portfolio, anything that should influence listings or outreach. If nothing urgent, say so plainly.",
  "data_quality": "One paragraph: what pulled clean, what failed or was missing, what was cached/stale. Be honest about gaps — no fake precision."
}}

Hard rules:
- No owner names, tenant names, specific addresses, or client details — market patterns only
- No fake precision — if data is thin, say the data is thin
- content_angles: return 3 to 5, ranked by usefulness to Andrew
- reddit_friction: return 3 to 5 most notable patterns
- Return ONLY valid JSON. No markdown code fences. No preamble. No trailing text.

DATA THIS WEEK:

Reddit posts ({len(reddit_posts)} pulled):
{chr(10).join(reddit_lines) if reddit_lines else 'None pulled'}

News RSS ({len(rss_items)} pulled):
{chr(10).join(rss_lines) if rss_lines else 'None pulled'}

RentCast market data (76179 NW Fort Worth):
{market_line}
"""

    print('SIGNAL: running LLM analysis...', flush=True)
    response = call_claude(prompt, api_key)
    if not response:
        return {}

    text = response.strip()
    if text.startswith('```'):
        lines = text.split('\n', 1)
        text = lines[1] if len(lines) > 1 else text[3:]
        if text.rstrip().endswith('```'):
            text = text.rstrip()[:-3]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f'WARNING: LLM response not valid JSON: {e}', file=sys.stderr)
        return {}


# ── Output writers ────────────────────────────────────────────────────────────

def write_data_json(data, path='signal/data.json'):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_brief_md(data, analysis, path='signal/brief.md'):
    """Write structured Markdown brief combining LLM analysis and market data."""
    pulled_at = data.get('pulled_at', '')
    market    = data.get('market', {})
    angles    = data.get('angles', [])

    lines = [
        f'# SIGNAL Weekly Brief — {pulled_at[:10]}',
        '',
        f'_Generated: {pulled_at[:16]} UTC_',
        '',
        '---',
        '',
        '## Owner Lead Signals',
        '',
    ]

    if analysis.get('owner_lead_signals'):
        lines.append(analysis['owner_lead_signals'])
    else:
        lines.append('_LLM analysis unavailable this pull._')

    lines += ['', '---', '', '## NW Fort Worth / 76179 Rental Notes', '']

    if market.get('median_rent'):
        yoy     = market.get('rent_yoy_change')
        yoy_str = f'{yoy:+.1f}%' if isinstance(yoy, (int, float)) else 'N/A'
        stale   = ' _(cached — may be stale)_' if market.get('_stale') else ''
        lines += [
            f'- **Median Rent:** ${market["median_rent"]:,.0f}{stale}',
            f'- **YoY Change:** {yoy_str}',
            f'- **Rental DOM:** {market.get("rental_dom", "N/A")}d',
            f'- **New Listings:** {market.get("rental_new_listings", "N/A")}',
        ]
        if market.get('sale_median_price'):
            lines += [
                f'- **Sale Median:** ${market["sale_median_price"]:,.0f}',
                f'- **Sale DOM:** {market.get("sale_dom", "N/A")}d',
            ]
        lines += [
            '',
            f'_Source: RentCast · Zip 76179 · Pulled: {market.get("pulled_at", "")[:10]}_',
        ]
        if market.get('_cache_note'):
            lines.append(f'_{market["_cache_note"]}_')
    else:
        lines.append('_RentCast data unavailable this pull. Do not publish market stats until verified._')

    lines += ['', '---', '', '## Reddit Community Friction', '']

    friction = analysis.get('reddit_friction', [])
    if friction:
        for item in friction:
            lines.append(f'- **[{item.get("category", "unknown")}]** {item.get("pattern", "")}')
            if item.get('example'):
                lines.append(f'  > _{item["example"]}_')
    else:
        lines.append('_LLM analysis unavailable this pull._')

    lines += ['', '---', '', '## Content Angles', '']

    llm_angles = analysis.get('content_angles', [])
    if llm_angles:
        for a in llm_angles:
            lines += [
                f'**{a.get("rank", "")}. {a.get("topic", "")}**',
                f'- Format: {a.get("format", "").upper()} · SEO: `{a.get("seo_keyword", "")}`',
                f'- Source: {a.get("source", "")}',
            ]
            if a.get('why'):
                lines.append(f'- {a["why"]}')
            lines.append('')
    else:
        for a in angles[:5]:
            lines += [
                f'**{a["rank"]}. {a["headline"]}**',
                f'- Format: {a["format"].upper()} · SEO: `{a.get("seo_keyword", "")}`',
                f'- Source: {a.get("source_title", "")}',
                '',
            ]

    lines += ['---', '', '## Action Board', '']

    if analysis.get('action_board'):
        lines.append(analysis['action_board'])
    else:
        lines.append('_LLM analysis unavailable this pull._')

    lines += ['', '---', '', '## Data Quality Notes', '']

    if analysis.get('data_quality'):
        lines.append(analysis['data_quality'])
    else:
        lines += [
            f'- Reddit RSS: {len(data.get("reddit", []))} posts pulled',
            f'- News RSS: {len(data.get("rss", []))} items pulled',
            f'- RentCast: {"OK" if market.get("median_rent") else "FAILED — data unavailable"}',
            f'- LLM analysis: unavailable (API key missing or call failed)',
        ]

    lines += [
        '',
        '---',
        '',
        '_SIGNAL · allpantherproperties.com · Every stat is sourced and timestamped. '
        'Do not publish unverified data._',
    ]

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def write_archive(brief_md_path, archive_dir='signal/archive'):
    """Copy brief.md to archive/YYYY-MM-DD-brief.md."""
    date_str     = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    archive_path = os.path.join(archive_dir, f'{date_str}-brief.md')
    os.makedirs(archive_dir, exist_ok=True)
    try:
        with open(brief_md_path, encoding='utf-8') as f:
            content = f.read()
        with open(archive_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'SIGNAL: archived to {archive_path}', flush=True)
    except Exception as e:
        print(f'WARNING: archive write failed: {e}', file=sys.stderr)


# ── HTML generator ────────────────────────────────────────────────────────────

def generate_html(data, analysis=None, path='signal/brief.html'):
    """Generate self-contained visual dashboard HTML."""
    pulled_at = data.get('pulled_at', 'Unknown')
    angles    = data.get('angles', [])
    market    = data.get('market', {})
    analysis  = analysis or {}

    FORMAT_BADGES = {
        'blog':             ('#2563eb', 'BLOG POST'),
        'social':           ('#16a34a', 'SOCIAL'),
        'youtube':          ('#dc2626', 'YOUTUBE'),
        'screen_recording': ('#7c3aed', 'SCREEN REC'),
        'fallback':         ('#6b7280', 'VERIFY DATA'),
    }
    LENS_BADGES = {
        'pm':    ('#0891b2', 'PM'),
        'sales': ('#b45309', 'SALES'),
        'both':  ('#6d28d9', 'BOTH'),
    }
    URGENCY_BADGES = {
        'now':       ('#dc2626', 'NOW'),
        'this_week': ('#d97706', 'THIS WEEK'),
        'evergreen': ('#15803d', 'EVERGREEN'),
    }

    def badge(text, bg):
        return (f'<span style="background:{bg};color:#fff;padding:2px 8px;'
                f'border-radius:4px;font-size:11px;font-weight:700;">{text}</span>')

    def action_card(a):
        color, fmt_label = FORMAT_BADGES.get(a.get('format', ''), ('#6b7280', a.get('format', '').upper()))
        lens_color, lens_label = LENS_BADGES.get(a.get('business_lens', 'both'), ('#6b7280', 'BOTH'))
        urg_color, urg_label   = URGENCY_BADGES.get(a.get('urgency', 'this_week'), ('#6b7280', ''))
        score      = a.get('priority_score', '')
        score_html = (f'<span style="background:#1e3a5f;color:#38bdf8;padding:2px 8px;'
                      f'border-radius:4px;font-size:11px;font-weight:700;">SCORE {score}</span>'
                      if score != '' else '')
        action_html = (f'<div style="color:#fbbf24;font-size:13px;margin-bottom:8px;">'
                       f'&rarr; {a.get("action", "")}</div>' if a.get('action') else '')
        src = (f'<a href="{a["source_url"]}" target="_blank" style="color:#94a3b8;font-size:12px;">'
               f'&rarr; {a.get("source_title", "")[:80]}</a>'
               if a.get('source_url') else
               f'<span style="color:#ef4444;font-size:12px;">&#9888; {a.get("source_title", "")}</span>')
        return (
            f'<div style="background:#1e293b;border-radius:8px;padding:16px;margin-bottom:12px;border-left:4px solid {color};">'
            f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;flex-wrap:wrap;">'
            + badge(lens_label, lens_color) + badge(urg_label, urg_color)
            + f'<span style="background:#334155;color:#94a3b8;padding:2px 8px;border-radius:4px;font-size:11px;">#{a["rank"]}</span>'
            + score_html + badge(fmt_label, color)
            + f'<span style="background:#334155;color:#94a3b8;padding:2px 8px;border-radius:4px;font-size:11px;">{a.get("competition","").upper()} COMP</span>'
            + '</div>'
            + f'<div style="color:#f1f5f9;font-size:16px;font-weight:600;margin-bottom:8px;">{a["headline"]}</div>'
            + action_html
            + f'<div style="color:#64748b;font-size:12px;margin-bottom:6px;">SEO: <code style="color:#38bdf8;background:#0f172a;padding:2px 4px;">{a.get("seo_keyword","")}</code></div>'
            + src + '</div>'
        )

    def llm_angle_card(a, rank):
        fmt = a.get('format', 'social')
        color, fmt_label = FORMAT_BADGES.get(fmt, ('#6b7280', fmt.upper()))
        return (
            f'<div style="background:#1e293b;border-radius:8px;padding:16px;margin-bottom:12px;border-left:4px solid {color};">'
            f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;flex-wrap:wrap;">'
            + f'<span style="background:#334155;color:#94a3b8;padding:2px 8px;border-radius:4px;font-size:11px;">#{rank}</span>'
            + badge(fmt_label, color)
            + '</div>'
            + f'<div style="color:#f1f5f9;font-size:16px;font-weight:600;margin-bottom:8px;">{a.get("topic","")}</div>'
            + (f'<div style="color:#fbbf24;font-size:13px;margin-bottom:8px;">&rarr; {a["why"]}</div>' if a.get('why') else '')
            + f'<div style="color:#64748b;font-size:12px;margin-bottom:6px;">SEO: <code style="color:#38bdf8;background:#0f172a;padding:2px 4px;">{a.get("seo_keyword","")}</code></div>'
            + f'<span style="color:#94a3b8;font-size:12px;">{a.get("source","")}</span>'
            + '</div>'
        )

    def stat_box(value, label, color='#38bdf8', note=''):
        note_html = (f'<div style="color:#475569;font-size:10px;margin-top:4px;line-height:1.3">{note}</div>'
                     if note else '')
        return (
            f'<div style="background:#1e293b;border-radius:8px;padding:16px;text-align:center;">'
            f'<div style="color:{color};font-size:24px;font-weight:700;">{value}</div>'
            f'<div style="color:#64748b;font-size:11px;margin-top:4px;">{label}</div>'
            + note_html + '</div>'
        )

    # Market HTML
    if market.get('median_rent') or market.get('sale_median_price'):
        pulled   = market.get('pulled_at', '')[:10]
        zipc     = market.get('zip', '76179')
        yoy      = market.get('rent_yoy_change')
        yoy_disp = f'{yoy:+.1f}%' if isinstance(yoy, (int, float)) else 'N/A'
        yoy_color = '#4ade80' if isinstance(yoy, (int, float)) and yoy > 0 else '#f87171'
        yoy_note = ('Strong growth — flag for owner renewals' if isinstance(yoy, (int, float)) and yoy > 3
                    else 'Modest growth — hold rents on renewals' if isinstance(yoy, (int, float)) and yoy > 0
                    else 'Declining — review pricing on vacants' if isinstance(yoy, (int, float)) else '')
        dom      = market.get('rental_dom')
        dom_note = ('Below 21d — price at or above market' if isinstance(dom, (int, float)) and dom < 21
                    else 'Healthy — price competitively' if isinstance(dom, (int, float)) and dom < 30
                    else 'Above 30d — consider price cut' if isinstance(dom, (int, float)) else '')
        stale_banner = (
            '<div style="color:#f59e0b;background:#1e293b;border-radius:6px;padding:8px 12px;'
            'margin-bottom:12px;font-size:12px;">&#9888; Cached response — live fetch was skipped '
            '(budget limit or fetch error). Verify before publishing rent stats.</div>'
            if market.get('_stale') else ''
        )
        rental_row = (
            f'<div style="margin-bottom:8px;color:#94a3b8;font-size:11px;font-weight:600;'
            f'text-transform:uppercase;letter-spacing:1px;">Rental Market</div>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:20px;">'
            + stat_box(f'${market["median_rent"]:,.0f}', 'Median Rent', '#38bdf8', 'Anchor for rental pricing')
            + stat_box(yoy_disp, 'YoY Change', yoy_color, yoy_note)
            + stat_box(f'{dom or "N/A"}d', 'Avg DOM', '#a78bfa', dom_note)
            + stat_box(str(market.get('rental_new_listings') or 'N/A'), 'New Listings', '#fb923c', 'Supply entering market')
            + '</div>'
        ) if market.get('median_rent') else ''

        sale_dom = market.get('sale_dom')
        sale_dom_note = ("Sellers' market — buyers need pre-approval ready"
                         if isinstance(sale_dom, (int, float)) and sale_dom < 30
                         else 'Balanced — competitive listings win'
                         if isinstance(sale_dom, (int, float)) and sale_dom < 60
                         else "Buyers' market — price to move"
                         if isinstance(sale_dom, (int, float)) else '')
        sale_row = (
            f'<div style="margin-bottom:8px;color:#94a3b8;font-size:11px;font-weight:600;'
            f'text-transform:uppercase;letter-spacing:1px;">Sale Market</div>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;">'
            + stat_box(f'${market["sale_median_price"]:,.0f}', 'Median Sale Price', '#34d399', 'Tarrant County median')
            + stat_box(f'${market.get("sale_price_per_sqft") or 0:,.0f}/sqft', 'Price / SqFt', '#34d399', 'Comp baseline')
            + stat_box(f'{sale_dom or "N/A"}d', 'Avg DOM', '#a78bfa', sale_dom_note)
            + stat_box(str(market.get('sale_new_listings') or 'N/A'), 'New Listings', '#fb923c', 'Watch for inventory shifts')
            + stat_box(str(market.get('sale_total_listings') or 'N/A'), 'Total Listings', '#64748b', 'Overall inventory depth')
            + '</div>'
        ) if market.get('sale_median_price') else ''

        market_html = (
            stale_banner + rental_row + sale_row +
            f'<div style="color:#64748b;font-size:11px;margin-top:10px;">'
            f'Source: RentCast &middot; Zip {zipc} &middot; Pulled: {pulled}</div>'
        )
    else:
        market_html = (
            '<div style="color:#ef4444;padding:12px;background:#1e293b;border-radius:8px;">'
            '&#9888; RentCast data unavailable this pull &mdash; do not publish market stats '
            'until verified from another source.</div>'
        )

    # Owner Lead Signals section
    owner_html = ''
    if analysis.get('owner_lead_signals'):
        raw = analysis['owner_lead_signals'].replace('\n', '<br>')
        owner_html = (
            f'<div style="background:#1e293b;border-radius:8px;padding:20px;border-left:4px solid #f59e0b;">'
            f'<p style="color:#e2e8f0;font-size:14px;line-height:1.7;">{raw}</p></div>'
        )

    # Reddit Friction section
    friction_html = ''
    friction = analysis.get('reddit_friction', [])
    if friction:
        FRICTION_COLORS = {
            'pricing confusion': '#f59e0b',
            'lease-up delay': '#ef4444',
            'tenant screening pain': '#8b5cf6',
            'repair/vendor complaint': '#f97316',
            'property tax anxiety': '#dc2626',
            'insurance anxiety': '#dc2626',
            'builder incentive skepticism': '#64748b',
            'renter affordability complaint': '#06b6d4',
            'landlord burnout': '#ec4899',
            'remote owner friction': '#10b981',
        }
        items_html = ''
        for item in friction:
            cat   = item.get('category', 'other')
            color = FRICTION_COLORS.get(cat, '#64748b')
            items_html += (
                f'<div style="background:#0f172a;border-radius:6px;padding:12px;margin-bottom:8px;">'
                f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;'
                f'font-size:10px;font-weight:700;text-transform:uppercase;">{cat}</span>'
                f'<div style="color:#e2e8f0;font-size:14px;margin-top:8px;">{item.get("pattern","")}</div>'
                + (f'<div style="color:#64748b;font-size:12px;margin-top:6px;font-style:italic;">'
                   f'&ldquo;{item.get("example","")}&rdquo;</div>' if item.get('example') else '')
                + '</div>'
            )
        friction_html = items_html

    # Content Angles
    llm_angles = analysis.get('content_angles', [])
    if llm_angles:
        angles_html = ''.join(llm_angle_card(a, a.get('rank', i+1)) for i, a in enumerate(llm_angles))
    else:
        angles_html = ''.join(action_card(a) for a in angles)

    # Action Board
    if analysis.get('action_board'):
        raw = analysis['action_board'].replace('\n', '<br>')
        action_board_html = (
            f'<div style="background:#1e293b;border-radius:8px;padding:20px;border-left:4px solid #38bdf8;">'
            f'<p style="color:#e2e8f0;font-size:14px;line-height:1.7;">{raw}</p></div>'
        )
    else:
        action_board_html = (
            '<div style="color:#64748b;font-size:13px;padding:12px;">'
            'LLM analysis unavailable — see content angles above for action items.</div>'
        )

    # Data Quality
    if analysis.get('data_quality'):
        dq_text = analysis['data_quality'].replace('\n', '<br>')
        dq_html = (
            f'<div style="background:#1e293b;border-radius:8px;padding:16px;">'
            f'<p style="color:#94a3b8;font-size:13px;line-height:1.6;">{dq_text}</p></div>'
        )
    else:
        dq_html = (
            f'<div style="background:#1e293b;border-radius:8px;padding:16px;">'
            f'<p style="color:#94a3b8;font-size:13px;">Reddit RSS: {len(data.get("reddit",[]))} posts &nbsp;|&nbsp; '
            f'News RSS: {len(data.get("rss",[]))} items &nbsp;|&nbsp; '
            f'RentCast: {"OK" if market.get("median_rent") else "unavailable"} &nbsp;|&nbsp; '
            f'LLM: unavailable</p></div>'
        )

    summary_text = _executive_summary(angles, market)

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

  <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:36px;flex-wrap:wrap;gap:12px">
    <div>
      <div style="font-size:11px;font-weight:700;letter-spacing:3px;color:#38bdf8;text-transform:uppercase;margin-bottom:6px">All Panther Properties</div>
      <div style="font-size:32px;font-weight:800;color:#f8fafc;letter-spacing:-0.5px">&#9889; SIGNAL</div>
      <div style="color:#475569;font-size:13px;margin-top:5px">Fort Worth Business Intelligence &mdash; Week of {pulled_at[:10]}</div>
    </div>
  </div>

  <div class="section">
    <div class="section-label">&#9889; This Week&#39;s Signal</div>
    <div style="background:#1e293b;border-radius:8px;padding:20px;border-left:4px solid #38bdf8;">
      <p style="color:#e2e8f0;font-size:15px;line-height:1.6;">{summary_text}</p>
    </div>
  </div>

  <hr class="divider">

  <div class="section">
    <div class="section-label">&#128273; Owner Lead Signals</div>
    {owner_html if owner_html else '<div style="color:#64748b;font-size:13px;padding:12px;">LLM analysis unavailable this pull.</div>'}
  </div>

  <hr class="divider">

  <div class="section">
    <div class="section-label">&#128172; Reddit Community Friction</div>
    {friction_html if friction_html else '<div style="color:#64748b;font-size:13px;padding:12px;">LLM analysis unavailable this pull.</div>'}
  </div>

  <hr class="divider">

  <div class="section">
    <div class="section-label">&#127919; Content Angles</div>
    <div id="angles">{angles_html}</div>
  </div>

  <hr class="divider">

  <div class="section">
    <div class="section-label">&#9889; Action Board</div>
    {action_board_html}
  </div>

  <hr class="divider">

  <div class="section">
    <div class="section-label">&#128202; Market Snapshot &mdash; Tarrant County / 76179</div>
    <div id="market">{market_html}</div>
  </div>

  <hr class="divider">

  <div class="section">
    <div class="section-label">&#128269; Data Quality Notes</div>
    {dq_html}
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


# ── Discord webhook ───────────────────────────────────────────────────────────

def send_discord_webhook(data, analysis, webhook_url):
    """Post SIGNAL summary card to Discord."""
    if not webhook_url:
        print('WARNING: DISCORD_WEBHOOK_URL not set — skipping Discord notification', file=sys.stderr)
        return

    pulled_at = data.get('pulled_at', '')[:10]
    market    = data.get('market', {})
    angles    = data.get('angles', [])

    if market.get('median_rent'):
        yoy     = market.get('rent_yoy_change')
        yoy_str = f'{yoy:+.1f}%' if isinstance(yoy, (int, float)) else 'N/A'
        dom     = market.get('rental_dom', 'N/A')
        stale   = ' (cached)' if market.get('_stale') else ''
        market_line = f'NW Fort Worth Rental: **${market["median_rent"]:,.0f}** | YoY {yoy_str} | {dom}d DOM{stale}'
    else:
        market_line = 'NW Fort Worth Rental: data unavailable this pull'

    friction     = analysis.get('reddit_friction', [])
    friction_str = ' | '.join(f.get('category', '') for f in friction[:2]) if friction else 'see brief'

    llm_angles = analysis.get('content_angles', [])
    top_angle  = (llm_angles[0].get('topic', '') if llm_angles
                  else angles[0].get('headline', '') if angles else 'see brief')[:90]

    brief_url = ('https://raw.githubusercontent.com/andrewchavis63/'
                 'c21-property-site/main/signal/brief.html')

    content = (
        f'\U0001f4cd **SIGNAL Weekly Brief — {pulled_at}**\n'
        f'{market_line}\n'
        f'Top friction: {friction_str}\n'
        f'Top angle: {top_angle}\n'
        f'Full brief: {brief_url}'
    )

    payload = json.dumps({'content': content}).encode('utf-8')
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={'Content-Type': 'application/json', 'User-Agent': USER_AGENT},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f'SIGNAL: Discord webhook sent (status {resp.status})', flush=True)
    except urllib.error.HTTPError as e:
        print(f'WARNING: Discord webhook failed {e.code}: {e.read().decode()[:200]}', file=sys.stderr)
    except Exception as e:
        print(f'WARNING: Discord webhook failed: {e}', file=sys.stderr)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    rentcast_key  = os.environ.get('RENTCAST_API_KEY', '')
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY', '')
    discord_url   = os.environ.get('DISCORD_WEBHOOK_URL', '')

    print('SIGNAL: pulling Reddit RSS...', flush=True)
    reddit_data = fetch_reddit_rss(REDDIT_RSS_FEEDS)
    print(f'  -> {len(reddit_data)} posts', flush=True)

    print('SIGNAL: pulling RSS feeds...', flush=True)
    rss_data = fetch_rss(RSS_FEEDS)
    print(f'  -> {len(rss_data)} items', flush=True)

    print('SIGNAL: pulling RentCast market data...', flush=True)
    market_data = fetch_rentcast(rentcast_key)
    rent_status = f'${market_data["median_rent"]:,.0f}' if market_data.get('median_rent') else 'unavailable'
    print(f'  -> median rent: {rent_status}', flush=True)

    print('SIGNAL: generating algorithmic angles...', flush=True)
    angles = generate_angles(reddit_data, rss_data, market_data)

    analysis = run_llm_analysis(reddit_data, rss_data, market_data, anthropic_key)
    if analysis:
        print('SIGNAL: LLM analysis complete', flush=True)
    else:
        print('SIGNAL: LLM unavailable — algorithmic angles only', flush=True)

    data = {
        'pulled_at': datetime.now(timezone.utc).isoformat(),
        'reddit':    reddit_data,
        'rss':       rss_data,
        'market':    market_data,
        'angles':    angles,
    }

    write_data_json(data)
    print('SIGNAL: signal/data.json written', flush=True)

    write_brief_md(data, analysis)
    print('SIGNAL: signal/brief.md written', flush=True)

    write_archive('signal/brief.md')

    generate_html(data, analysis)
    print('SIGNAL: signal/brief.html written', flush=True)

    print('SIGNAL: sending Discord webhook...', flush=True)
    send_discord_webhook(data, analysis, discord_url)

    llm_angles = analysis.get('content_angles', [])
    top = (llm_angles[0].get('topic') if llm_angles
           else angles[0]['headline'][:70] if angles else 'none')
    print(f'\nSIGNAL: done. Top angle: {top}', flush=True)


if __name__ == '__main__':
    main()
