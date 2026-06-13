"""
LangGraph 工作流节点实现。

节点职责：
1. parse_intent      — 输入解析：提取人物实体，分类意图
2. decide_route      — 意图判断：决定是否查询 KG 或直接 LLM 回答
3. generate_sparql   — SPARQL 生成（如需查询 KG）
4. execute_query     — 查询执行
5. verify_result     — 结果验证
6. synthesize_answer — 答案合成
7. handle_error      — 异常处理（SPARQL错误/无结果 → LLM人设回答）
"""
import logging
import re
from typing import Dict, Any, List
from .state import QAState, ErrorType, VerificationResult
from .tools import QATools
from .sparql_generator import SPARQLGenerator

logger = logging.getLogger(__name__)

# ============================================================
# 书法领域知识助理人设
# ============================================================
SEAL_ENGRAVING_PERSONA = (
    "你是一位专业的书法篆刻知识助理，对《印人传》及中国篆刻史有深入研究。\n"
    "你的职责是：\n"
    "1. 根据用户问题，结合已有信息给出准确、专业的回答\n"
    "2. 如果知识图谱中没有相关信息，要诚实告知用户，绝不凭空臆造\n"
    "3. 用流畅、自然的中文回答，不要机械罗列数据\n"
    "4. 可以适当补充相关背景知识，帮助用户理解\n"
    "5. 若信息不完整，可基于图谱结构推断，但须说明是「根据图谱结构推断」"
)


# ============================================================
# 节点1：输入解析
# ============================================================

def parse_intent(state: QAState) -> QAState:
    """
    输入解析节点。

    从用户问题中：
    1. 提取人物实体（最长中文词匹配）
    2. 判断问题意图（query_attribute / query_relation / query_school / query_path / opinion / general）
    """
    question = state.get("question", "")
    logger.info(f"[NODE:parse_intent] question={question}")

    # --- 提取人物实体 ---
    # 提取所有连续的 2-4 个汉字子串（人名多为 2 字）
    person_pattern = re.compile(r"[\u4e00-\u9fa5]{2,4}")
    raw_matches = person_pattern.findall(question)

    entities = []
    seen = set()
    for name in raw_matches:
        SKIP_WORDS = {
            "什么", "哪个", "如何", "怎么", "为什么", "请问", "有人",
            "印人", "印派", "流派", "年代", "时期", "明代", "清代", "元代",
            "印学", "篆刻", "知识", "问题", "师承", "弟子", "师父", "老师",
            "学习", "研究", "开创", "著名", "多少", "哪些", "几个", "这里",
            "以上", "以下", "之间", "之前", "之后",
        }
        SKIP_PREFIXES = {"什", "哪", "如", "怎", "为", "请", "有"}
        if name in SKIP_WORDS or len(name) < 2:
            continue
        if name[:2] in SKIP_PREFIXES:
            continue
        # 清理末尾的常见助词/名词后缀（如"文彭的" → "文彭"，"文彭字" → "文彭"）
        name_clean = name
        while name_clean and name_clean[-1] in "的了是在和之有被所字师友派":
            name_clean = name_clean[:-1]
        # 清理开头的常见助词
        while name_clean and name_clean[0] in "的了是在和之有被所字师友":
            name_clean = name_clean[1:]
        if len(name_clean) < 2 or name_clean in SKIP_WORDS:
            continue
        if name_clean not in seen:
            seen.add(name_clean)
            entities.append(name_clean)

    # --- 意图判断 ---
    intent = _classify_intent(question)
    needs_kg = intent not in ("opinion", "unknown")
    skip_reason = ""
    if intent == "opinion":
        skip_reason = "观点性问题，无需查询知识图谱"
    elif intent == "unknown":
        skip_reason = "问题意图不明确"

    state["parsed_entities"] = entities
    state["intent"] = intent
    state["needs_kg_query"] = needs_kg
    state["skip_reason"] = skip_reason

    logger.info(f"[NODE:parse_intent] entities={entities}, intent={intent}, needs_kg={needs_kg}")
    return state


