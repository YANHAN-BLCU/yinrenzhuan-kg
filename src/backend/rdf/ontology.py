from rdflib import Namespace, Graph, URIRef, Literal, RDF, RDFS, OWL, Namespace
from rdflib.namespace import NamespaceManager

INK = Namespace("http://example.org/inkperson/")
REL = Namespace("http://example.org/inkperson/relation/")
CTEXT = Namespace("http://example.org/ctext/")
CBDB = Namespace("http://example.org/cbdb/")

CLASSES = {
    "Thing": OWL.Class,
    "Person": None,
    "Place": None,
    "TimePeriod": None,
    "School": None,
    "Style": None,
    "Work": None,
    "Artifact": None,
    "Evidence": None,
    "Relation": OWL.ObjectProperty,
}

PROPERTIES_DATATYPE = {
    "personName": ("Person", "string"),
    "styleName": ("Person", "string"),
    "hao": ("Person", "string"),
    "birthYear": ("Person", "integer"),
    "deathYear": ("Person", "integer"),
    "birthYearString": ("Person", "string"),
    "deathYearString": ("Person", "string"),
    "nativePlace": ("Person", "string"),
    "dynasty": ("Person", "string"),
    "occupation": ("Person", "string"),
    "officialRank": ("Person", "string"),
    "confidence": ("Thing", "float"),
    "sourceText": ("Evidence", "string"),
    "extractionMethod": ("Evidence", "string"),
    "dataSource": ("Thing", "string"),
    "schoolName": ("School", "string"),
    "period": ("School", "string"),
    "region": ("School", "string"),
    "placeName": ("Place", "string"),
    "periodName": ("TimePeriod", "string"),
    "appellation": ("Person", "string"),
}

PROPERTIES_OBJECT = {
    "fatherOf": ("Person", "Person"),
    "sonOf": ("Person", "Person"),
    "teacherOf": ("Person", "Person"),
    "studentOf": ("Person", "Person"),
    "friendOf": ("Person", "Person"),
    "brotherOf": ("Person", "Person"),
    "foundedSchool": ("Person", "School"),
    "belongsToSchool": ("Person", "School"),
    "inheritedFrom": ("Person", "Person"),
    "influencedBy": ("Person", "Person"),
    "fromPlace": ("Person", "Place"),
    "hasPeriod": ("Person", "TimePeriod"),
    "hasStyle": ("Person", "Style"),
    "sameAs": ("Thing", "Thing"),
    "ctextId": ("Person", "string"),
    "cbdbId": ("Person", "string"),
    "extractedBy": ("Evidence", "Person"),
    "source": ("Evidence", "Thing"),
}

EX = INK
REL_NS = REL


def get_person_uri(name: str) -> URIRef:
    if not name:
        return EX["unknown"]
    key = name.strip().replace(" ", "_")
    return EX[f"person/{key}"]


def get_school_uri(name: str) -> URIRef:
    if not name:
        return EX["unknown_school"]
    key = name.strip().replace(" ", "_")
    return EX[f"school/{key}"]


def get_place_uri(name: str) -> URIRef:
    if not name:
        return EX["unknown_place"]
    key = name.strip().replace(" ", "_")
    return EX[f"place/{key}"]


def get_evidence_uri(subject: str, predicate: str) -> URIRef:
    key = f"{subject}_{predicate}".strip().replace(" ", "_")
    return EX[f"evidence/{key}"]


def get_relation_uri(predicate: str) -> URIRef:
    return REL_NS[predicate]
