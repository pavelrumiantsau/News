#!/usr/bin/env python3
"""World news collector — builds docs/news.json for the static dashboard.

Zero API keys, zero AI, stdlib only. Run it on a schedule; the site is static.

Pipeline, per country:
  1. Ask Google News RSS with the country's terms, constrained by `site:` to a
     curated allowlist of trusted, free-to-read publishers (precision pass).
  2. Ask again without the site: constraint (recall pass), then keep only items
     whose publisher is on the full allowlist.
  3. Optionally ask the country's national Google News edition in its own
     language, for countries whose English coverage is thin.
  4. Filter: denylists (paywalled / state propaganda / non-news), topic noise,
     and a relevance test that the country is actually named in the headline.
  5. Score by source tier, freshness, language preference and significance
     keywords; de-duplicate near-identical headlines; keep the top few.
  6. If a country came back empty, widen the time window and retry; if still
     empty, carry forward the previous run's story marked stale.

Usage:
  python3 collect.py                 # full run
  python3 collect.py --only UA,NR    # just those countries (fast iteration)
  python3 collect.py --limit 20      # first N countries
"""

import argparse
import concurrent.futures
import datetime as dt
import html
import json
import os
import random
import re
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(ROOT, "config")
DOCS = os.path.join(ROOT, "docs")
OUT = os.path.join(DOCS, "news.json")

UA_STRING = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# How many headlines the dashboard shows collapsed vs. expanded.
TOP_N = 3
KEEP_N = 12

# Time windows tried in order until a country yields enough stories.
WINDOWS = ["2d", "7d", "30d", "180d"]
ENOUGH = 3

# Language preference: English first, then Ukrainian, then Russian, then native.
LANG_RANK = {"en": 0, "uk": 1, "ru": 2}
NATIVE_RANK = 3

# Minimum spacing between any two Google News requests, across all threads.
# Google tolerated ~8/sec comfortably in testing; this stays well under that
# while keeping a full 197-country run to a few minutes.
MIN_GAP = 0.15

_throttle = threading.Semaphore(8)
_last_call = [0.0]
_last_lock = threading.Lock()

# Sport is rarely "what is happening in a country", but for the smallest states
# it is sometimes the only coverage that exists. So we demote hard rather than
# drop, and let it surface only when nothing else does.
SPORTS_RE = re.compile(
    r"(?i)\b(cricket|football|soccer|rugby|netball|basketball|volleyball|athletics|"
    r"under-?\d{1,2}|u-?\d{1,2}\s|CFU|CONCACAF|CAF|AFC|OFC|CONMEBOL|CWI|ICC|"
    r"tournament|championship|qualifier|friendly|squad|striker|goalkeeper|"
    r"medal|Olympic|Games|League|Cup|beat|defeat|win over|draw with|"
    r"coach|captain|player|team|match|final|semi-final|score)\b"
)
# Section/tag/index pages that some publishers expose in feeds as if they were
# articles ("Tuvalu Climate Change - ABC News & Headlines").
SECTION_RE = re.compile(
    r"(?i)(news\s*&\s*headlines|latest news|breaking news$|"
    r"^\s*[\w\s]{3,30}\s*[-–|]\s*(news|topics?|latest|archive)\s*$|"
    r"\|\s*(latest|topics?|tag|category)\b|^\s*(topics?|tag)\s*:)"
)
# If a headline contains none of these, it is probably not English.
EN_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "as",
    "at", "by", "from", "after", "over", "into", "is", "are", "was", "were",
    "be", "has", "have", "had", "will", "would", "says", "said", "not", "no",
    "new", "more", "than", "that", "this", "its", "his", "her", "their", "up",
    "out", "off", "amid", "against", "about", "but", "how", "why", "what",
}


# ----------------------------------------------------------------- utilities

def load_json(name):
    with open(os.path.join(CONFIG, name), encoding="utf-8") as f:
        return json.load(f)


