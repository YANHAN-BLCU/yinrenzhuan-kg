from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="印人传 · 知识图谱问答系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1",
        "http://localhost",
        f"http://{os.environ.get('HOST', '127.0.0.1')}",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_graph_data: Dict[str, Any] = {}
_rdf_store = None
_rag_retriever = None  # RAG retriever, lazily loaded

_api_base = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")

# 视图类查询缓存（首次访问时计算一次；TTL 重载后清空）
_view_cache: Dict[str, Any] = {}


def _clear_view_cache():
    _view_cache.clear()


class QARequest(BaseModel):
    question: str


class SPARQLRequest(BaseModel):
    sparql: str


def _get_project_root() -> Path:
    return Path(__file__).parent.parent


def _ensure_loaded():
    global _rdf_store
    if _rdf_store is not None:
        return

    project_root = _get_project_root()
    data_output = project_root / "data" / "output"
    data_output.mkdir(parents=True, exist_ok=True)

    try:
        from backend.rdf.rdf_store import RDFStore

        rdf_path = data_output / "linked_graph.ttl"
        if not rdf_path.exists():
            rdf_path = data_output / "knowledge_graph.ttl"
        if rdf_path.exists():
            _rdf_store = RDFStore().load(rdf_path)
            logger.info(f"RDF store loaded from {rdf_path}")
        else:
            _rdf_store = RDFStore()
            logger.info("RDF store initialized (no file yet)")

    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        _rdf_store = None


def _load_rag_retriever():
    """Lazily load RAG retriever from saved FAISS index."""
    global _rag_retriever
    if _rag_retriever is not None:
        return

    try:
        from backend.utils.config import FAISS_INDEX, FAISS_META
        if not FAISS_INDEX.exists() or not FAISS_META.exists():
            logger.info("RAG index files not found; RAG disabled")
            return

        from backend.qa.rag.retriever import RAGRetriever
        retriever = RAGRetriever()
        if retriever.load(FAISS_INDEX, FAISS_META):
            _rag_retriever = retriever
            logger.info(f"RAG retriever loaded from {FAISS_INDEX}")
        else:
            logger.warning("RAG retriever failed to load")
    except Exception as e:
        logger.warning(f"RAG retriever load failed: {e}")


