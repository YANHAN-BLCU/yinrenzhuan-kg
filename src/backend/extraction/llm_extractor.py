import json
import logging
from typing import List, Optional
from dataclasses import dataclass
import httpx
from ..utils.config import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)


@dataclass
class LLMExtractedTriple:
    subject: str
    predicate: str
    obj: str
    confidence: float
    evidence: str


class LLMExtractor:
    SYSTEM_PROMPT = (
        "你是一位专业的古籍信息抽取专家，专门从《印人传》文本中抽取人物关系三元组。"
        "请严格按JSON Schema格式输出，抽取所有可能的关系三元组。"
    )

    USER_PROMPT_TEMPLATE = (
        '请从以下《印人传》文本中抽取所有人物关系三元组。'
        "关系类型包括：\n"
        "  - styleName: 人的字（如：文彭，字寿承）\n"
        "  - hao: 人的号（如：文彭，号三桥）\n"
        "  - sonOf: 父子关系（子 -> 父）\n"
        "  - fatherOf: 父子关系（父 -> 子）\n"
        "  - studentOf: 师承关系（徒弟 -> 师父）\n"
        "  - teacherOf: 师承关系（师父 -> 徒弟）\n"
        "  - friendOf: 交游关系\n"
        "  - belongsToSchool: 所属流派\n"
        "  - foundedSchool: 开创流派\n"
        "  - fromPlace: 籍贯/所在地\n"
        "  - dynasty: 朝代\n"
        "  - appellation: 其他称谓/别名\n"
        "\n"
        "文本：\n{text}\n"
        "\n"
        "请以以下JSON格式输出（仅输出JSON，不要有其他内容）：\n"
        '{\n  "relations": [\n    {\n      "subject": "人物A",\n      "predicate": "关系类型",\n      "object": "人物B或属性值",\n      "confidence": 0.85,\n      "evidence": "原文片段"\n    }\n  ]\n}\n'
    )

    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL):
        self.base_url = base_url
        self.model = model
        self.available = self._check_availability()

    def _check_availability(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            logger.warning(f"Ollama not available at {self.base_url}, LLM extraction disabled")
            return False

    def extract(self, text: str, max_tokens: int = 512) -> List[LLMExtractedTriple]:
        if not self.available:
            return []

        if len(text) > 2000:
            text = text[:2000]

        user_prompt = self.USER_PROMPT_TEMPLATE.format(text=text)

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": user_prompt,
                        "system": self.SYSTEM_PROMPT,
                        "stream": False,
                        "options": {"num_predict": 512},
                    },
                )
                if resp.status_code != 200:
                    logger.error(f"LLM request failed: {resp.status_code}")
                    return []

                result_text = resp.json().get("response", "")
                return self._parse_json_output(result_text)

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return []

    def _parse_json_output(self, text: str) -> List[LLMExtractedTriple]:
        text = text.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            logger.warning("No JSON found in LLM output")
            return []

        try:
            data = json.loads(text[start:end])
            triples = []
            for rel in data.get("relations", []):
                triples.append(LLMExtractedTriple(
                    subject=rel.get("subject", ""),
                    predicate=rel.get("predicate", ""),
                    obj=rel.get("object", ""),
                    confidence=rel.get("confidence", 0.80),
                    evidence=rel.get("evidence", ""),
                ))
            logger.info(f"LLM extracted {len(triples)} triples")
            return triples
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM JSON: {e}")
            return []
