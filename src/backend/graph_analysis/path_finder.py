"""
路径发现与流派演化分析模块。

提供：
- 两人之间的最短路径查询
- 师承脉络追溯
- 流派传承树构建与演化分析
"""
import logging
from typing import Dict, List, Optional, Any
import networkx as nx

logger = logging.getLogger(__name__)


# 关系谓词 → 中文描述
REL_CHINESE: Dict[str, str] = {
    # 师承
    "hasTeacher": "教授",
    "hasStudent": "师从",
    "teacherOf": "教授",
    "studentOf": "师从",
    "inheritedFrom": "继承",
    # 亲属
    "hasFather": "为父",
    "hasSon": "为子",
    "fatherOf": "为父",
    "sonOf": "为子",
    "hasAncestor": "为先祖",
    "hasDescendant": "为后裔",
    # 交游
    "hasFriend": "交往",
    "friendOf": "交往",
    "influencedBy": "受其影响",
    # 流派
    "hasFounder": "开创",
    "foundedSchool": "开创",
    "belongsToSchool": "隶属",
    "hasMember": "成员",
    # 属性
    "belongsTo": "属于",
    "locatedIn": "位于",
    "nativePlace": "籍贯",
}

# 流派关键词（用于从节点名推断流派）
SCHOOL_KEYWORDS: Dict[str, List[str]] = {
    "浙派": ["浙", "錢塘", "杭州"],
    "皖派": ["皖", "婺源", "徽州", "新安", "休寧"],
    "吳門印派": ["吳門", "蘇州"],
    "吳門": ["吳門", "蘇州"],
    "漳海派": ["漳海", "漳浦"],
    "莆田派": ["莆田", "福州"],
    "婁東派": ["婁東", "婁東"],
    "文人篆刻": [],
    "秦漢印風": ["秦漢"],
}

# 流派地域映射
SCHOOL_REGIONS: Dict[str, str] = {
    "浙派": "錢塘（杭州）",
    "皖派": "徽州（安徽）",
    "吳門印派": "蘇州",
    "漳海派": "漳浦（福建）",
    "莆田派": "莆田（福建）",
    "婁東派": "婁東",
}


