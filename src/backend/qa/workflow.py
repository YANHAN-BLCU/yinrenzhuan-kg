"""
基于 LangGraph 的可控问答工作流。

节点序列：
  parse_intent → decide_route
                        ├→ synthesize_answer (opinion / unknown 路径)
                        └→ generate_sparql → execute_query → verify_result
                                                               ├→ synthesize_answer (验证通过)
                                                               └→ handle_error (验证失败：SPARQL错误/无结果)

条件边（conditional_edges）：
  decide_route:
    - opinion / unknown → END
    - generate_sparql
  verify_result:
    - valid (有结果) → synthesize_answer
    - invalid (无结果/SPARQL错误) → handle_error
"""
import logging
from typing import Literal
from .state import QAState, ErrorType
from .nodes import (
    normalize_question,
    parse_intent,
    decide_route,
    generate_sparql,
    execute_query,
    verify_result,
    synthesize_answer,
    handle_error,
)
from .tools import QATools
from .sparql_generator import SPARQLGenerator
from .question_normalizer import QuestionNormalizer

logger = logging.getLogger(__name__)


def build_langgraph_workflow(
    rdf_store,
    use_llm_sparql: bool = False,
    use_llm_fallback: bool = True,
    rag_retriever=None,
    use_question_normalizer: bool = True,
) -> "CompiledStateGraph":
    """
    构建 LangGraph 工作流图。

    Args:
        rdf_store: RDFStore 实例
        use_llm_sparql: 是否使用 LLM 生成 SPARQL（需 Ollama）
        use_llm_fallback: 是否使用 LLM 生成兜底答案
        rag_retriever: RAGRetriever 实例（可选，用于从原文检索上下文）
        use_question_normalizer: 是否启用 LLM 问句规范化（默认开启）

    Returns:
        编译后的 LangGraph StateGraph
    """
    try:
        from langgraph.graph import StateGraph, END, START
    except ImportError:
        logger.warning("langgraph not installed, using fallback workflow")
        return None

    tools = QATools(rdf_store)
    sparql_gen = SPARQLGenerator(use_llm=use_llm_sparql)
    llm_client = _LLMClient(use_llm_fallback) if use_llm_fallback else None
    normalizer = QuestionNormalizer(enabled=use_question_normalizer)

    # --- 定义节点函数（绑定工具） ---
    def _normalize(s: QAState) -> QAState:
        return normalize_question(s, normalizer)

    def _parse_intent(s: QAState) -> QAState:
        return parse_intent(s)

    def _decide_route(s: QAState) -> QAState:
        return decide_route(s)

    def _generate_sparql(s: QAState) -> QAState:
        return generate_sparql(s, sparql_gen)

    def _execute_query(s: QAState) -> QAState:
        return execute_query(s, tools)

    def _verify_result(s: QAState) -> QAState:
        return verify_result(s)

    def _synthesize(s: QAState) -> QAState:
        return synthesize_answer(s)

    def _handle_error(s: QAState) -> QAState:
        return handle_error(s, llm_client, rag_retriever)

    # --- 构建图 ---
    builder = StateGraph(QAState)

    # 添加节点
    builder.add_node("normalize_question", _normalize)
    builder.add_node("parse_intent", _parse_intent)
    builder.add_node("decide_route", _decide_route)
    builder.add_node("generate_sparql", _generate_sparql)
    builder.add_node("execute_query", _execute_query)
    builder.add_node("verify_result", _verify_result)
    builder.add_node("synthesize_answer", _synthesize)
    builder.add_node("handle_error", _handle_error)

    # 设置入口
    builder.add_edge(START, "normalize_question")
    # normalize_question → parse_intent
    builder.add_edge("normalize_question", "parse_intent")

    # parse_intent → decide_route
    builder.add_edge("parse_intent", "decide_route")

    # decide_route → 条件分支
    def route_decide(s: QAState) -> Literal["synthesize_answer", "generate_sparql", "__end__"]:
        """
        路由决策：
        - opinion / unknown 意图 → 直接合成答案
        - needs_kg_query=False → 异常处理
        - 其他 → SPARQL 生成
        """
        intent = s.get("intent", "")
        needs_kg = s.get("needs_kg_query", False)

        if intent in ("opinion", "unknown"):
            return "synthesize_answer"
        if not needs_kg:
            return "handle_error"
        return "generate_sparql"

    builder.add_conditional_edges(
        "decide_route",
        route_decide,
        {
            "synthesize_answer": "synthesize_answer",
            "generate_sparql": "generate_sparql",
            "handle_error": "handle_error",
        },
    )

    # generate_sparql → execute_query
    builder.add_edge("generate_sparql", "execute_query")

    # execute_query → verify_result
    builder.add_edge("execute_query", "verify_result")

    # verify_result → 条件分支
    def route_verify(s: QAState) -> Literal["synthesize_answer", "handle_error"]:
        """
        验证结果路由：
        - valid（有结果） → 合成答案
        - invalid（无结果/SPARQL错误） → 异常处理
        """
        verification = s.get("verification")
        error_type = s.get("error_type", ErrorType.NONE)

        if verification and verification.is_valid and verification.row_count > 0:
            return "synthesize_answer"

        # 执行成功但结果为空，或有执行错误 → 异常处理
        return "handle_error"

    builder.add_conditional_edges(
        "verify_result",
        route_verify,
        {
            "synthesize_answer": "synthesize_answer",
            "handle_error": "handle_error",
        },
    )

    # 所有终点 → END
    builder.add_edge("synthesize_answer", END)
    builder.add_edge("handle_error", END)

    # 编译图（无 checkpointer：每次问答独立，无需跨请求持久化）
    graph = builder.compile()
    logger.info("LangGraph workflow compiled successfully")
    return graph


