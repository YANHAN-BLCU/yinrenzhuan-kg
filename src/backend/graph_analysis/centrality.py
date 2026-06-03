import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import networkx as nx

logger = logging.getLogger(__name__)


class CentralityAnalysis:

    def __init__(self, graph: Optional[nx.DiGraph] = None):
        self.graph = graph
        self.results: Dict[str, Any] = {}

    def set_graph(self, graph: nx.DiGraph):
        self.graph = graph

    def degree_centrality(self, top_n: int = 20) -> List[Dict[str, Any]]:
        if not self.graph:
            raise ValueError("Graph not set")
        dc = nx.degree_centrality(self.graph)
        sorted_dc = sorted(dc.items(), key=lambda x: x[1], reverse=True)
        result = [{"name": n, "degree_centrality": round(v, 4), "rank": i + 1}
                  for i, (n, v) in enumerate(sorted_dc[:top_n])]
        self.results["degree_centrality"] = result
        logger.info(f"Degree centrality: top={result[0] if result else None}")
        return result

    def betweenness_centrality(self, top_n: int = 20) -> List[Dict[str, Any]]:
        if not self.graph:
            raise ValueError("Graph not set")
        bc = nx.betweenness_centrality(self.graph)
        sorted_bc = sorted(bc.items(), key=lambda x: x[1], reverse=True)
        result = [{"name": n, "betweenness_centrality": round(v, 4), "rank": i + 1}
                  for i, (n, v) in enumerate(sorted_bc[:top_n])]
        self.results["betweenness_centrality"] = result
        return result

    def pagerank(self, top_n: int = 20, alpha: float = 0.85) -> List[Dict[str, Any]]:
        if not self.graph:
            raise ValueError("Graph not set")
        pr = nx.pagerank(self.graph, alpha=alpha)
        sorted_pr = sorted(pr.items(), key=lambda x: x[1], reverse=True)
        result = [{"name": n, "pagerank": round(v, 4), "rank": i + 1}
                  for i, (n, v) in enumerate(sorted_pr[:top_n])]
        self.results["pagerank"] = result
        return result

    def closeness_centrality(self, top_n: int = 20) -> List[Dict[str, Any]]:
        if not self.graph:
            raise ValueError("Graph not set")
        cc = nx.closeness_centrality(self.graph)
        sorted_cc = sorted(cc.items(), key=lambda x: x[1], reverse=True)
        result = [{"name": n, "closeness_centrality": round(v, 4), "rank": i + 1}
                  for i, (n, v) in enumerate(sorted_cc[:top_n])]
        self.results["closeness_centrality"] = result
        return result

    def analyze_all(self, top_n: int = 20) -> Dict[str, Any]:
        self.degree_centrality(top_n)
        self.betweenness_centrality(top_n)
        self.pagerank(top_n)
        self.closeness_centrality(top_n)
        self.results["summary"] = {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "density": round(nx.density(self.graph), 4),
        }
        return self.results

    def school_analysis(self, school_members: Dict[str, List[str]]) -> Dict[str, Any]:
        results = {}
        for school, members in school_members.items():
            subgraph_nodes = [m for m in members if m in self.graph]
            if not subgraph_nodes:
                continue
            subgraph = self.graph.subgraph(subgraph_nodes)
            dc = nx.degree_centrality(subgraph)
            top_persons = sorted(dc.items(), key=lambda x: x[1], reverse=True)[:3]
            results[school] = {
                "member_count": len(members),
                "core_persons": [n for n, _ in top_persons],
                "internal_edges": subgraph.number_of_edges(),
                "density": round(nx.density(subgraph), 4) if len(subgraph_nodes) > 1 else 0.0,
            }
        return results

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved centrality analysis to {path}")
