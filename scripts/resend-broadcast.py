#!/usr/bin/env python3
"""
Fire newsletter via Supabase Edge Function when a new TAR(RENT) post publishes.
Usage: python scripts/resend-broadcast.py <slug> <title> <description>
No secrets required — uses hardcoded Supabase anon key (public, safe to commit).
"""

import sys
import json
import urllib.request
import urllib.error

SUPABASE_URL = "https://zksjjekaiscwkmiibbqp.supabase.co/functions/v1/send-post-newsletter"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inprc2pqZWthaXNjd2ttaWliYnFwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMxMzgyODIsImV4cCI6MjA4ODcxNDI4Mn0.wPlNgLu4GvaGCsSHnM5loewvgysTSqRHgLXczzrDqRo"


def fire_newsletter(slug, title, description):
    payload = {
        "title": title,
        "subtitle": description,
        "url": f"TARRENT/{slug}.html",
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        SUPABASE_URL,
        data=data,
        headers={
            'Authorization': f'Bearer {SUPABASE_ANON_KEY}',
            'Content-Type': 'application/json',
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            if result.get('success'):
                print(f"  [ok] Newsletter sent for: {slug}")
            else:
                print(f"  [warn] Unexpected response: {result}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"ERROR sending newsletter: {e.code} — {body}")
        sys.exit(1)


def main():
    if len(sys.argv) < 4:
        print("Usage: python scripts/resend-broadcast.py <slug> <title> <description>")
        sys.exit(1)

    slug = sys.argv[1]
    title = sys.argv[2]
    description = sys.argv[3]

    print(f"Firing newsletter for: {slug}")
    fire_newsletter(slug, title, description)


if __name__ == '__main__':
    main()
