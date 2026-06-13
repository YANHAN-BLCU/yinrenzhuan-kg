"""
专用工具封装。

每个工具均符合 LangChain/LangGraph Tool 接口规范，
提供结构化的 Schema 定义、参数验证和错误处理。
"""
import logging
from typing import Dict, List, Any, Optional, get_type_hints, get_origin, get_args
from dataclasses import dataclass
from ..rdf.rdf_store import RDFStore
from ..rdf.ontology import SCHEMA_TO_RDF, normalize_predicate

logger = logging.getLogger(__name__)

# ============================================================
# 工具元数据定义
# ============================================================

TOOL_DEFINITIONS = [
    {
        "name": "query_person_basic_info",
        "description": (
            "根据提供的人物姓名，查询其在《印人传》知识图谱中的基本信息。"
            "返回字、号、生卒年、籍贯、朝代等结构化数据。"
            "适用于询问「某人的字是什么」「某人是哪个朝代的」等问题。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "person_name": {
                    "type": "string",
                    "description": "人物姓名，必须精确匹配图谱中人名，如「文彭」「何震」",
                    "minLength": 2,
                    "maxLength": 10,
                },
            },
            "required": ["person_name"],
        },
        "returns": {
            "type": "object",
            "description": "包含查询到的各项属性的 JSON 对象，若未找到则返回空对象",
            "example": {
                "person_name": "文彭",
                "style_name": "壽承",
                "hao": "三橋",
                "birth_year": 1498,
                "death_year": 1575,
                "native_place": "蘇州",
                "dynasty": "明",
                "schools": ["吳門印派"],
            },
        },
    },
    {
        "name": "query_person_relations",
        "description": (
            "查询某人物的完整关系网络，包括师承、亲属、交游、所属流派等各类关系。"
            "支持关系类型过滤，可仅返回指定类型的关系。"
            "适用于询问「某人的师父是谁」「某人的朋友有谁」「某派有哪些人」等问题。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "person_name": {
                    "type": "string",
                    "description": "人物姓名",
                },
                "relation_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "关系类型过滤，支持：hasTeacher/hasStudent（师承），"
                        "hasFather/hasSon（亲属），hasFriend（交游），"
                        "belongsToSchool/hasFounder（流派），influencedBy（影响）"
                    ),
                    "default": [],
                },
            },
            "required": ["person_name"],
        },
        "returns": {
            "type": "object",
            "description": "包含人物基本信息和关系列表",
        },
    },
    {
        "name": "query_school_info",
        "description": (
            "查询篆刻流派的详细信息，包括创始人、活跃时期、代表成员。"
            "适用于询问「某派的创始人是谁」「某派有哪些人」等问题。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "school_name": {
                    "type": "string",
                    "description": "流派名称，支持：浙派、皖派、吳門印派、漳海派、莆田派、婁東派",
                },
            },
            "required": ["school_name"],
        },
        "returns": {
            "type": "object",
            "description": "流派基本信息与成员列表",
        },
    },
    {
        "name": "query_path",
        "description": (
            "查询两位历史人物之间的最短师承或交游路径。"
            "适用于询问「A和B之间是什么关系」「A如何认识B」等问题。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "person_a": {
                    "type": "string",
                    "description": "人物A姓名",
                },
                "person_b": {
                    "type": "string",
                    "description": "人物B姓名",
                },
            },
            "required": ["person_a", "person_b"],
        },
        "returns": {
            "type": "object",
            "description": "最短路径信息，包含路径节点列表和中文描述",
        },
    },
    {
        "name": "execute_sparql",
        "description": (
            "执行 SPARQL 查询语句，直接查询知识图谱 RDF 数据。"
            "适用于复杂查询，如「所有属于某流派的印人」「某人的所有师承关系」等。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sparql": {
                    "type": "string",
                    "description": "标准 SPARQL SELECT 查询语句（需包含 PREFIX 声明）",
                },
            },
            "required": ["sparql"],
        },
        "returns": {
            "type": "object",
            "description": "查询结果或错误信息",
        },
    },
]


@dataclass
class ToolResult:
    """工具调用结果容器。"""
    tool_name: str
    success: bool
    data: Any = None
    error: str = ""
    row_count: int = 0


# ============================================================
# 工具实现类
# ============================================================