class PathFinder:

    def __init__(self, graph: Optional[nx.DiGraph] = None):
        self.graph = graph

    def set_graph(self, graph: nx.DiGraph):
        self.graph = graph

    # ============================================================
    # 路径查询
    # ============================================================

    def shortest_path(self, source: str, target: str,
                      relation_types: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """查询两人之间的最短关系路径。"""
        if not self.graph:
            raise ValueError("Graph not set")

        if source not in self.graph or target not in self.graph:
            logger.warning(f"Node not found: {source} or {target}")
            return None

        filtered = self._filter_by_relation_types(relation_types) if relation_types else self.graph

        try:
            path = nx.shortest_path(filtered, source, target)
            edges_data = self._edges_along_path(path, filtered)
            return {
                "source": source,
                "target": target,
                "path": path,
                "edges": edges_data,
                "length": len(path) - 1,
                "description": self._format_path(edges_data),
            }
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def all_paths(self, source: str, target: str, max_length: int = 4) -> List[Dict[str, Any]]:
        """查询两人之间的所有可达路径（限制最大长度）。"""
        if not self.graph:
            raise ValueError("Graph not set")
        if source not in self.graph or target not in self.graph:
            return []

        all_p = list(nx.all_simple_paths(self.graph, source, target, cutoff=max_length))
        results = []
        for path in all_p:
            edges_data = self._edges_along_path(path, self.graph)
            results.append({
                "path": path,
                "edges": edges_data,
                "length": len(path) - 1,
                "description": self._format_path(edges_data),
            })
        results.sort(key=lambda x: x["length"])
        return results

    # ============================================================
    # 师承脉络追溯
    # ============================================================

    def find_teacher_lineage(self, person: str, max_depth: int = 6) -> List[Dict[str, Any]]:
        """追溯某人的师承祖先链（BFS）。"""
        if not self.graph:
            raise ValueError("Graph not set")
        if person not in self.graph:
            return []

        TEACHER_RELS = {"hasTeacher", "teacherOf", "inheritedFrom"}
        lineage = []
        queue = [(person, 0, [])]
        visited = {person}

        while queue:
            current, depth, ancestors = queue.pop(0)
            if depth > max_depth:
                continue

            for teacher in self.graph.predecessors(current):
                if teacher in visited:
                    continue
                visited.add(teacher)
                rel = self.graph[teacher][current].get("relation", "")
                entry = {
                    "teacher": teacher,
                    "student": current,
                    "depth": depth + 1,
                    "relation": rel,
                    "relation_label": REL_CHINESE.get(rel, rel),
                    "ancestors": ancestors + [teacher],
                }
                lineage.append(entry)
                queue.append((teacher, depth + 1, ancestors + [teacher]))

        lineage.sort(key=lambda x: x["depth"])
        return lineage

    def find_student_lineage(self, person: str, max_depth: int = 6) -> List[Dict[str, Any]]:
        """追溯某人的弟子传承链（BFS）。"""
        if not self.graph:
            raise ValueError("Graph not set")
        if person not in self.graph:
            return []

        STUDENT_RELS = {"hasStudent", "studentOf"}
        lineage = []
        queue = [(person, 0, [])]
        visited = {person}

        while queue:
            current, depth, descendants = queue.pop(0)
            if depth > max_depth:
                continue

            for student in self.graph.successors(current):
                if student in visited:
                    continue
                visited.add(student)
                rel = self.graph[current][student].get("relation", "")
                entry = {
                    "teacher": current,
                    "student": student,
                    "depth": depth + 1,
                    "relation": rel,
                    "relation_label": REL_CHINESE.get(rel, rel),
                    "descendants": descendants + [student],
                }
                lineage.append(entry)
                queue.append((student, depth + 1, descendants + [student]))

        lineage.sort(key=lambda x: x["depth"])
        return lineage

    # ============================================================
    # 流派演化分析
    # ============================================================

    def school_evolution(self, school: str, school_members: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        分析某流派的演化脉络。

        构建流派传承树：找出该流派如何通过人物影响到其他流派，
        以及该流派内部的师承代际分布。
        """
        if not self.graph:
            return {}

        members = school_members.get(school, [])
        evolution: Dict[str, Any] = {
            "school": school,
            "region": SCHOOL_REGIONS.get(school, ""),
            "generation_map": self._build_generation_map(members),
            "influence_chains": [],
            "cross_school_connections": [],
        }

        if not members:
            return evolution

        for member in members:
            if member not in self.graph:
                continue

            for _, successor, data in self.graph.out_edges(member, data=True):
                rel = data.get("relation", "")
                succ_school = self._infer_school(successor)
                if succ_school and succ_school != school:
                    evolution["cross_school_connections"].append({
                        "from": member,
                        "to": successor,
                        "target_school": succ_school,
                        "relation": rel,
                        "relation_label": REL_CHINESE.get(rel, rel),
                    })

        evolution["cross_school_connections"].sort(key=lambda x: x["depth"] if "depth" in x else 0)
        return evolution

    def build_evolution_tree(self, schools: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        构建所有流派的演化树。

        基于流派成员之间的师承关系，推断流派间的传承方向：
        如果流派A的成员是流派B成员的老师，则A可能影响了B。
        """
        if not self.graph:
            return {}

        school_influence: Dict[str, Dict[str, List[str]]] = {}
        for school, members in schools.items():
            school_influence[school] = {"influences": {}, "influenced_by": {}}

        for school_a, members_a in schools.items():
            for member_a in members_a:
                if member_a not in self.graph:
                    continue
                for _, successor, data in self.graph.out_edges(member_a, data=True):
                    succ_school = self._infer_school(successor)
                    if succ_school and succ_school != school_a:
                        if succ_school not in school_influence[school_a]["influences"]:
                            school_influence[school_a]["influences"][succ_school] = []
                        school_influence[school_a]["influences"][succ_school].append({
                            "from_person": member_a,
                            "to_person": successor,
                        })
                        if school_a not in school_influence[succ_school]["influenced_by"]:
                            school_influence[succ_school]["influenced_by"][school_a] = []
                        school_influence[succ_school]["influenced_by"][school_a].append({
                            "from_person": member_a,
                            "to_person": successor,
                        })

        return {
            "schools": list(schools.keys()),
        }

    def evolution_analysis(self, schools: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        综合流派演化分析（供前端可视化使用）。

        输出：
        - 各流派代际分布（开创者、第1代、第2代……）
        - 流派间影响关系（谁影响了谁）
        - 关键传承人物（同时连接多个流派）
        """
        if not self.graph:
            return {}

        analysis: Dict[str, Any] = {
            "school_generations": {},
            "school_influence": {},
            "key_bridges": [],
        }

        for school, members in schools.items():
            analysis["school_generations"][school] = self._build_generation_map(members)

        for school_a, members_a in schools.items():
            for member_a in members_a:
                if member_a not in self.graph:
                    continue
                for _, successor, data in self.graph.out_edges(member_a, data=True):
                    rel = data.get("relation", "")
                    succ_school = self._infer_school(successor)
                    if succ_school and succ_school != school_a:
                        if school_a not in analysis["school_influence"]:
                            analysis["school_influence"][school_a] = {}
                        if succ_school not in analysis["school_influence"][school_a]:
                            analysis["school_influence"][school_a][succ_school] = []
                        analysis["school_influence"][school_a][succ_school].append({
                            "bridge_person": member_a,
                            "target_person": successor,
                            "relation": REL_CHINESE.get(rel, rel),
                        })
                        if member_a not in [b["name"] for b in analysis.get("key_bridges", [])]:
                            bridges = analysis.get("key_bridges", [])
                            bridges.append({
                                "name": member_a,
                                "schools": [school_a, succ_school],
                                "role": "bridge",
                            })
                            analysis["key_bridges"] = bridges

        return analysis

    # ============================================================
    # 辅助方法
    # ============================================================

    def _filter_by_relation_types(self, relation_types: List[str]) -> nx.DiGraph:
        """根据关系类型过滤子图。"""
        filtered = nx.DiGraph()
        for u, v, data in self.graph.edges(data=True):
            rel = data.get("relation", "")
            if any(rt in rel for rt in relation_types):
                filtered.add_edge(u, v, **data)
        return filtered

    def _edges_along_path(self, path: List[str], graph: nx.DiGraph) -> List[Dict[str, str]]:
        edges = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            rel = graph[u][v].get("relation", "unknown")
            edges.append({
                "from": u, "to": v,
                "relation": rel,
                "relation_label": REL_CHINESE.get(rel, rel),
            })
        return edges

    def _format_path(self, edges: List[Dict[str, str]]) -> str:
        """将路径格式化为中文描述。"""
        if not edges:
            return ""
        parts = []
        for e in edges:
            parts.append(f"{e['from']}({e.get('relation_label', e['relation'])})→{e['to']}")
        return " → ".join(parts)

    def _infer_school(self, name: str) -> Optional[str]:
        """根据节点名或相邻节点推断流派。"""
        for school, keywords in SCHOOL_KEYWORDS.items():
            if not keywords:
                continue
            if any(kw in name for kw in keywords):
                return school
        return None

    def _build_generation_map(self, members: List[str]) -> Dict[int, List[str]]:
        """
        根据师承深度为流派成员划分代际。

        代际定义：直接师从开创者 = 第1代，师从第1代 = 第2代……
        无师承记录但属于该流派 = 第0代（同期）。
        """
        if not members or not self.graph:
            return {}

        TEACHER_RELS = {"hasTeacher", "teacherOf"}

        generations: Dict[int, List[str]] = {}
        visited = set()

        def get_generation(person: str, visited_local: set) -> int:
            if person in visited_local:
                return 0
            if person not in self.graph:
                return 0

            max_gen = 0
            for teacher in self.graph.predecessors(person):
                rel = self.graph[teacher][person].get("relation", "")
                if rel in TEACHER_RELS:
                    if teacher in members:
                        gen = get_generation(teacher, visited_local | {person}) + 1
                        max_gen = max(max_gen, gen)
                    elif teacher in self.graph:
                        gen = get_generation(teacher, visited_local | {person})
                        max_gen = max(max_gen, gen)

            return max_gen

        for member in members:
            if member in visited:
                continue
            visited.add(member)
            gen = get_generation(member, {member})
            generations.setdefault(gen, []).append(member)

        return {k: sorted(v) for k, v in sorted(generations.items())}