@app.get("/api/info")
def root():
    return {"message": "印人传 · 知识图谱问答系统 API", "version": "1.0.0"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


from fastapi.responses import Response
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(content=b"", media_type="image/x-icon", status_code=204)


@app.post("/api/qa")
def qa(req: QARequest):
    _ensure_loaded()
    _load_rag_retriever()
    if _rdf_store is None:
        raise HTTPException(status_code=503, detail="知识图谱未加载，请先运行抽取流程")

    try:
        from backend.qa.workflow import build_qa_workflow
        from backend.qa.tools import QATools

        tools = QATools(_rdf_store)
        workflow = build_qa_workflow(_rdf_store, _rag_retriever)

        if hasattr(workflow, "invoke"):
            result = workflow.invoke({"question": req.question})
        else:
            result = workflow(req.question)

        return {
            "question": req.question,
            "answer": result.get("answer", ""),
            "intent": result.get("intent", ""),
            "entities": result.get("parsed_entities", []),
            "needs_kg_query": result.get("needs_kg_query", False),
            "sparql": result.get("sparql", ""),
            "answer_source": result.get("answer_source", ""),
            "error_type": result.get("error_type", ""),
            "query_result": result.get("query_result"),
            "verification": result.get("verification"),
        }
    except Exception as e:
        logger.error(f"QA error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sparql")
def execute_sparql(req: SPARQLRequest):
    _ensure_loaded()
    if _rdf_store is None:
        raise HTTPException(status_code=503, detail="知识图谱未加载")

    try:
        result = _rdf_store.query_sparql(req.sparql)
        return {"success": True, "results": result, "row_count": len(result)}
    except Exception as e:
        return {"success": False, "error": str(e), "results": [], "row_count": 0}


@app.get("/api/person/{name}")
def get_person(name: str):
    _ensure_loaded()
    if _rdf_store is None:
        raise HTTPException(status_code=503, detail="知识图谱未加载")

    info = _rdf_store.get_person_info(name)
    if not info:
        raise HTTPException(status_code=404, detail=f"未找到人物：{name}")
    return info


@app.get("/api/relations/{name}")
def get_relations(name: str, types: Optional[str] = None):
    _ensure_loaded()
    if _rdf_store is None:
        raise HTTPException(status_code=503, detail="知识图谱未加载")

    rel_types = types.split(",") if types else None
    return _rdf_store.get_relations(name, rel_types)


@app.get("/api/graph")
def get_graph():
    _ensure_loaded()
    if _rdf_store is None:
        return {"nodes": [], "links": []}
    if "graph" not in _view_cache:
        _view_cache["graph"] = _rdf_store.get_graph_view()
    return _view_cache["graph"]


@app.get("/api/persons")
def get_persons():
    _ensure_loaded()
    if _rdf_store is None:
        return {"persons": [], "count": 0}
    persons = _rdf_store.get_all_persons()
    return {"persons": persons, "count": len(persons)}


@app.get("/api/schools")
def get_schools():
    _ensure_loaded()
    if _rdf_store is None:
        return {"schools": [], "count": 0}
    schools = _rdf_store.get_all_schools()
    return {"schools": schools, "count": len(schools)}


@app.get("/api/school/{name}")
def get_school(name: str):
    _ensure_loaded()
    if _rdf_store is None:
        raise HTTPException(status_code=503, detail="知识图谱未加载")
    try:
        members = _rdf_store.get_school_members(name)
        return {"school_name": name, "members": members, "count": len(members)}
    except Exception as e:
        logger.error(f"School query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _compute_centrality() -> Dict[str, Any]:
    from backend.graph_analysis.centrality import CentralityAnalysis
    if _rdf_store is None:
        return {"error": "知识图谱未加载"}
    G = _rdf_store.to_networkx()
    ca = CentralityAnalysis(G)
    return {
        "degree_centrality": ca.degree_centrality(),
        "betweenness_centrality": ca.betweenness_centrality(),
        "pagerank": ca.pagerank(),
        "closeness_centrality": ca.closeness_centrality(),
    }


def _compute_communities() -> Dict[str, Any]:
    from backend.graph_analysis.community import CommunityDetection
    if _rdf_store is None:
        return {"error": "知识图谱未加载"}
    G = _rdf_store.to_networkx()
    cd = CommunityDetection(G)
    cd.louvain()
    return cd.communities


@app.get("/api/analysis/centrality")
def get_centrality():
    _ensure_loaded()
    if "centrality" not in _view_cache:
        _view_cache["centrality"] = _compute_centrality()
    return _view_cache["centrality"]


@app.get("/api/analysis/communities")
def get_communities():
    _ensure_loaded()
    if "communities" not in _view_cache:
        _view_cache["communities"] = _compute_communities()
    return _view_cache["communities"]


@app.post("/api/reload")
def reload_data():
    """清除缓存并重新加载 TTL + RAG（开发用）。"""
    global _rdf_store, _rag_retriever
    _rdf_store = None
    _rag_retriever = None
    _clear_view_cache()
    _ensure_loaded()
    _load_rag_retriever()
    triples = len(_rdf_store.graph) if _rdf_store else 0
    return {"reloaded": True, "triples": triples, "rag_loaded": _rag_retriever is not None}


def _mount_frontend():
    """Mount index.html at / and serve static assets (index_card/, data/) from project root."""
    project_root = _get_project_root()
    index_path = project_root / "index.html"
    if index_path.exists():
        from fastapi.responses import FileResponse
        @app.get("/")
        def serve_index():
            return FileResponse(str(index_path))
        logger.info(f"Frontend mounted at / -> {index_path}")

        card_dir = project_root / "index_card"
        if card_dir.exists():
            app.mount("/index_card", StaticFiles(directory=str(card_dir)), name="index_card")
            logger.info(f"Mounted index_card/ at /index_card/")

        data_dir = project_root / "data"
        if data_dir.exists():
            app.mount("/data", StaticFiles(directory=str(data_dir)), name="data")
            logger.info(f"Mounted data/ at /data/")

        static_dir = project_root / "static"
        if static_dir.exists():
            app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
            logger.info(f"Mounted static/ at /static/")
    else:
        logger.warning(f"index.html not found at {index_path}, frontend not mounted")


_mount_frontend()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