def norm(s):
    """Casefold + strip accents, so 'Yaoundé' matches 'Yaounde'."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.casefold()


def domain_of(url):
    try:
        host = urllib.parse.urlparse(url).netloc.lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def registrable(host):
    """Crude eTLD+1 so 'edition.cnn.com' matches a 'cnn.com' rule."""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    if parts[-2] in {"co", "com", "org", "net", "gov", "ac", "or", "ne"} and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def fetch(url, timeout=25, retries=2):
    for attempt in range(retries + 1):
        with _throttle:
            # Global pacing so we never hammer Google News.
            with _last_lock:
                gap = time.time() - _last_call[0]
                if gap < MIN_GAP:
                    time.sleep(MIN_GAP - gap)
                _last_call[0] = time.time()
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": UA_STRING, "Accept": "application/rss+xml,*/*"}
                )
                return urllib.request.urlopen(req, timeout=timeout).read()
            except (urllib.error.URLError, OSError) as exc:
                if attempt == retries:
                    raise
                time.sleep(1.5 * (attempt + 1) + random.random())
    return b""


def parse_rss(blob):
    """Return list of dicts from a Google News RSS payload."""
    out = []
    try:
        root = ET.fromstring(blob)
    except ET.ParseError:
        return out
    for item in root.findall(".//item"):
        def txt(tag):
            el = item.find(tag)
            return (el.text or "").strip() if el is not None and el.text else ""

        src_el = item.find("source")
        out.append({
            "title": html.unescape(txt("title")),
            "link": txt("link"),
            "pub": txt("pubDate"),
            "desc": re.sub(r"<[^>]+>", " ", html.unescape(txt("description")))[:400],
            "source_name": (src_el.text or "").strip() if src_el is not None else "",
            "source_url": (src_el.get("url") or "") if src_el is not None else "",
        })
    return out


def clean_title(raw, source_name):
    """Google News appends ' - Publisher'. Strip it, including multi-dash names."""
    t = re.sub(r"\s+", " ", raw).strip()
    if source_name:
        # Strip an exact trailing ' - <source>' (or a truncated form of it).
        esc = re.escape(source_name.strip())
        t = re.sub(rf"\s*[-–—|]\s*{esc}\s*$", "", t, flags=re.I).strip()
        head = source_name.strip()[:14]
        if len(head) >= 6:
            t = re.sub(rf"\s*[-–—|]\s*{re.escape(head)}.*$", "", t, flags=re.I).strip()
    # Generic fallback: a trailing ' - Some Publisher Name' of up to 6 words.
    t = re.sub(r"\s+[-–—]\s+(?:[A-Z][\w.&\']*\s*){1,6}$", "", t).strip()
    return t


def looks_english(title):
    words = re.findall(r"[a-zA-Z']+", title.lower())
    if len(words) < 4:
        return True                       # too short to judge; don't penalise
    return any(w in EN_STOPWORDS for w in words)


def parse_date(s):
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            d = dt.datetime.strptime(s, fmt)
            return d.replace(tzinfo=dt.timezone.utc) if d.tzinfo is None else d
        except ValueError:
            continue
    return None


def gnews_url(query, hl="en-US", gl="US", ceid="US:en"):
    return (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(query)
        + f"&hl={hl}&gl={gl}&ceid={ceid}"
    )


# --------------------------------------------------------------- trust model

class Trust:
    def __init__(self, cfg):
        self.tier1 = {d.lower(): n for d, n in cfg["tier1"].items()}
        self.tier2 = {d.lower(): n for d, n in cfg["tier2"].items()}
        self.allow = {}
        self.allow.update({d: 1 for d in self.tier1})
        self.allow.update({d: 2 for d in self.tier2})
        self.names = dict(self.tier1)
        self.names.update(self.tier2)
        self.bloc = cfg["bloc_domains"]
        self.core = cfg["core_query_domains"]
        self.deny = set()
        self.deny_reason = {}
        for key, label in (
            ("deny_paywall", "paywall"),
            ("deny_state_propaganda", "state/unreliable"),
            ("deny_not_news", "not-news"),
        ):
            for d in cfg[key]:
                d = d.lower()
                self.deny.add(d)
                self.deny_reason[d] = label
        self.noise = [re.compile(p) for p in cfg["topic_noise_patterns"]]
        self.boost = [re.compile(p) for p in cfg["significance_boost_patterns"]]

    def verdict(self, host):
        """-> (tier, reason). tier None means rejected."""
        if not host:
            return None, "no-domain"
        cands = {host, registrable(host)}
        cands |= {".".join(host.split(".")[i:]) for i in range(len(host.split(".")) - 1)}
        for c in cands:
            if c in self.deny:
                return None, self.deny_reason[c]
        for c in cands:
            if c in self.allow:
                return self.allow[c], c
        return None, "not-allowlisted"

    def display(self, host):
        for c in (host, registrable(host)):
            if c in self.names:
                return self.names[c].split("—")[0].strip()
        return None


# ---------------------------------------------------------------- collection

def build_queries(country, trust, window):
    """Return [(url, lang, pass_name)] for one country/window."""
    terms = country["terms"]
    # Quoted OR-group. Cap length: Google tolerates long queries but there is no
    # value in more than ~8 alternates.
    alts = " OR ".join(f'"{t}"' for t in terms[:8])
    doms = list(dict.fromkeys(trust.core + trust.bloc.get(country["bloc"], [])))[:55]
    sites = " OR ".join(f"site:{d}" for d in doms)

    q = []
    q.append((gnews_url(f"({alts}) when:{window} ({sites})"), "en", "allowlist"))
    q.append((gnews_url(f"({alts}) when:{window}"), "en", "broad"))

    ed = country.get("edition")
    if ed and ed["hl"].split("-")[0] != "en":
        lang = ed["hl"].split("-")[0]
        q.append((
            gnews_url(f"({alts}) when:{window}", ed["hl"], ed["gl"], ed["ceid"]),
            lang, "native",
        ))
    return q


def relevance(country, title, desc):
    """How confidently is this item *about* this country? 2 = named in headline."""
    nt, nd = norm(title), norm(desc)
    primary = norm(country["name"])
    for t in country["terms"]:
        term = norm(t)
        # Short terms need word boundaries; 'Chad' must not match 'Chadwick'.
        pattern = r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"
        if re.search(pattern, nt):
            return 2
    for t in country["terms"]:
        pattern = r"(?<![a-z0-9])" + re.escape(norm(t)) + r"(?![a-z0-9])"
        if re.search(pattern, nd):
            return 1
    return 0


def score(item, trust, country):
    s = 0.0
    s += {1: 30.0, 2: 18.0}.get(item["tier"], 0.0)
    s += 14.0 * item["rel"]                       # named in headline beats named in blurb
    s -= 6.0 * item["lang_rank"]                  # en > uk > ru > native
    age = item.get("age_h")
    if age is not None:
        s += max(0.0, 26.0 - (age / 12.0))        # decays over ~2 weeks
    hits = sum(1 for p in trust.boost if p.search(item["title"]))
    s += min(hits, 3) * 7.0                       # hard-news keywords
    if len(item["title"]) < 25:
        s -= 8.0
    if item.get("sport"):
        s -= 45.0                                 # only surfaces if nothing else does
    if not item.get("english"):
        s -= 12.0                                 # regional-language service output
    return s


def dedupe_key(title):
    t = norm(re.sub(r"\s+", " ", title))
    t = re.sub(r"[^a-z0-9 ]", "", t)
    words = [w for w in t.split() if len(w) > 3][:7]
    return " ".join(sorted(words))


def collect_country(country, trust, now):
    seen_keys, seen_links, items = set(), set(), []
    windows_used = []

    for window in WINDOWS:
        windows_used.append(window)
        for url, lang, pass_name in build_queries(country, trust, window):
            try:
                raw = parse_rss(fetch(url))
            except Exception:
                continue
            for r in raw:
                title = clean_title(r["title"], r["source_name"])
                if not title or len(title) < 15 or len(title.split()) < 4:
                    continue
                if SECTION_RE.search(title):
                    continue
                host = domain_of(r["source_url"]) or domain_of(r["link"])
                tier, why = trust.verdict(host)
                if tier is None:
                    continue
                if any(p.search(title) for p in trust.noise):
                    continue
                rel = relevance(country, title, r["desc"])
                if rel == 0:
                    continue
                key = dedupe_key(title)
                if key in seen_keys or r["link"] in seen_links:
                    continue
                seen_keys.add(key)
                seen_links.add(r["link"])

                pub = parse_date(r["pub"])
                age_h = (now - pub).total_seconds() / 3600.0 if pub else None
                lr = LANG_RANK.get(lang, NATIVE_RANK)
                items.append({
                    "title": title,
                    "link": r["link"],
                    "source": trust.display(host) or r["source_name"] or host,
                    "domain": host,
                    "tier": tier,
                    "rel": rel,
                    "lang": lang,
                    "lang_rank": lr,
                    "age_h": age_h,
                    "pub": pub.isoformat() if pub else None,
                    "pass": pass_name,
                    "sport": bool(SPORTS_RE.search(title)),
                    "english": looks_english(title) if lang == "en" else True,
                })
        # Only real, on-topic, non-sport stories count towards "enough".
        strong = [i for i in items
                  if i["rel"] == 2 and not i["sport"] and (i["age_h"] or 0) < 24 * 21]
        if len(strong) >= ENOUGH:
            break

    for i in items:
        i["score"] = round(score(i, trust, country), 1)
    items.sort(key=lambda i: -i["score"])

    clean = []
    for i in items[:KEEP_N]:
        clean.append({
            "title": i["title"], "link": i["link"], "source": i["source"],
            "domain": i["domain"], "tier": i["tier"], "lang": i["lang"], "pub": i["pub"],
        })
    return {
        "iso": country["iso"],
        "name": country["name"],
        "region": country["region"],
        "capital": country["capital"],
        "items": clean,
        "window": windows_used[-1],
        "count": len(clean),
    }


# --------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated ISO2 codes")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    countries = load_json("countries.json")
    trust = Trust(load_json("sources.json"))

    if args.only:
        want = {c.strip().upper() for c in args.only.split(",")}
        countries = [c for c in countries if c["iso"] in want]
    if args.limit:
        countries = countries[: args.limit]

    previous = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                for c in json.load(f).get("countries", []):
                    previous[c["iso"]] = c
        except (json.JSONDecodeError, OSError):
            pass

    now = dt.datetime.now(dt.timezone.utc)
    results, done = [], 0
    t0 = time.time()

    with concurrent.futures.ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(collect_country, c, trust, now): c for c in countries}
        for fut in concurrent.futures.as_completed(futs):
            c = futs[fut]
            try:
                res = fut.result()
            except Exception as exc:
                print(f"  !! {c['name']}: {type(exc).__name__} {exc}", file=sys.stderr)
                res = {"iso": c["iso"], "name": c["name"], "region": c["region"],
                       "capital": c["capital"], "items": [], "window": "-", "count": 0}
            # Carry forward the last known story when a country is silent today.
            if not res["items"] and c["iso"] in previous:
                old = previous[c["iso"]]
                if old.get("items"):
                    res["items"] = old["items"][:TOP_N]
                    res["stale"] = True
                    res["stale_since"] = old.get("fetched", old.get("stale_since"))
            res["fetched"] = now.isoformat()
            results.append(res)
            done += 1
            if done % 20 == 0 or done == len(countries):
                print(f"  {done}/{len(countries)} ({time.time() - t0:.0f}s)", flush=True)

    results.sort(key=lambda r: r["name"])

    covered = sum(1 for r in results if r["items"] and not r.get("stale"))
    stale = sum(1 for r in results if r.get("stale"))
    empty = sum(1 for r in results if not r["items"])
    total = sum(len(r["items"]) for r in results)

    # Global top: the strongest tier-1 stories of the day across all countries.
    pool = []
    for r in results:
        if r.get("stale"):
            continue
        for i in r["items"][:2]:
            if i["tier"] == 1 and i.get("pub"):
                pool.append({**i, "country": r["name"], "iso": r["iso"]})
    pool.sort(key=lambda i: i["pub"], reverse=True)
    seen, world = set(), []
    for i in pool:
        k = dedupe_key(i["title"])
        if k in seen:
            continue
        seen.add(k)
        world.append(i)
        if len(world) >= 12:
            break

    payload = {
        "generated": now.isoformat(),
        "generated_human": now.strftime("%d %B %Y, %H:%M UTC"),
        "stats": {
            "countries": len(results), "covered": covered,
            "stale": stale, "empty": empty, "stories": total,
        },
        "world": world,
        "countries": results,
    }
    os.makedirs(DOCS, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\n{len(results)} countries | fresh {covered} | carried-forward {stale} | "
          f"empty {empty} | {total} stories | {time.time() - t0:.0f}s")
    print(f"-> {OUT}")
    if empty:
        names = [r["name"] for r in results if not r["items"]]
        print(f"no coverage: {', '.join(names)}")


if __name__ == "__main__":
    main()
