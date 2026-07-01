"""
Fetches and normalizes the <title> tag of a webpage given its URL.
Used so task lists show concise page titles instead of raw links.
"""
import html
import re
from urllib.parse import unquote, urlparse

import aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=8)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TrackerBot/1.0)"}
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_PROGRESS_RE = re.compile(r"\b(?:chapter|chap|ch\.?|episode|ep\.?)\s*[-:#]?\s*(\d+(?:\.\d+)?)\b", re.IGNORECASE)
_SITE_RE = re.compile(r"\b(?:online\s+at\s+)?[a-z0-9-]+\.(?:com|net|org|io|to|xyz)\b", re.IGNORECASE)


def _strip_read_noise(value: str) -> str:
    value = re.sub(r"^read\s+", "", value, flags=re.IGNORECASE).strip()
    value = re.sub(r"\s+(?:manga|manhwa|manhua|webtoon)\s*$", "", value, flags=re.IGNORECASE).strip()
    value = re.sub(r"\s+online(?:\s+at\s+.*)?$", "", value, flags=re.IGNORECASE).strip()
    return value


def extract_progress(*values: str | None) -> int:
    """Extract a chapter/episode number from title-like text or a URL."""
    for value in values:
        if not value:
            continue
        decoded = unquote(value).replace("-", " ").replace("_", " ")
        match = _PROGRESS_RE.search(decoded)
        if match:
            try:
                return int(float(match.group(1)))
            except ValueError:
                continue
    return 0


def clean_page_title(title: str | None, url: str | None = None) -> str | None:
    """Return a concise, stable series/page title from noisy browser titles."""
    if not title:
        return None

    cleaned = html.unescape(title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = _PROGRESS_RE.sub("", cleaned).strip(" -|:•")
    cleaned = _SITE_RE.sub("", cleaned).strip(" -|:•")

    parts = [p.strip(" -|:•") for p in re.split(r"\s+[-|•]\s+", cleaned) if p.strip(" -|:•")]
    candidates = [_strip_read_noise(p) for p in parts] or [_strip_read_noise(cleaned)]
    candidates = [c for c in candidates if c]

    # Prefer the shortest meaningful candidate because many manga sites repeat
    # the same title with marketing suffixes in the <title> tag.
    if candidates:
        candidates.sort(key=lambda c: (len(c.split()) < 2, len(c)))
        cleaned = candidates[0]
    else:
        cleaned = _strip_read_noise(cleaned)

    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -|:•")
    if cleaned:
        return cleaned

    if url:
        parsed = urlparse(url)
        slug = parsed.path.rstrip("/").split("/")[-1]
        slug = unquote(slug).replace("-", " ").replace("_", " ").strip()
        return slug.title() if slug else url
    return None


async def fetch_title(url: str) -> str | None:
    """Returns a normalized page title string, or None if it can't be fetched."""
    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT, headers=HEADERS) as session:
            async with session.get(url, allow_redirects=True) as resp:
                if resp.status != 200:
                    return None
                # Read only first 10KB — title is normally near the top.
                chunk = await resp.content.read(10240)
                html_text = chunk.decode("utf-8", errors="ignore")
                match = _TITLE_RE.search(html_text)
                if match:
                    return clean_page_title(match.group(1), url)
    except Exception as e:
        print(f"[link_title] Could not fetch title for {url}: {e}")
    return None
