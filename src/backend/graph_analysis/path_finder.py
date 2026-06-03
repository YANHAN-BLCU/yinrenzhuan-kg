import logging
from typing import Dict, List, Optional, Any
import networkx as nx

logger = logging.getLogger(__name__)


class PathFinder:

    def __init__(self, graph: Optional[nx.DiGraph] = None):
        self.graph = graph

    def set_graph(self, graph: nx.DiGraph):
        self.graph = graph

    def shortest_path(self, source: str, target: str,
                     relation_types: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        if not self.graph:
            raise ValueError("Graph not set")

        if source not in self.graph or target not in self.graph:
            logger.warning(f"Node not found: {source} or {target}")
            return None

        if relation_types:
            filtered = self._filter_by_relation_types(relation_types)
        else:
            filtered = self.graph

        try:
            path = nx.shortest_path(filtered, source, target)
            edges_data = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                rel = filtered[u][v].get("relation", "unknown")
                edges_data.append({
                    "from": u, "to": v, "relation": rel
                })
            return {
                "path": path,
                "edges": edges_data,
                "length": len(path) - 1,
                "description": self._format_path_description(edges_data),
            }
        except nx.NetworkXNoPath:
            return None
        except nx.NodeNotFound:
            return None

    def all_paths(self, source: str, target: str, max_length: int = 4) -> List[Dict[str, Any]]:
        if not self.graph:
            raise ValueError("Graph not set")
        if source not in self.graph or target not in self.graph:
            return []

        all_p = list(nx.all_simple_paths(self.graph, source, target, cutoff=max_length))
        results = []
        for path in all_p:
            edges_data = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                rel = self.graph[u][v].get("relation", "unknown")
                edges_data.append({"from": u, "to": v, "relation": rel})
            results.append({
                "path": path,
                "edges": edges_data,
                "length": len(path) - 1,
                "description": self._format_path_description(edges_data),
            })
        results.sort(key=lambda x: x["length"])
        return results

    def find_teacher_lineage(self, person: str, max_depth: int = 6) -> List[Dict[str, Any]]:
        if not self.graph:
            raise ValueError("Graph not set")
        if person not in self.graph:
            return []

        lineage = []
        queue = [(person, 0, [])]
        visited = {person}

        while queue:
            current, depth, ancestors = queue.pop(0)
            if depth > max_depth:
                continue

            teachers = list(self.graph.predecessors(current))
            for teacher in teachers:
                if teacher in visited:
                    continue
                visited.add(teacher)
                rel = self.graph[teacher][current].get("relation", "")
                entry = {
                    "teacher": teacher,
                    "student": current,
                    "depth": depth + 1,
                    "relation": rel,
                    "ancestors": ancestors + [teacher],
                }
                lineage.append(entry)
                queue.append((teacher, depth + 1, ancestors + [teacher]))

        lineage.sort(key=lambda x: x["depth"])
        return lineage

    def school_evolution(self, school: str, school_members: Dict[str, List[str]]) -> Dict[str, Any]:
        if school not in school_members:
            return {}

        members = school_members[school]
        period_map: Dict[str, List[str]] = {}

        for member in members:
            if member in self.graph:
                for _, successor, data in self.graph.out_edges(member, data=True):
                    rel = data.get("relation", "")
                    if "School" in rel or "派" in rel:
                        successor_school = self._infer_school_from_name(successor)
                        if successor_school and successor_school != school:
                            period_map.setdefault(successor_school, []).append(member)

        return {
            "source_school": school,
            "influenced_schools": {
                s: {"members": m, "count": len(m)}
                for s, m in period_map.items()
            }
        }

    def _filter_by_relation_types(self, relation_types: List[str]) -> nx.DiGraph:
        filtered = nx.DiGraph()
        for u, v, data in self.graph.edges(data=True):
            rel = data.get("relation", "")
            if any(rt in rel for rt in relation_types):
                filtered.add_edge(u, v, **data)
        return filtered

    def _format_path_description(self, edges: List[Dict[str, str]]) -> str:
        if not edges:
            return ""
        parts = []
        for e in edges:
            rel_map = {
                "fatherOf": "为父", "sonOf": "为子",
                "teacherOf": "教授", "studentOf": "师从",
                "friendOf": "交往", "brotherOf": "为兄弟",
                "belongsToSchool": "属于", "foundedSchool": "开创",
                "inheritedFrom": "继承", "influencedBy": "受其影响",
            }
            rel_desc = rel_map.get(e["relation"], e["relation"])
            parts.append(f"{e['from']}({rel_desc})→{e['to']}")
        return " → ".join(parts)

    def _infer_school_from_name(self, name: str) -> Optional[str]:
        school_keywords = {
            "浙派": ["錢塘", "杭州"],
            "皖派": ["婺源", "徽州", "新安"],
            "吳門印派": ["蘇州", "吳門"],
            "漳海派": ["漳浦"],
        }
        for school, keywords in school_keywords.items():
            if any(kw in name for kw in keywords):
                return school
        return None
