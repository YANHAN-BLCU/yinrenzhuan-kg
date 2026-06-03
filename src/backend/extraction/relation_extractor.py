import re
import logging
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTriple:
    subject: str
    predicate: str
    obj: str
    confidence: float
    method: str
    evidence: str
    chapter: str = ""
    source_text: str = ""


@dataclass
class ExtractionResult:
    triples: List[ExtractedTriple] = field(default_factory=list)
    entry_title: str = ""


class RelationExtractor:

    def extract_from_entry(self, text: str, title: str = "", chapter: str = "",
                          known_persons: Optional[Set[str]] = None) -> ExtractionResult:
        result = ExtractionResult(entry_title=title)
        if known_persons is None:
            known_persons = set()

        seen = set()

        def add(key, subj, pred, obj, conf, evidence):
            if key in seen:
                return
            seen.add(key)
            result.triples.append(ExtractedTriple(
                subject=subj, predicate=pred, obj=obj,
                confidence=conf, method="ner-scoped",
                evidence=evidence, chapter=chapter, source_text=title,
            ))

        def add_bidir(key1, key2, subj1, pred1, obj1, subj2, pred2, obj2, conf, evidence):
            add(key1, subj1, pred1, obj1, conf, evidence)
            add(key2, subj2, pred2, obj2, conf, evidence)

        def extract_names(chunk: str) -> List[str]:
            return [p for p in known_persons if p in chunk]

        def ctx(pos: int, length: int = 40) -> str:
            return text[max(0, pos - length // 2):min(len(text), pos + length // 2)]

        # Sort by length descending
        sorted_persons = sorted(known_persons, key=len, reverse=True)

        # =============================================================
        # 1. 师承：千秋繼何主臣起 / 梁千秋繼何主臣起
        # =============================================================
        for m in re.finditer(r"[\u4e00-\u9fa5]{2,4}繼[\u4e00-\u9fa5]{2,4}起", text):
            chunk = m.group(0)
            names = extract_names(chunk)
            if len(names) >= 2:
                subj, obj = names[0], names[1]
                if subj != obj:
                    ev = ctx(m.start())
                    add_bidir(
                        f"studentOf:{subj}:{obj}", f"teacherOf:{obj}:{subj}",
                        subj, "studentOf", obj, obj, "teacherOf", subj,
                        0.93, ev
                    )

        # =============================================================
        # 2. 字/号：文彭，字壽承 / 文彭，一字六水 / 何主臣震，一字長卿
        # =============================================================
        for m in re.finditer(
                r"[\u4e00-\u9fa5]{2,4}[，,，\s]*(?:字|號|一字|亦稱)[^\u4e00-\u9fa5\n]{0,10}",
                text):
            chunk = m.group(0)
            names = extract_names(chunk)
            if names:
                subj = names[0]
                style_chunk = chunk.replace(subj, "")
                # Remove all punctuation and 字号 markers
                style = re.sub(r"^[，,\s]+(?:字|號|一字|亦稱)", "", style_chunk)
                style = style.strip("，,\s")
                # Take only the first part before the next comma/号
                if style:
                    # Only take the first name/surname part
                    parts = re.split(r"[，,，]", style)
                    style = parts[0].strip()
                if style and 1 <= len(style) <= 8:
                    add(f"styleName:{subj}:{style}", subj, "styleName", style, 0.95, ctx(m.start()))

        # =============================================================
        # 3. 师承：X得之Y
        # =============================================================
        for m in re.finditer(r"[\u4e00-\u9fa5]{2,4}得之[\u4e00-\u9fa5]{2,4}", text):
            chunk = m.group(0)
            names = extract_names(chunk)
            if len(names) >= 2:
                subj, obj = names[0], names[1]
                if subj != obj:
                    ev = ctx(m.start())
                    add_bidir(
                        f"studentOf:{subj}:{obj}", f"teacherOf:{obj}:{subj}",
                        subj, "studentOf", obj, obj, "teacherOf", subj,
                        0.91, ev
                    )

        # =============================================================
        # 4. 师友：X於Y師友間 / X從Y討論 / X從Y得凍石
        # =============================================================
        for m in re.finditer(
                r"[\u4e00-\u9fa5]{2,4}[於從][\u4e00-\u9fa5]{2,4}(?:師友間|討論|得凍石)",
                text):
            chunk = m.group(0)
            names = extract_names(chunk)
            if len(names) >= 2:
                subj, obj = names[0], names[1]
                if subj != obj:
                    ev = ctx(m.start())
                    add_bidir(
                        f"studentOf:{subj}:{obj}", f"teacherOf:{obj}:{subj}",
                        subj, "studentOf", obj, obj, "teacherOf", subj,
                        0.90, ev
                    )

        # =============================================================
        # 5. 开创：自文彭開之 / 自文彭開吳門印派 / 文彭開吳門印派
        # =============================================================
        for m in re.finditer(r"自?[\u4e00-\u9fa5]{2,4}開(?:之|[之派][\u4e00-\u9fa5]{0,10}派?)", text):
            chunk = m.group(0)
            names = extract_names(chunk)
            if names:
                subj = names[0]
                after = text[m.end():m.end() + 30]
                school = self._detect_school(after)
                add(f"foundedSchool:{subj}:{school}", subj, "foundedSchool", school,
                    0.90, ctx(m.start()))

        # Also: X開YYY派 (without 自)
        for m in re.finditer(r"[\u4e00-\u9fa5]{2,4}開[\u4e00-\u9fa5]{2,4}派", text):
            chunk = m.group(0)
            names = extract_names(chunk)
            if names:
                subj = names[0]
                school = self._detect_school(chunk)
                add(f"foundedSchool:{subj}:{school}", subj, "foundedSchool", school,
                    0.88, ctx(m.start()))

        # =============================================================
        # 6. 籍贯：X為婺源人 / X之休寧人
        # =============================================================
        for m in re.finditer(
                r"[\u4e00-\u9fa5]{2,4}[之為是是屬][\u4e00-\u9fa5]{2,6}人",
                text):
            chunk = m.group(0)
            names = extract_names(chunk)
            if names:
                subj = names[0]
                place = chunk.replace(subj, "").strip("之為是屬")
                if place and len(place) >= 2 and place not in {"友人", "同人", "一人", "人人", "世人",
                                                                 "元人", "此人", "其人", "出人", "驚人"}:
                    add(f"nativePlace:{subj}:{place}", subj, "nativePlace", place,
                        0.90, ctx(m.start()))

        # =============================================================
        # 7. 流派隶属：X屬浙派 / X屬吳門印派
        # =============================================================
        for m in re.finditer(r"[\u4e00-\u9fa5]{2,4}(?:屬|為)[\u4e00-\u9fa5]{2,6}派", text):
            chunk = m.group(0)
            names = extract_names(chunk)
            if names:
                subj = names[0]
                school = self._detect_school(chunk)
                add(f"belongsToSchool:{subj}:{school}", subj, "belongsToSchool", school,
                    0.88, ctx(m.start()))

        # =============================================================
        # 8. 师承：X之傳Y / X私淑Y / X之弟子Y
        # =============================================================
        for m in re.finditer(
                r"[\u4e00-\u9fa5]{2,4}(?:之傳|私淑|之弟子)[\u4e00-\u9fa5]{2,4}",
                text):
            chunk = m.group(0)
            names = extract_names(chunk)
            if len(names) >= 2:
                subj, obj = names[0], names[1]
                if subj != obj:
                    ev = ctx(m.start())
                    add_bidir(
                        f"studentOf:{subj}:{obj}", f"teacherOf:{obj}:{subj}",
                        subj, "studentOf", obj, obj, "teacherOf", subj,
                        0.90, ev
                    )

        logger.debug(f"Extracted {len(result.triples)} triples from '{title}'")
        return result

    def _detect_school(self, chunk: str) -> str:
        school_map = {
            "吳門印派": "吳門印派", "吳門": "吳門印派",
            "浙派": "浙派", "浙": "浙派",
            "皖派": "皖派", "皖": "皖派", "徽派": "皖派",
            "漳海派": "漳海派", "漳海": "漳海派",
            "婁東派": "婁東派", "婁東": "婁東派",
            "莆田派": "莆田派", "莆田": "莆田派",
            "新安派": "皖派", "新安": "皖派",
            "錢塘派": "浙派", "錢塘": "浙派",
        }
        for kw, school in school_map.items():
            if kw in chunk:
                return school
        return "吳門印派"
