import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from .ctext_client import CtextClient
from .cbdb_client import CBDBClient

logger = logging.getLogger(__name__)


@dataclass
class LinkCandidate:
    external_id: str
    name: str
    source: str
    score: float
    details: Dict[str, Any]

    def __repr__(self):
        return f"LinkCandidate({self.name}, {self.source}, score={self.score:.2f})"


class EntityLinker:

    PERIOD_SCORES = {
        "明": ["明代", "明初", "明中期", "明末", "明末清初", "嘉靖", "萬曆", "天啟", "崇禎"],
        "清": ["清代", "清初", "清中期", "清晚期", "康熙", "雍正", "乾隆", "光緒", "道光", "咸豐", "同治", "宣統"],
        "元": ["元代", "元末"],
    }

    def __init__(self):
        self.ctext = CtextClient()
        self.cbdb = CBDBClient()

    def find_candidates(self, person_name: str, style_name: Optional[str] = None,
                       hao: Optional[str] = None, dynasty: Optional[str] = None,
                       period: Optional[str] = None) -> List[LinkCandidate]:
        candidates = []
        seen = {}

        ctext_results = self.ctext.search_person(person_name)
        for r in ctext_results:
            key = f"ctext:{r.get('ctext_url', '')}"
            if key in seen:
                continue
            seen[key] = True
            score = self._compute_score(r.get("name", ""), person_name, style_name, hao, dynasty, period)
            candidates.append(LinkCandidate(
                external_id=r.get("ctext_url", ""),
                name=r.get("name", ""),
                source="ctext",
                score=score,
                details=r,
            ))

        cbdb_results = self.cbdb.search_person(person_name)
        for r in cbdb_results:
            key = f"cbdb:{r.get('cbdb_id', '')}"
            if key in seen:
                continue
            seen[key] = True
            score = self._compute_score(r.get("name", ""), person_name, style_name, hao, dynasty, period)
            cbdb_detail = self.cbdb.get_person_detail(r.get("cbdb_id", ""))
            r.update(cbdb_detail)
            candidates.append(LinkCandidate(
                external_id=r.get("cbdb_id", ""),
                name=r.get("name", ""),
                source="cbdb",
                score=score,
                details=r,
            ))

        candidates.sort(key=lambda c: c.score, reverse=True)
        logger.info(f"Found {len(candidates)} candidates for '{person_name}', top score: {candidates[0].score if candidates else 0:.2f}")
        return candidates

    def _compute_score(
        self, candidate_name: str, target_name: str,
        style_name: Optional[str], hao: Optional[str],
        dynasty: Optional[str], period: Optional[str]
    ) -> float:
        score = 0.0

        if candidate_name.strip() == target_name.strip():
            score += 4.0
        elif target_name in candidate_name or candidate_name in target_name:
            score += 2.0

        if style_name and style_name in candidate_name:
            score += 4.0
        if hao and hao in candidate_name:
            score += 4.0

        if dynasty:
            for period_name in self.PERIOD_SCORES.get(dynasty, []):
                if period_name in candidate_name or period_name in str(self.ctext.search_person.__self__ if hasattr(self.ctext, "search_person") else {}):
                    score += 2.0
                    break

        if dynasty:
            candidate_dynasty = self._detect_dynasty(candidate_name)
            if candidate_dynasty == dynasty:
                score += 1.0

        return min(score, 10.0)

    def _detect_dynasty(self, text: str) -> Optional[str]:
        for period_name in ["明", "清", "元", "宋", "唐", "漢"]:
            if period_name in text:
                return period_name
        return None

    def disambiguate(self, candidates: List[LinkCandidate]) -> Optional[LinkCandidate]:
        if not candidates:
            return None
        if candidates[0].score >= 6.0:
            return candidates[0]
        if len(candidates) == 1:
            return candidates[0] if candidates[0].score >= 3.0 else None

        by_source: Dict[str, List[LinkCandidate]] = {}
        for c in candidates:
            by_source.setdefault(c.source, []).append(c)

        best = None
        for source, cs in by_source.items():
            top = cs[0]
            if best is None or top.score > best.score:
                best = top

        return best if best and best.score >= 3.0 else None

    def close(self):
        self.ctext.close()
        self.cbdb.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
