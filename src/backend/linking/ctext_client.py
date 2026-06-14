"""
ctext.org（中国哲学书电子化计划）API 客户端。

支持：
- 人物搜索
- 人物详情页解析

注意：ctext.org 有频率限制，可能返回 403 Forbidden，
需要添加 User-Agent 和重试逻辑。
"""
import logging
import re
import time
import httpx

logger = logging.getLogger(__name__)


class CtextClient:
    """ctext.org API 客户端，支持自动重试和 UA 伪装。"""

    BASE_URL = "https://ctext.org"

    def __init__(self):
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        带重试的 HTTP 请求。
        ctext 对频繁请求返回 403，需要指数退避重试。
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        kwargs.setdefault("headers", {})
        kwargs["headers"].update(headers)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.client.request(method, url, **kwargs)
                if resp.status_code == 403 and attempt < max_retries - 1:
                    wait = (attempt + 1) * 2.0
                    logger.debug(f"ctext 403, retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait)
                    continue
                return resp
            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
        return self.client.request(method, url, **kwargs)

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
            resp = self._request("GET", url, params=params)
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
            resp = self._request("GET", ctext_url)
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
