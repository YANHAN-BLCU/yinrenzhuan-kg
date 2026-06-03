import re
import logging
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class NamedEntity:
    text: str
    type: str
    start: int
    end: int
    confidence: float = 0.95
    source: str = "rule"
    evidence: str = ""


@dataclass
class NERResult:
    entities: List[NamedEntity] = field(default_factory=list)
    raw_text: str = ""


class TrieNode:
    __slots__ = ('children', 'is_word', 'word')

    def __init__(self):
        self.children: Dict[str, TrieNode] = {}
        self.is_word: bool = False
        self.word: Optional[str] = None


class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str) -> None:
        node = self.root
        for ch in word:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.is_word = True
        node.word = word

    def match_at(self, text: str, pos: int) -> Optional[str]:
        node = self.root
        longest: Optional[str] = None
        i = pos
        while i < len(text):
            ch = text[i]
            if ch not in node.children:
                break
            node = node.children[ch]
            i += 1
            if node.is_word:
                longest = node.word
        return longest


class NERRules:

    PERSON_NAMES: Set[str] = {
        "文彭", "文壽承", "文國博", "何震", "何主臣", "何長卿",
        "丁敬", "丁敬身", "程邃", "程穆倩", "程孟長", "程六水",
        "程與繩", "程雲來", "程稚昭", "祝允明", "祝希哲",
        "文徵明", "文徵仲", "文衡山",
        "蘇宣", "蘇爾宣",
        "梁千秋", "梁大年", "梁袠",
        "黃學", "黃濟叔", "黃山松",
        "金一甫", "金光先",
        "沈世和", "沈石民",
        "林晉白", "林熊",
        "陳師黃", "陳玉石",
        "陳朝喗", "陳瑞聲",
        "黃子環", "黃克侯", "黃炳猷",
        "劉漁仲", "劉履丁",
        "沈鶴生", "吳午叔", "吳正陽",
        "張穉恭", "張恂",
        "汪尹子", "汪杲叔", "汪宏度", "汪泓",
        "汪宗周", "汪徽", "汪先之",
        "吳仁趾", "吳麐",
        "顧元方", "顧聽",
        "邱令和", "邱文",
        "胡中翰", "胡曰從",
        "許有介", "許友", "許友字", "許宰",
        "朱簡", "朱修能",
        "周亮工", "周櫟園",
        "萬年少", "萬壽祺", "慧壽",
        "姜次生", "姜正學",
        "陳濬",
        "李文甫", "李根", "李雲穀",
        "方仲芝", "方直之", "方東來",
        "李耕隱", "李悅已", "李尊",
        "徐之固", "徐堅",
        "鄭宏祐", "鄭基相",
        "陶石公", "陶碧",
        "江高臣",
        "鈿閣", "韓約素",
        "錢陸燦", "葉銘",
        "張彝令",
        "朱蘭嵎", "朱尚書",
        "曹秋嶽",
        "魏斯", "魏楚山",
        "趙之謙",
        "鄧石如",
        "袁曾期", "袁魯",
        "袁籜庵",
        "袁臥生", "袁雪",
        "倪師留", "倪覲公", "倪鴻寶",
        "王安節", "王概",
        "王文安", "王定",
        "王宓屮",
        "張鶴千", "張日中",
        "吳尊生", "吳道榮",
        "林公兆",
        "吳秋朗", "吳暉",
        "吳平子", "吳晉",
        "薛宏璧", "薛穆生",
        "秦以巽", "秦漁",
        "顧築公", "顧墣", "顧山臣",
        "吳仁長", "吳山常", "吳拳石",
        "吳頌筠", "吳明圩", "吳虎候",
        "黃聖期",
        "王雪蕉",
        "杜茶村",
        "張月坡", "張嵋",
        "吳遠度",
        "陸漢標", "陸天禦",
        "李箕山", "李穎",
        "沈逢吉", "沈遘",
        "顧雲美", "顧苓",
        "須來西", "須仍孫",
        "張大風", "張風",
        "沙門慧壽",
        "顧中翰", "顧貞觀", "顧華峰", "顧梁汾",
        "張江如", "張宗齡",
    }

    PLACE_NAMES: Set[str] = {
        "蘇州", "吳門", "金陵", "南京", "白下", "秣陵",
        "杭州", "錢塘", "武林", "西泠",
        "婺源", "新安", "歙", "徽州", "皖",
        "黃山", "休寧", "屯溪",
        "廣陵", "揚州", "維揚",
        "吳興", "菱湖",
        "莆田", "蒲田", "侯官", "福州", "閩", "榕城",
        "京口", "丹霞", "長汀",
        "嘉禾", "嘉興", "乍浦",
        "昆山", "婁東",
        "常熟",
        "如皋",
        "蘭溪", "蘭谿",
        "毗陵", "常州",
        "武進",
        "山陰", "會稽",
        "天都",
        "上元",
        "涇陽",
        "梁谿", "錫山",
        "梧州",
        "天津",
        "京師", "都門",
        "白門",
        "江寧",
        "東皋",
        "留都",
        "西虹橋",
        "南監",
        "公路浦",
        "浮山",
        "東萊",
        "青州",
        "江右",
        "關中",
        "東林書院",
        "小桃源",
        "南司馬",
    }

    SCHOOL_NAMES: Set[str] = {
        "吳門印派", "吳門",
        "浙派", "浙",
        "皖派", "皖", "徽派",
        "秦漢印風", "秦漢",
        "漳海", "漳海派",
        "莆田派", "宋比玉",
        "婁東派", "學山堂",
        "新安派",
        "錢塘派",
    }

    PERIOD_PATTERNS: List[str] = [
        r"嘉靖", r"萬曆", r"天啟", r"崇禎",
        r"康熙", r"雍正", r"乾隆", r"光緒", r"咸豐",
        r"道光", r"宣統", r"順治", r"同治",
        r"明初", r"明末", r"清初", r"明中期", r"明末清初",
        r"明代", r"清代", r"近代",
        r"庚午", r"辛未", r"壬子", r"丁亥", r"戊申",
        r"甲申", r"辛亥", r"丙子", r"丁丑", r"乙酉", r"癸丑",
    ]

    PERIOD_COMPILED = [re.compile(p) for p in PERIOD_PATTERNS]

    STYLE_PATTERNS: List[str] = [
        r"元朱文", r"白文", r"朱文", r"朱砂文",
        r"秦漢印風", r"文人篆刻",
        r"猛利", r"和平", r"離奇", r"錯落",
        r"婉秀", r"纖弱", r"蒼勁", r"質樸",
        r"剛健", r"婀娜", r"古拙", r"秀逸",
        r"雄渾", r"清新", r"典雅", r"洗鍊",
    ]

    STYLE_COMPILED = re.compile("|".join(STYLE_PATTERNS))

    def __init__(self):
        self.person_trie = Trie()
        for name in self.PERSON_NAMES:
            self.person_trie.insert(name)
        self.person_set = set(self.PERSON_NAMES)

        self.place_trie = Trie()
        for name in self.PLACE_NAMES:
            self.place_trie.insert(name)
        self.place_set = set(self.PLACE_NAMES)

        self.school_trie = Trie()
        for name in self.SCHOOL_NAMES:
            self.school_trie.insert(name)
        self.school_set = set(self.SCHOOL_NAMES)

    def _trie_extract(self, text: str, trie: Trie, entity_set: Set[str],
                      etype: str) -> List[NamedEntity]:
        entities = []
        i = 0
        while i < len(text):
            name = trie.match_at(text, i)
            if name:
                entities.append(NamedEntity(
                    text=name, type=etype,
                    start=i, end=i + len(name),
                    confidence=0.95, source="trie",
                    evidence=self._get_evidence(text, i, i + len(name)),
                ))
                i += len(name)
            else:
                i += 1
        return entities

    def _get_evidence(self, text: str, start: int, end: int) -> str:
        ctx_start = max(0, start - 20)
        ctx_end = min(len(text), end + 20)
        return text[ctx_start:ctx_end]

    def extract_persons(self, text: str) -> List[NamedEntity]:
        entities = self._trie_extract(text, self.person_trie, self.person_set, "PERSON")
        seen = set()
        result = []
        for e in entities:
            key = (e.text, e.start)
            if key not in seen:
                seen.add(key)
                result.append(e)
        return result

    def extract_places(self, text: str) -> List[NamedEntity]:
        entities = self._trie_extract(text, self.place_trie, self.place_set, "PLACE")
        seen = set()
        result = []
        for e in entities:
            key = (e.text, e.start)
            if key not in seen:
                seen.add(key)
                result.append(e)
        return result

    def extract_schools(self, text: str) -> List[NamedEntity]:
        entities = self._trie_extract(text, self.school_trie, self.school_set, "SCHOOL")
        seen = set()
        result = []
        for e in entities:
            key = (e.text, e.start)
            if key not in seen:
                seen.add(key)
                result.append(e)
        return result

    def extract_periods(self, text: str) -> List[NamedEntity]:
        entities = []
        seen = set()
        for p in self.PERIOD_COMPILED:
            for m in p.finditer(text):
                name = m.group(0)
                if (name, m.start()) not in seen:
                    seen.add((name, m.start()))
                    entities.append(NamedEntity(
                        text=name, type="PERIOD",
                        start=m.start(), end=m.end(),
                        confidence=0.90, source="period_regex",
                        evidence=self._get_evidence(text, m.start(), m.end()),
                    ))
        return entities

    def extract_styles(self, text: str) -> List[NamedEntity]:
        entities = []
        seen = set()
        for m in self.STYLE_COMPILED.finditer(text):
            name = m.group(0)
            if (name, m.start()) not in seen:
                seen.add((name, m.start()))
                entities.append(NamedEntity(
                    text=name, type="STYLE",
                    start=m.start(), end=m.end(),
                    confidence=0.90, source="style_regex",
                    evidence=self._get_evidence(text, m.start(), m.end()),
                ))
        return entities

    def extract_all(self, text: str) -> NERResult:
        entities = []
        entities += self.extract_persons(text)
        entities += self.extract_places(text)
        entities += self.extract_schools(text)
        entities += self.extract_periods(text)
        entities += self.extract_styles(text)
        return NERResult(entities=entities, raw_text=text)
