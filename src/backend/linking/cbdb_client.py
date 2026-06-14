"""
CBDB（中国历代人物传记资料库）API 客户端。

CBDB API 文档：https://input.cbdb.fas.harvard.edu/cbdbapi/index.html
支持：人物搜索、传记详情、亲属关系查询。

注意：CBDB API 返回格式可能为空字符串或非 JSON 响应，
需要做健壮性处理。参数使用 o=json 而非 output=json。
"""
import logging
import json
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


@dataclass
class CbdbPerson:
    """CBDB 人物标准化数据结构。"""
    cbdb_id: str
    name: str
    style_name: str = ""
    hao: str = ""
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    native_place: str = ""
    dynasty: str = ""
    father: str = ""
    occupation: str = ""
    official_rank: str = ""


class CBDBClient:

    BASE_URL = "https://cbdb.fas.harvard.edu/cbdbapi"
    # CBDB 有频率限制，添加延时
    _last_request_time: float = 0.0
    _min_interval: float = 1.5  # 秒

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)

    def _rate_limit(self):
        """两次请求之间强制延时，防止触发 CBDB 限流。"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _get(self, endpoint: str, params: dict) -> Optional[Any]:
        """统一的 GET 请求处理，使用 o=json 参数获取 JSON 输出。"""
        self._rate_limit()
        try:
            params = {k: v for k, v in params.items() if v is not None and v != ""}
            url = f"{self.BASE_URL}/{endpoint}"
            resp = self.client.get(url, params=params)
            if resp.status_code == 404:
                logger.debug(f"CBDB {endpoint} HTTP 404 for params: {params}")
                return None
            if resp.status_code != 200:
                logger.warning(f"CBDB {endpoint} HTTP {resp.status_code}")
                return None
            if not resp.text.strip():
                logger.warning(f"CBDB {endpoint} empty response")
                return None
            return resp.json()
        except json.JSONDecodeError:
            logger.debug(f"CBDB {endpoint} non-JSON response: {resp.text[:200]}")
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
        # 使用 o=json 参数，CBDB 默认返回 HTML
        data = self._get("person.php", {"name": name, "o": "json"})
        if not data:
            return []
        return self._parse_person_list(data, name)

    def _parse_person_list(self, data: Any, query: str) -> List[Dict[str, Any]]:
        """解析人物列表响应——支持新版嵌套结构。"""
        results = []

        def extract_from_basic(basic: dict) -> Optional[dict]:
            if not isinstance(basic, dict):
                return None
            c_id = str(basic.get("PersonId", ""))
            if not c_id:
                return None
            name = basic.get("ChName", "")
            if not name:
                return None
            return {
                "cbdb_id": c_id,
                "name": name,
                "dynasty": basic.get("Dynasty", ""),
                "birth_year": self._safe_int(basic.get("YearBirth")),
                "death_year": self._safe_int(basic.get("YearDeath")),
                "source": "cbdb",
            }

        # 新版 CBDB JSON 嵌套结构
        try:
            package = data.get("Package", {})
            authority = package.get("PersonAuthority", {})
            person_info = authority.get("PersonInfo", {})
            person = person_info.get("Person", {})

            if isinstance(person, dict) and person.get("BasicInfo"):
                basic = person.get("BasicInfo", {})
                result = extract_from_basic(basic)
                if result:
                    results.append(result)
            elif isinstance(person, dict):
                # 直接有 BasicInfo
                result = extract_from_basic(person)
                if result:
                    results.append(result)
        except (TypeError, AttributeError):
            pass

        # 回退：尝试旧版直接结构（以防 API 格式变化）
        if not results:
            if isinstance(data, dict):
                basic = data.get("BasicInfo") or data
                result = extract_from_basic(basic)
                if result:
                    results.append(result)
            elif isinstance(data, list):
                for item in data:
                    result = extract_from_basic(item)
                    if result:
                        results.append(result)

        return results[:10]

    def get_person_detail(self, cbdb_id: str) -> Dict[str, Any]:
        """
        获取人物详细传记信息。

        注意：CBDB API 没有独立的 bio.php 端点。
        详情通过 person.php?id={cbdb_id}&o=json 获取。

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
        # 使用 person.php 带 id 参数获取完整详情
        bio = self._get("person.php", {"id": cbdb_id, "o": "json"})
        if not bio:
            return {}

        def safe(v: Any) -> str:
            return str(v) if v else ""

        # 解析新版嵌套结构
        try:
            package = bio.get("Package", {})
            authority = package.get("PersonAuthority", {})
            person_info = authority.get("PersonInfo", {})
            person = person_info.get("Person", {})
            basic = person.get("BasicInfo", {})

            # 别名信息
            alt_names = person.get("PersonAliases", {}).get("Alias", [])
            if not isinstance(alt_names, list):
                alt_names = [alt_names] if alt_names else []
            style_name = ""
            hao = ""
            for alt in alt_names:
                if isinstance(alt, dict):
                    rel = str(alt.get("c_relation_eng", "")).lower()
                    if "style" in rel:
                        style_name = safe(alt.get("c_alt_name_chn", ""))
                    elif "hao" in rel or "artname" in rel:
                        hao = safe(alt.get("c_alt_name_chn", ""))

            # 籍贯信息
            addrs = person.get("PersonAddresses", {}).get("Address", [])
            if not isinstance(addrs, list):
                addrs = [addrs] if addrs else []
            native_place = ""
            for addr in addrs:
                if isinstance(addr, dict) and addr.get("c_addr_type_chn", "") == "籍贯":
                    native_place = safe(addr.get("c_addr_chn", ""))
                    break

            # 任职信息
            postings = person.get("PersonPostings", {}).get("Posting", [])
            if not isinstance(postings, list):
                postings = [postings] if postings else []
            official_rank = safe(postings[0].get("c_adm_duty_chn", "")) if postings else ""

            return {
                "cbdb_id": safe(basic.get("PersonId")),
                "name": safe(basic.get("ChName")),
                "style_name": style_name,
                "hao": hao,
                "birth_year": self._safe_int(basic.get("YearBirth")),
                "death_year": self._safe_int(basic.get("YearDeath")),
                "native_place": native_place,
                "dynasty": safe(basic.get("Dynasty")),
                "father": "",
                "occupation": "",
                "official_rank": official_rank,
            }
        except (TypeError, AttributeError):
            # 回退：直接解析
            return {
                "cbdb_id": safe(bio.get("PersonId", "")),
                "name": safe(bio.get("ChName", "")),
                "style_name": safe(bio.get("cename", "")),
                "hao": safe(bio.get("chnname", "")),
                "birth_year": self._safe_int(bio.get("YearBirth")),
                "death_year": self._safe_int(bio.get("YearDeath")),
                "native_place": safe(bio.get("c_addr_chn", "")),
                "dynasty": safe(bio.get("Dynasty", "")),
                "father": safe(bio.get("c_fath_name", "")),
                "occupation": safe(bio.get("c_basic_occup_chn", "")),
                "official_rank": safe(bio.get("c_adm_duty_chn", "")),
            }

    def get_relations(self, cbdb_id: str) -> List[Dict[str, Any]]:
        """获取人物的亲属关系。"""
        data = self._get("relatives.php", {"id": cbdb_id, "o": "json"})
        if not data:
            return []
        try:
            package = data.get("Package", {})
            authority = package.get("PersonAuthority", {})
            person_info = authority.get("PersonInfo", {})
            person = person_info.get("Person", {})
            relatives = person.get("PersonKinshipInfo", {}).get("Kinship", [])
        except (TypeError, AttributeError):
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
        data = self._get("work.php", {"id": cbdb_id, "o": "json"})
        if not data:
            return []
        try:
            package = data.get("Package", {})
            authority = package.get("PersonAuthority", {})
            person_info = authority.get("PersonInfo", {})
            person = person_info.get("Person", {})
            works = person.get("PersonTexts", {}).get("Text", [])
        except (TypeError, AttributeError):
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
