#!/usr/bin/env python3
"""
Fire a Resend broadcast when a new TAR(RENT) post publishes.
Usage: python scripts/resend-broadcast.py <slug> <title> <description> <pub_date>
Requires: RESEND_API_KEY and RESEND_AUDIENCE_ID environment variables
"""

import sys
import os
import json
import urllib.request
import urllib.error


def fire_broadcast(slug, title, description, pub_date):
    api_key = os.environ.get('RESEND_API_KEY')
    audience_id = os.environ.get('RESEND_AUDIENCE_ID')

    if not api_key:
        print("ERROR: RESEND_API_KEY not set")
        sys.exit(1)

    post_url = f"https://allpantherproperties.com/TARRENT/{slug}.html"

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: 'Georgia', serif; background: #f8f7f4; margin: 0; padding: 0; }}
    .container {{ max-width: 600px; margin: 0 auto; background: #fff; }}
    .header {{ background: #2B2B2B; padding: 32px 40px; border-bottom: 3px solid #C9A84C; }}
    .header-brand {{ font-size: 13px; color: #C9A84C; letter-spacing: 2px; text-transform: uppercase; }}
    .body {{ padding: 40px; }}
    .cat {{ font-size: 11px; letter-spacing: 2px; text-transform: uppercase; color: #C9A84C; margin-bottom: 12px; }}
    h1 {{ font-size: 26px; line-height: 1.25; color: #1C1C1C; margin: 0 0 16px; }}
    p {{ font-size: 15px; line-height: 1.8; color: #3A3A3A; margin: 0 0 24px; }}
    .cta {{ display: inline-block; background: #C9A84C; color: #2B2B2B; text-decoration: none; padding: 14px 28px; font-size: 12px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; }}
    .footer {{ padding: 32px 40px; border-top: 1px solid #e8e5e0; font-size: 12px; color: #999; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="header-brand">TAR(RENT) — All Panther Properties</div>
    </div>
    <div class="body">
      <div class="cat">New Post</div>
      <h1>{title}</h1>
      <p>{description}</p>
      <a href="{post_url}" class="cta">Read the Full Article &rarr;</a>
    </div>
    <div class="footer">
      Andrew Chavis &middot; REALTOR&reg; &middot; Century 21 Alliance Properties &middot; Saginaw, TX<br>
      TREC Lic. No. 0845090 &middot; <a href="https://www.trec.texas.gov/forms/iabs-and-consumer-protection-notice">IABS</a><br><br>
      <a href="{{{{unsubscribe_url}}}}">Unsubscribe</a>
    </div>
  </div>
</body>
</html>"""

    payload = {
        "audience_id": audience_id,
        "from": "TAR(RENT) <tarrent@allpantherproperties.com>",
        "reply_to": "andrewchavis63@gmail.com",
        "subject": title,
        "html": html_body,
        "name": f"TAR(RENT) — {title[:60]}",
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        'https://api.resend.com/broadcasts',
        data=data,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
            broadcast_id = result.get('id')
            print(f"  [ok] Broadcast created: {broadcast_id}")

            send_req = urllib.request.Request(
                f'https://api.resend.com/broadcasts/{broadcast_id}/send',
                data=b'{}',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                method='POST'
            )
            with urllib.request.urlopen(send_req) as send_resp:
                send_result = json.loads(send_resp.read().decode())
                print(f"  [ok] Broadcast sent: {send_result}")

    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"ERROR firing Resend broadcast: {e.code} — {body}")
        sys.exit(1)


def main():
    if len(sys.argv) < 5:
        print("Usage: python scripts/resend-broadcast.py <slug> <title> <description> <pub_date>")
        sys.exit(1)

    slug = sys.argv[1]
    title = sys.argv[2]
    description = sys.argv[3]
    pub_date = sys.argv[4]

    print(f"Firing Resend broadcast for: {slug}")
    fire_broadcast(slug, title, description, pub_date)


if __name__ == '__main__':
    main()
