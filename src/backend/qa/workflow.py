import logging
from typing import Optional
from .state import QAState
from .nodes import (
    parse_intent_node, decide_tool_or_sparql_node,
    call_local_tools_node, generate_sparql_node,
    execute_sparql_node, generate_answer_node, fallback_answer_node,
)
from .tools import QATools
from .sparql_generator import SPARQLGenerator

logger = logging.getLogger(__name__)


def build_qa_workflow(rdf_store, rag_retriever=None, llm_client=None):
    try:
        from langgraph.graph import StateGraph, END
        has_langgraph = True
    except ImportError:
        has_langgraph = False

    tools = QATools(rdf_store)
    sparql_gen = SPARQLGenerator(llm_client)

    def run_workflow(question: str) -> QAState:
        state: QAState = {
            "question": question,
            "intent": "unknown",
            "entities": [],
            "can_use_tools": False,
            "tool_result": None,
            "sparql_generated": "",
            "sparql_executed": False,
            "sparql_result": None,
            "answer": "",
            "fallback_used": False,
            "rag_retrieved": None,
            "rag_used": False,
        }

        state = parse_intent_node(state)
        state = decide_tool_or_sparql_node(state, tools)

        if state["can_use_tools"]:
            state = call_local_tools_node(state, tools)
            state = generate_answer_node(state)
            return state
        else:
            state = generate_sparql_node(state, sparql_gen)
            if state.get("sparql_generated"):
                state = execute_sparql_node(state, tools)
                if state.get("sparql_executed"):
                    state = generate_answer_node(state)
                    return state

            if rag_retriever:
                try:
                    chunks = rag_retriever.retrieve(question, top_k=3)
                    if chunks:
                        state["rag_retrieved"] = {"chunks": chunks}
                        state["rag_used"] = True
                except Exception as e:
                    logger.warning(f"RAG retrieval failed: {e}")

            state = fallback_answer_node(state)
            return state

    if has_langgraph:
        def build_graph():
            builder = StateGraph(QAState)
            builder.add_node("parse_intent", lambda s: parse_intent_node(s))
            builder.add_node("decide", lambda s: decide_tool_or_sparql_node(s, tools))
            builder.add_node("tools", lambda s: call_local_tools_node(s, tools))
            builder.add_node("gen_sparql", lambda s: generate_sparql_node(s, sparql_gen))
            builder.add_node("exec_sparql", lambda s: execute_sparql_node(s, tools))
            builder.add_node("gen_answer", lambda s: generate_answer_node(s))
            builder.add_node("fallback", lambda s: fallback_answer_node(s))

            builder.set_entry_point("parse_intent")
            builder.add_edge("parse_intent", "decide")

            def route_decide(state: QAState) -> str:
                if state.get("can_use_tools", False):
                    return "tools"
                return "gen_sparql"

            builder.add_conditional_edges("decide", route_decide, {
                "tools": "tools",
                "gen_sparql": "gen_sparql",
            })
            builder.add_edge("tools", "gen_answer")
            builder.add_edge("gen_sparql", "exec_sparql")

            def route_exec(state: QAState) -> str:
                if state.get("sparql_executed", False):
                    return "gen_answer"
                return "fallback"

            builder.add_conditional_edges("exec_sparql", route_exec, {
                "gen_answer": "gen_answer",
                "fallback": "fallback",
            })
            builder.add_edge("gen_answer", END)
            builder.add_edge("fallback", END)
            return builder.compile()

        graph = build_graph()
        return graph

    return run_workflow
