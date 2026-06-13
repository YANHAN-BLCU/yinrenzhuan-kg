"""
CBDB（中国历代人物传记资料库）API 客户端。

CBDB API 文档：https://projects.iq.harvard.edu/cbdb
支持：人物搜索、传记详情、亲属关系查询。

注意：CBDB API 返回格式可能为空字符串或非 JSON 响应，
需要做健壮性处理。
"""
import logging
import json
from typing import List, Dict, Optional, Any
import httpx

logger = logging.getLogger(__name__)


class CBDBClient:

    BASE_URL = "https://cbdb.fas.harvard.edu/cbdbapi"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)

    def _get(self, endpoint: str, params: dict) -> Optional[Any]:
        """统一的 GET 请求处理。"""
        try:
            params = {k: v for k, v in params.items() if v}
            resp = self.client.get(f"{self.BASE_URL}/{endpoint}", params=params)
            if resp.status_code != 200:
                logger.warning(f"CBDB {endpoint} HTTP {resp.status_code}")
                return None
            if not resp.text.strip():
                logger.warning(f"CBDB {endpoint} empty response")
                return None
            return resp.json()
        except json.JSONDecodeError:
            logger.warning(f"CBDB {endpoint} non-JSON response: {resp.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"CBDB {endpoint} error: {e}")
            return None

    def search_person(self, name: str) -> List[Dict[str, Any]]:
        """
        搜索人物。

        返回格式：
        [{
            "cbdb_id": "...",
            "name": "文彭",
            "dynasty": "明",
            "birth_year": 1498,
            "death_year": 1575,
        }]
        """
        data = self._get("person.php", {"name": name, "output": "json"})
        if not data:
            return []
        return self._parse_person_list(data, name)

    def _parse_person_list(self, data: Any, query: str) -> List[Dict[str, Any]]:
        """解析人物列表响应。"""
        results = []

        def extract_person(p: dict) -> Optional[dict]:
            if not isinstance(p, dict):
                return None
            c_id = str(p.get("c_personid", ""))
            if not c_id:
                return None
            name = p.get("c_name", "")
            if not name:
                return None
            return {
                "cbdb_id": c_id,
                "name": name,
                "dynasty": p.get("c_dynasty_chn", ""),
                "birth_year": self._safe_int(p.get("c_birthyear")),
                "death_year": self._safe_int(p.get("c_deathyear")),
                "source": "cbdb",
            }

        if isinstance(data, dict):
            persons = data.get("PERSON", [])
            if not persons:
                persons = [data]
        elif isinstance(data, list):
            persons = data
        else:
            persons = []

        for p in (persons if isinstance(persons, list) else [persons]):
            result = extract_person(p)
            if result:
                results.append(result)

        return results[:10]

    def get_person_detail(self, cbdb_id: str) -> Dict[str, Any]:
        """
        获取人物详细传记信息。

        返回格式：
        {
            "cbdb_id": "...",
            "name": "...",
            "style_name": "...",
            "hao": "...",
            "birth_year": int,
            "death_year": int,
            "native_place": "...",
            "dynasty": "...",
            "father": "...",
            "occupation": "...",
            "official_rank": "...",
        }
        """
        bio = self._get("bio.php", {"id": cbdb_id, "output": "json"})
        if not bio:
            return {}

        def safe(v: Any) -> str:
            return str(v) if v else ""

        return {
            "cbdb_id": safe(bio.get("c_personid")),
            "name": safe(bio.get("c_name")),
            "style_name": safe(bio.get("cename")),
            "hao": safe(bio.get("chnname")),
            "birth_year": self._safe_int(bio.get("c_birthyear")),
            "death_year": self._safe_int(bio.get("c_deathyear")),
            "native_place": safe(bio.get("c_addr_chn")),
            "dynasty": safe(bio.get("c_dynasty_chn")),
            "father": safe(bio.get("c_fath_name")),
            "occupation": safe(bio.get("c_basic_occup_chn")),
            "official_rank": safe(bio.get("c_adm_duty_chn")),
        }

    def get_relations(self, cbdb_id: str) -> List[Dict[str, Any]]:
        """获取人物的亲属关系。"""
        data = self._get("relatives.php", {"id": cbdb_id, "output": "json"})
        if not data:
            return []
        relatives = data.get("RELATIVES", [])
        if not isinstance(relatives, list):
            relatives = [relatives] if relatives else []
        results = []
        for r in relatives:
            if isinstance(r, dict):
                results.append({
                    "cbdb_id": str(r.get("c_personid", "")),
                    "name": r.get("c_name", ""),
                    "relation_type": r.get("c_rela_chn", ""),
                    "relation_code": r.get("c_rela_code", ""),
                })
        return results

    def get_works(self, cbdb_id: str) -> List[Dict[str, Any]]:
        """获取人物的著作信息。"""
        data = self._get("work.php", {"id": cbdb_id, "output": "json"})
        if not data:
            return []
        works = data.get("WORKS", [])
        if not isinstance(works, list):
            works = [works] if works else []
        results = []
        for w in works:
            if isinstance(w, dict):
                results.append({
                    "title": w.get("c_work_chn", ""),
                    "type": w.get("c_work_typ_chn", ""),
                })
        return results

    @staticmethod
    def _safe_int(v: Any) -> Optional[int]:
        """安全转换为整数。"""
        if v is None:
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
