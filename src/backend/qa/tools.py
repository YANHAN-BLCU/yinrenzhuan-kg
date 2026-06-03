import logging
from typing import Dict, List, Any, Optional
from ..rdf.rdf_store import RDFStore

logger = logging.getLogger(__name__)


class QATools:
    TOOL_DEFINITIONS = [
        {
            "name": "get_person_info",
            "description": "根据人名查询人物的基本信息（字、号、生卒年、籍贯、朝代）",
            "parameters": {
                "type": "object",
                "properties": {
                    "person_name": {
                        "type": "string",
                        "description": "人物姓名"
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "指定要查询的字段列表，默认全部字段",
                    },
                },
                "required": ["person_name"],
            },
            "returns": {
                "person_name": "文彭",
                "style_name": "寿承",
                "hao": "三桥",
                "birth_year": 1498,
                "death_year": 1575,
                "native_place": "苏州",
                "dynasty": "明",
            },
        },
        {
            "name": "get_person_relations",
            "description": "查询某人物的关系网络，支持关系类型过滤",
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
                        "description": "过滤关系类型（如 ['fatherOf', 'teacherOf', 'friendOf', 'belongsToSchool']）",
                    },
                },
                "required": ["person_name"],
            },
            "returns": {
                "person_name": "文彭",
                "relations": [
                    {"type": "sonOf", "target": "文徵明", "direction": "child"},
                    {"type": "belongsToSchool", "target": "吳門印派", "direction": "self"},
                    {"type": "friendOf", "target": "祝允明", "direction": "both"},
                ],
            },
        },
        {
            "name": "get_school_members",
            "description": "查询流派的详细信息、创始人和成员",
            "parameters": {
                "type": "object",
                "properties": {
                    "school_name": {
                        "type": "string",
                        "description": "流派名称",
                    },
                },
                "required": ["school_name"],
            },
            "returns": {
                "school_name": "吳門印派",
                "founder": "文彭",
                "period": "明中期",
                "region": "苏州",
                "members": ["文彭", "文徵明", "苏宣", "何震"],
            },
        },
        {
            "name": "find_path_between",
            "description": "查询两个人物之间的最短师承或交游路径",
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
                    "relation_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "关系类型约束，默认 ['teacherOf', 'studentOf', 'friendOf', 'fatherOf']",
                    },
                },
                "required": ["person_a", "person_b"],
            },
            "returns": {
                "path": ["何震", "师承", "文彭", "师承", "文徵明"],
                "description": "何震 通过 文彭 师承于 文徵明",
                "length": 3,
            },
        },
        {
            "name": "execute_sparql",
            "description": "执行 SPARQL 查询语句",
            "parameters": {
                "type": "object",
                "properties": {
                    "sparql_query": {
                        "type": "string",
                        "description": "SPARQL 查询语句",
                    },
                },
                "required": ["sparql_query"],
            },
            "returns": {
                "success": True,
                "results": [{"person": "文彭", "style_name": "寿承"}],
                "row_count": 1,
            },
        },
    ]

    def __init__(self, rdf_store: RDFStore):
        self.rdf_store = rdf_store

    def get_person_info(self, person_name: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        logger.info(f"[TOOL] get_person_info: {person_name}")
        info = self.rdf_store.get_person_info(person_name)
        if fields:
            info = {k: v for k, v in info.items() if k in fields}
        return info

    def get_person_relations(self, person_name: str,
                            relation_types: Optional[List[str]] = None) -> Dict[str, Any]:
        logger.info(f"[TOOL] get_person_relations: {person_name}, types={relation_types}")
        return self.rdf_store.get_relations(person_name, relation_types)

    def get_school_members(self, school_name: str) -> Dict[str, Any]:
        logger.info(f"[TOOL] get_school_members: {school_name}")
        members = self.rdf_store.get_school_members(school_name)
        return {
            "school_name": school_name,
            "members": [m.get("name", "") for m in members],
            "member_count": len(members),
        }

    def find_path_between(self, person_a: str, person_b: str,
                         relation_types: Optional[List[str]] = None) -> Dict[str, Any]:
        logger.info(f"[TOOL] find_path_between: {person_a} -> {person_b}")
        path = self.rdf_store.find_path(person_a, person_b)
        if path:
            return {
                "path": path,
                "length": len(path) - 1,
                "found": True,
            }
        return {
            "path": None,
            "length": 0,
            "found": False,
        }

    def execute_sparql(self, sparql_query: str) -> Dict[str, Any]:
        logger.info(f"[TOOL] execute_sparql")
        try:
            results = self.rdf_store.query_sparql(sparql_query)
            return {
                "success": True,
                "results": results,
                "row_count": len(results),
            }
        except Exception as e:
            logger.error(f"SPARQL execution failed: {e}")
            return {
                "success": False,
                "results": [],
                "row_count": 0,
                "error": str(e),
            }

    def can_answer_with_tools(self, question: str, entities: List[str]) -> bool:
        can_answer = False
        if not entities:
            return False
        info_indicators = ["字", "号", "生", "卒", "年", "籍贯", "哪", "什么"]
        relation_indicators = ["关系", "师承", "师父", "弟子", "朋友", "交往"]
        school_indicators = ["流派", "属于", "派", "成员", "创始人"]

        has_info = any(ind in question for ind in info_indicators)
        has_relation = any(ind in question for ind in relation_indicators)
        has_school = any(ind in question for ind in school_indicators)
        can_answer = (has_info or has_relation or has_school) and len(entities) > 0
        logger.info(f"[TOOL] can_answer_with_tools={can_answer} for question: {question}")
        return can_answer
