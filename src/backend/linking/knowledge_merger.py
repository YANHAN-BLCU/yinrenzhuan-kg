"""
知识合并模块。

将外部数据库（cText、CBDB）的匹配结果回填至知识图谱，
包括生卒年、籍贯、官职、作品等数据属性，
并建立 owl:sameAs 等同关系链接。
"""
import logging
from typing import Dict, Optional, Any, List
from .linker import EntityLinker, LinkCandidate

logger = logging.getLogger(__name__)


class KnowledgeMerger:

    def __init__(self, rdf_store):
        self.rdf_store = rdf_store
        self.linker = EntityLinker()
        self.merge_results: List[Dict[str, Any]] = []

    def merge_external_knowledge(
        self,
        person_name: str,
        style_name: Optional[str] = None,
        hao: Optional[str] = None,
        dynasty: Optional[str] = None,
        native_place: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        对单个历史人物执行实体链接与知识回填。

        返回结果包含：
        - linked: 是否成功链接
        - auto_linked: 是否达到自动链接阈值
        - needs_review: 是否需要人工审核
        - confidence: 匹配置信度
        - cbdb_data: CBDB 回填的详细数据（生卒年、籍贯、官职等）
        """
        candidates = self.linker.find_candidates(
            person_name, style_name, hao, dynasty, native_place
        )
        best = self.linker.disambiguate(candidates)

        merged: Dict[str, Any] = {
            "person_name": person_name,
            "style_name": style_name,
            "hao": hao,
            "dynasty": dynasty,
            "native_place": native_place,
            "ctext_id": None,
            "cbdb_id": None,
            "ctext_url": None,
            "birth_year": None,
            "death_year": None,
            "occupation": None,
            "official_rank": None,
            "biography": None,
            "masterpiece": None,
            "linked": False,
            "auto_linked": False,
            "needs_review": True,
            "confidence": 0.0,
        }

        if not best:
            logger.info(f"No link found for '{person_name}'")
            self.merge_results.append(merged)
            return merged

        merged["linked"] = True
        merged["confidence"] = best.score
        merged["auto_linked"] = best.score >= self.linker.confidence_threshold
        merged["needs_review"] = best.score < self.linker.confidence_threshold

        # 回填数据
        if best.source == "ctext":
            merged["ctext_url"] = best.external_id
            merged["ctext_id"] = best.external_id
            # ctext 详情补充
            from .ctext_client import CtextClient
            ctext = CtextClient()
            detail = ctext.get_person_detail(best.external_id)
            ctext.close()
            if detail.get("description"):
                merged["biography"] = detail["description"]

        elif best.source == "cbdb":
            merged["cbdb_id"] = best.external_id
            # CBDB 详情已在 linker 中获取
            details = best.details
            merged["birth_year"] = details.get("birth_year")
            merged["death_year"] = details.get("death_year")
            merged["native_place"] = details.get("native_place") or native_place
            merged["occupation"] = details.get("occupation")
            merged["official_rank"] = details.get("official_rank")
            # 如果原图谱没有字/号，从 CBDB 补充
            if not merged.get("style_name") and details.get("style_name"):
                merged["style_name"] = details["style_name"]
            if not merged.get("hao") and details.get("hao"):
                merged["hao"] = details["hao"]

        # 写入 RDF 图谱
        self._write_to_graph(merged)

        logger.info(
            f"Linked '{person_name}' → {best.source} ({best.name}), "
            f"confidence: {best.score:.2f}, auto: {merged['auto_linked']}"
        )
        self.merge_results.append(merged)
        return merged

    def _write_to_graph(self, merged: Dict[str, Any]):
        """将回填数据写入 RDF 图谱。"""
        from ..rdf.ontology import get_person_uri, INK_NS
        from rdflib import Literal

        person_uri = get_person_uri(merged["person_name"])

        def add_triple(prop, value, dtype=None):
            from rdflib.namespace import XSD
            if value is None:
                return
            lit = Literal(value, datatype=dtype) if dtype else Literal(value)
            self.rdf_store.graph.add((person_uri, INK_NS[prop], lit))

        add_triple("birthYear", merged.get("birth_year"), "integer")
        add_triple("deathYear", merged.get("death_year"), "integer")
        add_triple("nativePlace", merged.get("native_place"))
        add_triple("occupation", merged.get("occupation"))
        add_triple("officialRank", merged.get("official_rank"))
        add_triple("biography", merged.get("biography"))
        add_triple("masterpiece", merged.get("masterpiece"))

        if merged.get("ctext_id"):
            add_triple("ctextId", str(merged["ctext_id"]))
        if merged.get("cbdb_id"):
            add_triple("cbdbId", str(merged["cbdb_id"]))

        conf = merged.get("confidence", 0.0)
        add_triple("dataSource", f"ctext+cbdb (confidence={conf:.1f})")

    def batch_merge(self, persons: List) -> Dict[str, Dict[str, Any]]:
        """
        批量执行实体链接与知识回填。

        Args:
            persons: 人物列表，每个元素可以是字符串（人名）或字典
                     {"person_name": "...", "style_name": "...", ...}
        Returns:
            {人名: 合并结果}
        """
        results = {}
        review_queue = []

        for person in persons:
            if isinstance(person, str):
                person_data = {"person_name": person}
            else:
                person_data = person
            name = person_data.get("person_name", "")
            if not name:
                continue
            merged = self.merge_external_knowledge(
                name,
                person_data.get("style_name"),
                person_data.get("hao"),
                person_data.get("dynasty"),
                person_data.get("native_place"),
            )
            results[name] = merged
            if merged["needs_review"]:
                review_queue.append(merged)

        auto_count = sum(1 for r in results.values() if r["auto_linked"])
        linked_count = sum(1 for r in results.values() if r["linked"])
        logger.info(
            f"Batch merged {len(results)} persons: "
            f"{linked_count} linked, {auto_count} auto, {len(review_queue)} need review"
        )
        return results

    def get_review_queue(self) -> List[Dict[str, Any]]:
        """获取需要人工审核的实体列表。"""
        return [r for r in self.merge_results if r["needs_review"]]

    def get_summary(self) -> Dict[str, Any]:
        """获取本次合并的统计摘要。"""
        results = self.merge_results
        return {
            "total": len(results),
            "linked": sum(1 for r in results if r["linked"]),
            "auto_linked": sum(1 for r in results if r["auto_linked"]),
            "needs_review": sum(1 for r in results if r["needs_review"]),
            "avg_confidence": (
                sum(r["confidence"] for r in results) / len(results)
                if results else 0.0
            ),
        }

    def close(self):
        self.linker.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
