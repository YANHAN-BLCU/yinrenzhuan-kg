#!/usr/bin/env python3
import sys
import json
import logging
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root.parent))
project_root = project_root.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline")


def run_pipeline(
    text_path: Path = None,
    use_rules_only: bool = False,
    skip_entity_linking: bool = False,
    skip_analysis: bool = False,
    skip_rag: bool = False,
):
    from src.backend.utils.config import (
        YINRENCHUAN_TXT, OUTPUT_DIR, RDF_OUTPUT, LINKED_OUTPUT,
        EXTRACTED_TRIPLES, PERSONS_JSON, RELATIONS_JSON, GRAPH_JSON,
        CENTRALITY_OUTPUT, COMMUNITIES_OUTPUT, FAISS_INDEX,
    )
    from src.backend.extraction.text_processor import TextProcessor
    from src.backend.extraction.llm_ner import LLMENTyper
    from src.backend.extraction.llm_relation_extractor import LLMRelationExtractor, normalize_predicate
    from src.backend.extraction.entity_normalizer import EntityNormalizer, PersonNormalizer
    from src.backend.rdf.turtle_writer import TurtleWriter
    from src.backend.rdf.rdf_store import RDFStore
    from src.backend.linking.linker import EntityLinker
    from src.backend.linking.knowledge_merger import KnowledgeMerger
    from src.backend.graph_analysis.centrality import CentralityAnalysis
    from src.backend.graph_analysis.community import CommunityDetection
    from src.backend.graph_analysis.path_finder import PathFinder
    from src.backend.qa.rag.retriever import RAGRetriever

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    text_file = text_path or YINRENCHUAN_TXT
    logger.info(f"=== Stage 1: Text Processing ===")
    tp = TextProcessor()
    entries = tp.preprocess(text_file)
    logger.info(f"Loaded {len(entries)} entries")

    logger.info(f"=== Stage 2: NER & Relation Extraction (LLM + Few-shot) ===")
    normalizer = EntityNormalizer()

    # ---- Phase 2a: NER via LLM (with fallback to rules) ----
    llm_ner = LLMENTyper(use_rules_only=use_rules_only)
    all_ner_entities = {}   # entry_title -> list of (name, type, normalized_name)
    all_persons = set()     # 所有已识别的标准人物名

    for entry in entries:
        ner_result = llm_ner.extract(entry.content, entry.title, entry.chapter)
        entities_in_entry = []
        for e in ner_result.entities:
            std_name = e.normalized if e.type == "PERSON" else e.name
            entities_in_entry.append((std_name, e.type, e.name))
            if e.type == "PERSON":
                all_persons.add(std_name)
        all_ner_entities[entry.title] = entities_in_entry
    logger.info(f"NER found {len(all_persons)} unique persons")

    # ---- Phase 2b: Relation Extraction via LLM (with fallback to rules) ----
    llm_rel = LLMRelationExtractor(use_rules_only=use_rules_only)
    all_triples = []

    for entry in entries:
        persons_in_entry = [p for p, t, _ in all_ner_entities.get(entry.title, []) if t == "PERSON"]
        known_set = set(persons_in_entry)
        rel_triples = llm_rel.extract(
            entry.content, known_set, entry.title, entry.chapter
        )
        for t in rel_triples:
            # Convert RelationTriple → dict matching pipeline format
            all_triples.append({
                "subject": t.subject,
                "predicate": t.predicate,
                "object": t.obj,
                "confidence": t.confidence,
                "method": "llm" if llm_rel.available else "rule",
                "evidence": t.evidence,
                "chapter": t.chapter,
                "source_text": t.source_text,
            })

    logger.info(f"Extracted {len(all_triples)} triples, {len(all_persons)} unique persons")

    # Merge knowledge base triples (high-confidence, core coverage)
    from src.backend.extraction.knowledge_base import INK_TRIPLES as KB_TRIPLES
    seen_keys = {(t["subject"], t["predicate"], t["object"]) for t in all_triples}
    for kb_t in KB_TRIPLES:
        key = (kb_t["subject"], kb_t["predicate"], kb_t["object"])
        if key not in seen_keys:
            all_triples.append(kb_t)
            seen_keys.add(key)
    logger.info(f"After knowledge base merge: {len(all_triples)} triples")

    # Schema predicate normalization: old predicate name → new schema format
    # This ensures backward compatibility with KB triples using old names
    for t in all_triples:
        pred = t.get("predicate", "")
        t["predicate"] = normalize_predicate(pred)

    EXTRACTED_TRIPLES.write_text(json.dumps(all_triples, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Saved triples to {EXTRACTED_TRIPLES}")

    # ---- Phase 2c: Apply entity normalization (alias → standard name) ----
    person_normalizer = PersonNormalizer()
    for t in all_triples:
        subj_res = person_normalizer.normalize(t["subject"])
        obj_res = person_normalizer.normalize(t["object"])
        t["subject"] = subj_res.normalized
        t["object"] = obj_res.normalized

    logger.info(f"=== Stage 3: Build RDF Graph ===")
    writer = TurtleWriter()

    # Schema predicate → RDF property name mapping
    SCHEMA_TO_RDF = {
        # kinship
        "kinship:fatherOf": "fatherOf",
        "kinship:sonOf": "sonOf",
        "kinship:ancestorOf": "fatherOf",
        "kinship:descendantOf": "sonOf",
        # education
        "education:teacherOf": "teacherOf",
        "education:studentOf": "studentOf",
        "education:inheritedFrom": "inheritedFrom",
        # social
        "social:friendOf": "friendOf",
        "social:influencedBy": "influencedBy",
        # attribute
        "attribute:hasStyleName": "styleName",
        "attribute:hasHao": "hao",
        "attribute:hasAppellation": "appellation",
        "attribute:nativePlace": "nativePlace",
        "attribute:dynasty": "dynasty",
        # school
        "school:founderOf": "foundedSchool",
        "school:belongsTo": "belongsToSchool",
        # legacy
        "foundedSchool": "foundedSchool",
        "belongsToSchool": "belongsToSchool",
        "nativePlace": "nativePlace",
        "fromPlace": "nativePlace",
    }

    def to_rdf_predicate(pred: str) -> str:
        return SCHEMA_TO_RDF.get(pred, pred)

    logger.info(f"NER validated persons: {len(all_persons)}")

    # Predicates that map Person → Person (object is a person name)
    PERSON_REL_PREDICATES = {
        # Old names (still used in KB triples)
        "fatherOf", "sonOf", "teacherOf", "studentOf",
        "friendOf", "brotherOf", "inheritedFrom", "influencedBy",
        # New Schema names
        "kinship:fatherOf", "kinship:sonOf",
        "kinship:ancestorOf", "kinship:descendantOf",
        "education:teacherOf", "education:studentOf",
        "education:inheritedFrom",
        "social:friendOf", "social:influencedBy",
    }
    # Predicates that map Person → string attribute
    ATTR_PREDICATES = {
        "styleName", "hao", "dynasty", "fromPlace",
        "appellation", "nativePlace",
        # New Schema attribute names
        "attribute:hasStyleName", "attribute:hasHao",
        "attribute:hasAppellation", "attribute:hasAppellation",
        "attribute:nativePlace", "attribute:dynasty",
    }

    person_set = set()
    attr_triples = []
    rel_triples = []
    schools_seen = set()

    for t in all_triples:
        subj = t.get("subject", "")
        pred = t.get("predicate", "")
        obj = t.get("object", "")

        if not subj or not obj:
            continue

        # KB triples (method="known") bypass NER validation — they are verified facts
        is_kb_triple = t.get("method") == "known"

        # subject 必须是人名（NER 发现 或 KB 知识库）
        if not is_kb_triple and subj not in all_persons:
            continue

        if pred in PERSON_REL_PREDICATES:
            # KB triples: allow object even if not in NER (e.g., KB says "文彭→文彭", NER might not have 文彭)
            if obj in all_persons or is_kb_triple:
                person_set.add(subj)
                person_set.add(obj)
                rel_triples.append(t)
        elif pred in ATTR_PREDICATES:
            person_set.add(subj)
            attr_triples.append(t)
        elif pred in ("foundedSchool", "belongsToSchool", "school:founderOf", "school:belongsTo"):
            person_set.add(subj)
            attr_triples.append(t)
            schools_seen.add(obj)
        else:
            person_set.add(subj)
            attr_triples.append(t)

    logger.info(f"Validated person_set size: {len(person_set)}")
    logger.info(f"Relation triples (person-person): {len(rel_triples)}")
    logger.info(f"Attribute triples: {len(attr_triples)}")

    for name in person_set:
        writer.add_person(name)

    for school_name in schools_seen:
        if school_name:
            writer.add_school(school_name)

    for t in attr_triples + rel_triples:
        writer.add_triple(
            subject=t["subject"],
            predicate=to_rdf_predicate(t["predicate"]),
            obj=t["object"],
            confidence=t.get("confidence", 0.95),
            method=t.get("method", "llm"),
            evidence_text=t.get("evidence", ""),
            chapter=t.get("chapter", ""),
        )

    writer.save(RDF_OUTPUT)
    logger.info(f"RDF graph saved: {RDF_OUTPUT}")

    logger.info(f"=== Stage 4: Entity Linking & Knowledge Merging ===")
    if not skip_entity_linking:
        rdf_store = RDFStore(writer.get_graph())
        merger = KnowledgeMerger(rdf_store)

        persons_to_link = list(person_set)[:30]
        for name in persons_to_link:
            person_triples = [t for t in all_triples if t["subject"] == name]
            style_name = next((t["object"] for t in person_triples if t["predicate"] == "styleName"), None)
            hao = next((t["object"] for t in person_triples if t["predicate"] == "hao"), None)
            dynasty = next((t["object"] for t in person_triples if t["predicate"] == "dynasty"), None)
            merger.merge_external_knowledge(name, style_name, hao, dynasty)

        rdf_store.save(LINKED_OUTPUT)
        logger.info(f"Linked graph saved: {LINKED_OUTPUT}")
    else:
        # Even when skipping linking, save the RDF graph so downstream stages
        # and API can load from linked_graph.ttl consistently.
        from src.backend.rdf.rdf_store import RDFStore
        linked_store = RDFStore(writer.get_graph())
        linked_store.save(LINKED_OUTPUT)
        logger.info(f"Copied graph to linked_graph.ttl (linking skipped)")

    logger.info(f"=== Stage 5: Graph Analysis ===")
    if not skip_analysis:
        rdf_store = RDFStore()
        rdf_file = LINKED_OUTPUT if LINKED_OUTPUT.exists() else RDF_OUTPUT
        if rdf_file.exists():
            rdf_store.load(rdf_file)

        G = rdf_store.as_networkx()
        logger.info(f"NetworkX graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

        centrality = CentralityAnalysis(G)
        centrality_results = centrality.analyze_all()
        centrality.save(CENTRALITY_OUTPUT)
        logger.info(f"Centrality analysis saved")

        community = CommunityDetection(G)
        community.louvain()
        community.save(COMMUNITIES_OUTPUT)
        logger.info(f"Community detection saved")

        # Use full networkx with node_type info from RDF
        G_full = rdf_store.as_networkx_full()
        logger.info(f"Full graph: {G_full.number_of_nodes()} nodes, {G_full.number_of_edges()} edges")

        nodes = []
        links = []
        seen_nodes = set()

        for node in G_full.nodes:
            if node in seen_nodes:
                continue
            seen_nodes.add(node)

            node_type = G_full.nodes[node].get("node_type", "person")
            school = None
            if node_type == "person":
                school = next(
                    (d.get("relation", "") for _, _, d in G_full.out_edges(node, data=True)
                     if "School" in d.get("relation", "")), None
                )
            # Clean name: remove "school/" prefix for display
            name = node.replace("school/", "") if node_type == "school" else node
            nodes.append({
                "id": node,
                "name": name,
                "type": node_type,
                "school": school,
            })

        for u, v, data in G_full.edges(data=True):
            links.append({
                "source": u, "target": v,
                "relation": data.get("relation", "unknown"),
            })

        graph_data = {"nodes": nodes, "links": links}
        GRAPH_JSON.write_text(json.dumps(graph_data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Graph JSON saved: {GRAPH_JSON}")

        # persons.json: only Person nodes (not schools) from RDF store
        all_rdf_persons = rdf_store.get_all_persons()
        # Exclude school nodes that may have leaked into person_set
        school_names = {name.replace("school/", "") for name in schools_seen} | schools_seen
        persons_data = [{"name": n} for n in sorted(n for n in set(all_rdf_persons) if n not in school_names)]
        PERSONS_JSON.write_text(json.dumps(persons_data, ensure_ascii=False, indent=2), encoding="utf-8")

        rels_data = [
            {"subject": t["subject"], "predicate": t["predicate"], "object": t["object"]}
            for t in all_triples
            if t.get("subject") and t.get("object")
        ]
        RELATIONS_JSON.write_text(json.dumps(rels_data, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(f"=== Stage 6: RAG Index (optional) ===")
    if not skip_rag:
        import signal, functools
        def _timeout_handler(signum, frame):
            raise TimeoutError("RAG initialization timed out")
        try:
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(30)
            try:
                rag_entries = [
                    {
                        "content": entry.content,
                        "title": entry.title,
                        "chapter": entry.chapter,
                    }
                    for entry in entries
                ]
                retriever = RAGRetriever(rag_entries)
                retriever.initialize()
                logger.info("RAG retriever initialized")
            finally:
                signal.alarm(0)
        except (ImportError, AttributeError, TimeoutError) as e:
            logger.warning(f"RAG initialization skipped: {e}")
        except Exception as e:
            logger.warning(f"RAG initialization skipped: {e}")

    logger.info(f"=== Pipeline Complete ===")
    logger.info(f"Output files:")
    for f in OUTPUT_DIR.glob("*"):
        logger.info(f"  {f.name}: {f.stat().st_size / 1024:.1f} KB")

    return {
        "entries": len(entries),
        "triples": len(all_triples),
        "persons": len(person_set),
        "schools": len(schools_seen),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="印人传知识图谱构建流程")
    parser.add_argument("--text", type=Path, default=None, help="《印人传》文本路径")
    parser.add_argument("--use-rules-only", action="store_true",
                          help="跳过 LLM，仅使用正则规则抽取（默认：LLM优先，规则兜底）")
    parser.add_argument("--skip-linking", action="store_true", help="跳过实体链接")
    parser.add_argument("--skip-analysis", action="store_true", help="跳过图分析")
    parser.add_argument("--skip-rag", action="store_true", help="跳过RAG构建")
    args = parser.parse_args()

    result = run_pipeline(
        text_path=args.text,
        use_rules_only=args.use_rules_only,
        skip_entity_linking=args.skip_linking,
        skip_analysis=args.skip_analysis,
        skip_rag=args.skip_rag,
    )
    print(f"\n结果统计: {result}")
