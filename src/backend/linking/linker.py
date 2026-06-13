"""
实体链接模块。

将抽取的人物实体与 ctext、CBDB 外部数据库进行对齐，
支持模糊字符串匹配、置信度阈值过滤和同名消歧。
"""
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from .ctext_client import CtextClient
from .cbdb_client import CBDBClient

logger = logging.getLogger(__name__)

# 朝代 → ctext/CBDB 中的时期关键词
PERIOD_SCORES: Dict[str, List[str]] = {
    "明": ["明代", "明初", "明中期", "明末", "明末清初", "嘉靖", "萬曆", "天啟", "崇禎"],
    "清": ["清代", "清初", "清中期", "清晚期", "康熙", "雍正", "乾隆", "光緒", "道光", "咸豐", "同治", "宣統"],
    "元": ["元代", "元末"],
}


@dataclass
class LinkCandidate:
    """外部数据库匹配候选结果。"""
    external_id: str
    name: str
    source: str
    score: float
    details: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self):
        return f"LinkCandidate({self.name}, {self.source}, score={self.score:.2f})"


class EntityLinker:

    def __init__(self, confidence_threshold: float = 0.85):
        """
        Args:
            confidence_threshold: 置信度阈值，高于此值自动建立链接，低于此值进入人工审核队列
        """
        self.ctext = CtextClient()
        self.cbdb = CBDBClient()
        self.confidence_threshold = confidence_threshold

    def find_candidates(
        self,
        person_name: str,
        style_name: Optional[str] = None,
        hao: Optional[str] = None,
        dynasty: Optional[str] = None,
        native_place: Optional[str] = None,
    ) -> List[LinkCandidate]:
        """
        在 ctext 和 CBDB 中搜索匹配候选。

        评分维度：姓名精确匹配(4分) / 字/号匹配(4分) /
                 朝代一致性(2分) / 籍贯一致性(1分)
        """
        candidates = []
        seen: Dict[str, bool] = {}

        # ctext 搜索
        ctext_results = self.ctext.search_person(person_name)
        for r in ctext_results:
            key = f"ctext:{r.get('ctext_url', '')}"
            if key in seen:
                continue
            seen[key] = True
            score = self._compute_score(
                r.get("name", ""), person_name,
                style_name=style_name, hao=hao,
                dynasty=dynasty, native_place=native_place,
            )
            candidates.append(LinkCandidate(
                external_id=r.get("ctext_url", ""),
                name=r.get("name", ""),
                source="ctext",
                score=score,
                details=r,
            ))

        # CBDB 搜索
        cbdb_results = self.cbdb.search_person(person_name)
        for r in cbdb_results:
            key = f"cbdb:{r.get('cbdb_id', '')}"
            if key in seen:
                continue
            seen[key] = True
            # CBDB 详情补充
            cbdb_id = r.get("cbdb_id", "")
            if cbdb_id:
                detail = self.cbdb.get_person_detail(cbdb_id)
                r.update(detail)
            score = self._compute_score(
                r.get("name", ""), person_name,
                style_name=style_name, hao=hao,
                dynasty=dynasty, native_place=native_place,
            )
            candidates.append(LinkCandidate(
                external_id=cbdb_id,
                name=r.get("name", ""),
                source="cbdb",
                score=score,
                details=r,
            ))

        candidates.sort(key=lambda c: c.score, reverse=True)
        logger.info(
            f"Found {len(candidates)} candidates for '{person_name}', "
            f"top score: {candidates[0].score:.2f}" if candidates else "No candidates"
        )
        return candidates

    def _compute_score(
        self,
        candidate_name: str,
        target_name: str,
        style_name: Optional[str] = None,
        hao: Optional[str] = None,
        dynasty: Optional[str] = None,
        native_place: Optional[str] = None,
    ) -> float:
        """
        多维度加权打分（满分 10 分）。

        姓名精确匹配     4分（严格相等）
        姓名包含关系     2分（互含）
        字/号匹配       4分
        朝代一致性       2分
        籍贯一致性       1分
        """
        score = 0.0
        cand = candidate_name.strip()
        targ = target_name.strip()

        if cand == targ:
            score += 4.0
        elif targ in cand or cand in targ:
            score += 2.0

        if style_name and style_name.strip() in cand:
            score += 4.0
        if hao and hao.strip() in cand:
            score += 4.0

        if dynasty:
            for period_keyword in PERIOD_SCORES.get(dynasty, []):
                if period_keyword in cand:
                    score += 2.0
                    break
            cand_dynasty = self._detect_dynasty(cand)
            if cand_dynasty == dynasty:
                score += 1.0

        if native_place and native_place.strip() in cand:
            score += 1.0

        return min(score, 10.0)

    def _detect_dynasty(self, text: str) -> Optional[str]:
        for period_name in ["明", "清", "元", "宋", "唐", "漢"]:
            if period_name in text:
                return period_name
        return None

    def disambiguate(self, candidates: List[LinkCandidate]) -> Optional[LinkCandidate]:
        """
        消歧：选择最优匹配。

        策略：
        1. 最高分 >= 6.0 → 直接返回
        2. 只有一个候选且 >= 3.0 → 返回
        3. 多候选 → 按数据源分别取最高分，取总最高分（>= 3.0）
        4. 无满足条件的候选 → 返回 None（进入人工审核）
        """
        if not candidates:
            return None

        top = candidates[0]
        if top.score >= 6.0:
            return top
        if len(candidates) == 1 and top.score >= 3.0:
            return top

        by_source: Dict[str, List[LinkCandidate]] = {}
        for c in candidates:
            by_source.setdefault(c.source, []).append(c)

        best: Optional[LinkCandidate] = None
        for source, cs in by_source.items():
            source_top = cs[0]
            if best is None or source_top.score > best.score:
                best = source_top

        if best and best.score >= 3.0:
            return best
        return None

    def is_auto_link(self, candidate: Optional[LinkCandidate]) -> bool:
        """判断是否达到自动链接阈值。"""
        return candidate is not None and candidate.score >= self.confidence_threshold

    def is_review_needed(self, candidate: Optional[LinkCandidate]) -> bool:
        """判断是否需要人工审核。"""
        if candidate is None:
            return True
        return candidate.score < self.confidence_threshold

    def close(self):
        self.ctext.close()
        self.cbdb.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
