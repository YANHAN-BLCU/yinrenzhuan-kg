"""
基于大语言模型（LLM）的命名实体抽取模块。

采用 Few-shot Learning + 结构化 RDF Turtle 输出方案，
直接从文本中抽取五类核心实体：历史人物、地理名称、时间点/段、书法书体、篆刻印风。
"""
import json
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import httpx

from ..utils.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from .entity_normalizer import PersonNormalizer

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """标准化实体表示，与 RDF Turtle 语义对齐。"""
    name: str
    type: str           # PERSON | PLACE | PERIOD | STYLE | SCHOOL
    confidence: float = 0.85
    evidence: str = ""  # 原文片段
    normalized: str = ""  # 归一化后的标准名称


@dataclass
class NERResult:
    entities: List[Entity] = field(default_factory=list)
    raw_text: str = ""
    entry_title: str = ""
    entry_chapter: str = ""


class LLMENTyper:
    """
    LLM-based NER with Few-shot Learning + structured RDF Turtle output.

    引导 LLM 直接输出符合 RDF Turtle 语义的结构化实体列表，
    确保格式统一、可直接映射到 RDF 图谱。

    LLM 不可用时，自动回退到正则规则抽取。
    """

    SYSTEM_PROMPT = (
        "你是一位专业的古籍信息抽取专家，擅长从《印人传》文本中识别并抽取标准化实体。\n"
        "你必须严格按 RDF Turtle 语义输出结构化实体列表。"
    )

    FEW_SHOT_EXAMPLES = """
【示例文本】
文彭，字壽承，號三橋，為待詔公子，休承郡博兄。其印章始自文國博，在南監與文徵仲友善。嘉靖年間活躍於蘇州吳門，自開吳門印派，傳何主臣。

【抽取结果】（严格按此 JSON 格式输出，不要有任何额外文字）
{
  "entities": [
    {"name": "文彭", "type": "PERSON", "confidence": 0.95, "evidence": "文彭，字壽承，號三橋"},
    {"name": "壽承", "type": "STYLE", "confidence": 0.95, "evidence": "文彭，字壽承"},
    {"name": "三橋", "type": "STYLE", "confidence": 0.95, "evidence": "號三橋"},
    {"name": "待詔公子", "type": "STYLE", "confidence": 0.80, "evidence": "待詔公子"},
    {"name": "休承郡博兄", "type": "STYLE", "confidence": 0.70, "evidence": "休承郡博兄"},
    {"name": "文徵仲", "type": "PERSON", "confidence": 0.93, "evidence": "在南京與文徵仲友善"},
    {"name": "嘉靖", "type": "PERIOD", "confidence": 0.95, "evidence": "嘉靖年間"},
    {"name": "蘇州", "type": "PLACE", "confidence": 0.95, "evidence": "活躍於蘇州"},
    {"name": "吳門", "type": "PLACE", "confidence": 0.90, "evidence": "吳門"},
    {"name": "吳門印派", "type": "SCHOOL", "confidence": 0.95, "evidence": "吳門印派"},
    {"name": "何主臣", "type": "PERSON", "confidence": 0.93, "evidence": "傳何主臣"}
  ]
}
"""

    USER_PROMPT_TEMPLATE = (
        "请从以下《印人传》文本中抽取所有实体。\n\n"
        "【实体类型定义】\n"
        "- PERSON: 历史人物（印人、作者、官员等），如 文彭、何震、丁敬\n"
        "- PLACE: 地理名称（地名、城市、区域），如 蘇州、杭州、吳門、金陵\n"
        "- PERIOD: 时间点/段（年号、朝代、年代），如 嘉靖、萬曆、明代、清初\n"
        "- STYLE: 书法书体或篆刻印风，如 元朱文、白文、秦漢印風、婉秀、蒼勁\n"
        "- SCHOOL: 篆刻流派名称，如 吳門印派、浙派、皖派、徽派、漳海派\n\n"
        "【抽取要求】\n"
        "1. 只输出 JSON，不要有其他任何文字\n"
        "2. confidence 取值范围 [0.7, 1.0]，根据抽取把握程度给定\n"
        "3. evidence 填写原文片段（10-30字），说明为何判定为该类型\n"
        "4. 对人物字号（字、號）统一标注为 STYLE 类型\n"
        "5. 若某实体在文本中多次出现，仍只列一次\n\n"
        "【格式】\n"
        '{{"entities": [{{"name": "实体名", "type": "类型", "confidence": 0.xx, "evidence": "原文片段"}}]}}\n\n'
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
            logger.warning(f"Ollama not available at {self.base_url}, LLM NER disabled")
            return False

    def extract(self, text: str, entry_title: str = "", entry_chapter: str = "") -> NERResult:
        """对单条文本执行 NER 抽取（LLM优先，规则兜底）。"""
        if self.available:
            return self._extract_by_llm(text, entry_title, entry_chapter)
        else:
            return self._extract_by_rules(text, entry_title, entry_chapter)

    def _extract_by_llm(self, text: str, entry_title: str, entry_chapter: str) -> NERResult:
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
                    logger.error(f"LLM NER request failed: {resp.status_code}")
                    return self._extract_by_rules(text, entry_title, entry_chapter)

                raw_output = resp.json().get("response", "")
                return self._parse_llm_output(raw_output, text, entry_title, entry_chapter)

        except Exception as e:
            logger.error(f"LLM NER extraction failed: {e}")
            return self._extract_by_rules(text, entry_title, entry_chapter)

    def _parse_llm_output(self, raw: str, text: str,
                           entry_title: str, entry_chapter: str) -> NERResult:
        result = NERResult(raw_text=text, entry_title=entry_title, entry_chapter=entry_chapter)

        raw = raw.strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            logger.warning("No JSON found in LLM NER output, falling back to rules")
            return self._extract_by_rules(text, entry_title, entry_chapter)

        try:
            data = json.loads(raw[start:end])
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM NER JSON: {e}")
            return self._extract_by_rules(text, entry_title, entry_chapter)

        entities = data.get("entities", [])
        seen = set()
        for item in entities:
            name = item.get("name", "").strip()
            etype = item.get("type", "").strip().upper()
            if not name or etype not in {"PERSON", "PLACE", "PERIOD", "STYLE", "SCHOOL"}:
                continue

            key = (name, etype)
            if key in seen:
                continue
            seen.add(key)

            norm_result = self._person_normalizer.normalize(name) if etype == "PERSON" else None
            std_name = norm_result.normalized if norm_result else name

            result.entities.append(Entity(
                name=name,
                type=etype,
                confidence=float(item.get("confidence", 0.85)),
                evidence=item.get("evidence", ""),
                normalized=std_name,
            ))

        logger.debug(f"LLM NER: {len(result.entities)} entities from '{entry_title}'")
        return result

    def _extract_by_rules(self, text: str, entry_title: str, entry_chapter: str) -> NERResult:
        """LLM 不可用时，使用正则规则抽取。"""
        from .ner_rules import NERRules

        result = NERResult(raw_text=text, entry_title=entry_title, entry_chapter=entry_chapter)
        ner = NERRules()
        ner_result = ner.extract_all(text)

        seen = set()
        for e in ner_result.entities:
            key = (e.text, e.type)
            if key in seen:
                continue
            seen.add(key)

            norm_result = self._person_normalizer.normalize(e.text) if e.type == "PERSON" else None
            std_name = norm_result.normalized if norm_result else e.text

            result.entities.append(Entity(
                name=e.text,
                type=e.type,
                confidence=e.confidence,
                evidence=e.evidence,
                normalized=std_name,
            ))

        return result
