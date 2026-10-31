#!/usr/bin/env python3
"""Daily news collector for the AI 旗艦模型競賽 page.

Fetches Google News RSS for each tracked lab, keeps the freshest headlines,
de-duplicates them, and rewrites news.json next to index.html.

Standard library only: runs on a bare GitHub Actions runner with no pip install.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.abspath(os.path.join(HERE, ".."))
NEWS_PATH = os.path.join(SITE_DIR, "news.json")

HKT = timezone(timedelta(hours=8))
WINDOW_DAYS = 45
PER_COMPANY = 4
TOTAL_CAP = 40

# Display name (must match data.json) -> Google News query
SOURCES = [
    ("OpenAI", '("OpenAI" OR "ChatGPT" OR "GPT-6") AI model'),
    ("Google DeepMind", '("Google DeepMind" OR "Gemini 4" OR "Gemini 3.8")'),
    ("Anthropic", '("Anthropic" OR "Claude Opus" OR "Claude Fable")'),
    ("Meta", '("Meta AI" OR "Muse Wonder" OR "Meta Superintelligence Labs")'),
    ("xAI", '("xAI" OR "Grok 4.7")'),
    ("Microsoft AI", '("Microsoft AI" OR "MAI-Thinking" OR "MAI-Base")'),
    ("Amazon", '("Amazon Nova" OR "AWS Bedrock" model)'),
    ("Alibaba（Qwen）", '("Qwen" OR "Alibaba AI model")'),
    ("DeepSeek", '("DeepSeek" model)'),
    ("Mistral AI", '("Mistral AI" OR "Mistral Large 4")'),
]

RSS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
UA = "Mozilla/5.0 (compatible; AI-Frontier-Tracker/1.0; +https://github.com)"

# Keep the feed about models and capabilities, not markets or courtrooms.
NOISE = re.compile(
    r"\b("
    r"lawsuit|sue[sd]?|suing|court|judge|settle(?:ment|d)?|antitrust|"
    r"stock|shares?|valuation|funding|raise[sd]?|investment|investors?|"
    r"ipo|earnings|revenue|profit|market share|"
    r"layoffs?|hires?|hiring|resign|ceo|board|"
    r"data cent(?:er|re)|home buyout|power plant|tariff|"
    r"bans?|banned|restrict\w*|export control|probe|investigat\w*|sanction\w*"
    r")\b",
    re.I,
)


def fetch(url: str, timeout: int = 20) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as exc:  # noqa: BLE001 - network errors must not fail the job
        print(f"  ! fetch failed: {exc}", file=sys.stderr)
        return None


def clean_title(title: str) -> tuple[str, str | None]:
    """Google News appends ' - Source'. Split it back out."""
    title = re.sub(r"\s+", " ", title).strip()
    m = re.match(r"^(.*)\s-\s([^-]{2,40})$", title)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return title, None


def parse_date(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        dt = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def norm(title: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", title.lower())


def collect(company: str, query: str, cutoff: datetime) -> list[dict]:
    q = urllib.parse.quote(f"{query} when:{WINDOW_DAYS}d")
    raw = fetch(RSS.format(q=q))
    if not raw:
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        print(f"  ! bad xml for {company}: {exc}", file=sys.stderr)
        return []

    out: list[dict] = []
    for item in root.iter("item"):
        title_raw = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title_raw or not link:
            continue
        dt = parse_date(item.findtext("pubDate"))
        if dt is None or dt < cutoff:
            continue
        title, src = clean_title(title_raw)
        if len(title) < 20 or NOISE.search(title):
            continue
        out.append(
            {
                "date": dt.astimezone(HKT).strftime("%Y-%m-%d"),
                "company": company,
                "title": title,
                "source": src or "Google News",
                "url": link,
                "_ts": dt.timestamp(),
            }
        )
        if len(out) >= PER_COMPANY:
            break
    return out


def main() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    previous: list[dict] = []
    if os.path.exists(NEWS_PATH):
        try:
            with open(NEWS_PATH, encoding="utf-8") as fh:
                previous = json.load(fh).get("items", [])
        except (OSError, json.JSONDecodeError):
            previous = []

    fetched: list[dict] = []
    for company, query in SOURCES:
        print(f"· {company}")
        fetched.extend(collect(company, query, cutoff))
        time.sleep(0.6)  # be polite to news.google.com

    # De-duplicate by normalised title, preferring the newest copy.
    seen: set[str] = set()
    merged: list[dict] = []
    for item in sorted(fetched, key=lambda x: x["_ts"], reverse=True):
        key = norm(item["title"])
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)

    # Keep yesterday's items that today's fetch missed, so a flaky feed
    # never blanks the page.
    for item in previous:
        if len(merged) >= TOTAL_CAP:
            break
        key = norm(item.get("title", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(item)

    merged.sort(key=lambda x: (x.get("date", ""), x.get("_ts", 0)), reverse=True)
    merged = merged[:TOTAL_CAP]
    for item in merged:
        item.pop("_ts", None)

    payload = {
        "generated": datetime.now(HKT).replace(microsecond=0).isoformat(),
        "window_days": WINDOW_DAYS,
        "items": merged,
    }
    with open(NEWS_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"wrote {len(merged)} items -> {NEWS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
