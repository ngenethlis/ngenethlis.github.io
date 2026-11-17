#!/usr/bin/env python3
"""Fetch currently-reading and last-read books from the Hardcover API and write
them to hardcover-last.json (consumed client-side by index.html).

Needs a Hardcover API token in HARDCOVER_TOKEN (scope: read:library).
Run: HARDCOVER_TOKEN=... python3 scripts/update_hardcover.py [username]
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.hardcover.app/v1/graphql"
USERNAME = sys.argv[1] if len(sys.argv) > 1 else "ngenethlis"
OUT = Path(__file__).resolve().parent.parent / "hardcover-last.json"

BOOK_FIELDS = """
  rating
  last_read_date
  first_started_reading_date
  book {
    title
    slug
    release_year
    image { url }
    contributions(limit: 2) { author { name } }
  }
"""

QUERY = f"""
query {{
  reading: user_books(
    where: {{ user: {{ username: {{ _eq: "{USERNAME}" }} }}, status_id: {{ _eq: 2 }} }}
    order_by: {{ updated_at: desc }}
    limit: 2
  ) {{ {BOOK_FIELDS} }}
  read: user_books(
    where: {{ user: {{ username: {{ _eq: "{USERNAME}" }} }}, status_id: {{ _eq: 3 }} }}
    order_by: [{{ last_read_date: desc_nulls_last }}, {{ updated_at: desc }}]
    limit: 1
  ) {{ {BOOK_FIELDS} }}
}}
"""


def stars(rating):
    if not rating:
        return ""
    full = int(rating)
    return "★" * full + ("½" if rating - full >= 0.5 else "")


def shape(ub):
    book = ub.get("book") or {}
    authors = [c["author"]["name"] for c in book.get("contributions") or []
               if c.get("author") and c["author"].get("name")]
    rating = float(ub["rating"]) if ub.get("rating") else None
    return {
        "title": book.get("title"),
        "year": book.get("release_year"),
        "authors": authors,
        "rating": rating,
        "ratingStars": stars(rating),
        "startedDate": ub.get("first_started_reading_date"),
        "finishedDate": ub.get("last_read_date"),
        "link": f"https://hardcover.app/books/{book['slug']}" if book.get("slug") else None,
        "cover": (book.get("image") or {}).get("url"),
    }


def main():
    token = os.environ.get("HARDCOVER_TOKEN", "").strip()
    if not token:
        sys.exit("HARDCOVER_TOKEN is not set.")
    if not token.lower().startswith("bearer "):
        token = "Bearer " + token

    req = urllib.request.Request(
        API,
        data=json.dumps({"query": QUERY}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": token,
            "User-Agent": "ngenethlis.github.io hardcover-last script",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"Hardcover API error {e.code}: {e.read().decode(errors='replace')}")

    if payload.get("errors"):
        sys.exit(f"Hardcover API error: {payload['errors']}")

    d = payload.get("data") or {}
    data = {
        "profile": f"https://hardcover.app/@{USERNAME}",
        "reading": [shape(ub) for ub in d.get("reading") or []],
        "lastRead": next((shape(ub) for ub in d.get("read") or []), None),
    }

    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    now = ", ".join(b["title"] for b in data["reading"]) or "nothing"
    last = data["lastRead"]["title"] if data["lastRead"] else "nothing"
    print(f"Wrote {OUT.name}: reading {now}; last read {last}")


if __name__ == "__main__":
    main()
