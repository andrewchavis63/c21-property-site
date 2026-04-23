#!/usr/bin/env python3
"""
TAR(RENT) Post Cascade Generator
Reads a posts-queue/*.md file and updates all 6 cascade targets.
Usage: python scripts/generate-post.py posts-queue/2026-04-20-slug.md
"""

import sys
import re
import os
from datetime import datetime

# ── YAML frontmatter parser (no PyYAML dependency) ──────────────────────────

def parse_frontmatter(text):
    """Extract YAML frontmatter and body from markdown file."""
    if not text.startswith('---'):
        raise ValueError("File must start with --- frontmatter block")
    end = text.index('---', 3)
    yaml_block = text[3:end].strip()
    body = text[end+3:].strip()
    meta = {}
    current_key = None
    current_list = None
    current_item = None

    for line in yaml_block.splitlines():
        if not line.strip() or line.strip().startswith('#'):
            continue
        if line.startswith('  - badge:'):
            if current_item:
                current_list.append(current_item)
            current_item = {'badge': line.split('badge:')[1].strip()}
        elif line.startswith('    detail:') and current_item is not None:
            current_item['detail'] = line.split('detail:')[1].strip().strip('"')
        elif line.startswith('    url:') and current_item is not None:
            current_item['url'] = line.split('url:')[1].strip()
        elif line.startswith('sources:'):
            current_key = 'sources'
            current_list = []
            meta['sources'] = current_list
            current_item = None
        elif re.match(r'^[a-zA-Z_]+:', line):
            if current_item:
                current_list.append(current_item)
                current_item = None
            current_list = None
            k, _, v = line.partition(':')
            meta[k.strip()] = v.strip().strip('"')
            current_key = k.strip()

    if current_item:
        current_list.append(current_item)

    return meta, body


# ── Path helpers ─────────────────────────────────────────────────────────────

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def repo_path(*parts):
    return os.path.join(REPO, *parts)

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  [ok] wrote {os.path.relpath(path, REPO)}")


# ── Task A: Generate standalone post HTML ────────────────────────────────────

