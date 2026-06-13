"""
问答系统状态定义。

使用 LangGraph TypedDict 建模，包含：
- 问题输入与解析结果
- 意图分类
- SPARQL 生成与执行结果
- 结果验证
- 最终答案
- 异常处理状态
"""
from typing import TypedDict, Optional, Any, List, Literal, Union
from dataclasses import dataclass, field


class ErrorType:
    """错误类型枚举常量。"""
    NONE = "none"
    SPARQL_SYNTAX_ERROR = "sparql_syntax_error"
    SPARQL_EXEC_ERROR = "sparql_exec_error"
    NO_RESULT = "no_result"
    NO_ENTITY = "no_entity"
    LLM_ERROR = "llm_error"
    KG_NOT_LOADED = "kg_not_loaded"


@dataclass
class VerificationResult:
    """查询结果验证结果。"""
    is_valid: bool
    row_count: int
    has_error: bool
    error_message: str = ""
    warning: str = ""
    raw_results: List[Any] = field(default_factory=list)


@dataclass
class ToolCall:
    """工具调用记录。"""
    tool_name: str
    arguments: dict
    result: Any = None
    success: bool = False
    error: str = ""


class QAState(TypedDict, total=False):
    """
    LangGraph 工作流状态。

    字段说明：
    - question: 用户原始问题
    - parsed_entities: 从问题中解析出的人物实体列表
    - intent: 意图分类结果
      * query_attribute — 查询属性（字/号/生卒年等）
      * query_relation — 查询关系（师承/交游/亲属）
      * query_school — 查询流派
      * query_path — 查询人物间路径
      * general — 通用问题
      * opinion — 观点问题（无需查询KG）
    - needs_kg_query: 是否需要查询知识图谱
    - sparql: 生成的 SPARQL 查询语句
    - sparql_error: SPARQL 语法错误信息
    - query_result: 查询执行结果
    - verification: 结果验证
    - tool_calls: 工具调用记录列表
    - answer: 最终生成的答案
    - answer_source: 答案来源（kg_query / rag / llm_fallback）
    - error_type: 错误类型（ErrorType 常量）
    - error_message: 错误详情
    - llm_available: LLM 是否可用
    - skip_reason: 跳过 KG 查询的原因（如为观点性问题）
    """

    # === 输入 ===
    question: str

    # === 解析 & 意图 ===
    parsed_entities: List[str]
    intent: str
    needs_kg_query: bool
    skip_reason: str  # opinion 等无需 KG 查询的原因

    # === SPARQL ===
    sparql: str
    sparql_error: str
    sparql_generation_method: str  # "rule_based" | "llm"

    # === 查询执行 ===
    query_result: Any
    verification: Optional[VerificationResult]

    # === 工具 ===
    tool_calls: List[ToolCall]
    current_tool: str

    # === 答案 ===
    answer: str
    answer_source: str  # "kg_query" | "rag" | "llm_fallback" | "opinion"

    # === 异常 ===
    error_type: str   # ErrorType 常量
    error_message: str
    handled: bool      # 是否已被异常处理节点处理
