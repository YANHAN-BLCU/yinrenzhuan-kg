"""
SPARQL 查询语句生成器。

支持两种模式：
1. 规则模式 — 基于问句关键词的启发式 SPARQL 生成
2. LLM 模式 — 通过 LLM 根据 Few-shot 示例生成（需 Ollama）

适配新的本体 Schema：
  hasFather/hasSon, hasTeacher/hasStudent, hasFriend,
  belongsToSchool/hasFounder, styleName, hao, nativePlace 等
"""
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


# ============================================================
# Few-shot 示例
# ============================================================

SPARQL_EXAMPLES = [
    {
        "question": "文彭的字是什么？",
        "sparql": (
            "PREFIX ex: <http://example.org/inkperson/>\n"
            "SELECT ?styleName WHERE {\n"
            "  ?person ex:personName \"文彭\" .\n"
            "  ?person ex:styleName ?styleName .\n"
            "}"
        ),
    },
    {
        "question": "何震的师父是谁？",
        "sparql": (
            "PREFIX ex: <http://example.org/inkperson/>\n"
            "SELECT ?teacherName WHERE {\n"
            "  ?person ex:personName \"何震\" .\n"
            "  ?person ex:hasTeacher ?teacher .\n"
            "  ?teacher ex:personName ?teacherName .\n"
            "}"
        ),
    },
    {
        "question": "吳門印派有哪些人？",
        "sparql": (
            "PREFIX ex: <http://example.org/inkperson/>\n"
            "SELECT DISTINCT ?personName WHERE {\n"
            "  ?person ex:belongsToSchool ?school .\n"
            "  ?school ex:schoolName \"吳門印派\" .\n"
            "  ?person ex:personName ?personName .\n"
            "}"
        ),
    },
    {
        "question": "丁敬是哪个流派的？",
        "sparql": (
            "PREFIX ex: <http://example.org/inkperson/>\n"
            "SELECT ?schoolName WHERE {\n"
            "  ?person ex:personName \"丁敬\" .\n"
            "  ?person ex:belongsToSchool ?school .\n"
            "  ?school ex:schoolName ?schoolName .\n"
            "}"
        ),
    },
    {
        "question": "文彭和何震是什么关系？",
        "sparql": (
            "PREFIX ex: <http://example.org/inkperson/>\n"
            "SELECT ?rel ?targetName WHERE {\n"
            "  ?personA ex:personName \"文彭\" .\n"
            "  ?personB ex:personName \"何震\" .\n"
            "  { ?personA ex:hasTeacher ?personB . BIND(\"hasTeacher\" AS ?rel) ?personB ex:personName ?targetName }\n"
            "  UNION\n"
            "  { ?personA ex:hasStudent ?personB . BIND(\"hasStudent\" AS ?rel) ?personB ex:personName ?targetName }\n"
            "  UNION\n"
            "  { ?personA ex:hasFriend ?personB . BIND(\"hasFriend\" AS ?rel) ?personB ex:personName ?targetName }\n"
            "}"
        ),
    },
]


# ============================================================
# 规则模式 SPARQL 生成
# ============================================================

# 问句关键词 → 意图映射
INTENT_PATTERNS = [
    # (关键词列表, 意图标签)
    (["字", "styleName"], "ask_style_name"),
    (["号", "hao"], "ask_hao"),
    (["生年", "生於", "出生"], "ask_birth"),
    (["卒年", "死", "去世"], "ask_death"),
    (["籍贯", "籍貫", "哪里人", "哪个地方"], "ask_native_place"),
    (["朝代", "哪个朝"], "ask_dynasty"),
    (["师父", "老师", "传授", "授业"], "ask_teacher"),
    (["弟子", "徒弟", "学生", "传承"], "ask_student"),
    (["朋友", "交往", "交游"], "ask_friend"),
    (["流派", "属于", "派"], "ask_school"),
    (["关系", "什么关系"], "ask_relation"),
    (["最短", "路径", "之间", "通过"], "ask_path"),
    (["开创", "创始人", "始创"], "ask_founder"),
    (["生平", "简介", "经历"], "ask_biography"),
    (["作品", "代表作", "代表作"], "ask_masterpiece"),
]


def _detect_intent(question: str) -> str:
    """基于关键词检测问句意图。"""
    for keywords, intent in INTENT_PATTERNS:
        for kw in keywords:
            if kw in question:
                return intent
    return "general"


def _make_prefix() -> str:
    return "PREFIX ex: <http://example.org/inkperson/>\n"