def _classify_intent(question: str) -> str:
    """
    问句意图分类，按优先级逐一匹配。

    优先级（高→低）：师承/流派 > 师父/弟子 > 字/号 > 其他
    """
    # 第一优先级：师承关系类
    if any(kw in question for kw in ["师承", "师父", "老师", "弟子", "徒弟", "学", "教", "传授"]):
        return "query_relation"

    # 第二优先级：流派类
    if any(kw in question for kw in ["派", "流派", "属于", "开创", "创始人", "成员"]):
        return "query_school"

    # 第三优先级：列举类
    if any(kw in question for kw in ["有哪些", "列举", "列出", "多少"]):
        return "query_list"

    # 第四优先级：路径关系类
    if any(kw in question for kw in ["最短", "路径", "之间", "通过"]):
        return "query_path"

    # 第五优先级：观点类
    if any(kw in question for kw in ["你觉得", "你认为", "好不好", "怎么样"]):
        return "opinion"

    # 第六优先级：属性类（字/号/生卒年/籍贯）
    if any(kw in question for kw in ["字", "号", "生年", "卒年", "生於", "籍贯", "籍貫", "朝代"]):
        return "query_attribute"

    # 第七优先级：询问某人
    if "是谁" in question:
        return "query_attribute"

    # 兜底
    if any(kw in question for kw in ["帮我", "请", "能不能", "可以吗"]):
        return "general"

    return "unknown"


# ============================================================
# 节点2：意图路由
# ============================================================

def decide_route(state: QAState) -> QAState:
    """
    意图判断节点。

    判断规则：
    - opinion 类 → 不查询 KG，直接进入合成节点
    - 有实体且 KG 可用 → 进入 SPARQL 生成
    - 无实体 → 进入异常处理
    """
    intent = state.get("intent", "unknown")
    needs_kg = state.get("needs_kg_query", False)
    entities = state.get("parsed_entities", [])

    if intent == "opinion":
        state["error_type"] = ErrorType.NONE
        state["handled"] = False
        state["needs_kg_query"] = False
        logger.info("[NODE:decide_route] -> opinion (skip KG)")
        return state

    if intent == "unknown":
        state["error_type"] = ErrorType.NONE
        state["handled"] = False
        state["needs_kg_query"] = False
        logger.info("[NODE:decide_route] -> unknown intent")
        return state

    if not entities:
        state["error_type"] = ErrorType.NO_ENTITY
        state["error_message"] = "未识别到人物实体，无法查询"
        state["handled"] = False
        state["needs_kg_query"] = False
        logger.info("[NODE:decide_route] -> no entities")
        return state

    state["error_type"] = ErrorType.NONE
    state["handled"] = False
    logger.info(f"[NODE:decide_route] -> generate_sparql")
    return state


# ============================================================
# 节点3：SPARQL 生成
# ============================================================

def generate_sparql(state: QAState, sparql_gen: SPARQLGenerator) -> QAState:
    """
    SPARQL 生成节点。

    基于意图和实体，生成精确的 SPARQL 查询语句。
    """
    question = state.get("question", "")
    entities = state.get("parsed_entities", [])
    intent = state.get("intent", "general")

    logger.info(f"[NODE:generate_sparql] intent={intent}, entities={entities}")

    sparql = sparql_gen.generate(question, entities, intent)

    if sparql:
        state["sparql"] = sparql
        state["sparql_error"] = ""
        state["sparql_generation_method"] = "llm" if sparql_gen.use_llm else "rule"
        logger.info(f"[NODE:generate_sparql] generated (len={len(sparql)})")
    else:
        state["sparql"] = ""
        state["sparql_error"] = "无法为该问题生成 SPARQL 查询"

    return state


# ============================================================
# 节点4：查询执行
# ============================================================