def run_workflow_simple(
    rdf_store,
    question: str,
    use_llm_sparql: bool = False,
    use_llm_fallback: bool = True,
    rag_retriever=None,
    use_question_normalizer: bool = True,
) -> QAState:
    """
    非 LangGraph 回退工作流（直接顺序调用）。

    当 langgraph 不可用时，使用此函数。
    """
    tools = QATools(rdf_store)
    sparql_gen = SPARQLGenerator(use_llm=use_llm_sparql)
    llm_client = _LLMClient(use_llm_fallback) if use_llm_fallback else None
    normalizer = QuestionNormalizer(enabled=use_question_normalizer)

    state: QAState = {
        "question": question,
        "normalized_question": "",
        "parsed_entities": [],
        "intent": "unknown",
        "needs_kg_query": False,
        "skip_reason": "",
        "sparql": "",
        "sparql_error": "",
        "sparql_generation_method": "rule",
        "query_result": None,
        "verification": None,
        "tool_calls": [],
        "current_tool": "",
        "answer": "",
        "answer_source": "",
        "error_type": ErrorType.NONE,
        "error_message": "",
        "handled": False,
    }

    # 节点0-2：问句规范化 + 实体/意图抽取
    state = normalize_question(state, normalizer)
    state = parse_intent(state)
    state = decide_route(state)

    intent = state.get("intent", "")
    needs_kg = state.get("needs_kg_query", False)

    if intent in ("opinion", "unknown") or not needs_kg:
        state = synthesize_answer(state)
        return state

    # 节点3-4-5-6-7
    state = generate_sparql(state, sparql_gen)
    state = execute_query(state, tools)
    state = verify_result(state)

    verification = state.get("verification")
    error_type = state.get("error_type", ErrorType.NONE)

    if verification and verification.is_valid and verification.row_count > 0:
        state = synthesize_answer(state)
    else:
        state = handle_error(state, llm_client, rag_retriever)

    return state


def build_qa_workflow(rdf_store, rag_retriever=None):
    """兼容旧 API：返回工作流对象（LangGraph graph 或简单函数）。"""
    graph = build_langgraph_workflow(rdf_store, rag_retriever=rag_retriever)
    if graph is not None:
        return graph

    def _run(question: str) -> "QAState":
        return run_workflow_simple(rdf_store, question, rag_retriever=rag_retriever)

    return _run


class _LLMClient:
    """LLM 调用包装器（用于人设回答）。"""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def generate(self, prompt: str, system: str = "") -> str:
        if not self.enabled:
            return ""
        try:
            import httpx
            from ..utils.config import OLLAMA_BASE_URL, OLLAMA_MODEL
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "system": system,
                        "stream": False,
                        "options": {"num_predict": 512, "temperature": 0.3},
                    },
                )
                if resp.status_code == 200:
                    return resp.json().get("response", "")
        except Exception:
            pass
        return ""
