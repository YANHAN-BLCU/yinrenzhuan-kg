import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import networkx as nx
import community as community_louvain

logger = logging.getLogger(__name__)


class CommunityDetection:

    def __init__(self, graph: Optional[nx.DiGraph] = None):
        self.graph = graph
        self.communities: Dict[str, Any] = {}

    def set_graph(self, graph: nx.DiGraph):
        self.graph = graph

    def louvain(self, resolution: float = 1.0) -> Dict[int, List[str]]:
        if not self.graph:
            raise ValueError("Graph not set")

        undirected = self.graph.to_undirected()
        partition = community_louvain.best_partition(undirected, resolution=resolution)

        community_map: Dict[int, List[str]] = {}
        for node, comm_id in partition.items():
            community_map.setdefault(comm_id, []).append(node)

        for comm_id, members in community_map.items():
            subgraph = self.graph.to_undirected().subgraph(members)
            internal_edges = subgraph.number_of_edges()

            person_members = [m for m in members]
            relation_types: Dict[str, int] = {}
            for _, _, data in subgraph.edges(data=True):
                rel = data.get("relation", "unknown")
                relation_types[rel] = relation_types.get(rel, 0) + 1

            schools: Dict[str, int] = {}
            for member in members:
                if member in self.graph:
                    for _, _, data in self.graph.out_edges(member, data=True):
                        school = data.get("relation", "")
                        if any(kw in school for kw in ["School", "派", "Founder", "Member", "founder", "member"]):
                            schools[school] = schools.get(school, 0) + 1

            self.communities[f"community_{comm_id}"] = {
                "id": comm_id,
                "members": sorted(members),
                "member_count": len(members),
                "internal_edges": internal_edges,
                "relation_types": relation_types,
                "dominant_schools": dict(sorted(schools.items(), key=lambda x: x[1], reverse=True)[:3]),
            }

        logger.info(f"Louvain detected {len(self.communities)} communities")
        return community_map

    def label_communities(self) -> List[Dict[str, Any]]:
        labeled = []
        for comm_name, comm_data in sorted(self.communities.items(), key=lambda x: x[1]["member_count"], reverse=True):
            dominant_school = comm_data.get("dominant_schools", {})
            label = next(iter(dominant_school.keys()), "未分类")
            labeled.append({
                "id": comm_data["id"],
                "label": label,
                "members": comm_data["members"],
                "member_count": comm_data["member_count"],
                "internal_edges": comm_data["internal_edges"],
                "relation_types": comm_data.get("relation_types", {}),
            })
        return labeled

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.communities, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved community detection to {path}")