def execute_query(state: QAState, tools: QATools) -> QAState:
    """
    查询执行节点。

    调用 RDF 存储执行 SPARQL 查询。
    """
    sparql = state.get("sparql", "")

    if not sparql:
        state["query_result"] = {"success": False, "results": [], "error": "no sparql"}
        return state

    logger.info("[NODE:execute_query]")
    result = tools.execute_sparql(sparql)
    state["query_result"] = result
    return state


# ============================================================
# 节点5：结果验证
# ============================================================

def verify_result(state: QAState) -> QAState:
    """
    结果验证节点。

    检查查询是否成功执行、结果是否为空，
    决定进入合成节点还是异常处理分支。
    """
    result = state.get("query_result", {})
    sparql_error = state.get("sparql_error", "")

    is_valid = False
    row_count = 0
    has_error = False
    error_message = ""
    warning = ""

    # 检查 SPARQL 生成错误
    if sparql_error:
        has_error = True
        error_message = sparql_error
        state["error_type"] = ErrorType.SPARQL_SYNTAX_ERROR
        state["verification"] = VerificationResult(
            is_valid=False, row_count=0, has_error=True,
            error_message=sparql_error,
        )
        logger.info("[NODE:verify_result] sparql_error -> error branch")
        return state

    # 检查执行错误
    if not result.get("success", False):
        has_error = True
        error_message = result.get("error", "unknown")
        state["error_type"] = ErrorType.SPARQL_EXEC_ERROR
        state["verification"] = VerificationResult(
            is_valid=False, row_count=0, has_error=True,
            error_message=error_message,
        )
        logger.info(f"[NODE:verify_result] exec_error={error_message}")
        return state

    # 检查结果数量
    rows = result.get("results", [])
    row_count = len(rows)
    if row_count == 0:
        is_valid = True  # 执行成功，但图谱中无匹配数据
        warning = "查询执行成功，但图谱中未找到匹配数据"
        # 注意：不修改 error_type，route_verify 会根据 row_count=0 路由到 handle_error
    else:
        is_valid = True
        warning = ""

    state["verification"] = VerificationResult(
        is_valid=is_valid,
        row_count=row_count,
        has_error=False,
        raw_results=rows,
        warning=warning,
    )

    logger.info(f"[NODE:verify_result] valid={is_valid}, rows={row_count}")
    return state


# ============================================================
# 节点6：答案合成
# ============================================================

def synthesize_answer(state: QAState) -> QAState:
    """
    答案合成节点。

    将结构化查询结果整理为流畅的自然语言答案。
    """
    intent = state.get("intent", "general")
    entities = state.get("parsed_entities", [])
    verification = state.get("verification")
    tool_result = state.get("tool_calls", [])

    person = entities[0] if entities else ""
    answer_parts = []

    if person:
        answer_parts.append(f"关于「{person}」：")

    if verification and verification.row_count > 0:
        rows = verification.raw_results
        answer_parts.append(_format_query_results(intent, rows))

        # 添加来源说明
        if verification.row_count > 0:
            answer_parts.append(f"\n（以上数据来源于《印人传》知识图谱，共 {verification.row_count} 条记录）")

        state["answer_source"] = "kg_query"
    else:
        state["answer"] = f"根据《印人传》知识图谱，暂未收录「{person}」的相关信息。"
        state["answer_source"] = "kg_query"
        state["handled"] = True
        return state

    state["answer"] = "".join(answer_parts)
    state["answer_source"] = "kg_query"
    state["handled"] = True
    logger.info(f"[NODE:synthesize_answer] answer len={len(state['answer'])}")
    return state


