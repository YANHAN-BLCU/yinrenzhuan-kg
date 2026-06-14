import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import NamespaceManager
from rdflib.namespace import RDF, RDFS, OWL
from .ontology import INK as INK_NS, get_person_uri, get_school_uri, normalize_predicate

logger = logging.getLogger(__name__)


class RDFStore:
    PERSON_TYPE = INK_NS.HistoricPerson


class RDFStore:
    def __init__(self, graph: Optional[Graph] = None):
        self.graph = graph or Graph()

    def load(self, path: Path) -> "RDFStore":
        self.graph.parse(str(path), format="turtle")
        logger.info(f"Loaded graph from {path}: {len(self.graph)} triples")
        return self

    def save(self, path: Path):
        self.graph.serialize(destination=str(path), format="turtle")
        logger.info(f"Saved graph to {path}")

    def get_person_info(self, name: str) -> Dict[str, Any]:
        info = {
            "person_name": name, "style_name": None, "hao": None,
            "birth_year": None, "death_year": None, "native_place": None,
            "dynasty": None, "occupation": None, "official_rank": None,
            "biography": None, "masterpiece": None, "style_description": None,
            "schools": [], "relations": [],
        }

        uri = get_person_uri(name)
        for p, o in self.graph.predicate_objects(uri):
            p_local = str(p).split("/")[-1]
            if p_local == "personName":
                continue
            elif p_local == "styleName":
                info["style_name"] = str(o)
            elif p_local == "hao":
                info["hao"] = str(o)
            elif p_local == "birthYear":
                info["birth_year"] = int(o)
            elif p_local == "deathYear":
                info["death_year"] = int(o)
            elif p_local == "nativePlace":
                info["native_place"] = str(o)
            elif p_local == "dynasty":
                info["dynasty"] = str(o)
            elif p_local == "occupation":
                info["occupation"] = str(o)
            elif p_local == "officialRank":
                info["official_rank"] = str(o)
            elif p_local == "biography":
                info["biography"] = str(o)
            elif p_local == "masterpiece":
                info["masterpiece"] = str(o)
            elif p_local == "styleDescription":
                info["style_description"] = str(o)
            elif p_local in ("foundedSchool", "belongsToSchool",
                             "hasFounder", "hasMember"):
                school_name = self._get_school_name(o)
                if school_name and school_name not in info["schools"]:
                    info["schools"].append(school_name)
            elif p_local in ("hasFather", "hasSon", "hasTeacher", "hasStudent",
                             "hasFriend", "hasAncestor", "hasDescendant",
                             "influencedBy", "inheritedFrom"):
                target_name = self._get_person_name(o)
                if target_name:
                    info["relations"].append({"type": p_local, "target": target_name})
        return info

    def _get_school_name(self, uri: URIRef) -> Optional[str]:
        for o in self.graph.objects(uri, INK_NS.schoolName):
            return str(o)
        return None

    def _get_person_name(self, uri: URIRef) -> Optional[str]:
        for o in self.graph.objects(uri, INK_NS.personName):
            return str(o)
        return None

    def query_sparql(self, sparql: str) -> List[Dict[str, Any]]:
        try:
            results = self.graph.query(sparql)
            rows = []
            for row in results:
                row_dict = {}
                for var in results.vars:
                    val = getattr(row, str(var))
                    if val:
                        row_dict[str(var)] = self._localize(val)
                rows.append(row_dict)
            return rows
        except Exception as e:
            logger.error(f"SPARQL query failed: {e}")
            return []

    def _localize(self, val) -> str:
        """把 URI 解析为友好名称（人名/流派名），否则返回 str(val)。"""
        s = str(val)
        if not s.startswith("http://") and not s.startswith("https://"):
            return s
        # URI → 查 personName / schoolName
        try:
            from rdflib import URIRef
            for predicate, attr in (
                ("personName", "personName"),
                ("schoolName", "schoolName"),
            ):
                # predicate 用完整 URI
                full_pred = f"http://example.org/inkperson/{predicate}"
                for o in self.graph.objects(URIRef(s), URIRef(full_pred)):
                    return str(o)
        except Exception:
            pass
        return s

    def get_relations(self, name: str, relation_types: Optional[List[str]] = None) -> Dict[str, Any]:
        info = self.get_person_info(name)
        if relation_types:
            info["relations"] = [r for r in info["relations"] if r["type"] in relation_types]
        return info

    def get_all_persons(self) -> List[str]:
        persons = []
        seen = set()
        for uri in self.graph.subjects(RDF.type, INK_NS.HistoricPerson):
            for name_obj in self.graph.objects(uri, INK_NS.personName):
                name = str(name_obj)
                if name not in seen:
                    seen.add(name)
                    persons.append(name)
        return persons

    def get_school_members(self, school_name: str) -> List[Dict[str, Any]]:
        results = self.query_sparql(f"""
PREFIX ex: <http://example.org/inkperson/>
SELECT DISTINCT ?name WHERE {{
  {{
    ?person ex:belongsToSchool ?school .
  }} UNION {{
    ?person ex:foundedSchool ?school .
  }}
  ?school ex:schoolName "{school_name}" .
  ?person ex:personName ?name .
}}""")
        return [{"name": r["name"]} for r in results]

    def get_all_schools(self) -> List[Dict[str, str]]:
        """返回所有流派节点：{name, region?, period?}。"""
        seen = set()
        out = []
        for s, _, _ in self.graph.triples((None, RDF.type, INK_NS.SealEngravingSchool)):
            name = self._get_school_name(s)
            if not name or name in seen:
                continue
            seen.add(name)
            region = None
            period = None
            for _, p, o in self.graph.triples((s, None, None)):
                pl = str(p).split("/")[-1]
                if pl == "region" and o:
                    region = str(o)
                elif pl == "period" and o:
                    period = str(o)
            out.append({"name": name, "region": region, "period": period})
        return out

    def get_graph_view(self) -> Dict[str, Any]:
        """导出前端图谱视图：{nodes, links}。"""
        G = self.as_networkx_full()
        nodes = []
        for n in G.nodes:
            nt = G.nodes[n].get("node_type", "unknown")
            disp = n.replace("school/", "") if nt == "school" else n
            school = None
            if nt == "person":
                school = next(
                    (d.get("relation", "") for _, _, d in G.out_edges(n, data=True)
                     if "School" in d.get("relation", "")),
                    None,
                )
            nodes.append({"id": n, "name": disp, "type": nt, "school": school})
        links = [
            {"source": u, "target": v, "relation": d.get("relation", "unknown")}
            for u, v, d in G.edges(data=True)
        ]
        return {"nodes": nodes, "links": links}

    def to_networkx(self):
        """导出为 NetworkX 图，供 centrality/community 算法使用。"""
        return self.as_networkx_full()

    def find_path(self, person_a: str, person_b: str, max_depth: int = 5) -> Optional[List[str]]:
        try:
            import networkx as nx
            G = nx.DiGraph()
            for s, p, o in self.graph:
                s_local = self._uri_to_name(str(s))
                o_local = self._uri_to_name(str(o))
                if s_local and o_local:
                    rel = str(p).split("/")[-1]
                    G.add_edge(s_local, o_local, relation=rel)
            path = nx.shortest_path(G, person_a, person_b, cutoff=max_depth)
            return path
        except Exception:
            return None

    def _uri_to_name(self, uri_str: str) -> Optional[str]:
        if "person/" in uri_str:
            name = uri_str.split("person/")[-1].replace("_", " ")
            return name
        if "school/" in uri_str:
            name = uri_str.split("school/")[-1].replace("_", " ")
            return name
        return None

    def as_networkx(self):
        """Convert RDF graph to NetworkX DiGraph."""
        import networkx as nx
        G = nx.DiGraph()
        for s, p, o in self.graph:
            s_str, o_str = str(s), str(o)
            p_str = str(p)
            if "#" in p_str:
                continue
            rel = p_str.split("/")[-1]
            if rel in ("extractedBy", "source", "extractionMethod",
                       "confidence", "dataSource", "personName", "schoolName"):
                continue
            ink_ns = str(INK_NS)
            if ink_ns not in s_str:
                continue
            s_name = self._uri_to_name(s_str)
            o_name = self._uri_to_name(o_str)
            if s_name and o_name and s_name != o_name:
                G.add_edge(s_name, o_name, relation=rel)
        return G

    def as_networkx_full(self):
        """Return NetworkX graph with node_type attribute (person/school/place/style)."""
        import networkx as nx
        G = nx.DiGraph()
        for s, p, o in self.graph:
            s_str, o_str = str(s), str(o)
            p_str = str(p)
            if "#" in p_str:
                continue
            rel = p_str.split("/")[-1]
            if rel in ("extractedBy", "source", "extractionMethod",
                       "confidence", "dataSource", "personName", "schoolName"):
                continue
            ink_ns = str(INK_NS)
            if ink_ns not in s_str:
                continue
            s_type = self._uri_to_node_type(s_str)
            o_type = self._uri_to_node_type(o_str)
            s_name = self._uri_to_name(s_str)
            o_name = self._uri_to_name(o_str)
            if s_name and o_name and s_name != o_name:
                G.add_edge(s_name, o_name, relation=rel)
                G.nodes[s_name]["node_type"] = s_type
                G.nodes[o_name]["node_type"] = o_type
        return G

    def _uri_to_node_type(self, uri_str: str) -> str:
        """Return node type based on URI path segment."""
        if "school/" in uri_str:
            return "school"
        if "person/" in uri_str:
            return "person"
        if "place/" in uri_str:
            return "place"
        if "style/" in uri_str:
            return "style"
        if "era/" in uri_str:
            return "era"
        return "unknown"
