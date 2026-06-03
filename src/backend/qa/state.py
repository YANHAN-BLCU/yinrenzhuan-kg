from typing import TypedDict, Optional, Any, List

class QAState(TypedDict, total=False):
    question: str
    intent: str
    entities: List[str]
    can_use_tools: bool
    tool_result: Any
    sparql_generated: str
    sparql_executed: bool
    sparql_result: Any
    answer: str
    fallback_used: bool
    error_message: str
    rag_retrieved: Any
    rag_used: bool