def _format_query_results(intent: str, rows: List[Dict]) -> str:
    """将 SPARQL 查询结果格式化为自然语言。"""
    if not rows:
        return "未找到相关信息"

    if intent == "query_attribute":
        return _format_attribute_results(rows)

    if intent == "query_relation":
        return _format_relation_results(rows)

    if intent == "query_school":
        return _format_school_results(rows)

    if intent == "query_list":
        return _format_list_results(rows)

    # 通用格式
    parts = []
    for row in rows[:5]:
        for key, val in row.items():
            key_clean = key.lstrip("?")
            if val and str(val).strip():
                parts.append(f"{key_clean}：{val}")
    return "；".join(parts) if parts else "未找到详细信息"


def _format_attribute_results(rows: List[Dict]) -> str:
    """格式化属性查询结果。"""
    ATTR_LABELS = {
        "styleName": "字",
        "hao": "号",
        "birthYear": "生年",
        "deathYear": "卒年",
        "nativePlace": "籍贯",
        "dynasty": "朝代",
        "occupation": "职业",
        "officialRank": "官职",
        "biography": "生平",
        "masterpiece": "代表作",
    }
    parts = []
    for row in rows:
        for key, val in row.items():
            key_clean = key.lstrip("?")
            label = ATTR_LABELS.get(key_clean, key_clean)
            if val:
                parts.append(f"{label}：{val}")
    return "；".join(parts) if parts else "未找到属性信息"


def _format_relation_results(rows: List[Dict]) -> str:
    """格式化关系查询结果。"""
    REL_LABELS = {
        "teacherName": "师父",
        "studentName": "弟子",
        "friendName": "友人",
        "targetName": "关联人物",
        "schoolName": "流派",
    }
    parts = []
    for row in rows:
        for key, val in row.items():
            key_clean = key.lstrip("?")
            label = REL_LABELS.get(key_clean, key_clean)
            if val:
                parts.append(f"{label}：{val}")
    return "；".join(parts) if parts else "未找到关系信息"


def _format_school_results(rows: List[Dict]) -> str:
    """格式化流派查询结果。"""
    names = []
    for row in rows:
        for key, val in row.items():
            key_clean = key.lstrip("?")
            if val and key_clean in ("personName", "name"):
                names.append(str(val))
    return f"包括：{'、'.join(names)}" if names else "未找到流派成员"


def _format_list_results(rows: List[Dict]) -> str:
    """格式化列举查询结果。"""
    names = []
    for row in rows:
        for key, val in row.items():
            key_clean = key.lstrip("?")
            if val and key_clean in ("personName", "name", "schoolName", "styleName", "hao"):
                names.append(str(val))
    return f"{'、'.join(names)}" if names else "未找到结果"


# ============================================================
# 节点7：异常处理
# ============================================================

def handle_error(state: QAState, llm_client=None) -> QAState:
    """
    异常处理节点。

    当 SPARQL 语法错误、查询无结果或无法生成查询时，
    由 LLM 以"书法领域知识助理"人设友好地回答用户。
    核心原则：绝不凭空臆造答案。
    """
    error_type = state.get("error_type", ErrorType.NONE)
    error_msg = state.get("error_message", "")
    sparql_error = state.get("sparql_error", "")
    verification = state.get("verification")
    question = state.get("question", "")
    entities = state.get("parsed_entities", [])
    person = entities[0] if entities else ""

    logger.info(f"[NODE:handle_error] error_type={error_type}")

    # 尝试工具查询作为兜底
    from .tools import QATools
    if entities and hasattr(llm_client, "_rdf_store"):
        try:
            tools = QATools(llm_client._rdf_store)
            if error_type == ErrorType.NO_RESULT:
                # 无结果 → 尝试直接查询基本信息
                info_result = tools.query_person_basic_info(person)
                if info_result and not info_result.get("error"):
                    state["answer"] = _format_attribute_results([info_result])
                    state["answer_source"] = "kg_query"
                    state["handled"] = True
                    state["error_type"] = ErrorType.NONE
                    return state
        except Exception:
            pass

    # 构建 LLM 人设回答
    if llm_client:
        answer = _llm_fallback(question, person, error_type, error_msg, sparql_error,
                               verification, llm_client)
    else:
        answer = _rule_fallback(question, person, error_type, error_msg, sparql_error)

    state["answer"] = answer
    state["answer_source"] = "llm_fallback"
    state["handled"] = True
    logger.info(f"[NODE:handle_error] fallback answer: {answer[:80]}...")
    return state


