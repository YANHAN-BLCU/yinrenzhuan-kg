import logging
from typing import Dict, Any
from .state import QAState
from .tools import QATools
from .sparql_generator import SPARQLGenerator

logger = logging.getLogger(__name__)


def parse_intent_node(state: QAState) -> QAState:
    question = state.get("question", "")
    logger.info(f"[NODE] parse_intent: {question}")

    intent = "unknown"
    entities = []

    import re
    # Match the longest prefix of Chinese chars (2+ chars) that is immediately
    # followed by a particle or end of string. Non-greedy +? backtracks through
    # 1,2,3,... chars until the lookahead (?=particle|$) succeeds.
    # Filter out matches that start with a particle char (e.g. "的字" -> skip "的" as prefix).
    PARTICLES = set("的是和为之在")
    person_pattern = re.compile(r"[\u4e00-\u9fa5]+?(?=[的是和为之在　]|$)")
    raw = person_pattern.findall(question)
    for m in raw:
        if len(m) >= 2 and m[0] not in PARTICLES:
            entities.append(m)

    if any(kw in question for kw in ["字", "号", "生年", "卒年", "籍贯", "朝代", "是谁"]):
        intent = "query_attribute"
    elif any(kw in question for kw in ["师承", "师父", "老师", "弟子", "徒弟", "学", "教"]):
        intent = "query_teacher"
    elif any(kw in question for kw in ["派", "流派", "属于", "开创", "创建"]):
        intent = "query_school"
    elif any(kw in question for kw in ["关系", "什么关系", "交往", "交游"]):
        intent = "query_relationship"
    elif any(kw in question for kw in ["路径", "最短", "之间", "通过"]):
        intent = "query_path"
    else:
        intent = "general_query"

    state["intent"] = intent
    state["entities"] = entities
    return state


def decide_tool_or_sparql_node(state: QAState, tools: QATools) -> QAState:
    question = state.get("question", "")
    entities = state.get("entities", [])
    can_use = tools.can_answer_with_tools(question, entities)
    state["can_use_tools"] = can_use
    logger.info(f"[NODE] decide_tool: can_use_tools={can_use}")
    return state


def call_local_tools_node(state: QAState, tools: QATools) -> QAState:
    question = state.get("question", "")
    entities = state.get("entities", [])
    intent = state.get("intent", "")
    logger.info(f"[NODE] call_local_tools: intent={intent}")

    if not entities:
        state["tool_result"] = {"error": "未识别到人物实体"}
        return state

    person = entities[0]
    result = {}

    if intent == "query_attribute":
        result = tools.get_person_info(person)
    elif intent == "query_teacher":
        result = tools.get_person_relations(person, ["teacherOf", "studentOf", "fatherOf", "sonOf"])
    elif intent == "query_school":
        result = tools.get_person_relations(person, ["belongsToSchool", "foundedSchool"])
    elif intent == "query_relationship":
        result = tools.get_person_relations(person)
    else:
        result = tools.get_person_info(person)

    state["tool_result"] = result
    return state


def generate_sparql_node(state: QAState, generator: SPARQLGenerator) -> QAState:
    question = state.get("question", "")
    entities = state.get("entities", [])
    intent = state.get("intent", "")
    logger.info(f"[NODE] generate_sparql")

    sparql = generator.generate(question, entities, intent)
    state["sparql_generated"] = sparql or ""
    return state


def execute_sparql_node(state: QAState, tools: QATools) -> QAState:
    sparql = state.get("sparql_generated", "")
    if not sparql:
        state["sparql_executed"] = False
        state["sparql_result"] = {"error": "No SPARQL generated"}
        return state

    logger.info(f"[NODE] execute_sparql")
    result = tools.execute_sparql(sparql)
    state["sparql_executed"] = result.get("success", False)
    state["sparql_result"] = result
    return state


def generate_answer_node(state: QAState) -> QAState:
    question = state.get("question", "")
    intent = state.get("intent", "")
    entities = state.get("entities", [])
    tool_result = state.get("tool_result", {})
    sparql_result = state.get("sparql_result", {})
    logger.info(f"[NODE] generate_answer")

    answer_parts = []

    if entities:
        person = entities[0]
        answer_parts.append(f"关于「{person}」：")

    if tool_result and not tool_result.get("error"):
        if intent == "query_attribute":
            info = tool_result
            attrs = []
            if info.get("style_name"):
                attrs.append(f"字：{info['style_name']}")
            if info.get("hao"):
                attrs.append(f"号：{info['hao']}")
            if info.get("birth_year"):
                attrs.append(f"生年：{info['birth_year']}")
            if info.get("death_year"):
                attrs.append(f"卒年：{info['death_year']}")
            if info.get("native_place"):
                attrs.append(f"籍贯：{info['native_place']}")
            if info.get("dynasty"):
                attrs.append(f"朝代：{info['dynasty']}")
            if attrs:
                answer_parts.append("；".join(attrs))
            if info.get("schools"):
                answer_parts.append(f"所属流派：{'、'.join(info['schools'])}")
            if info.get("relations"):
                rels = [f"{r['type']}：{r['target']}" for r in info['relations'][:5]]
                answer_parts.append("关系：" + "；".join(rels))

        elif intent in ("query_teacher", "query_school", "query_relationship"):
            rels = tool_result.get("relations", [])
            if rels:
                rel_texts = []
                for r in rels[:5]:
                    rel_texts.append(f"{r['type']}：{r['target']}")
                answer_parts.append("；".join(rel_texts))

    if sparql_result and sparql_result.get("success"):
        rows = sparql_result.get("results", [])
        if rows:
            answer_parts.append(f"（SPARQL 查询返回 {len(rows)} 条结果）")

    if len(answer_parts) <= 1:
        state["answer"] = f"根据《印人传》知识图谱，我找到了相关信息。以上数据来源于知识图谱查询。"
        state["fallback_used"] = True
    else:
        state["answer"] = "。".join(answer_parts)
        state["fallback_used"] = False

    return state


def fallback_answer_node(state: QAState) -> QAState:
    question = state.get("question", "")
    entities = state.get("entities", [])
    rag_result = state.get("rag_retrieved", {})

    logger.info(f"[NODE] fallback_answer")

    if rag_result and rag_result.get("chunks"):
        chunks = rag_result.get("chunks", [])
        if chunks:
            state["answer"] = (
                f"根据《印人传》原文记载：\n"
                f"「{chunks[0].get('content', '')}」\n\n"
                f"（共检索到 {len(chunks)} 条相关原文）"
            )
            state["fallback_used"] = True
            return state

    if entities:
        person = entities[0]
        state["answer"] = (
            f"关于「{person}」的信息已在知识图谱中收录，"
            f"详细关系和属性请通过图谱可视化页面查看。"
        )
    else:
        state["answer"] = (
            "很抱歉，知识图谱中未找到与您问题相关的信息。"
            "您可以尝试调整问法，或通过图谱可视化页面手动探索。"
        )
    state["fallback_used"] = True
    return state