def generate_standalone_html(meta, body):
    slug = meta['slug']
    title = meta['title']
    description = meta['description']
    category = meta['category']
    date = meta['date']
    img = meta['img']
    img_alt = meta.get('img_alt', title)
    substack_slug = meta.get('substack_slug', slug)

    related = _build_related_links(slug)
    sources_note = f'Full sources at <a href="disclaimer.html" style="color:var(--gold);">disclaimer.html</a>. <a href="{slug}.html" style="color:var(--gold);">Read the full article →</a>'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title} | TAR(RENT)</title>
  <meta name="description" content="{description}" />
  <link rel="canonical" href="https://allpantherproperties.com/TARRENT/{slug}.html" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{description}" />
  <meta property="og:image" content="https://allpantherproperties.com/TARRENT/{img}" />
  <meta property="og:url" content="https://allpantherproperties.com/TARRENT/{slug}.html" />
  <meta property="og:site_name" content="TAR(RENT) — C21 Alliance Properties" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{title}" />
  <meta name="twitter:description" content="{description}" />
  <meta name="twitter:image" content="https://allpantherproperties.com/TARRENT/{img}" />
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"Article","headline":"{title}","description":"{description}","image":"https://allpantherproperties.com/TARRENT/{img}","datePublished":"{_pub_date_iso(meta['pubDate'])}","dateModified":"{_pub_date_iso(meta['pubDate'])}","author":{{"@type":"Person","name":"Andrew Chavis","url":"https://allpantherproperties.com/team-andrew.html"}},"publisher":{{"@type":"Organization","name":"Century 21 Alliance Properties","url":"https://allpantherproperties.com"}},"mainEntityOfPage":{{"@type":"WebPage","@id":"https://allpantherproperties.com/TARRENT/{slug}.html"}}}}
  </script>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet"/>
  <style>
    :root{{--gold:#C9A84C;--gold-light:#E8C96A;--gold-pale:#F5EDD5;--grey:#3A3A3A;--grey-dark:#1C1C1C;--grey-mid:#6B6B6B;--grey-light:#F0EFED;--white:#FAFAF8;--obsessed-grey:#2B2B2B;}}
    *{{margin:0;padding:0;box-sizing:border-box;}}body{{font-family:\'DM Sans\',sans-serif;background:var(--white);color:var(--grey-dark);}}
    nav{{position:sticky;top:0;z-index:100;background:var(--obsessed-grey);display:flex;justify-content:space-between;align-items:center;padding:0 48px;height:68px;border-bottom:2px solid var(--gold);}}
    .nav-logo{{display:flex;align-items:center;gap:10px;text-decoration:none;}}.nav-logo-img{{height:44px;width:auto;display:block;filter:brightness(0) saturate(100%) invert(70%) sepia(40%) saturate(600%) hue-rotate(5deg) brightness(0.95);}}
    .nav-brand-text{{font-family:\'Playfair Display\',serif;font-size:16px;font-weight:700;color:var(--white);letter-spacing:0.5px;line-height:1.2;}}.nav-brand-text span{{color:var(--gold);font-weight:400;font-size:13px;}}
    .nav-links{{display:flex;gap:32px;list-style:none;}}.nav-links a{{text-decoration:none;color:#aaa;font-size:13px;font-weight:500;letter-spacing:1px;text-transform:uppercase;transition:color 0.2s;}}.nav-links a:hover{{color:var(--gold);}}.nav-links a.active{{color:var(--gold);border-bottom:1px solid var(--gold);padding-bottom:2px;}}
    .nav-cta{{background:var(--gold);color:var(--obsessed-grey)!important;padding:8px 20px;border-radius:2px;font-weight:600!important;}}.nav-cta:hover{{background:var(--gold-light)!important;}}
    .breadcrumb{{background:var(--grey-light);padding:12px 48px;border-bottom:1px solid #e0ddd8;font-size:13px;color:var(--grey-mid);}}.breadcrumb a{{color:var(--gold);text-decoration:none;}}.breadcrumb a:hover{{text-decoration:underline;}}
    .post-page{{max-width:760px;margin:48px auto 80px;padding:0 24px;}}
    .article-hero-img{{width:100%;height:380px;object-fit:cover;display:block;filter:brightness(0.85);border-radius:4px;}}
    .article-body{{padding:48px 0 0;}}.article-meta{{display:flex;align-items:center;gap:12px;margin-bottom:20px;}}.article-cat{{font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--gold);}}.article-date{{font-size:12px;color:var(--grey-mid);}}.post-dot{{width:3px;height:3px;border-radius:50%;background:#ccc;display:inline-block;}}
    .article-body h1{{font-family:\'Playfair Display\',serif;font-size:36px;font-weight:900;line-height:1.2;color:var(--grey-dark);margin-bottom:24px;}}
    .article-body .intro{{font-size:17px;line-height:1.85;color:var(--grey);margin-bottom:32px;border-left:3px solid var(--gold);padding-left:20px;font-style:italic;}}
    .article-body h2{{font-family:\'Playfair Display\',serif;font-size:22px;font-weight:700;color:var(--obsessed-grey);margin:36px 0 14px;}}
    .article-body p{{font-size:15.5px;line-height:1.9;color:var(--grey);margin-bottom:20px;}}
    .article-body ul{{margin:0 0 24px 20px;}}.article-body ul li{{font-size:15px;line-height:1.8;color:var(--grey);margin-bottom:8px;}}.article-body ul li::marker{{color:var(--gold);}}
    .article-callout{{background:var(--gold-pale);border-left:4px solid var(--gold);padding:20px 24px;margin:28px 0;border-radius:2px;}}.article-callout p{{font-size:15px;color:var(--obsessed-grey);margin:0;font-weight:500;}}
    .stat-block{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:28px 0;}}
    .stat-item{{background:var(--grey-light);padding:20px;border-radius:4px;text-align:center;}}.stat-item .stat-num{{font-family:\'Playfair Display\',serif;font-size:32px;font-weight:900;color:var(--gold);display:block;}}.stat-item .stat-label{{font-size:12px;color:var(--grey-mid);margin-top:4px;letter-spacing:0.5px;}}
    .author-bio{{margin-top:40px;padding-top:32px;border-top:1px solid #eee;display:flex;align-items:center;gap:16px;}}.author-avatar{{width:52px;height:52px;border-radius:50%;background:var(--obsessed-grey);display:flex;align-items:center;justify-content:center;font-family:\'Playfair Display\',serif;font-weight:900;font-size:16px;color:var(--gold);flex-shrink:0;}}.author-name{{font-weight:600;font-size:14px;color:var(--grey-dark);}}.author-title{{font-size:12px;color:var(--grey-mid);margin-top:2px;}}.author-contact{{font-size:12px;color:var(--gold);margin-top:4px;}}
    .email-strip{{background:var(--obsessed-grey);padding:64px 48px;display:flex;justify-content:space-between;align-items:center;gap:40px;flex-wrap:wrap;margin-top:80px;}}
    .email-strip-text h3{{font-family:\'Playfair Display\',serif;font-size:28px;font-weight:700;color:var(--white);margin-bottom:8px;}}.email-strip-text h3 em{{color:var(--gold);font-style:italic;}}.email-strip-text p{{color:#999;font-size:14px;max-width:480px;line-height:1.6;}}
    .email-form{{display:flex;gap:12px;flex-shrink:0;}}.email-form input{{padding:12px 20px;background:rgba(255,255,255,0.08);border:1px solid #555;border-radius:2px;color:var(--white);font-family:\'DM Sans\',sans-serif;font-size:14px;width:260px;outline:none;transition:border-color 0.2s;}}.email-form input:focus{{border-color:var(--gold);}}.email-form input::placeholder{{color:#777;}}.email-form button{{padding:12px 28px;background:var(--gold);border:none;border-radius:2px;font-family:\'DM Sans\',sans-serif;font-size:12px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--obsessed-grey);cursor:pointer;transition:background 0.2s;}}.email-form button:hover{{background:var(--gold-light);}}
    footer{{background:#141414;padding:48px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:24px;}}.footer-logo-wrap{{display:flex;align-items:center;gap:14px;}}.footer-logo-img{{height:48px;width:auto;display:block;filter:brightness(0) saturate(100%) invert(70%) sepia(40%) saturate(600%) hue-rotate(5deg) brightness(0.95);}}.footer-logo-text{{font-family:\'Playfair Display\',serif;font-size:15px;color:var(--white);font-weight:700;}}.footer-logo-text span{{color:var(--gold);font-weight:400;font-size:13px;}}footer p{{font-size:12px;color:#555;}}.footer-links{{display:flex;gap:24px;}}.footer-links a{{font-size:12px;color:#555;text-decoration:none;transition:color 0.2s;}}.footer-links a:hover{{color:var(--gold);}}
    .related-posts{{margin:48px 0 0;padding:32px 0 0;border-top:1px solid rgba(183,102,53,.15);}}
    .related-label{{font-family:\'DM Sans\',sans-serif;font-size:11px;letter-spacing:3px;text-transform:uppercase;color:var(--gold);margin-bottom:16px;}}
    .related-link{{display:block;padding:12px 16px;border:1px solid rgba(183,102,53,.1);background:rgba(183,102,53,.02);text-decoration:none;margin-bottom:8px;transition:border-color .2s,background .2s;}}.related-link:hover{{border-color:rgba(183,102,53,.35);background:rgba(183,102,53,.06);}}
    .related-title{{font-family:\'DM Sans\',sans-serif;font-size:13px;color:#c0bdb6;font-weight:500;}}
    @media(max-width:900px){{nav{{padding:0 24px;}}.nav-links{{display:none;}}.breadcrumb{{padding:12px 24px;}}.email-strip{{padding:48px 24px;}}.stat-block{{grid-template-columns:1fr 1fr;}}}}
    @media(max-width:600px){{.email-form{{flex-direction:column;}}.email-form input{{width:100%;}}.stat-block{{grid-template-columns:1fr;}}}}
  </style>
</head>
<body>
<nav>
  <a class="nav-logo" href="../index.html"><img src="../img/C21_Seal_Black.png" alt="Century 21 Alliance Properties" class="nav-logo-img" /><div class="nav-brand-text">Andrew Chavis<span> | Century 21® Alliance Properties</span></div></a>
  <ul class="nav-links"><li><a href="../index.html#services">Services</a></li><li><a href="../index.html#about">Our Team</a></li><li><a href="../index.html#contact">Owners</a></li><li><a href="../tenant-criteria.html">Tenants</a></li><li><a href="index.html" class="active">TAR(RENT)</a></li><li><a href="../index.html" class="nav-cta">← C21 Site</a></li></ul>
</nav>
<div class="breadcrumb"><a href="index.html">TAR(RENT)</a> / {category} / {_breadcrumb_title(title)}</div>
<div class="post-page">
  <img class="article-hero-img" src="{img}" alt="{img_alt}" />
  <div class="article-body">
    <div class="article-meta"><span class="article-cat">{category}</span><span class="post-dot"></span><span class="article-date">{date}</span></div>
    <h1>{title}</h1>
    {body}

    {related}
    <div class="author-bio">
      <div class="author-avatar">AC</div>
      <div>
        <div class="author-name">Andrew Chavis</div>
        <div class="author-title">REALTOR® &amp; Property Manager · Century 21 Alliance Properties · Saginaw, TX</div>
        <div class="author-contact">TREC Lic. No. 0845090 · <a href="mailto:andrewchavis63@gmail.com" style="color:var(--gold);text-decoration:none;">andrewchavis63@gmail.com</a> · (817) 420-0833</div>
      </div>
    </div>

    <div style="margin-top:32px;padding-top:24px;border-top:1px solid #eee;font-size:13px;color:#999;line-height:1.6;">
      <strong style="color:#555;">Disclaimer:</strong> This article is for informational purposes only and does not constitute financial or real estate advice. Market data cited is sourced from publicly available reports — verify all figures with current sources before making purchase decisions. <a href="disclaimer.html" style="color:var(--gold);text-decoration:none;">View sources and disclaimers.</a>
      &nbsp;·&nbsp; <a href="https://allpantherproperties.substack.com/p/{substack_slug}" target="_blank" rel="noopener" style="color:var(--gold);text-decoration:none;">Read on Substack</a>
    </div>
  </div>
</div>

<div class="email-strip">
  <div class="email-strip-text">
    <h3>The market is moving.<br><em>Are you?</em></h3>
    <p>TAR(RENT) covers the Fort Worth and Tarrant County market straight — no spin, no cheer, just what the data says. Drop your email and get it when it drops.</p>
  </div>
  <form class="email-form" onsubmit="handleSubscribe(event)">
    <input type="email" id="subscribe-email" placeholder="your@email.com" required />
    <button type="submit">Subscribe</button>
  </form>
</div>

<footer>
  <div class="footer-logo-wrap">
    <img src="../img/C21_Seal_Black.png" alt="Century 21 Alliance Properties" class="footer-logo-img" />
    <div class="footer-logo-text">All Panther Properties<span><br>Century 21® Alliance Properties</span></div>
  </div>
  <p>© 2026 All Panther Properties · Century 21® Alliance Properties · License 0845090</p>
  <div class="footer-links">
    <a href="../index.html">Home</a>
    <a href="index.html">Blog</a>
    <a href="disclaimer.html">Sources</a>
    <a href="https://www.trec.texas.gov/forms/iabs-and-consumer-protection-notice" target="_blank" rel="noopener">IABS</a>
  </div>
</footer>

<script>
function handleSubscribe(e) {{
  e.preventDefault();
  const email = document.getElementById(\'subscribe-email\').value;
  fetch(\'https://zksjjekaiscwkmiibbqp.supabase.co/functions/v1/subscribe\', {{
    method: \'POST\',
    headers: {{\'Content-Type\': \'application/json\'}},
    body: JSON.stringify({{ email }})
  }}).then(r => r.json()).then(d => {{
    alert(d.message || \'You\\\'re in.\');
    document.getElementById(\'subscribe-email\').value = \'\';
  }}).catch(() => alert(\'Something went wrong. Try again.\'));
}}
</script>
</body>
</html>'''

    out_path = repo_path('TARRENT', f'{slug}.html')
    write_file(out_path, html)


def _pub_date_iso(pub_date_str):
    """Convert 'Mon, 20 Apr 2026 08:00:00 +0000' to '2026-04-20'."""
    try:
        dt = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return datetime.now().strftime('%Y-%m-%d')


def _breadcrumb_title(title):
    """Shorten title for breadcrumb."""
    words = title.split()
    if len(words) > 6:
        return ' '.join(words[:6]) + '...'
    return title


def _build_related_links(current_slug):
    """Return up to 3 related post links from existing TARRENT HTML files."""
    tarrent_dir = repo_path('TARRENT')
    links = ''
    count = 0
    for fname in sorted(os.listdir(tarrent_dir), reverse=True):
        if fname.endswith('.html') and fname not in ('index.html', 'disclaimer.html') and fname != f'{current_slug}.html':
            html_path = os.path.join(tarrent_dir, fname)
            content = read_file(html_path)
            m = re.search(r'<h1>(.*?)</h1>', content)
            if m:
                post_title = m.group(1)
                links += f'      <a href="{fname}" class="related-link"><span class="related-title">{post_title}</span></a>\n'
                count += 1
                if count >= 3:
                    break
    return f'    <div class="related-posts">\n      <div class="related-label">Related Reading</div>\n{links}    </div>\n' if links else ''


# ── Task B: Update TARRENT/index.html posts JS object ────────────────────────

def update_tarrent_index_posts_object(meta, body):
    """Prepend new entry to const posts = { in TARRENT/index.html."""
    path = repo_path('TARRENT', 'index.html')
    content = read_file(path)

    slug = meta['slug']
    posts_key = meta['posts_key']
    category = meta['category']
    date = meta['date']
    img = meta['img']
    title = meta['title']
    intro = meta['intro']

    body_text = re.sub(r'<[^>]+>', '', body)
    body_text = re.sub(r'\s+', ' ', body_text).strip()
    modal_content = body_text[:600] + ('...' if len(body_text) > 600 else '')

    title_js = title.replace("'", "\\'")
    intro_js = intro.replace("'", "\\'")

    new_entry = f"""    '{posts_key}': {{
      category: '{category}',
      date: '{date}',
      img: '{img}',
      title: '{title_js}',
      intro: '{intro_js}',
      fullLink: '{slug}.html',
      content: `
        {body}
        <p style="font-size:13px;color:#999;margin-top:24px;">Full sources at <a href="disclaimer.html" style="color:var(--gold);">disclaimer.html</a>. <a href="{slug}.html" style="color:var(--gold);">Read the full article →</a></p>
      `
    }},\n"""

    marker = 'const posts = {'
    if marker not in content:
        raise ValueError("Could not find 'const posts = {' in TARRENT/index.html")

    content = content.replace(marker, marker + '\n' + new_entry, 1)
    write_file(path, content)


# ── Task C: Update featured card in TARRENT/index.html ───────────────────────

def update_featured_card(meta):
    """Replace the featured card section with the new post."""
    path = repo_path('TARRENT', 'index.html')
    content = read_file(path)

    slug = meta['slug']
    posts_key = meta['posts_key']
    title = meta['title']
    intro = meta['intro']
    img = meta['img']
    img_alt = meta.get('img_alt', title)
    category = meta['category']

    new_featured = f"""<section class="featured-wrapper">
  <div class="section-label">Featured Article</div>
  <div class="featured-card" onclick="openPost('{posts_key}')">
    <div class="featured-img">
      <img src="{img}" alt="{img_alt}" loading="lazy">
      <div class="featured-img-overlay"></div>
    </div>
    <div class="featured-content">
      <div class="post-category">{category}</div>
      <h2>{title}</h2>
      <p>{intro}</p>
      <a href="{slug}.html" class="read-btn" onclick="event.stopPropagation();">
        Read the Full Article <span class="arrow">→</span>
      </a>
    </div>
  </div>
</section>"""

    pattern = r'<section class="featured-wrapper">.*?</section>'
    new_content = re.sub(pattern, new_featured, content, count=1, flags=re.DOTALL)

    if new_content == content:
        raise ValueError("Could not find featured-wrapper section in TARRENT/index.html")

    write_file(path, new_content)


# ── Task D: Prepend post card to posts grid in TARRENT/index.html ─────────────

def prepend_post_card(meta):
    """Add new post-card at the top of the posts grid."""
    path = repo_path('TARRENT', 'index.html')
    content = read_file(path)

    slug = meta['slug']
    posts_key = meta['posts_key']
    title = meta['title']
    intro = meta['intro']
    img = meta['img']
    img_alt = meta.get('img_alt', title)
    category = meta['category']
    date = meta['date']
    category_tag = meta['category_tag']

    new_card = f"""
  <a class="post-card" data-cat="{category_tag}" href="{slug}.html" onclick="event.preventDefault(); openPost('{posts_key}')">
    <div class="post-card-img">
      <img src="{img}" alt="{img_alt}" loading="lazy">
      <div class="img-overlay"></div>
    </div>
    <div class="post-meta">
      <span class="post-cat-tag">{category}</span>
      <div class="post-dot"></div>
      <span class="post-date">{date}</span>
    </div>
    <h3>{title}</h3>
    <p>{intro}</p>
  </a>
"""

    marker = '<!-- POST GRID -->\n<section class="posts-grid" id="postsGrid">'
    if marker not in content:
        raise ValueError("Could not find POST GRID marker in TARRENT/index.html")

    content = content.replace(marker, marker + new_card, 1)
    write_file(path, content)


# ── Task E: Update disclaimer.html source card ───────────────────────────────

def prepend_source_card(meta):
    """Prepend source card to disclaimer.html after the sources-label paragraph."""
    path = repo_path('TARRENT', 'disclaimer.html')
    content = read_file(path)

    title = meta['title']
    category = meta['category']
    date = meta['date']
    sources = meta.get('sources', [])

    source_rows = ''
    for s in sources:
        source_rows += f"""      <div class="source-row">
        <span class="source-badge">{s['badge']}</span>
        <span>{s['detail']} — <a href="{s['url']}" target="_blank" rel="noopener">{s['url']}</a></span>
      </div>\n"""

    new_card = f"""  <!-- Post: {title} ({date}) -->
  <div class="source-card">
    <div class="source-card-meta">
      <span class="source-card-cat">{category}</span>
      <span class="source-card-dot"></span>
      <span class="source-card-date">{date}</span>
    </div>
    <h3>{title}</h3>
    <div class="source-list">
{source_rows}    </div>
  </div>

"""

    marker = '<p class="sources-label">Sources by Article</p>'
    if marker not in content:
        raise ValueError("Could not find sources-label in disclaimer.html")

    content = content.replace(marker, marker + '\n\n' + new_card, 1)
    write_file(path, content)


# ── Task F: Update feed.xml ───────────────────────────────────────────────────

def prepend_feed_item(meta):
    """Prepend new item to feed.xml."""
    path = repo_path('TARRENT', 'feed.xml')
    content = read_file(path)

    slug = meta['slug']
    title = meta['title']
    description = meta['description']
    pub_date = meta['pubDate']

    new_item = f"""
    <item>
      <title>{title}</title>
      <link>https://allpantherproperties.com/TARRENT/{slug}.html</link>
      <description><![CDATA[{description}]]></description>
      <content:encoded><![CDATA[]]></content:encoded>
      <pubDate>{pub_date}</pubDate>
      <guid>https://allpantherproperties.com/TARRENT/{slug}.html</guid>
    </item>
"""

    marker = re.search(r'(<atom:link[^>]*/>\s*\n)', content)
    if not marker:
        raise ValueError("Could not find atom:link closing tag in feed.xml")

    insert_pos = marker.end()
    content = content[:insert_pos] + new_item + content[insert_pos:]
    write_file(path, content)


# ── Task G: Rotate root index.html blog teaser (3-card grid) ─────────────────

def rotate_home_teaser(meta):
    """Insert new post as first card in root index.html teaser grid, keep only 3 total."""
    path = repo_path('index.html')
    content = read_file(path)

    slug = meta['slug']
    title = meta['title']
    img = meta['img']
    img_alt = meta.get('img_alt', title)
    category = meta['category']
    date = meta['date']

    new_card_1 = f"""
      <a href="TARRENT/{slug}.html" class="bt-card reveal">
        <div class="bt-card-img">
          <img src="TARRENT/{img}" alt="{img_alt}" loading="lazy" />
          <div class="bt-card-img-overlay"></div>
        </div>
        <p class="bt-card-cat">{category}</p>
        <h3 class="bt-card-title">{title}</h3>
        <p class="bt-card-date">{date}</p>
      </a>"""

    card_pattern = re.compile(r'\s*<a href="TARRENT/[^"]+\.html" class="bt-card[^"]*"[^>]*>.*?</a>', re.DOTALL)
    existing_cards = card_pattern.findall(content)

    if not existing_cards:
        raise ValueError("Could not find bt-card entries in root index.html")

    card2 = re.sub(r'class="bt-card reveal[^"]*"', 'class="bt-card reveal reveal-delay-1"', existing_cards[0].strip())
    cards_to_keep = [new_card_1, '\n\n      ' + card2]

    if len(existing_cards) >= 2:
        card3 = re.sub(r'class="bt-card reveal[^"]*"', 'class="bt-card reveal reveal-delay-2"', existing_cards[1].strip())
        cards_to_keep.append('\n\n      ' + card3)

    grid_marker = '<div class="blog-teaser-grid">'
    if grid_marker not in content:
        raise ValueError("Could not find blog-teaser-grid in root index.html")

    grid_start = content.index(grid_marker) + len(grid_marker)

    # Find the matching closing </div> by tracking nesting depth
    depth = 1
    pos = grid_start
    grid_end = -1
    while pos < len(content):
        next_open = content.find('<div', pos)
        next_close = content.find('</div>', pos)
        if next_close == -1:
            raise ValueError("Could not find closing </div> for blog-teaser-grid")
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + 4
        else:
            depth -= 1
            if depth == 0:
                grid_end = next_close
                break
            pos = next_close + 6
    if grid_end == -1:
        raise ValueError("Could not find closing </div> for blog-teaser-grid")

    new_grid_inner = '\n' + '\n'.join(cards_to_keep) + '\n\n    '
    content = content[:grid_start] + new_grid_inner + content[grid_end:]
    write_file(path, content)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate-post.py posts-queue/YYYY-MM-DD-slug.md")
        sys.exit(1)

    input_path = sys.argv[1]
    print(f"\nGenerating cascade for: {input_path}")

    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()

    meta, body = parse_frontmatter(text)

    print("\n[A] Generating standalone post HTML...")
    generate_standalone_html(meta, body)

    print("\n[B] Updating TARRENT/index.html posts object...")
    update_tarrent_index_posts_object(meta, body)

    print("\n[C] Updating featured card...")
    update_featured_card(meta)

    print("\n[D] Prepending post card to grid...")
    prepend_post_card(meta)

    print("\n[E] Updating disclaimer.html source card...")
    prepend_source_card(meta)

    print("\n[F] Updating feed.xml...")
    prepend_feed_item(meta)

    print("\n[G] Rotating root index.html blog teaser...")
    rotate_home_teaser(meta)

    print(f"\n[DONE] Cascade complete for '{meta['slug']}'")
    print("Files to commit: TARRENT/{slug}.html, TARRENT/index.html, TARRENT/disclaimer.html, TARRENT/feed.xml, index.html")


if __name__ == '__main__':
    main()