def _build_person_triple(var: str = "?person") -> str:
    return f"?person ex:personName \"{var}\" ."


class SPARQLGenerator:
    """
    SPARQL 查询语句生成器。

    优先使用规则模式（无需 LLM），在 Ollama 可用时通过 LLM 生成复杂查询。
    """

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm

    def generate(self, question: str, entities: List[str],
                 intent: Optional[str] = None) -> Optional[str]:
        """
        生成 SPARQL 查询。

        Args:
            question: 用户问题
            entities: 从问题中解析出的人物实体列表
            intent: 意图标签（由意图判断节点提供）

        Returns:
            SPARQL 查询语句，或 None（无法生成时）
        """
        if not entities:
            logger.warning("SPARQL generation skipped: no entities")
            return None

        person = entities[0]

        # 规则模式：query_attribute 需要从问句中提取具体属性关键词
        # 其他意图使用映射表
        INTENT_MAP = {
            "query_attribute": None,     # 从问句词推导具体属性（见下方）
            "query_relation": "ask_teacher",
            "query_school": "ask_school",
            "query_path": "ask_relation",
            "query_list": "ask_relation",
            "general": "general",
            "opinion": "general",
            "unknown": "general",
        }
        mapped = INTENT_MAP.get(intent, None)
        if intent == "query_attribute":
            # 从问句中提取具体属性查询意图
            attr_intent = _detect_intent(question)
            sparql = self._rule_based_generate(person, question, attr_intent)
        elif mapped:
            sparql = self._rule_based_generate(person, question, mapped)
        else:
            detected_intent = _detect_intent(question)
            sparql = self._rule_based_generate(person, question, detected_intent)
        if sparql:
            logger.info(f"[SPARQL] generated: {intent}->{sparql[:60]}")
            return sparql

        # LLM 模式
        if self.use_llm:
            sparql = self._llm_generate(question, entities)
            if sparql:
                logger.info(f"[SPARQL] LLM-generated")
                return sparql

        return None

    def _rule_based_generate(self, person: str, question: str, intent: str) -> Optional[str]:
        """基于规则的 SPARQL 生成。"""
        p = _make_prefix()

        if intent == "ask_style_name":
            return (
                f"{p}"
                f"SELECT ?styleName WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  ?person ex:styleName ?styleName .\n"
                f"}}"
            )

        if intent == "ask_hao":
            return (
                f"{p}"
                f"SELECT ?hao WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  ?person ex:hao ?hao .\n"
                f"}}"
            )

        if intent == "ask_birth":
            return (
                f"{p}"
                f"SELECT ?birthYear WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  ?person ex:birthYear ?birthYear .\n"
                f"}}"
            )

        if intent == "ask_death":
            return (
                f"{p}"
                f"SELECT ?deathYear WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  ?person ex:deathYear ?deathYear .\n"
                f"}}"
            )

        if intent == "ask_native_place":
            return (
                f"{p}"
                f"SELECT ?nativePlace WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  ?person ex:nativePlace ?nativePlace .\n"
                f"}}"
            )

        if intent == "ask_dynasty":
            return (
                f"{p}"
                f"SELECT ?dynasty WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  ?person ex:dynasty ?dynasty .\n"
                f"}}"
            )

        if intent == "ask_teacher":
            return (
                f"{p}"
                f"SELECT ?teacherName ?rel WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  {{ ?person ex:hasTeacher ?teacher . BIND(\"hasTeacher\" AS ?rel) }}\n"
                f"  UNION\n"
                f"  {{ ?person ex:studentOf ?teacher . BIND(\"studentOf\" AS ?rel) }}\n"
                f"  ?teacher ex:personName ?teacherName .\n"
                f"}}"
            )

        if intent == "ask_student":
            return (
                f"{p}"
                f"SELECT ?studentName ?rel WHERE {{\n"
                f"  ?teacher ex:personName \"{person}\" .\n"
                f"  {{ ?teacher ex:hasStudent ?student . BIND(\"hasStudent\" AS ?rel) }}\n"
                f"  UNION\n"
                f"  {{ ?teacher ex:studentOf ?student . BIND(\"studentOf\" AS ?rel) }}\n"
                f"  ?student ex:personName ?studentName .\n"
                f"}}"
            )

        if intent == "ask_friend":
            return (
                f"{p}"
                f"SELECT DISTINCT ?friendName WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  {{ ?person ex:hasFriend ?friend . }}\n"
                f"  UNION\n"
                f"  {{ ?friend ex:hasFriend ?person . }}\n"
                f"  ?friend ex:personName ?friendName .\n"
                f"  FILTER(?friendName != \"{person}\")\n"
                f"}}"
            )

        if intent == "ask_school":
            return (
                f"{p}"
                f"SELECT ?schoolName WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  ?person ex:belongsToSchool ?school .\n"
                f"  ?school ex:schoolName ?schoolName .\n"
                f"}}"
            )

        if intent == "ask_relation":
            return (
                f"{p}"
                f"SELECT ?rel ?targetName WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  ?person ?rel ?target .\n"
                f"  ?target ex:personName ?targetName .\n"
                f"  FILTER(?rel IN (ex:hasTeacher, ex:hasStudent, ex:hasFriend,\n"
                f"                  ex:hasFather, ex:hasSon, ex:hasFounder, ex:influencedBy))\n"
                f"}}"
            )

        if intent == "ask_path":
            # 路径查询需要两个实体，暂时取前两个
            # (简化处理，仅查询直接关系)
            return (
                f"{p}"
                f"SELECT ?rel ?targetName WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  ?person ?rel ?target .\n"
                f"  ?target ex:personName ?targetName .\n"
                f"  FILTER(?rel IN (ex:hasTeacher, ex:hasStudent, ex:hasFriend,\n"
                f"                  ex:hasFather, ex:hasSon))\n"
                f"}}"
            )

        if intent == "ask_founder":
            return (
                f"{p}"
                f"SELECT ?founderName WHERE {{\n"
                f"  ?school ex:schoolName ?schoolName .\n"
                f"  FILTER(CONTAINS(?schoolName, \"{person}\"))\n"
                f"  ?person ex:hasFounder ?school .\n"
                f"  ?person ex:personName ?founderName .\n"
                f"}}"
            )

        if intent == "ask_biography":
            return (
                f"{p}"
                f"SELECT ?biography WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  ?person ex:biography ?biography .\n"
                f"}}"
            )

        if intent == "ask_masterpiece":
            return (
                f"{p}"
                f"SELECT ?masterpiece WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  ?person ex:masterpiece ?masterpiece .\n"
                f"}}"
            )

        # 通用查询
        return (
            f"{p}"
            f"SELECT ?p ?o WHERE {{\n"
            f"  ?person ex:personName \"{person}\" .\n"
            f"  ?person ?p ?o .\n"
            f"  FILTER(?p NOT IN (ex:personName, ex:confidence, ex:dataSource,\n"
            f"                   ex:extractionMethod, ex:ctextId, ex:cbdbId))\n"
            f"}}"
        )

    def _llm_generate(self, question: str, entities: List[str]) -> Optional[str]:
        """通过 LLM 生成 SPARQL。"""
        try:
            import httpx
            from ..utils.config import OLLAMA_BASE_URL, OLLAMA_MODEL

            examples_text = "\n".join(
                f"问：{ex['question']}\nSPARQL：\n{ex['sparql']}"
                for ex in SPARQL_EXAMPLES
            )

            prompt = (
                "你是一个 SPARQL 查询生成器，根据用户问题生成可执行的 SPARQL 查询。\n\n"
                "本体谓词参考（http://example.org/inkperson/）：\n"
                "- ex:personName / ex:styleName / ex:hao\n"
                "- ex:birthYear / ex:deathYear / ex:nativePlace / ex:dynasty\n"
                "- ex:hasTeacher / ex:hasStudent（师承）\n"
                "- ex:hasFather / ex:hasSon（亲属）\n"
                "- ex:hasFriend（交游）\n"
                "- ex:belongsToSchool / ex:hasFounder（流派）\n"
                "- ex:schoolName / ex:period（流派属性）\n\n"
                f"Few-shot 示例：\n{examples_text}\n\n"
                f"问题：{question}\n识别人物：{entities}\n\n"
                "请仅输出 SPARQL 语句（以 PREFIX 或 SELECT 开头，不要有其他文字）："
            )

            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_predict": 512, "temperature": 0.1},
                    },
                )
                if resp.status_code != 200:
                    return None

                raw = resp.json().get("response", "").strip()
                return self._extract_sparql(raw)

        except Exception as e:
            logger.error(f"LLM SPARQL generation failed: {e}")
            return None

    def _extract_sparql(self, text: str) -> Optional[str]:
        """从 LLM 输出中提取 SPARQL。"""
        text = text.strip()
        start = text.find("PREFIX")
        if start == -1:
            start = text.find("SELECT")
        if start == -1:
            return None
        end = max(text.rfind("}"), text.rfind("} ."))
        if end == -1:
            end = len(text)
        return text[start:end + 1].strip()
