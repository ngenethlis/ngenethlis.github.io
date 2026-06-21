#!/usr/bin/env python3
"""Fetch the latest watched film from a Letterboxd RSS feed and write it to
letterboxd-last.json (consumed client-side by index.html).

Run: python3 scripts/update_letterboxd.py [username]
"""
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

USERNAME = sys.argv[1] if len(sys.argv) > 1 else "ngene"
FEED = f"https://letterboxd.com/{USERNAME}/rss/"
OUT = Path(__file__).resolve().parent.parent / "letterboxd-last.json"
LB = "{https://letterboxd.com}"


def stars(rating):
    if rating is None:
        return ""
    full = int(rating)
    return "★" * full + ("½" if rating - full >= 0.5 else "")


def main():
    req = urllib.request.Request(FEED, headers={"User-Agent": "Mozilla/5.0 (letterboxd-last)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        xml = resp.read().decode("utf-8")

    root = ET.fromstring(xml)
    item = root.find(".//item")
    if item is None:
        print("No items in feed; leaving JSON untouched.")
        return

    def text(tag):
        el = item.find(LB + tag)
        return el.text if el is not None else None

    rating = text("memberRating")
    rating = float(rating) if rating else None

    desc = item.findtext("description") or ""
    m = re.search(r'<img src="([^"]+)"', desc)
    poster = m.group(1) if m else None

    data = {
        "title": text("filmTitle"),
        "year": text("filmYear"),
        "rating": rating,
        "ratingStars": stars(rating),
        "liked": text("memberLike") == "Yes",
        "rewatch": text("rewatch") == "Yes",
        "watchedDate": text("watchedDate"),
        "link": item.findtext("link"),
        "poster": poster,
    }

    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.name}: {data['title']} ({data['year']}) {data['ratingStars']}")


if __name__ == "__main__":
    main()
