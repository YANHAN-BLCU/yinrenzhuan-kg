import logging
import httpx
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class CBDBClient:
    BASE_URL = "https://cbdb.fas.harvard.edu/cbdbapi/"
    LOCAL_SQLITE_URL = "https://raw.githubusercontent.com/cbdb-project/cbdb-data/master/data/cbdb_person.db"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)

    def search_person(self, name: str) -> List[Dict[str, Any]]:
        try:
            url = f"{self.BASE_URL}person.php"
            params = {
                "name": name,
                "output": "json",
            }
            if self.api_key:
                params["apikey"] = self.api_key
            resp = self.client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning(f"CBDB search failed: {resp.status_code}")
                return []
            data = resp.json()
            return self._parse_results(data, name)
        except Exception as e:
            logger.error(f"CBDB search error: {e}")
            return []

    def _parse_results(self, data: Any, query: str) -> List[Dict[str, Any]]:
        results = []
        if isinstance(data, dict):
            persons = data.get("PERSON", [])
            if isinstance(persons, dict):
                persons = [persons]
            elif not isinstance(persons, list):
                persons = [data]
        elif isinstance(data, list):
            persons = data
        else:
            persons = []

        for p in persons:
            if isinstance(p, dict):
                results.append({
                    "cbdb_id": str(p.get("c_personid", "")),
                    "name": p.get("c_name", ""),
                    "dynasty": p.get("c_dynasty_chn", ""),
                    "birth_year": p.get("c_birthyear", ""),
                    "death_year": p.get("c_deathyear", ""),
                    "source": "cbdb",
                })
        return results[:10]

    def get_person_detail(self, cbdb_id: str) -> Dict[str, Any]:
        try:
            url = f"{self.BASE_URL}bio.php"
            params = {
                "id": cbdb_id,
                "output": "json",
            }
            if self.api_key:
                params["apikey"] = self.api_key
            resp = self.client.get(url, params=params)
            if resp.status_code != 200:
                return {}
            data = resp.json()
            return {
                "cbdb_id": str(data.get("c_personid", "")),
                "name": data.get("c_name", ""),
                "style_name": data.get("cename", ""),
                "hao": data.get("chnname", ""),
                "birth_year": data.get("c_birthyear", ""),
                "death_year": data.get("c_deathyear", ""),
                "native_place": data.get("c_addr_chn", ""),
                "dynasty": data.get("c_dynasty_chn", ""),
                "father": data.get("c_fath_name", ""),
            }
        except Exception as e:
            logger.error(f"CBDB detail error: {e}")
            return {}

    def get_relations(self, cbdb_id: str) -> List[Dict[str, Any]]:
        try:
            url = f"{self.BASE_URL}relatives.php"
            params = {
                "id": cbdb_id,
                "output": "json",
            }
            if self.api_key:
                params["apikey"] = self.api_key
            resp = self.client.get(url, params=params)
            if resp.status_code != 200:
                return []
            return resp.json().get("RELATIVES", [])
        except Exception as e:
            logger.error(f"CBDB relations error: {e}")
            return []

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