def _rule_fallback(question: str, person: str,
                   error_type: str, error_msg: str,
                   sparql_error: str) -> str:
    """规则兜底回答（无 LLM 时）。"""
    if error_type == ErrorType.NO_ENTITY:
        return (
            "抱歉，我在您的问题中没有识别到具体的人物姓名，"
            "请提供完整的人名（如「文彭」「何震」），我会为您查询相关信息。"
        )

    if error_type == ErrorType.SPARQL_SYNTAX_ERROR:
        return (
            f"很抱歉，查询过程中遇到了技术问题：{sparql_error or error_msg}。"
            "建议您尝试简化问题，或直接告诉我您想了解的人物姓名。"
        )

    if error_type == ErrorType.SPARQL_EXEC_ERROR:
        return (
            "很抱歉，知识图谱查询遇到了问题。"
            "请稍后重试，或直接告诉我您想查询的人物姓名。"
        )

    if error_type == ErrorType.NO_RESULT:
        if person:
            return (
                f"经过查询，《印人传》知识图谱中暂未收录「{person}」的详细信息。"
                "这可能是因为该人物在原文记载较少，或尚未被抽取进入图谱。"
                "您可以尝试查询其他人物（如文彭、何震等），或查看图谱可视化页面探索更多信息。"
            )
        return (
            "很抱歉，经过查询，知识图谱中未找到与您问题相关的信息。"
            "您可以换个方式提问，例如：「文彭的字是什么」「浙派有哪些人」。"
        )

    return (
        "很抱歉，我无法回答您的问题。"
        "请尝试提供具体人物姓名，如：「文彭是谁」「何震的师父」等。"
    )


def _llm_fallback(question: str, person: str,
                  error_type: str, error_msg: str,
                  sparql_error: str,
                  verification,
                  llm_client) -> str:
    """LLM 人设兜底回答。"""
    # 构建上下文
    context_parts = [
        f"用户问题：{question}",
    ]
    if person:
        context_parts.append(f"已识别人物：{person}")

    error_descriptions = {
        ErrorType.SPARQL_SYNTAX_ERROR: f"SPARQL 查询语法错误：{sparql_error or error_msg}",
        ErrorType.SPARQL_EXEC_ERROR: f"查询执行错误：{error_msg}",
        ErrorType.NO_RESULT: "查询执行成功，但图谱中未找到匹配数据",
        ErrorType.NO_ENTITY: "未能从问题中识别人物实体",
    }
    if error_type in error_descriptions:
        context_parts.append(f"情况说明：{error_descriptions[error_type]}")

    context_parts.append(
        "重要原则：\n"
        "1. 如果图谱中没有确切信息，必须诚实告知用户，绝不凭空编造\n"
        "2. 如果信息不完整，可以说明「图谱中仅收录了部分信息」\n"
        "3. 用流畅自然的中文回答，不要机械罗列\n"
        "4. 可以适当补充书法/篆刻领域的背景知识"
    )

    system_prompt = SEAL_ENGRAVING_PERSONA
    user_prompt = "\n\n".join(context_parts)

    try:
        import httpx
        from ..utils.config import OLLAMA_BASE_URL, OLLAMA_MODEL

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": user_prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {"num_predict": 512, "temperature": 0.3},
                },
            )
            if resp.status_code == 200:
                answer = resp.json().get("response", "").strip()
                if answer:
                    return answer
    except Exception as e:
        logger.error(f"LLM fallback failed: {e}")

    return _rule_fallback(question, person, error_type, error_msg, sparql_error)
