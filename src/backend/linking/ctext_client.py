import logging
import httpx
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class CtextClient:
    BASE_URL = "https://ctext.org"

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)

    def search_person(self, name: str) -> List[Dict[str, Any]]:
        try:
            url = f"{self.BASE_URL}/searchbooks.py"
            params = {
                "res": "person",
                "cid": "",
                "searchfor": name,
            }
            resp = self.client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning(f"ctext search failed: {resp.status_code}")
                return []
            return self._parse_search_results(resp.text, name)
        except Exception as e:
            logger.error(f"ctext search error: {e}")
            return []

    def _parse_search_results(self, html: str, query: str) -> List[Dict[str, Any]]:
        import re
        results = []
        person_pattern = re.compile(
            r'<li[^>]*>.*?<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>.*?</li>',
            re.DOTALL,
        )
        for m in person_pattern.finditer(html):
            href = m.group(1)
            title = m.group(2).strip()
            if query in title or any(q in title for q in query):
                results.append({
                    "name": title,
                    "ctext_url": f"{self.BASE_URL}/{href}" if not href.startswith("http") else href,
                    "source": "ctext",
                })
        return results[:10]

    def get_person_detail(self, ctext_id: str) -> Dict[str, Any]:
        try:
            url = f"{self.BASE_URL}/{ctext_id}"
            resp = self.client.get(url)
            if resp.status_code != 200:
                return {}
            return self._parse_detail(resp.text)
        except Exception as e:
            logger.error(f"ctext detail error: {e}")
            return {}

    def _parse_detail(self, html: str) -> Dict[str, Any]:
        import re
        info = {}
        name_m = re.search(r"<title>([^<]+)</title>", html)
        if name_m:
            info["name"] = name_m.group(1).strip()
        era_m = re.search(r"([元明清][^<]{0,20}?)</p>", html)
        if era_m:
            info["era"] = era_m.group(1).strip()
        desc_m = re.search(r'<div[^>]*class="seg"[^>]*>(.*?)</div>', html, re.DOTALL)
        if desc_m:
            info["description"] = re.sub(r"<[^>]+>", "", desc_m.group(1)).strip()[:200]
        return info

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
