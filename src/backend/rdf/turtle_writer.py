"""
RDF Turtle 写入器。

将抽取的知识写入标准 RDF/Turtle 格式，支持 OWL 本体约束。
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional
from rdflib import Graph, URIRef, Literal, RDF, RDFS, OWL
from rdflib.namespace import NamespaceManager
from rdflib.namespace import XSD
from .ontology import (
    INK, REL, CTEXT, CBDB, EX,
    get_person_uri, get_school_uri, get_place_uri,
    get_style_uri, get_era_uri, get_work_uri,
    get_evidence_uri, get_relation_uri,
    PROPERTIES_DATATYPE, PROPERTIES_OBJECT, CLASSES,
    normalize_predicate, get_object_uri,
)

logger = logging.getLogger(__name__)

INK_NS = INK
REL_NS = REL


class TurtleWriter:

    def __init__(self):
        self.graph = Graph()
        self._bind_namespaces()
        self._declare_ontology()

    def _bind_namespaces(self):
        nm = NamespaceManager(self.graph)
        nm.bind("ex", INK_NS)
        nm.bind("rel", REL_NS)
        nm.bind("ctext", CTEXT)
        nm.bind("cbdb", CBDB)
        nm.bind("xsd", XSD)
        nm.bind("rdfs", RDFS)
        nm.bind("owl", OWL)

    def _declare_ontology(self):
        """声明 OWL 类层次和属性约束。"""
        self.graph.add((EX.RDF, OWL.Ontology, EX["ontology"]))

        # --- 类声明 ---
        # 顶层类
        self.graph.add((EX.Thing, RDF.type, OWL.Class))

        # HistoricPerson ← Thing
        HistoricPerson = INK_NS.HistoricPerson
        self.graph.add((HistoricPerson, RDF.type, OWL.Class))
        self.graph.add((HistoricPerson, RDFS.subClassOf, EX.Thing))

        # SealEngravingSchool ← Thing
        School = INK_NS.SealEngravingSchool
        self.graph.add((School, RDF.type, OWL.Class))
        self.graph.add((School, RDFS.subClassOf, EX.Thing))

        # CalligraphyStyle ← Thing
        Style = INK_NS.CalligraphyStyle
        self.graph.add((Style, RDF.type, OWL.Class))
        self.graph.add((Style, RDFS.subClassOf, EX.Thing))

        # Location ← Thing
        Location = INK_NS.Location
        self.graph.add((Location, RDF.type, OWL.Class))
        self.graph.add((Location, RDFS.subClassOf, EX.Thing))

        # Era ← Thing
        Era = INK_NS.Era
        self.graph.add((Era, RDF.type, OWL.Class))
        self.graph.add((Era, RDFS.subClassOf, EX.Thing))

        # SealWork ← Thing
        Work = INK_NS.SealWork
        self.graph.add((Work, RDF.type, OWL.Class))
        self.graph.add((Work, RDFS.subClassOf, EX.Thing))

        # Evidence ← Thing
        Evidence = INK_NS.Evidence
        self.graph.add((Evidence, RDF.type, OWL.Class))
        self.graph.add((Evidence, RDFS.subClassOf, EX.Thing))

        # 兼容旧类名
        for cls_name in ["Place", "TimePeriod", "Style", "Work"]:
            cls = INK_NS[cls_name]
            self.graph.add((cls, RDF.type, OWL.Class))
            self.graph.add((cls, RDFS.subClassOf, EX.Thing))

        # --- 数据属性声明 ---
        for prop_name, (domain, rng) in PROPERTIES_DATATYPE.items():
            prop = INK_NS[prop_name]
            self.graph.add((prop, RDF.type, OWL.DatatypeProperty))
            domain_cls = INK_NS[domain] if domain != "Thing" else EX.Thing
            self.graph.add((prop, RDFS.domain, domain_cls))
            xsd_rng = XSD[rng] if rng in {"string", "integer", "float", "dateTime", "boolean"} else XSD.string
            self.graph.add((prop, RDFS.range, xsd_rng))

        # --- 对象属性声明 ---
        for prop_name, (domain, rng) in PROPERTIES_OBJECT.items():
            prop = INK_NS[prop_name]
            self.graph.add((prop, RDF.type, OWL.ObjectProperty))
            domain_cls = INK_NS[domain] if domain in CLASSES else EX.Thing
            range_cls = INK_NS[rng] if rng in CLASSES else EX.Thing
            self.graph.add((prop, RDFS.domain, domain_cls))
            self.graph.add((prop, RDFS.range, range_cls))

        # --- 逆属性声明 ---
        self.graph.add((INK_NS.hasFather, OWL.inverseOf, INK_NS.hasSon))
        self.graph.add((INK_NS.hasTeacher, OWL.inverseOf, INK_NS.hasStudent))
        self.graph.add((INK_NS.hasFounder, OWL.inverseOf, INK_NS.hasMember))

        # --- 属性链 ---
        # 如果 A hasTeacher B，B hasTeacher C，则 A hasStudent C（传递性近似）
        # 通过直接关系支持路径查询实现

    # ============================================================
    # 实体写入方法
    # ============================================================

    def add_person(
        self,
        name: str,
        style_name: Optional[str] = None,
        hao: Optional[str] = None,
        birth_year: Optional[int] = None,
        death_year: Optional[int] = None,
        native_place: Optional[str] = None,
        dynasty: Optional[str] = None,
        occupation: Optional[str] = None,
        official_rank: Optional[str] = None,
        appellation: Optional[str] = None,
        biography: Optional[str] = None,
        masterpiece: Optional[str] = None,
        style_description: Optional[str] = None,
        ctext_id: Optional[str] = None,
        cbdb_id: Optional[str] = None,
    ):
        uri = get_person_uri(name)
        self.graph.add((uri, RDF.type, INK_NS.HistoricPerson))
        self.graph.add((uri, INK_NS.personName, Literal(name)))

        if style_name:
            self.graph.add((uri, INK_NS.styleName, Literal(style_name)))
        if hao:
            self.graph.add((uri, INK_NS.hao, Literal(hao)))
        if birth_year:
            self.graph.add((uri, INK_NS.birthYear, Literal(int(birth_year), datatype=XSD.integer)))
        if death_year:
            self.graph.add((uri, INK_NS.deathYear, Literal(int(death_year), datatype=XSD.integer)))
        if native_place:
            self.graph.add((uri, INK_NS.nativePlace, Literal(native_place)))
        if dynasty:
            self.graph.add((uri, INK_NS.dynasty, Literal(dynasty)))
        if occupation:
            self.graph.add((uri, INK_NS.occupation, Literal(occupation)))
        if official_rank:
            self.graph.add((uri, INK_NS.officialRank, Literal(official_rank)))
        if appellation:
            self.graph.add((uri, INK_NS.appellation, Literal(appellation)))
        if biography:
            self.graph.add((uri, INK_NS.biography, Literal(biography)))
        if masterpiece:
            self.graph.add((uri, INK_NS.masterpiece, Literal(masterpiece)))
        if style_description:
            self.graph.add((uri, INK_NS.styleDescription, Literal(style_description)))
        if ctext_id:
            self.graph.add((uri, INK_NS.ctextId, Literal(ctext_id)))
        if cbdb_id:
            self.graph.add((uri, INK_NS.cbdbId, Literal(cbdb_id)))

    def add_school(
        self,
        name: str,
        period: Optional[str] = None,
        region: Optional[str] = None,
        founder: Optional[str] = None,
        description: Optional[str] = None,
    ):
        uri = get_school_uri(name)
        self.graph.add((uri, RDF.type, INK_NS.SealEngravingSchool))
        self.graph.add((uri, INK_NS.schoolName, Literal(name)))
        if period:
            self.graph.add((uri, INK_NS.period, Literal(period)))
        if region:
            self.graph.add((uri, INK_NS.region, Literal(region)))
        if founder:
            self.graph.add((uri, INK_NS.founder, Literal(founder)))
            self.graph.add((get_person_uri(founder), INK_NS.foundedSchool, uri))
        if description:
            self.graph.add((uri, INK_NS.description, Literal(description)))

    def add_style(
        self,
        name: str,
        description: Optional[str] = None,
    ):
        uri = get_style_uri(name)
        self.graph.add((uri, RDF.type, INK_NS.CalligraphyStyle))
        self.graph.add((uri, INK_NS.styleName, Literal(name)))
        if description:
            self.graph.add((uri, INK_NS.styleDescription, Literal(description)))

    def add_place(
        self,
        name: str,
        place_type: Optional[str] = None,
    ):
        uri = get_place_uri(name)
        self.graph.add((uri, RDF.type, INK_NS.Location))
        self.graph.add((uri, INK_NS.placeName, Literal(name)))
        if place_type:
            self.graph.add((uri, INK_NS.placeType, Literal(place_type)))

    def add_era(
        self,
        name: str,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ):
        uri = get_era_uri(name)
        self.graph.add((uri, RDF.type, INK_NS.Era))
        self.graph.add((uri, INK_NS.periodName, Literal(name)))
        if start_year:
            self.graph.add((uri, INK_NS.startYear, Literal(int(start_year), datatype=XSD.integer)))
        if end_year:
            self.graph.add((uri, INK_NS.endYear, Literal(int(end_year), datatype=XSD.integer)))

    def add_work(
        self,
        name: str,
        creator: Optional[str] = None,
        creation_period: Optional[str] = None,
        material: Optional[str] = None,
    ):
        uri = get_work_uri(name)
        self.graph.add((uri, RDF.type, INK_NS.SealWork))
        self.graph.add((uri, INK_NS.workTitle, Literal(name)))
        if creator:
            self.graph.add((uri, RDF.type, INK_NS.SealWork))
            self.graph.add((get_person_uri(creator), INK_NS.createdWork, uri))
        if creation_period:
            self.graph.add((uri, INK_NS.creationPeriod, Literal(creation_period)))
        if material:
            self.graph.add((uri, INK_NS.material, Literal(material)))

    def add_triple(
        self,
        subject: str,
        predicate: str,
        obj: str,
        confidence: float = 0.95,
        method: str = "llm",
        evidence_text: str = "",
        chapter: str = "",
    ):
        """写入带证据元数据的三元组。"""
        subj_uri = get_person_uri(subject)
        pred_rdf = normalize_predicate(predicate)
        pred_uri = INK_NS[pred_rdf]
        obj_uri = get_object_uri(obj, predicate)

        if pred_rdf in PROPERTIES_OBJECT:
            self.graph.add((subj_uri, pred_uri, obj_uri))
        else:
            self.graph.add((subj_uri, pred_uri, Literal(obj)))

        # 证据节点
        ev_uri = get_evidence_uri(subject, predicate)
        self.graph.add((ev_uri, RDF.type, INK_NS.Evidence))
        if evidence_text:
            self.graph.add((ev_uri, INK_NS.sourceText, Literal(evidence_text)))
        self.graph.add((ev_uri, INK_NS.confidence, Literal(float(confidence), datatype=XSD.float)))
        self.graph.add((ev_uri, INK_NS.extractionMethod, Literal(method)))
        if chapter:
            self.graph.add((ev_uri, INK_NS.source, Literal(chapter)))
        self.graph.add((ev_uri, INK_NS.extractedBy, subj_uri))

    def add_relationship(
        self,
        subject: str,
        predicate: str,
        obj: str,
        confidence: float = 0.90,
        method: str = "llm",
        evidence_text: str = "",
        chapter: str = "",
    ):
        """专门写入人物间关系（师承/亲属/交游），带证据。"""
        self.add_triple(subject, predicate, obj, confidence, method, evidence_text, chapter)

    def add_same_as(self, person_name: str,
                    ctext_uri: Optional[str] = None, cbdb_uri: Optional[str] = None):
        person_uri = get_person_uri(person_name)
        if ctext_uri:
            self.graph.add((person_uri, OWL.sameAs, URIRef(ctext_uri)))
        if cbdb_uri:
            self.graph.add((person_uri, OWL.sameAs, URIRef(cbdb_uri)))

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.graph.serialize(destination=str(path), format="turtle")
        logger.info(f"Saved RDF graph to {path} ({len(self.graph)} triples)")

    def get_graph(self) -> Graph:
        return self.graph

    def get_all_persons(self) -> List[str]:
        persons = []
        for s in self.graph.subjects(RDF.type, INK_NS.HistoricPerson):
            for p in self.graph.objects(s, INK_NS.personName):
                persons.append(str(p))
        return persons
