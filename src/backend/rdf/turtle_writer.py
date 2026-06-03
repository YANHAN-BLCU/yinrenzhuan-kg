import logging
from pathlib import Path
from typing import List, Dict, Optional
from rdflib import Graph, URIRef, Literal, RDF, RDFS, OWL
from rdflib.namespace import NamespaceManager
from rdflib.namespace import XSD
from .ontology import (
    INK, REL, CTEXT, CBDB, EX, get_person_uri, get_school_uri,
    get_place_uri, get_evidence_uri, get_relation_uri,
    PROPERTIES_DATATYPE, PROPERTIES_OBJECT,
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
        self.graph.add((EX.RDF, OWL.Ontology, EX["ontology"]))

        Person = INK_NS.Person
        self.graph.add((Person, RDF.type, OWL.Class))
        self.graph.add((Person, RDFS.subClassOf, EX.Thing))

        for cls_name in ["Place", "TimePeriod", "School", "Style", "Work", "Artifact", "Evidence"]:
            cls = INK_NS[cls_name]
            self.graph.add((cls, RDF.type, OWL.Class))
            self.graph.add((cls, RDFS.subClassOf, EX.Thing))

        for prop_name, (domain, rng) in PROPERTIES_DATATYPE.items():
            prop = INK_NS[prop_name]
            self.graph.add((prop, RDF.type, OWL.DatatypeProperty))
            self.graph.add((prop, RDFS.domain, INK_NS[domain]))
            self.graph.add((prop, RDFS.range, XSD[rng]))

        for prop_name, (domain, rng) in PROPERTIES_OBJECT.items():
            prop = INK_NS[prop_name]
            self.graph.add((prop, RDF.type, OWL.ObjectProperty))
            self.graph.add((prop, RDFS.domain, INK_NS[domain]))
            self.graph.add((prop, RDFS.range, INK_NS[rng]))

        self.graph.add((INK_NS.fatherOf, OWL.inverseOf, INK_NS.sonOf))
        self.graph.add((INK_NS.teacherOf, OWL.inverseOf, INK_NS.studentOf))

    def add_person(
        self,
        name: str,
        style_name: Optional[str] = None,
        hao: Optional[str] = None,
        birth_year: Optional[int] = None,
        death_year: Optional[int] = None,
        native_place: Optional[str] = None,
        dynasty: Optional[str] = None,
        appellation: Optional[str] = None,
        ctext_id: Optional[str] = None,
        cbdb_id: Optional[str] = None,
    ):
        uri = get_person_uri(name)
        self.graph.add((uri, RDF.type, INK_NS.Person))
        self.graph.add((uri, INK_NS.personName, Literal(name)))

        if style_name:
            self.graph.add((uri, INK_NS.styleName, Literal(style_name)))
        if hao:
            self.graph.add((uri, INK_NS.hao, Literal(hao)))
        if birth_year:
            self.graph.add((uri, INK_NS.birthYear, Literal(birth_year, datatype=XSD.integer)))
        if death_year:
            self.graph.add((uri, INK_NS.deathYear, Literal(death_year, datatype=XSD.integer)))
        if native_place:
            self.graph.add((uri, INK_NS.nativePlace, Literal(native_place)))
        if dynasty:
            self.graph.add((uri, INK_NS.dynasty, Literal(dynasty)))
        if appellation:
            self.graph.add((uri, INK_NS.appellation, Literal(appellation)))
        if ctext_id:
            self.graph.add((uri, INK_NS.ctextId, Literal(ctext_id)))
        if cbdb_id:
            self.graph.add((uri, INK_NS.cbdbId, Literal(cbdb_id)))

    def add_school(self, name: str, period: Optional[str] = None, region: Optional[str] = None, founder: Optional[str] = None):
        uri = get_school_uri(name)
        self.graph.add((uri, RDF.type, INK_NS.School))
        self.graph.add((uri, INK_NS.schoolName, Literal(name)))
        if period:
            self.graph.add((uri, INK_NS.period, Literal(period)))
        if region:
            self.graph.add((uri, INK_NS.region, Literal(region)))
        if founder:
            self.graph.add((uri, INK_NS.founder, get_person_uri(founder)))

    def add_triple(
        self,
        subject: str,
        predicate: str,
        obj: str,
        confidence: float = 0.95,
        method: str = "rule-template",
        evidence_text: str = "",
        chapter: str = "",
    ):
        subj_uri = get_person_uri(subject)
        obj_uri = self._get_object_uri(obj, predicate)
        pred_uri = INK_NS[predicate]

        if predicate in PROPERTIES_OBJECT:
            self.graph.add((subj_uri, pred_uri, obj_uri))
        else:
            self.graph.add((subj_uri, pred_uri, Literal(obj)))

        ev_uri = get_evidence_uri(subject, predicate)
        self.graph.add((ev_uri, RDF.type, INK_NS.Evidence))
        if evidence_text:
            self.graph.add((ev_uri, INK_NS.sourceText, Literal(evidence_text)))
        self.graph.add((ev_uri, INK_NS.confidence, Literal(confidence, datatype=XSD.float)))
        self.graph.add((ev_uri, INK_NS.extractionMethod, Literal(method)))
        if chapter:
            self.graph.add((ev_uri, INK_NS.source, Literal(chapter)))
        self.graph.add((ev_uri, INK_NS.extractedBy, subj_uri))

    def _get_object_uri(self, obj: str, predicate: str) -> URIRef:
        if predicate in ["fatherOf", "sonOf", "teacherOf", "studentOf",
                          "friendOf", "brotherOf", "inheritedFrom", "influencedBy"]:
            return get_person_uri(obj)
        elif predicate in ["foundedSchool", "belongsToSchool"]:
            return get_school_uri(obj)
        elif predicate == "fromPlace":
            return get_place_uri(obj)
        else:
            return get_person_uri(obj)

    def add_same_as(self, person_name: str, ctext_uri: Optional[str] = None, cbdb_uri: Optional[str] = None):
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
        for s in self.graph.subjects(RDF.type, INK_NS.Person):
            for p in self.graph.objects(s, INK_NS.personName):
                persons.append(str(p))
        return persons
