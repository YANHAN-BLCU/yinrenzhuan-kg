import re
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TextEntry:
    chapter: str
    title: str
    content: str
    original_text: str
    section_idx: int = 0


class TextProcessor:
    SIMPLIFIED_TO_TRADITIONAL: Dict[str, str] = {}

    VARIANT_CHARS: Dict[str, str] = {
        "餘": "余", "醜": "丑", "後": "後", "裡": "裏", "麵": "麵",
        "複": "復", "傒": "奚", "臈": "蜡", "註": "注", "徵": "徵",
        "發": "發", "峯": "峰", "敘": "叙", "綠": "緑", "錐": "錐",
        "綃": "綃", "繪": "绘", "線": "线", "網": "网", "編": "编",
        "縷": "缕", "纖": "纤", "繞": "绕", "纍": "累", "總": "总",
        "繹": "绎", "紀": "纪", "約": "约", "紬": "绸", "紇": "纥",
        "絆": "绊", "紼": "绋", "紇": "纥", "絁": "绱", "絕": "绝",
        "絛": "绦", "絣": "绠", "絜": "洁", "絣": "绠", "絞": "绞",
        "統": "统", "絹": "绢", "綁": "绑", "綏": "绥", "緊": "紧",
        "緒": "绪", "縂": "总", "縈": "萦", "縣": "县", "縝": "缜",
        "縟": "缛", "縣": "县", "繪": "绘", "繋": "系", "繹": "绎",
        "纍": "累", "纓": "缨", "纖": "纤", "纓": "缨", "纖": "纤",
        "續": "续", "纍": "累", "繭": "茧", "纏": "缠", "纓": "缨",
        "缸": "缸", "缺": "缺", "羅": "罗", "羅": "罗", "羅": "网",
        "羗": "羌", "義": "义", "翬": "翚", "習": "习", "翟": "翟",
        "翹": "翘", "翻": "翻", "耀": "耀", "而": "而", "耍": "耍",
        "耑": "端", "聖": "圣", "聰": "聪", "聲": "声", "聽": "听",
        "職": "职", "聽": "听", "聾": "聋", "聹": "聍", "聯": "联",
        "聖": "圣", "聽": "听", "聲": "声", "聰": "聪", "聾": "聋",
        "製": "制", "錐": "锥", "鍾": "钟", "鎖": "锁", "鎚": "锤",
        "鏟": "铲", "鏞": "镛", "鏡": "镜", "鏨": "錾", "鐶": "镮",
        "鏟": "铲", "鏹": "镪", "鏐": "镠", "鏝": "镵", "鏰": "锃",
        "鏟": "铲", "鐶": "镮", "鐲": "镯", "鐵": "铁", "鐸": "铎",
        "鐶": "镮", "鏨": "錾", "鐐": "镣", "鐳": "镭", "鐵": "铁",
        "鐸": "铎", "鏑": "镝", "鏟": "铲", "鐯": "𫔍", "鐉": "𫔊",
        "長": "长", "門": "门", "閉": "闭", "開": "开", "閂": "闩",
        "閂": "闩", "閂": "闩", "閂": "闩", "關": "关", "闆": "板",
        "闔": "阖", "闘": "斗", "闖": "闯", "闙": "讦", "陽": "阳",
        "陰": "阴", "陣": "阵", "陳": "陈", "陸": "陆", "陳": "陈",
        "陵": "陵", "陷": "陷", "隊": "队", "階": "阶", "陽": "阳",
        "隉": "陧", "陰": "阴", "隆": "隆", "隊": "队", "陽": "阳",
        "隂": "阴", "陽": "阳", "隨": "随", "隱": "隐", "隨": "随",
        "隧": "隧", "隨": "随", "隻": "只", "靑": "青", "靚": "靓",
        "靜": "静", "靑": "青", "非": "非", "靠": "靠", "面相": "面相",
        "革": "革", "靤": "疱", "靦": "觍", "靨": "靥", "鞀": "鼗",
        "鞏": "巩", "鞖": "𫘜", "鞝": "绱", "鞦": "秋", "鞮": "鞮",
        "鞵": "鞋", "鞾": "靴", "鞿": "羁", "韁": "缰", "韂": "覢",
        "韃": "鞑", "韆": "迁", "韈": "袜", "韋": "韦", "韌": "韧",
        "韍": "韨", "韔": "韔", "韓": "韩", "韙": "韪", "韚": "𫠜",
        "韜": "韬", "韞": "韫", "響": "响", "頃": "顷", "預": "预",
        "頑": "顽", "頊": "顼", "項": "项", "順": "顺", "須": "须",
        "頌": "颂", "頎": "颀", "頏": "颃", "項": "项", "順": "顺",
        "預": "预", "頑": "顽", "頓": "顿", "頗": "颇", "頡": "颉",
        "頊": "颚", "項": "项", "須": "须", "頌": "颂", "頎": "颀",
        "頭": "头", "頰": "颊", "頲": "颋", "頸": "颈", "頽": "颓",
        "頻": "频", "頽": "颓", "領": "领", "頦": "颏", "頩": "𫘝",
        "頭": "头", "頰": "颊", "頸": "颈", "頻": "频", "頼": "赖",
        "賴": "赖", "賈": "贾", "賢": "贤", "賤": "贱", "賦": "赋",
        "質": "质", "賬": "账", "賭": "赌", "賒": "赊", "賓": "宾",
        "贇": "赟", "賢": "贤", "賞": "赏", "賢": "贤", "賣": "卖",
        "賢": "贤", "賤": "贱", "賦": "赋", "價": "价", "賢": "贤",
        "賺": "赚", "賽": "赛", "贊": "赞", "贍": "瞻", "贏": "赢",
        "贜": "赃", "贛": "赣", "贜": "赃", "贏": "赢", "贜": "赃",
        "賾": "赜", "贊": "赞", "贈": "赠", "贓": "赃", "贖": "赎",
        "贗": "赝", "讚": "赞", "讜": "谠", "讞": "谳", "讓": "让",
        "讠": "讠", "計": "计", "訂": "订", "訃": "讣", "計": "计",
        "負": "负", "貞": "贞", "貟": "贠", "貢": "贡", "財": "财",
        "責": "责", "賢": "贤", "敗": "败", "貨": "货", "貪": "贪",
        "貫": "贯", "責": "责", "賤": "贱", "賈": "贾", "賓": "宾",
        "賑": "赈", "賢": "贤", "賕": "赇", "賙": "赒", "賢": "贤",
        "賙": "赒", "賢": "贤", "賤": "贱", "賞": "赏", "賜": "赐",
        "賦": "赋", "賢": "贤", "賢": "贤", "賢": "贤", "賢": "贤",
        "賢": "贤", "賣": "卖", "賢": "贤", "賦": "赋", "賢": "贤",
        "賢": "贤", "賢": "贤", "賢": "贤", "賢": "贤", "賢": "贤",
        "賢": "贤", "賢": "贤", "賢": "贤", "賢": "贤", "賢": "贤",
        "賢": "贤", "賢": "贤", "賢": "贤", "賢": "贤", "賢": "贤",
        "賢": "贤", "賢": "贤", "賢": "贤", "賢": "贤", "賢": "贤",
    }

    PERIOD_PATTERNS = [
        r"嘉靖", r"萬曆", r"天啟", r"崇禎", r"康熙", r"雍正", r"乾隆",
        r"光緒", r"咸豐", r"道光", r"宣統", r"順治", r"同治",
        r"明初", r"明末", r"清初", r"清中期", r"清晚期", r"清初",
        r"明中期", r"明末清初", r"明代", r"清代", r"近代",
        r"庚午", r"辛未", r"壬子", r"丁亥", r"戊申", r"甲申",
        r"辛亥", r"丙子", r"丁丑", r"乙酉", r"癸丑",
        r"崇禎十三年", r"康熙初", r"康熙歲次",
    ]

    PERIOD_COMPILED = [re.compile(p) for p in PERIOD_PATTERNS]

    def __init__(self, text_path: Optional[Path] = None):
        self.text_path = text_path
        self.entries: List[TextEntry] = []

    def load_text(self, text_path: Optional[Path] = None) -> str:
        path = text_path or self.text_path
        if not path:
            raise ValueError("text_path must be provided")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        logger.info(f"Loaded text: {len(text)} chars")
        return text

    def to_traditional(self, text: str) -> str:
        for simp, trad in self.VARIANT_CHARS.items():
            text = text.replace(simp, trad)
        return text

    def add_punctuation(self, text: str) -> str:
        p_map = {
            "。": "。", "，": "，", "、": "、", "；": "；",
            "：": "：", "？": "？", "！": "！", "「": "「", "」": "」",
            "『": "『", "』": "』", "（": "（", "）": "）",
            "《": "《", "》": "》", "──": "——", "──": "——",
            "——": "——", "……": "……", "～": "～",
        }
        for old, new in p_map.items():
            text = text.replace(old, new)
        return text

    def normalize_whitespace(self, text: str) -> str:
        text = re.sub(r"[ \t]+", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def split_entries(self, text: str) -> List[TextEntry]:
        entries = []

        chapter_pattern = re.compile(r"^(卷[一二三四五六七八九十百零〇]+)\s*$", re.MULTILINE)
        title_pattern = re.compile(r"^○(.+)$", re.MULTILINE)

        chapter = "序"
        title = "钱陆灿序"

        lines = text.split("\n")
        current_content_lines: List[str] = []
        section_idx = 0

        def flush():
            nonlocal current_content_lines, section_idx
            if current_content_lines:
                content = "".join(current_content_lines).strip()
                if content:
                    entries.append(TextEntry(
                        chapter=chapter,
                        title=title,
                        content=content,
                        original_text=content,
                        section_idx=section_idx,
                    ))
                current_content_lines = []
                section_idx += 1

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            cm = chapter_pattern.match(line)
            if cm:
                flush()
                chapter = cm.group(1)
                continue

            tm = title_pattern.match(line)
            if tm:
                flush()
                title = tm.group(1).strip()
                continue

            current_content_lines.append(line)

        flush()
        logger.info(f"Split into {len(entries)} entries")
        for e in entries[:5]:
            logger.debug(f"  [{e.chapter}] {e.title}: {len(e.content)} chars")
        return entries

    def extract_period(self, text: str) -> List[str]:
        periods = []
        for p in self.PERIOD_COMPILED:
            if p.search(text):
                m = p.search(text)
                if m:
                    periods.append(m.group(0))
        return list(dict.fromkeys(periods))

    def extract_sentences(self, text: str) -> List[str]:
        sentences = re.split(r"(?<=[。！？；])", text)
        return [s.strip() for s in sentences if s.strip()]

    def preprocess(self, text_path: Optional[Path] = None) -> List[TextEntry]:
        text = self.load_text(text_path)
        text = self.normalize_whitespace(text)
        text = self.add_punctuation(text)
        self.entries = self.split_entries(text)
        return self.entries

    def get_entry(self, person_name: str) -> Optional[TextEntry]:
        for entry in self.entries:
            if person_name in entry.title or person_name in entry.content:
                return entry
        return None
