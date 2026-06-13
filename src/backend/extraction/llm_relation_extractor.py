"""
基于大语言模型（LLM）的人物关系抽取模块。

采用预定义关系 Schema + Few-shot Learning + RDF Turtle 语义映射方案，
从文本中抽取标准化人物关系三元组。

关系 Schema：
  kinship:fatherOf / kinship:sonOf          — 亲属
  education:teacherOf / education:studentOf — 师承
  social:friendOf                          — 交游
  school:founderOf / school:belongsTo      — 流派
  attribute:hasStyleName                   — 字号
  attribute:hasHao                         — 号
  attribute:nativePlace                   — 籍贯
  attribute:dynasty                       — 朝代
"""
import json
import logging
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
import httpx

from ..utils.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from .entity_normalizer import PersonNormalizer

logger = logging.getLogger(__name__)


@dataclass
class RelationTriple:
    """标准化关系三元组，谓词严格对应预定义 Schema。"""
    subject: str
    predicate: str
    obj: str
    confidence: float = 0.85
    evidence: str = ""
    chapter: str = ""
    source_text: str = ""


PREDICATE_ALIAS_MAP: Dict[str, str] = {
    "styleName": "attribute:hasStyleName",
    "hao": "attribute:hasHao",
    "fatherOf": "kinship:fatherOf",
    "sonOf": "kinship:sonOf",
    "ancestorOf": "kinship:ancestorOf",
    "descendantOf": "kinship:descendantOf",
    "teacherOf": "education:teacherOf",
    "studentOf": "education:studentOf",
    "friendOf": "social:friendOf",
    "influencedBy": "social:influencedBy",
    "foundedSchool": "school:founderOf",
    "belongsToSchool": "school:belongsTo",
    "nativePlace": "attribute:nativePlace",
    "fromPlace": "attribute:nativePlace",
    "dynasty": "attribute:dynasty",
    "appellation": "attribute:hasAppellation",
    "inheritedFrom": "education:inheritedFrom",
}


def normalize_predicate(pred: str) -> str:
    """将抽取得到的自由谓词映射到标准 Schema 谓词。"""
    return PREDICATE_ALIAS_MAP.get(pred.strip(), pred.strip())


