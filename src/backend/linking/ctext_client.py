"""
ctext.org（中国哲学书电子化计划）API 客户端。

支持：
- 人物搜索
- 人物详情页解析
"""
import logging
import re
import httpx

logger = logging.getLogger(__name__)


class CtextClient:
    """ctext.org API 客户端，支持自动重定向。"""

    BASE_URL = "https://ctext.org"

    def __init__(self):
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)

    def search_person(self, name: str) -> list:
        """
        在 ctext 搜索人物记录。

        返回格式：
        [{
            "name": "文彭",
            "ctext_url": "/person/...",
            "source": "ctext",
        }]
        """
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

    def _parse_search_results(self, html: str, query: str) -> list:
        """从 HTML 中解析人物搜索结果。"""
        results = []
        person_pattern = re.compile(
            r'<li[^>]*>.*?<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>.*?</li>',
            re.DOTALL,
        )
        for m in person_pattern.finditer(html):
            href = m.group(1).strip()
            title = m.group(2).strip()
            if not title or len(title) > 50:
                continue
            if query in title or any(q in title for q in query):
                if href.startswith("/"):
                    ctext_url = f"{self.BASE_URL}{href}"
                elif href.startswith("http"):
                    ctext_url = href
                else:
                    ctext_url = f"{self.BASE_URL}/{href}"
                results.append({
                    "name": title,
                    "ctext_url": ctext_url,
                    "source": "ctext",
                })
        return results[:10]

    def get_person_detail(self, ctext_url: str) -> dict:
        """
        获取人物详情页内容。

        返回格式：
        {
            "name": "...",
            "era": "...",
            "description": "...",
        }
        """
        if not ctext_url:
            return {}
        try:
            resp = self.client.get(ctext_url)
            if resp.status_code != 200:
                return {}
            return self._parse_detail(resp.text)
        except Exception as e:
            logger.error(f"ctext detail error: {e}")
            return {}

    def _parse_detail(self, html: str) -> dict:
        """从详情页 HTML 解析人物信息。"""
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
