import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


SPARQL_FEW_SHOT_EXAMPLES = [
    {
        "question": "文彭的字是什么？",
        "sparql": (
            "PREFIX ex: <http://example.org/inkperson/>\n"
            "SELECT ?person ?styleName WHERE {\n"
            "  ?person ex:personName \"文彭\" .\n"
            "  ?person ex:styleName ?styleName .\n"
            "}"
        ),
    },
    {
        "question": "何震的师父是谁？",
        "sparql": (
            "PREFIX ex: <http://example.org/inkperson/>\n"
            "SELECT ?teacher ?teacherName WHERE {\n"
            "  ?person ex:personName \"何震\" .\n"
            "  ?person ex:studentOf ?teacher .\n"
            "  ?teacher ex:personName ?teacherName .\n"
            "}"
        ),
    },
    {
        "question": "吴门印派有哪些人？",
        "sparql": (
            "PREFIX ex: <http://example.org/inkperson/>\n"
            "SELECT ?person ?personName WHERE {\n"
            "  ?person ex:belongsToSchool ?school .\n"
            "  ?school ex:schoolName \"吳門印派\" .\n"
            "  ?person ex:personName ?personName .\n"
            "}"
        ),
    },
    {
        "question": "文彭和何震之间有什么关系？",
        "sparql": (
            "PREFIX ex: <http://example.org/inkperson/>\n"
            "SELECT ?mid ?midName WHERE {\n"
            "  ?personA ex:personName \"文彭\" .\n"
            "  ?personB ex:personName \"何震\" .\n"
            "  ?personA ex:teacherOf* ?mid .\n"
            "  ?mid ex:teacherOf* ?personB .\n"
            "  FILTER(?mid != ?personA && ?mid != ?personB)\n"
            "}"
        ),
    },
    {
        "question": "丁敬是哪个流派的？",
        "sparql": (
            "PREFIX ex: <http://example.org/inkperson/>\n"
            "SELECT ?school ?schoolName WHERE {\n"
            "  ?person ex:personName \"丁敬\" .\n"
            "  ?person ex:belongsToSchool ?school .\n"
            "  ?school ex:schoolName ?schoolName .\n"
            "}"
        ),
    },
]

SPARQL_CONSTRAINTS = (
    "生成SPARQL的约束：\n"
    "1. 所有SPARQL必须以 PREFIX ex: <http://example.org/inkperson/> 开头\n"
    "2. 谓词必须使用本体中定义的属性（如 ex:personName、ex:fatherOf、ex:teacherOf、"
    "ex:studentOf、ex:friendOf、ex:belongsToSchool、ex:foundedSchool、"
    "ex:styleName、ex:hao、ex:dynasty、ex:fromPlace）\n"
    "3. 变量使用 ? 前缀\n"
    "4. 使用 FILTER 进行字符串精确匹配\n"
    "5. 如果问句涉及流派，使用 ex:belongsToSchool 关联 school 节点，"
    "然后用 ex:schoolName 匹配流派名称\n"
    "6. 如果问句涉及师承关系，使用 ex:teacherOf 或 ex:studentOf\n"
    "7. 仅生成 SELECT 查询，不要生成 INSERT/DELETE 等修改语句\n"
)


class SPARQLGenerator:

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate(self, question: str, entities: List[str], intent: str) -> Optional[str]:
        if not self.llm_client:
            return self._rule_based_generate(question, entities, intent)

        examples_text = "\n".join(
            f'问：{ex["question"]}\nSPARQL：\n{ex["sparql"]}'
            for ex in SPARQL_FEW_SHOT_EXAMPLES
        )

        prompt = (
            f"你是一个SPARQL查询生成器，根据用户问题生成可执行的SPARQL语句。\n\n"
            f"{SPARQL_CONSTRAINTS}\n\n"
            f"Few-shot示例：\n{examples_text}\n\n"
            f"用户问题：{question}\n"
            f"识别到的实体：{entities}\n"
            f"意图：{intent}\n\n"
            f"请生成SPARQL查询（仅输出SPARQL语句，不要有其他内容）："
        )

        try:
            response = self.llm_client.generate(prompt)
            sparql = self._extract_sparql(response)
            if sparql:
                logger.info(f"Generated SPARQL: {sparql[:100]}...")
                return sparql
        except Exception as e:
            logger.error(f"SPARQL generation failed: {e}")

        return self._rule_based_generate(question, entities, intent)

    def _extract_sparql(self, text: str) -> Optional[str]:
        text = text.strip()
        start = text.find("PREFIX")
        if start == -1:
            start = text.find("SELECT")
        if start == -1:
            return None
        return text[start:].strip()

    def _rule_based_generate(self, question: str, entities: List[str], intent: str) -> Optional[str]:
        if not entities:
            return None

        person = entities[0]
        prefix = "PREFIX ex: <http://example.org/inkperson/>\n"

        if any(kw in question for kw in ["字", "styleName"]):
            return (
                f"{prefix}"
                f"SELECT ?person ?styleName WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  ?person ex:styleName ?styleName .\n"
                f"}}"
            )

        if any(kw in question for kw in ["号", "hao"]):
            return (
                f"{prefix}"
                f"SELECT ?person ?hao WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  ?person ex:hao ?hao .\n"
                f"}}"
            )

        if any(kw in question for kw in ["师", "师父", "老师", "teacher"]):
            return (
                f"{prefix}"
                f"SELECT ?teacher ?teacherName WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  ?person ex:studentOf ?teacher .\n"
                f"  ?teacher ex:personName ?teacherName .\n"
                f"}}"
            )

        if any(kw in question for kw in ["弟子", "徒弟", "学生", "student"]):
            return (
                f"{prefix}"
                f"SELECT ?student ?studentName WHERE {{\n"
                f"  ?teacher ex:personName \"{person}\" .\n"
                f"  ?teacher ex:studentOf ?student .\n"
                f"  ?student ex:personName ?studentName .\n"
                f"}}"
            )

        if any(kw in question for kw in ["派", "流派", "属于", "school"]):
            return (
                f"{prefix}"
                f"SELECT ?school ?schoolName WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  ?person ex:belongsToSchool ?school .\n"
                f"  ?school ex:schoolName ?schoolName .\n"
                f"}}"
            )

        if any(kw in question for kw in ["关系", "relationship"]):
            return (
                f"{prefix}"
                f"SELECT ?rel ?target WHERE {{\n"
                f"  ?person ex:personName \"{person}\" .\n"
                f"  ?person ?rel ?target .\n"
                f"  FILTER(STRSTARTS(STR(?rel), STR(ex:)) && ?rel != ex:personName && ?rel != ex:confidence)\n"
                f"}}"
            )

        return (
            f"{prefix}"
            f"SELECT ?p ?o WHERE {{\n"
            f"  ?person ex:personName \"{person}\" .\n"
            f"  ?person ?p ?o .\n"
            f"  FILTER(?p != ex:personName && ?p != ex:confidence)\n"
            f"}}"
        )
