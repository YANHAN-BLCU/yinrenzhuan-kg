import logging
from typing import Dict, Optional, Any
from .linker import EntityLinker, LinkCandidate

logger = logging.getLogger(__name__)


class KnowledgeMerger:

    def __init__(self, rdf_store):
        self.rdf_store = rdf_store
        self.linker = EntityLinker()

    def merge_external_knowledge(self, person_name: str, style_name: Optional[str] = None,
                                 hao: Optional[str] = None, dynasty: Optional[str] = None,
                                 period: Optional[str] = None) -> Dict[str, Any]:
        candidates = self.linker.find_candidates(
            person_name, style_name, hao, dynasty, period
        )
        best = self.linker.disambiguate(candidates)

        merged = {
            "person_name": person_name,
            "style_name": style_name,
            "hao": hao,
            "dynasty": dynasty,
            "ctext_id": None,
            "cbdb_id": None,
            "birth_year": None,
            "death_year": None,
            "native_place": None,
            "ctext_url": None,
            "linked": False,
            "confidence": 0.0,
        }

        if not best:
            logger.info(f"No link found for '{person_name}'")
            return merged

        merged["linked"] = True
        merged["confidence"] = best.score

        if best.source == "ctext":
            merged["ctext_url"] = best.external_id
            merged["ctext_id"] = best.external_id
        elif best.source == "cbdb":
            merged["cbdb_id"] = best.external_id
            details = best.details
            merged["birth_year"] = details.get("birth_year")
            merged["death_year"] = details.get("death_year")
            merged["native_place"] = details.get("native_place")
            if not merged["style_name"] and details.get("style_name"):
                merged["style_name"] = details.get("style_name")
            if not merged["hao"] and details.get("hao"):
                merged["hao"] = details.get("hao")

        self._add_to_graph(merged)
        logger.info(f"Linked '{person_name}' to {best.source} ({best.name}), confidence: {best.score:.2f}")
        return merged

    def _add_to_graph(self, merged: Dict[str, Any]):
        from ..rdf.ontology import get_person_uri, INK_NS
        from rdflib import Literal
        person_uri = get_person_uri(merged["person_name"])

        if merged.get("birth_year"):
            try:
                self.rdf_store.graph.add((
                    person_uri, INK_NS.birthYear,
                    Literal(int(merged["birth_year"]))
                ))
            except (ValueError, TypeError):
                pass

        if merged.get("death_year"):
            try:
                self.rdf_store.graph.add((
                    person_uri, INK_NS.deathYear,
                    Literal(int(merged["death_year"]))
                ))
            except (ValueError, TypeError):
                pass

        if merged.get("native_place"):
            self.rdf_store.graph.add((
                person_uri, INK_NS.nativePlace,
                Literal(merged["native_place"])
            ))

        if merged.get("ctext_id"):
            self.rdf_store.graph.add((
                person_uri, INK_NS.ctextId,
                Literal(str(merged["ctext_id"]))
            ))

        if merged.get("cbdb_id"):
            self.rdf_store.graph.add((
                person_uri, INK_NS.cbdbId,
                Literal(str(merged["cbdb_id"]))
            ))

        self.rdf_store.graph.add((
            person_uri, INK_NS.dataSource,
            Literal(f"ctext+cbdb (confidence={merged['confidence']:.1f})")
        ))

    def batch_merge(self, persons: list) -> Dict[str, Dict[str, Any]]:
        results = {}
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
                person_data.get("period"),
            )
            results[name] = merged
        logger.info(f"Batch merged {len(results)} persons")
        return results

    def close(self):
        self.linker.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
