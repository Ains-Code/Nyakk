"""
Fetches the <title> tag of a webpage given its URL.
Used so task lists show "One Piece Chapter 1100" instead of a raw link.
"""
import asyncio
import re
import aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=8)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TrackerBot/1.0)"}
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


async def fetch_title(url: str) -> str | None:
    """Returns the page title string, or None if it can't be fetched."""
    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT, headers=HEADERS) as session:
            async with session.get(url, allow_redirects=True) as resp:
                if resp.status != 200:
                    return None
                # Read only first 10KB — title is always near the top
                chunk = await resp.content.read(10240)
                html = chunk.decode("utf-8", errors="ignore")
                match = _TITLE_RE.search(html)
                if match:
                    title = match.group(1).strip()
                    # Clean up HTML entities and extra whitespace
                    title = title.replace("&amp;", "&").replace("&lt;", "<") \
                                 .replace("&gt;", ">").replace("&quot;", '"') \
                                 .replace("&#39;", "'")
                    title = re.sub(r"\s+", " ", title).strip()
                    return title or None
    except Exception as e:
        print(f"[link_title] Could not fetch title for {url}: {e}")
    return None