class QATools:

    def __init__(self, rdf_store: RDFStore):
        self.rdf_store = rdf_store

    def query_person_basic_info(self, person_name: str) -> Dict[str, Any]:
        """
        查询人物基础信息。

        Args:
            person_name: 人物姓名

        Returns:
            {
                "person_name": str,
                "style_name": Optional[str],  # 字
                "hao": Optional[str],           # 号
                "birth_year": Optional[int],
                "death_year": Optional[int],
                "native_place": Optional[str],
                "dynasty": Optional[str],
                "occupation": Optional[str],
                "official_rank": Optional[str],
                "biography": Optional[str],
                "masterpiece": Optional[str],
                "schools": List[str],
            }
        """
        logger.info(f"[TOOL] query_person_basic_info: {person_name}")
        try:
            info = self.rdf_store.get_person_info(person_name)
            if not info or not info.get("person_name"):
                logger.warning(f"Person not found: {person_name}")
                return {}
            return info
        except Exception as e:
            logger.error(f"query_person_basic_info error: {e}")
            return {"error": str(e)}

    def query_person_relations(
        self,
        person_name: str,
        relation_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        查询人物关系网络。

        Args:
            person_name: 人物姓名
            relation_types: 关系类型过滤列表，如 ["hasTeacher", "hasStudent"]

        Returns:
            {
                "person_name": str,
                "relations": [{"type": str, "target": str}, ...]
            }
        """
        logger.info(f"[TOOL] query_person_relations: {person_name}, types={relation_types}")
        try:
            # 标准化关系类型（支持新旧命名）
            if relation_types:
                normalized = [normalize_predicate(t) for t in relation_types]
            else:
                normalized = None

            info = self.rdf_store.get_relations(person_name, normalized)
            return info
        except Exception as e:
            logger.error(f"query_person_relations error: {e}")
            return {"person_name": person_name, "relations": [], "error": str(e)}

    def query_school_info(self, school_name: str) -> Dict[str, Any]:
        """
        查询流派信息。

        Args:
            school_name: 流派名称

        Returns:
            {
                "school_name": str,
                "founder": Optional[str],
                "members": List[str],
                "member_count": int,
            }
        """
        logger.info(f"[TOOL] query_school_info: {school_name}")
        try:
            members_raw = self.rdf_store.get_school_members(school_name)
            members = [m.get("name", "") for m in members_raw]
            return {
                "school_name": school_name,
                "members": members,
                "member_count": len(members),
            }
        except Exception as e:
            logger.error(f"query_school_info error: {e}")
            return {"school_name": school_name, "members": [], "error": str(e)}

    def query_path(self, person_a: str, person_b: str) -> Dict[str, Any]:
        """
        查询两人之间的最短路径。

        Args:
            person_a: 人物A
            person_b: 人物B

        Returns:
            {
                "found": bool,
                "path": List[str],      # 节点列表
                "length": int,
                "edges": List[Dict],    # 边详情
                "description": str,      # 中文描述
            }
        """
        logger.info(f"[TOOL] query_path: {person_a} -> {person_b}")
        try:
            path = self.rdf_store.find_path(person_a, person_b)
            if path:
                return {
                    "found": True,
                    "path": path,
                    "length": len(path) - 1,
                    "description": f"{person_a} 与 {person_b} 通过 {len(path) - 1} 步关联",
                }
            return {"found": False, "path": None, "length": 0, "description": "未找到关联路径"}
        except Exception as e:
            logger.error(f"query_path error: {e}")
            return {"found": False, "error": str(e)}

    def execute_sparql(self, sparql: str) -> Dict[str, Any]:
        """
        执行 SPARQL 查询。

        Args:
            sparql: 完整 SPARQL 查询语句

        Returns:
            {
                "success": bool,
                "results": List[Dict],
                "row_count": int,
                "error": Optional[str],
            }
        """
        logger.info(f"[TOOL] execute_sparql (len={len(sparql)})")
        try:
            results = self.rdf_store.query_sparql(sparql)
            return {
                "success": True,
                "results": results,
                "row_count": len(results),
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"execute_sparql error: {error_msg}")
            return {
                "success": False,
                "results": [],
                "row_count": 0,
                "error": error_msg,
            }

    # ============================================================
    # 辅助方法
    # ============================================================

    def list_available_tools(self) -> List[str]:
        """返回可用工具名称列表。"""
        return [t["name"] for t in TOOL_DEFINITIONS]

    def get_tool_schema(self, tool_name: str) -> Optional[Dict]:
        """获取工具的 JSON Schema 定义。"""
        for t in TOOL_DEFINITIONS:
            if t["name"] == tool_name:
                return t
        return None

    def can_answer_without_llm(self, question: str, entities: List[str]) -> bool:
        """
        判断是否可直接通过工具回答（无需 LLM 合成）。

        当问题明确属于结构化查询范畴时返回 True。
        """
        if not entities:
            return False

        KG_INDICATORS = [
            "字", "號", "号", "生年", "卒年", "籍贯", "朝代",
            "师承", "师父", "弟子", "徒弟", "老师",
            "朋友", "交往", "交游", "关系",
            "流派", "属于", "派", "创始人", "开创",
            "最短", "路径", "之间", "通过",
            "生卒", "生卒年", "生平",
        ]
        return any(ind in question for ind in KG_INDICATORS)
