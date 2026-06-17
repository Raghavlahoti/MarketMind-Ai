# ============================================================================
# MARKETMIND AI - NEWS DATA INGESTION PROVIDER
# ============================================================================

import xml.etree.ElementTree as ET
import datetime
import logging
import httpx
import re
from typing import Any, Dict, List

logger = logging.getLogger("marketmind_ai")

class NewsProvider:
    """Fetches financial news from Google News RSS and Yahoo Finance RSS."""

    def __init__(self) -> None:
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def fetch_google_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetches news from Google News RSS search query."""
        url = f"https://news.google.com/rss/search?q={symbol}&hl=en-US&gl=US&ceid=US:en"
        return await self._fetch_rss(url, "Google News")

    async def fetch_yahoo_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetches news from Yahoo Finance Headline RSS."""
        url = f"https://finance.yahoo.com/rss/headline?s={symbol}"
        return await self._fetch_rss(url, "Yahoo Finance")

    async def _fetch_rss(self, url: str, source_default: str) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code != 200:
                    logger.warning("Failed to fetch RSS from %s (Status: %s)", url, resp.status_code)
                    return []
                xml_content = resp.text
                
                # Parse XML
                root = ET.fromstring(xml_content)
                items = []
                for item in root.findall(".//item"):
                    title = item.find("title").text if item.find("title") is not None else ""
                    link = item.find("link").text if item.find("link") is not None else ""
                    
                    pub_date_str = item.find("pubDate").text if item.find("pubDate") is not None else ""
                    published_at = datetime.datetime.now(datetime.timezone.utc)
                    if pub_date_str:
                        pub_date_str_clean = pub_date_str.replace("UT", "GMT")
                        for fmt in [
                            "%a, %d %b %Y %H:%M:%S %Z", 
                            "%a, %d %b %Y %H:%M:%S %z", 
                            "%a, %d %b %Y %H:%M:%S",
                            "%d %b %Y %H:%M:%S %Z",
                            "%d %b %Y %H:%M:%S %z"
                        ]:
                            try:
                                dt = datetime.datetime.strptime(pub_date_str_clean, fmt)
                                if not dt.tzinfo:
                                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                                published_at = dt
                                break
                            except ValueError:
                                continue
                                
                    source = source_default
                    source_el = item.find("source")
                    if source_el is not None and source_el.text:
                        source = source_el.text
                    
                    summary = item.find("description").text if item.find("description") is not None else ""
                    if summary:
                        summary_clean = re.sub(r'<[^>]*>', '', summary)
                    else:
                        summary_clean = None
                        
                    items.append({
                        "title": title,
                        "url": link,
                        "published_at": published_at,
                        "source_name": source,
                        "summary": summary_clean,
                        "content": summary_clean or title,
                        "metadata": {"rss_feed": url}
                    })
                return items
        except Exception as e:
            logger.error("Exception fetching RSS from %s: %s", url, e)
            return []

    async def get_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetches news from both Google News and Yahoo Finance RSS, merging and deduplicating by URL."""
        google_items = await self.fetch_google_news(symbol)
        yahoo_items = await self.fetch_yahoo_news(symbol)
        
        all_items = google_items + yahoo_items
        
        seen_urls = set()
        unique_items = []
        for item in all_items:
            url = item["url"]
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_items.append(item)
                
        return unique_items
