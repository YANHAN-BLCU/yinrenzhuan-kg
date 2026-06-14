import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Load .env if python-dotenv is available
_env_path = BASE_DIR / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path, override=True)
    except ImportError:
        # Manual fallback: read KEY=VALUE lines
        for line in _env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = DATA_DIR / "output"
SRC_DIR = BASE_DIR / "src"

YINRENCHUAN_TXT = BASE_DIR / "印人傳.txt"

RDF_OUTPUT = OUTPUT_DIR / "knowledge_graph.ttl"
LINKED_OUTPUT = OUTPUT_DIR / "linked_graph.ttl"
FAISS_INDEX = OUTPUT_DIR / "yinrenchuan_faiss.index"
FAISS_META = OUTPUT_DIR / "yinrenchuan_faiss.meta.json"

YINRENCHUAN_TXT_URL = "https://raw.githubusercontent.com/gretielect/xiangmai_zh/raw/master/yinrenchuan.txt"

ONTOLOGY_NS = "http://example.org/inkperson/"
REL_NS = "http://example.org/inkperson/relation/"
CTEXT_NS = "http://example.org/ctext/"
CBDB_NS = "http://example.org/cbdb/"

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "deepseek-chat")

EMBEDDING_API_KEY = os.environ.get("EMBEDDING_API_KEY", "") or OPENAI_API_KEY
EMBEDDING_BASE_URL = os.environ.get("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM = 1024  # BAAI/bge-m3

CTEXT_API_BASE = "https://ctext.org/searchbooks.py"
CBDB_API_BASE = "https://cbdb.fas.harvard.edu/cbdbapi/"

MAX_CONTEXT_TOKENS = 512
TOP_K_RAG = 5
RAG_SIMILARITY_THRESHOLD = 0.6

PERSON_NAME_MIN_LEN = 2
PERSON_NAME_MAX_LEN = 4

for d in [DATA_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
