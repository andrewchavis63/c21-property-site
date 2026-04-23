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
    'StarTelegram': 'https://www.star-telegram.com/arc/outboundfeeds/rss/?outputType=xml',
    'BiggerPockets': 'https://www.biggerpockets.com/blog/feed',
    'Norada': 'https://www.noradarealestate.com/blog/feed/',
}

USER_AGENT = 'signal-pull/1.0 (allpantherproperties.com; content research bot)'
RENTCAST_BASE = 'https://api.rentcast.io/v1/markets'


def main():
    print('SIGNAL: skeleton ready', flush=True)


if __name__ == '__main__':
    main()
