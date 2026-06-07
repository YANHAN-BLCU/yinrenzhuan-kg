from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import json
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

_api_base = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")


class QARequest(BaseModel):
    question: str


class SPARQLRequest(BaseModel):
    sparql: str


def _get_project_root() -> Path:
    return Path(__file__).parent.parent


def _ensure_loaded():
    global _graph_data, _rdf_store
    if _rdf_store is not None:
        return

    project_root = _get_project_root()
    data_output = project_root / "data" / "output"
    data_output.mkdir(parents=True, exist_ok=True)

    try:
        from backend.rdf.rdf_store import RDFStore

        rdf_path = data_output / "linked_graph.ttl"
        if rdf_path.exists():
            _rdf_store = RDFStore().load(rdf_path)
            logger.info(f"RDF store loaded from {rdf_path}")
        else:
            rdf_path = data_output / "knowledge_graph.ttl"
            if rdf_path.exists():
                _rdf_store = RDFStore().load(rdf_path)
                logger.info(f"RDF store loaded from {rdf_path} (linked_graph not found)")
            else:
                _rdf_store = RDFStore()
                logger.info("RDF store initialized (no file yet)")

        persons_path = data_output / "persons.json"
        if persons_path.exists():
            with open(persons_path, "r", encoding="utf-8") as f:
                _graph_data["persons"] = json.load(f)

        rels_path = data_output / "relations.json"
        if rels_path.exists():
            with open(rels_path, "r", encoding="utf-8") as f:
                _graph_data["relations"] = json.load(f)

        graph_path = data_output / "graph.json"
        if graph_path.exists():
            with open(graph_path, "r", encoding="utf-8") as f:
                _graph_data["graph"] = json.load(f)

    except Exception as e:
        logger.warning(f"Failed to preload data: {e}")


@app.get("/api/info")
def root():
    return {"message": "印人传 · 知识图谱问答系统 API", "version": "1.0.0"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/qa")
def qa(req: QARequest):
    _ensure_loaded()
    if _rdf_store is None:
        raise HTTPException(status_code=503, detail="知识图谱未加载，请先运行抽取流程")

    try:
        from backend.qa.workflow import build_qa_workflow
        from backend.qa.tools import QATools

        tools = QATools(_rdf_store)
        workflow = build_qa_workflow(_rdf_store)

        if hasattr(workflow, "invoke"):
            result = workflow.invoke({"question": req.question})
        else:
            result = workflow(req.question)

        return {
            "question": req.question,
            "answer": result.get("answer", ""),
            "intent": result.get("intent", ""),
            "entities": result.get("entities", []),
            "tool_used": result.get("can_use_tools", False),
            "sparql": result.get("sparql_generated", ""),
            "fallback_used": result.get("fallback_used", False),
            "tool_result": result.get("tool_result"),
            "sparql_result": result.get("sparql_result"),
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
    g = _graph_data.get("graph")
    if not g:
        return {"nodes": [], "links": []}
    return g


@app.get("/api/persons")
def get_persons():
    _ensure_loaded()
    persons = _graph_data.get("persons", [])
    if not persons and _rdf_store:
        persons = _rdf_store.get_all_persons()
    return {"persons": persons, "count": len(persons)}


@app.get("/api/schools")
def get_schools():
    _ensure_loaded()
    g = _graph_data.get("graph", {})
    schools = [n for n in g.get("nodes", []) if n.get("type") == "school"]
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


@app.get("/api/analysis/centrality")
def get_centrality():
    _ensure_loaded()
    project_root = _get_project_root()
    path = project_root / "data" / "output" / "centrality.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"error": "analysis not available yet"}


@app.get("/api/analysis/communities")
def get_communities():
    _ensure_loaded()
    project_root = _get_project_root()
    path = project_root / "data" / "output" / "communities.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"error": "communities not available yet"}


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

        # Serve index_card/ images at /index_card/...
        card_dir = project_root / "index_card"
        if card_dir.exists():
            app.mount("/index_card", StaticFiles(directory=str(card_dir)), name="index_card")
            logger.info(f"Mounted index_card/ at /index_card/")

        # Serve data/output/ at /data/... (for any future static assets)
        data_dir = project_root / "data"
        if data_dir.exists():
            app.mount("/data", StaticFiles(directory=str(data_dir)), name="data")
            logger.info(f"Mounted data/ at /data/")
    else:
        logger.warning(f"index.html not found at {index_path}, frontend not mounted")


_mount_frontend()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