class LLMRelationExtractor:
    """
    LLM-based Relation Extraction with pre-defined Schema mapping.

    设计要点：
    1. Few-shot 示例明确展示每个关系类型如何映射到 Schema 谓词
    2. 输出 JSON，predicates 直接使用 Schema 格式
    3. 置信度 < 0.75 的关系标记为待审核
    4. 师承/亲属关系自动添加双向谓词
    """

    SYSTEM_PROMPT = (
        "你是一位专业的古籍信息抽取专家，擅长从《印人传》文本中抽取人物关系三元组。\n"
        "你必须严格将关系映射到预定义的 Schema 谓词，确保无歧义、可推理。"
    )

    FEW_SHOT_EXAMPLES = """
【示例文本】
文彭，字壽承，號三橋，為待詔公子。其印章自文國博開之，傳何主臣。千秋繼何主臣起，主臣之於文國博，蓋在師友間。

【抽取结果】（严格按此 JSON 格式输出，不要有任何额外文字）
{
  "relations": [
    {
      "subject": "文彭",
      "predicate": "attribute:hasStyleName",
      "object": "壽承",
      "confidence": 0.95,
      "evidence": "文彭，字壽承"
    },
    {
      "subject": "文彭",
      "predicate": "attribute:hasHao",
      "object": "三橋",
      "confidence": 0.95,
      "evidence": "號三橋"
    },
    {
      "subject": "文彭",
      "predicate": "school:founderOf",
      "object": "吳門印派",
      "confidence": 0.90,
      "evidence": "其印章自文國博開之"
    },
    {
      "subject": "何震",
      "predicate": "education:studentOf",
      "object": "文彭",
      "confidence": 0.93,
      "evidence": "傳何主臣；主臣之於文國博，在師友間"
    },
    {
      "subject": "梁千秋",
      "predicate": "education:studentOf",
      "object": "何震",
      "confidence": 0.93,
      "evidence": "千秋繼何主臣起"
    }
  ],
  "review_items": []
}
"""

    USER_PROMPT_TEMPLATE = (
        "请从以下《印人传》文本中抽取所有人物关系三元组。\n\n"
        "【预定义关系 Schema】（必须严格使用以下谓词）\n\n"
        "【亲属关系】\n"
        "  kinship:fatherOf    — 父子关系（父 → 子）\n"
        "  kinship:sonOf       — 父子关系（子 → 父）\n"
        "  kinship:ancestorOf — 祖孙关系\n\n"
        "【师承关系】\n"
        "  education:teacherOf   — 师承（师父 → 徒弟）\n"
        "  education:studentOf   — 师承（徒弟 → 师父）\n"
        "  education:inheritedFrom — 继承\n\n"
        "【交游关系】\n"
        "  social:friendOf      — 友人交往\n"
        "  social:influencedBy  — 受影响\n\n"
        "【流派关系】\n"
        "  school:founderOf  — 开创流派\n"
        "  school:belongsTo  — 所属流派\n\n"
        "【属性关系】\n"
        "  attribute:hasStyleName   — 字（字号）\n"
        "  attribute:hasHao        — 号\n"
        "  attribute:hasAppellation — 别名/称谓\n"
        "  attribute:nativePlace   — 籍贯\n"
        "  attribute:dynasty       — 朝代\n\n"
        "【抽取要求】\n"
        "1. 仅输出 JSON，不要有任何其他文字\n"
        "2. predicate 必须从上述 Schema 中选择\n"
        "3. confidence 取值范围 [0.7, 1.0]\n"
        "4. evidence 填写原文片段（15-40字）\n"
        "5. 置信度 < 0.75 时，review 设为 true\n\n"
        "【格式】\n"
        '{{"relations": [{{"subject": "人物A", "predicate": "谓词", "object": "人物B或属性值", '
        '"confidence": 0.xx, "evidence": "原文片段"}}], "review_items": []}}\n\n'
        "【待抽取文本】\n"
        "{text}\n"
    )

    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL,
                 use_rules_only: bool = False):
        self.base_url = base_url
        self.model = model
        self.use_rules_only = use_rules_only
        self.available = False if use_rules_only else self._check_availability()
        self._person_normalizer = PersonNormalizer()

    def _check_availability(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            logger.warning(f"Ollama not available, LLM relation extraction disabled")
            return False

    def extract(self, text: str, known_persons: Optional[Set[str]] = None,
                entry_title: str = "", entry_chapter: str = "") -> List[RelationTriple]:
        """对单条文本执行关系抽取（LLM优先，规则兜底）。"""
        if self.available:
            return self._extract_by_llm(text, known_persons, entry_title, entry_chapter)
        else:
            return self._extract_by_rules(text, known_persons, entry_title, entry_chapter)

    def _extract_by_llm(self, text: str, known_persons: Optional[Set[str]],
                          entry_title: str, entry_chapter: str) -> List[RelationTriple]:
        if len(text) > 1500:
            text = text[:1500]

        user_prompt = self.USER_PROMPT_TEMPLATE.format(text=text)
        full_prompt = (
            f"{self.SYSTEM_PROMPT}\n\n"
            f"【Few-shot 示例】\n{self.FEW_SHOT_EXAMPLES}\n\n"
            f"{user_prompt}"
        )

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {"num_predict": 1024, "temperature": 0.1},
                    },
                )
                if resp.status_code != 200:
                    logger.error(f"LLM relation request failed: {resp.status_code}")
                    return self._extract_by_rules(text, known_persons, entry_title, entry_chapter)

                raw_output = resp.json().get("response", "")
                return self._parse_llm_output(raw_output, known_persons, entry_title, entry_chapter)

        except Exception as e:
            logger.error(f"LLM relation extraction failed: {e}")
            return self._extract_by_rules(text, known_persons, entry_title, entry_chapter)

    def _parse_llm_output(self, raw: str, known_persons: Optional[Set[str]],
                           entry_title: str, entry_chapter: str) -> List[RelationTriple]:
        raw = raw.strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            logger.warning("No JSON in LLM relation output, falling back to rules")
            return self._extract_by_rules("", known_persons, entry_title, entry_chapter)

        try:
            data = json.loads(raw[start:end])
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM relation JSON: {e}")
            return self._extract_by_rules("", known_persons, entry_title, entry_chapter)

        triples = []
        seen = set()
        known = known_persons or set()

        for item in data.get("relations", []):
            subj = item.get("subject", "").strip()
            pred = item.get("predicate", "").strip()
            obj = item.get("object", "").strip()
            if not subj or not obj:
                continue

            subj_norm = self._person_normalizer.normalize(subj).normalized
            obj_norm = self._person_normalizer.normalize(obj).normalized
            pred_norm = normalize_predicate(pred)

            key = (subj_norm, pred_norm, obj_norm)
            if key in seen:
                continue
            seen.add(key)

            if subj_norm not in known:
                continue

            conf = float(item.get("confidence", 0.85))

            triples.append(RelationTriple(
                subject=subj_norm,
                predicate=pred_norm,
                obj=obj_norm,
                confidence=conf,
                evidence=item.get("evidence", ""),
                chapter=entry_chapter,
                source_text=entry_title,
            ))

            self._add_inverse_relation(triples, subj_norm, pred_norm, obj_norm, conf,
                                       item.get("evidence", ""), entry_chapter, entry_title)

        review_items = data.get("review_items", [])
        if review_items:
            logger.info(f"LLM relation: {len(review_items)} items need review")

        logger.debug(f"LLM relation: {len(triples)} triples from '{entry_title}'")
        return triples

    def _add_inverse_relation(self, triples: List[RelationTriple], subj: str, pred: str,
                                obj: str, conf: float, evidence: str,
                                chapter: str, source_text: str):
        """为师承/亲属关系自动添加反向谓词。"""
        inverse_map = {
            "education:studentOf": "education:teacherOf",
            "education:teacherOf": "education:studentOf",
            "kinship:fatherOf": "kinship:sonOf",
            "kinship:sonOf": "kinship:fatherOf",
        }
        inv_pred = inverse_map.get(pred)
        if inv_pred:
            seen_key = (obj, inv_pred, subj)
            seen = {(t.subject, t.predicate, t.obj) for t in triples}
            if seen_key not in seen:
                triples.append(RelationTriple(
                    subject=obj,
                    predicate=inv_pred,
                    obj=subj,
                    confidence=conf,
                    evidence=evidence,
                    chapter=chapter,
                    source_text=source_text,
                ))

    def _extract_by_rules(self, text: str, known_persons: Optional[Set[str]],
                            entry_title: str, entry_chapter: str) -> List[RelationTriple]:
        """LLM 不可用时，使用正则规则抽取。"""
        from .relation_extractor import RelationExtractor as RuleExtractor

        if not text:
            return []

        extractor = RuleExtractor()
        result = extractor.extract_from_entry(text, entry_title, entry_chapter, known_persons)

        triples = []
        for t in result.triples:
            subj_norm = self._person_normalizer.normalize(t.subject).normalized
            obj_norm = self._person_normalizer.normalize(t.obj).normalized
            pred_norm = normalize_predicate(t.predicate)

            triples.append(RelationTriple(
                subject=subj_norm,
                predicate=pred_norm,
                obj=obj_norm,
                confidence=t.confidence,
                evidence=t.evidence,
                chapter=entry_chapter,
                source_text=entry_title,
            ))

            self._add_inverse_relation(triples, subj_norm, pred_norm, obj_norm,
                                        t.confidence, t.evidence, entry_chapter, entry_title)

        return triples
