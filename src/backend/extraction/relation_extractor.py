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

        # 关键修复：先把 known_persons 按长度从长到短排序。
        # 这样 find_names_at_position() 优先匹配最长人名，避免"程孟長" 错误覆盖 "程原"。
        sorted_persons = sorted(known_persons, key=len, reverse=True)

        def find_names_at_position(text: str, start: int, end: int) -> List[str]:
            """
            在 text[start:end] 范围内找出按出现顺序的已知人名。
            - 用 sort by length, reverse=True 保证长名优先匹配（防止"程孟長"覆盖"程原"）
            - 用位置检查避免重叠（已匹配的位置不再被覆盖）
            """
            chunk = text[start:end]
            used_spans = []  # list of (start, end)
            results = []  # list of (offset_in_chunk, name)

            for name in sorted_persons:
                if not name:
                    continue
                # 找出所有出现位置
                idx = 0
                while True:
                    pos = chunk.find(name, idx)
                    if pos == -1:
                        break
                    span = (pos, pos + len(name))
                    # 检查是否与已用区间重叠
                    if any(not (span[1] <= s or span[0] >= e) for s, e in used_spans):
                        idx = pos + 1
                        continue
                    used_spans.append(span)
                    results.append((pos, name))
                    idx = pos + len(name)  # 跳过当前匹配，继续往后找

            # 按出现顺序排序
            results.sort(key=lambda x: x[0])
            return [name for _, name in results]

        # 兼容旧 API：在 chunk 中按顺序找出所有人名（仍用长度优先，但简单版）
        def extract_names(chunk: str) -> List[str]:
            # 用 sorted_persons 优先匹配长名；按 chunk 中出现顺序返回
            used_spans = []
            results = []
            for name in sorted_persons:
                if not name:
                    continue
                idx = 0
                while True:
                    pos = chunk.find(name, idx)
                    if pos == -1:
                        break
                    span = (pos, pos + len(name))
                    if any(not (span[1] <= s or span[0] >= e) for s, e in used_spans):
                        idx = pos + 1
                        continue
                    used_spans.append(span)
                    results.append((pos, name))
                    idx = pos + len(name)
            results.sort(key=lambda x: x[0])
            return [n for _, n in results]

        def ctx(pos: int, length: int = 40) -> str:
            return text[max(0, pos - length // 2):min(len(text), pos + length // 2)]

        # =============================================================
        # 1. 师承：千秋繼何主臣起 / 梁千秋繼何主臣起
        # =============================================================
        for m in re.finditer(r"[\u4e00-\u9fa5]{2,8}繼[\u4e00-\u9fa5]{2,8}起", text):
            names = find_names_at_position(text, m.start(), m.end())
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
                r"[\u4e00-\u9fa5]{2,8}[，,，\s]*(?:字|號|一字|亦稱)[^\u4e00-\u9fa5\n]{0,10}",
                text):
            names = find_names_at_position(text, m.start(), m.end())
            if names:
                subj = names[0]
                chunk = text[m.start():m.end()]
                style_chunk = chunk.replace(subj, "")
                # Remove all punctuation and 字号 markers
                style = re.sub(r"^[，,\s]+(?:字|號|一字|亦稱)", "", style_chunk)
                style = style.strip(r"，,\s")
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
        for m in re.finditer(r"[\u4e00-\u9fa5]{2,8}得之[\u4e00-\u9fa5]{2,8}", text):
            names = find_names_at_position(text, m.start(), m.end())
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
        #    关键：X是学生、Y是老师，取名时按顺序即可
        #    例："主臣之於文國博" → 主臣(学生) 之於 文國博(老师)
        #    例："X從Y討論" → X(学生) 從 Y(老师)
        # =============================================================
        for m in re.finditer(
                r"[\u4e00-\u9fa5]{2,8}[於從][\u4e00-\u9fa5]{2,8}(?:師友間|討論|得凍石)",
                text):
            names = find_names_at_position(text, m.start(), m.end())
            if len(names) >= 2:
                subj, obj = names[0], names[1]
                if subj != obj:
                    ev = ctx(m.start())
                    # 顺序即语义：X於/從Y → X是学生(Subject)，Y是老师(Object)
                    add_bidir(
                        f"studentOf:{subj}:{obj}", f"teacherOf:{obj}:{subj}",
                        subj, "studentOf", obj, obj, "teacherOf", subj,
                        0.90, ev
                    )

        # =============================================================
        # 5. 开创：自文彭開之 / 自文彭開吳門印派 / 文彭開吳門印派
        # =============================================================
        for m in re.finditer(r"自?[\u4e00-\u9fa5]{2,8}開(?:之|[之派][\u4e00-\u9fa5]{0,10}派?)", text):
            names = find_names_at_position(text, m.start(), m.end())
            if names:
                subj = names[0]
                after = text[m.end():m.end() + 30]
                school = self._detect_school(after)
                if school:  # 只在能识别出流派时才添加
                    add(f"foundedSchool:{subj}:{school}", subj, "foundedSchool", school,
                        0.90, ctx(m.start()))

        # Also: X開YYY派 (without 自)
        for m in re.finditer(r"[\u4e00-\u9fa5]{2,8}開[\u4e00-\u9fa5]{2,8}派", text):
            names = find_names_at_position(text, m.start(), m.end())
            if names:
                subj = names[0]
                school = self._detect_school(text[m.start():m.end()])
                if school:  # 只在能识别出流派时才添加
                    add(f"foundedSchool:{subj}:{school}", subj, "foundedSchool", school,
                        0.88, ctx(m.start()))

        # =============================================================
        # 6. 籍贯：X為婺源人 / X之休寧人
        # =============================================================
        for m in re.finditer(
                r"[\u4e00-\u9fa5]{2,8}[之為是是屬][\u4e00-\u9fa5]{2,6}人",
                text):
            names = find_names_at_position(text, m.start(), m.end())
            if names:
                subj = names[0]
                chunk = text[m.start():m.end()]
                place = chunk.replace(subj, "").strip("之為是屬")
                if place and len(place) >= 2 and place not in {"友人", "同人", "一人", "人人", "世人",
                                                                 "元人", "此人", "其人", "出人", "驚人"}:
                    add(f"nativePlace:{subj}:{place}", subj, "nativePlace", place,
                        0.90, ctx(m.start()))

        # =============================================================
        # 7. 流派隶属：X屬浙派 / X屬吳門印派
        # =============================================================
        for m in re.finditer(r"[\u4e00-\u9fa5]{2,8}(?:屬|為)[\u4e00-\u9fa5]{2,6}派", text):
            names = find_names_at_position(text, m.start(), m.end())
            if names:
                subj = names[0]
                school = self._detect_school(text[m.start():m.end()])
                add(f"belongsToSchool:{subj}:{school}", subj, "belongsToSchool", school,
                    0.88, ctx(m.start()))

        # =============================================================
        # 8. 师承：X之傳Y / X私淑Y / X之弟子Y
        # =============================================================
        for m in re.finditer(
                r"[\u4e00-\u9fa5]{2,8}(?:之傳|私淑|之弟子)[\u4e00-\u9fa5]{2,8}",
                text):
            names = find_names_at_position(text, m.start(), m.end())
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
        # 9. 师承（跨词条模式，全文级人物）: "X從Y學…/X從Y治印/X得Y之傳"
        # 典型: "嚐從江高臣學印章" → 陶石公 studentOf 江高臣
        #       "中子與繩亦從君治印" → 程與繩 studentOf 程雲來(君)
        #       "得文氏之傳" → ? studentOf 文彭
        #       "行圖章得何氏之傳" → 鄭宏祐 studentOf 何震
        #       "嫡傳則獨有程孟長父子" → 程原/程樸 studentOf 何震
        # =============================================================
        # 9a. X 從 Y 學/治印
        for m in re.finditer(
                r"[\u4e00-\u9fa5]{2,8}從[\u4e00-\u9fa5]{2,8}(?:學|治|受學)",
                text):
            names = find_names_at_position(text, m.start(), m.end())
            if len(names) >= 2:
                subj, obj = names[0], names[1]
                if subj != obj:
                    ev = ctx(m.start())
                    add_bidir(
                        f"studentOf:{subj}:{obj}", f"teacherOf:{obj}:{subj}",
                        subj, "studentOf", obj, obj, "teacherOf", subj,
                        0.90, ev
                    )
        # 9b. X 得 Y (之) 傳  / X 學 Y / X 學於 Y
        for m in re.finditer(
                r"[\u4e00-\u9fa5]{2,8}得[\u4e00-\u9fa5]{2,8}(?:之)?傳",
                text):
            names = find_names_at_position(text, m.start(), m.end())
            if len(names) >= 2:
                subj, obj = names[0], names[1]
                if subj != obj:
                    ev = ctx(m.start())
                    add_bidir(
                        f"studentOf:{subj}:{obj}", f"teacherOf:{obj}:{subj}",
                        subj, "studentOf", obj, obj, "teacherOf", subj,
                        0.90, ev
                    )
        # 9c. "其嫡傳則獨有X"（X 是被传者）— 在引文/上下文里抓 "嫡傳則獨有X" 时，
        #     需借助本词条的主人物。这里检测 "X / Y父子" 时，要把 X/Y 加为 entry_title 的人物之弟子。
        for m in re.finditer(
                r"嫡傳則獨有[\u4e00-\u9fa5]{2,8}(?:父子|兄弟|兄弟子)",
                text):
            names = find_names_at_position(text, m.start(), m.end())
            if names:
                # 继承者 = names[0]，师承者 = 词条主角（entry_title）
                student_name = names[0]
                teacher_name = title.strip()  # 词条标题就是师承者
                if student_name and teacher_name and student_name != teacher_name:
                    ev = ctx(m.start())
                    add_bidir(
                        f"studentOf:{student_name}:{teacher_name}",
                        f"teacherOf:{teacher_name}:{student_name}",
                        student_name, "studentOf", teacher_name,
                        teacher_name, "teacherOf", student_name,
                        0.92, ev
                    )

        # =============================================================
        # 10. 师承：X師Y / X受業於Y
        # =============================================================
        for m in re.finditer(
                r"[\u4e00-\u9fa5]{2,8}師[\u4e00-\u9fa5]{2,8}|[\u4e00-\u9fa5]{2,8}受業於[\u4e00-\u9fa5]{2,8}",
                text):
            names = find_names_at_position(text, m.start(), m.end())
            if len(names) >= 2:
                subj, obj = names[0], names[1]
                if subj != obj:
                    ev = ctx(m.start())
                    add_bidir(
                        f"studentOf:{subj}:{obj}", f"teacherOf:{obj}:{subj}",
                        subj, "studentOf", obj, obj, "teacherOf", subj,
                        0.88, ev
                    )

        # =============================================================
        # 11. 继承 / 继起: "X繼Y起" / "X繼Y"（注意：X = 后继者，Y = 前辈）
        # 例: "千秋繼何主臣起" → 梁千秋 studentOf 何震 (已在#1覆盖)
        # 例: "子環、鶴生…劉漁仲、程穆倩合…為一" → 同派
        # =============================================================

        # =============================================================
        # 12. 仿/师：X仿Y / X法Y / X摹Y
        # 例: "印章好仿文何" / "其印章始自文國博"
        # =============================================================
        for m in re.finditer(
                r"[\u4e00-\u9fa5]{2,8}(?:仿|法|摹|摹倣)[\u4e00-\u9fa5]{2,8}",
                text):
            names = find_names_at_position(text, m.start(), m.end())
            if len(names) >= 2:
                subj, obj = names[0], names[1]
                if subj != obj:
                    ev = ctx(m.start())
                    # 仿/法/摹 → 学派传承（弱）
                    add(f"influencedBy:{subj}:{obj}", subj, "influencedBy", obj,
                        0.80, ev)

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
        # 返回空字符串而非默认值，防止未识别时错误默认为吳門印派
        return ""
