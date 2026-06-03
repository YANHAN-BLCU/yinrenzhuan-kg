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
    skip_llm: bool = True,
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
    from src.backend.extraction.ner_rules import NERRules
    from src.backend.extraction.relation_extractor import RelationExtractor
    from src.backend.extraction.llm_extractor import LLMExtractor
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

    logger.info(f"=== Stage 2: NER & Relation Extraction ===")
    ner = NERRules()
    extractor = RelationExtractor()

    # 第一遍：NER 收集所有人名
    all_persons = set()
    entry_persons = {}
    for entry in entries:
        ner_result = ner.extract_all(entry.content)
        persons_in_entry = [e.text for e in ner_result.entities if e.type == "PERSON"]
        entry_persons[entry.title] = set(persons_in_entry)
        for p in persons_in_entry:
            all_persons.add(p)
    logger.info(f"NER found {len(all_persons)} unique persons")

    # 第二遍：基于 NER 人名约束抽取关系
    all_triples = []
    for entry in entries:
        known = entry_persons.get(entry.title, set())
        rel_result = extractor.extract_from_entry(entry.content, entry.title, entry.chapter, known)
        for triple in rel_result.triples:
            all_triples.append({
                "subject": triple.subject,
                "predicate": triple.predicate,
                "object": triple.obj,
                "confidence": triple.confidence,
                "method": triple.method,
                "evidence": triple.evidence,
                "chapter": triple.chapter,
                "source_text": triple.source_text,
            })

    logger.info(f"Extracted {len(all_triples)} triples, {len(all_persons)} unique persons")

    # 合并知识库三元组（高可信度，覆盖核心人物）
    from src.backend.extraction.knowledge_base import INK_TRIPLES as KB_TRIPLES
    seen_keys = {(t["subject"], t["predicate"], t["object"]) for t in all_triples}
    for kb_t in KB_TRIPLES:
        key = (kb_t["subject"], kb_t["predicate"], kb_t["object"])
        if key not in seen_keys:
            all_triples.append(kb_t)
            seen_keys.add(key)
    logger.info(f"After knowledge base merge: {len(all_triples)} triples")

    EXTRACTED_TRIPLES.write_text(json.dumps(all_triples, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Saved triples to {EXTRACTED_TRIPLES}")

    if not skip_llm:
        logger.info(f"=== Stage 2b: LLM-assisted extraction ===")
        llm = LLMExtractor()
        for entry in entries[:20]:
            llm_triples = llm.extract(entry.content)
            for t in llm_triples:
                all_triples.append({
                    "subject": t.subject,
                    "predicate": t.predicate,
                    "object": t.obj,
                    "confidence": t.confidence,
                    "method": "llm",
                    "evidence": t.evidence,
                    "chapter": entry.chapter,
                    "source_text": entry.title,
                })
        logger.info(f"After LLM: {len(all_triples)} triples")

    logger.info(f"=== Stage 3: Build RDF Graph ===")
    writer = TurtleWriter()

    # 直接复用 Stage 2 的 NER 验证人名
    all_ner_persons = all_persons
    logger.info(f"NER validated persons: {len(all_ner_persons)}")

    # 人名对象谓词（object 应该是人名）
    PERSON_REL_PREDICATES = {
        "fatherOf", "sonOf", "teacherOf", "studentOf",
        "friendOf", "brotherOf", "inheritedFrom", "influencedBy",
    }
    # 字/号/籍贯等属性（object 是字符串，不是人名）
    ATTR_PREDICATES = {
        "styleName", "hao", "dynasty", "fromPlace",
        "appellation", "nativePlace",
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

        # subject 必须是人名
        if subj not in all_ner_persons:
            continue

        if pred in PERSON_REL_PREDICATES:
            if obj in all_ner_persons:
                person_set.add(subj)
                person_set.add(obj)
                rel_triples.append(t)
        elif pred in ATTR_PREDICATES:
            person_set.add(subj)
            attr_triples.append(t)
        elif pred in ("foundedSchool", "belongsToSchool"):
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
            predicate=t["predicate"],
            obj=t["object"],
            confidence=t.get("confidence", 0.95),
            method=t.get("method", "rule"),
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

        # Skip RDF schema class names and metadata nodes
        RDF_SCHEMA_NODES = {
            "Person", "School", "Place", "TimePeriod", "Style", "Evidence",
            "Thing", "Property", "Class", "Ontology",
        }

        nodes = []
        links = []
        seen_nodes = set()

        for node in G.nodes:
            if node in seen_nodes:
                continue
            if node in RDF_SCHEMA_NODES:
                continue
            if node.startswith("evidence/"):
                continue
            seen_nodes.add(node)
            school = next((d.get("relation", "") for _, _, d in G.out_edges(node, data=True)
                          if "School" in d.get("relation", "")), None)
            nodes.append({
                "id": node,
                "name": node,
                "type": "person",
                "school": school,
            })

        for u, v, data in G.edges(data=True):
            links.append({
                "source": u, "target": v,
                "relation": data.get("relation", "unknown"),
            })

        graph_data = {"nodes": nodes, "links": links}
        GRAPH_JSON.write_text(json.dumps(graph_data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Graph JSON saved: {GRAPH_JSON}")

        persons_data = [{"name": n} for n in sorted(p for p in person_set if p)]
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
    parser.add_argument("--skip-llm", action="store_true", help="跳过LLM抽取")
    parser.add_argument("--skip-linking", action="store_true", help="跳过实体链接")
    parser.add_argument("--skip-analysis", action="store_true", help="跳过图分析")
    parser.add_argument("--skip-rag", action="store_true", help="跳过RAG构建")
    args = parser.parse_args()

    result = run_pipeline(
        text_path=args.text,
        skip_llm=args.skip_llm,
        skip_entity_linking=args.skip_linking,
        skip_analysis=args.skip_analysis,
        skip_rag=args.skip_rag,
    )
    print(f"\n结果统计: {result}")
