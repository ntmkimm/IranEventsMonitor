

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import os

GAMMA_BASES = [
    "https://gamma-api.polymarket.com",
    "https://clob.polymarket.com",
]
DEFAULT_TAGS = ["iran", "middle-east"]
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
FETCH_TIMEOUT_SEC = 12
PER_TAG_LIMIT = 30

EXCLUDE_KEYWORDS = {
    "nba", "nfl", "mlb", "nhl", "fifa", "world cup", "super bowl", "championship",
    "playoffs", "oscar", "grammy", "emmy", "box office", "movie", "album", "song",
    "streamer", "influencer", "celebrity", "kardashian", "bachelor", "reality tv",
}

MENA_PATTERN = re.compile(r"\b(middle east|iran|iraq|syria|israel|palestine|gaza|saudi|yemen|houthi|lebanon)\b", re.I)


@dataclass
class Market:
    title: str
    yes_price: float
    volume: float
    url: str
    end_date: str | None
    source: str = "polymarket"


def _fetch_json(url: str) -> Any:
    req = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urlopen(req, timeout=FETCH_TIMEOUT_SEC) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_json_with_fallback(path: str, params: dict[str, str]) -> Any:
    query = urlencode(params)
    last_err: Exception | None = None
    for base in GAMMA_BASES:
        url = f"{base}{path}?{query}"
        try:
            return _fetch_json(url)
        except Exception as e:
            last_err = e
            continue
    if last_err is not None:
        raise RuntimeError(f"all endpoints failed: {last_err}")
    raise RuntimeError("all endpoints failed")


def fetch_events_by_tag(tag: str, limit: int = PER_TAG_LIMIT) -> list[dict[str, Any]]:
    params = {
        "tag_slug": tag,
        "closed": "false",
        "active": "true",
        "archived": "false",
        "order": "volume",
        "ascending": "false",
        "limit": str(limit),
        "end_date_min": datetime.now(timezone.utc).isoformat(),
    }
    data = _fetch_json_with_fallback("/events", params)
    return data if isinstance(data, list) else []


def parse_yes_price(market: dict[str, Any]) -> float | None:
    raw = market.get("outcomePrices")
    if raw is None:
        return None
    try:
        arr = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(arr, list) and len(arr) > 0:
            p = float(arr[0])
            if 0 <= p <= 1:
                return round(p * 100, 1)
    except Exception:
        return None
    return None


def is_excluded(title: str) -> bool:
    low = title.lower()
    return any(k in low for k in EXCLUDE_KEYWORDS)


def score_market(yes_price: float, volume: float) -> float:
    uncertainty = 1 - (2 * abs(yes_price - 50) / 100)
    vol = math.log10(max(volume, 1.0)) / math.log10(10_000_000)
    return (uncertainty * 0.6) + (min(vol, 1.0) * 0.4)


def filter_and_rank(markets: list[Market]) -> list[Market]:
    filtered: list[Market] = []
    for m in markets:
        if m.yes_price < 5 or m.yes_price > 95:
            continue
        if m.volume < 1000:
            continue
        if is_excluded(m.title):
            continue
        if not MENA_PATTERN.search(m.title):
            continue
        filtered.append(m)

    filtered.sort(key=lambda x: score_market(x.yes_price, x.volume), reverse=True)
    return filtered


def collect_markets(tags: list[str]) -> tuple[list[Market], dict[str, int]]:
    seen_event_ids: set[str] = set()
    out: list[Market] = []
    stats: dict[str, int] = {}

    for tag in tags:
        events = fetch_events_by_tag(tag)
        stats[tag] = len(events)

        for ev in events:
            event_id = str(ev.get("id") or "")
            if not event_id or event_id in seen_event_ids:
                continue
            seen_event_ids.add(event_id)

            event_volume = float(ev.get("volume") or 0)
            if event_volume < 1000:
                continue

            markets = ev.get("markets") or []
            if not isinstance(markets, list) or not markets:
                continue

            active_markets = [m for m in markets if not m.get("closed")]
            if not active_markets:
                continue

            top = max(active_markets, key=lambda m: float(m.get("volumeNum") or m.get("volume") or 0))
            yes_price = parse_yes_price(top)
            if yes_price is None:
                continue

            slug = ev.get("slug") or ""
            title = top.get("question") or ev.get("title") or "(no title)"
            out.append(
                Market(
                    title=title,
                    yes_price=yes_price,
                    volume=event_volume,
                    url=f"https://polymarket.com/event/{slug}" if slug else "https://polymarket.com",
                    end_date=top.get("endDate") or ev.get("endDate"),
                )
            )

        time.sleep(0.2)

    return out, stats


def run_health_check(raw_count: int, ranked_count: int, tag_stats: dict[str, int]) -> tuple[bool, dict[str, Any]]:
    checks = {
        "fetch_has_events": sum(tag_stats.values()) > 0,
        "raw_markets_nonzero": raw_count > 0,
        "ranked_markets_nonzero": ranked_count > 0,
    }
    ok = all(checks.values())
    return ok, checks


DEFAULT_TAGS = ["iran", "middle-east"]
# Tự động định tuyến vào thư mục backend/data tương tự như các crawler khác
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
OUTPUT_FILE = os.path.join(BACKEND_DIR, 'data', 'polymarket-results.json')

def main():
    # Sử dụng DEFAULT_TAGS (mặc định là DEFAULT_TAGS) và args.output (mặc định là OUTPUT_FILE)
    raw_markets, tag_stats = collect_markets(DEFAULT_TAGS)
    ranked = filter_and_rank(raw_markets)

    print("=" * 30)
    print("🚀 JOB: POLYMARKET FETCHING")
    print(f"Tags: {', '.join(DEFAULT_TAGS)}")
    print(f"Stats per tag: {tag_stats}")
    print(f"Found: {len(raw_markets)} raw -> {len(ranked)} ranked")
    print("=" * 30)

    # In kết quả top 15 ra console
    for i, m in enumerate(ranked[:15], start=1):
        print(f"{i:02d}. {m.title}")
        print(f"    Yes: {m.yes_price}% | Vol: {m.volume:.0f}")
        print(f"    URL: {m.url}")

    # Chuẩn bị dữ liệu lưu file
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "tags": DEFAULT_TAGS,
        "stats": {
            "events_per_tag": tag_stats,
            "raw_markets": len(raw_markets),
            "ranked_markets": len(ranked),
        },
        "markets": [asdict(x) for x in ranked],
    }

    # Đảm bảo thư mục tồn tại và ghi file
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Kiểm tra sức khỏe dữ liệu
    ok, checks = run_health_check(len(raw_markets), len(ranked), tag_stats)
    print("\n=== Health Check ===")
    for k, v in checks.items():
        print(f"- {k}: {'✅ OK' if v else '❌ FAIL'}")
    
    print(f"\nFinal status: {'PASS' if ok else 'FAIL'}")
    print(f"Output saved to: {output_path}")


if __name__ == "__main__":
    main()