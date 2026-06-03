import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
DICT_DIR = DATA_DIR / "dictionaries"
OUTPUT_DIR = DATA_DIR / "output"
SRC_DIR = BASE_DIR / "src"

YINRENCHUAN_TXT = BASE_DIR / "印人傳.txt"
if not YINRENCHUAN_TXT.exists():
    YINRENCHUAN_TXT = RAW_DIR / "印人傳.txt"

RDF_OUTPUT = OUTPUT_DIR / "knowledge_graph.ttl"
LINKED_OUTPUT = OUTPUT_DIR / "linked_graph.ttl"
EXTRACTED_TRIPLES = OUTPUT_DIR / "extracted_triples.json"
FAISS_INDEX = OUTPUT_DIR / "yinrenchuan_faiss.index"
CENTRALITY_OUTPUT = OUTPUT_DIR / "centrality.json"
COMMUNITIES_OUTPUT = OUTPUT_DIR / "communities.json"
PERSONS_JSON = OUTPUT_DIR / "persons.json"
RELATIONS_JSON = OUTPUT_DIR / "relations.json"
GRAPH_JSON = OUTPUT_DIR / "graph.json"

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

CTEXT_API_BASE = "https://ctext.org/searchbooks.py"
CBDB_API_BASE = "https://cbdb.fas.harvard.edu/cbdbapi/"

EMBEDDING_MODEL = "BAAI/bge-base-zh-v1.5"
EMBEDDING_DIM = 768

MAX_CONTEXT_TOKENS = 512
TOP_K_RAG = 5
RAG_SIMILARITY_THRESHOLD = 0.6

PERSON_NAME_MIN_LEN = 2
PERSON_NAME_MAX_LEN = 4

for d in [DATA_DIR, RAW_DIR, DICT_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
