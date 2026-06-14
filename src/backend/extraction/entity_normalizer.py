"""
实体归一化模块。

对抽取出的实体进行标准化清洗与合并，确保知识图谱中每个实体只有唯一的标准表示。

包含三大功能：
1. 人物别名归一化 — 同一人物的不同称呼统一到标准名
2. 地名标准化 — 同一地方的不同写法统一
3. 流派名标准化 — 流派别名归一
"""
import logging
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class NormalizationResult:
    """归一化结果。"""
    original: str
    normalized: str
    entity_type: str
    alias_used: str = ""
    confidence: float = 1.0


class PersonNormalizer:
    """
    历史人物别名归一化。

    依据《印人传》文本中实际出现的别名情况，建立人物别名映射表，
    将所有变体名称统一到标准人名。
    """

    # 别名 → 标准名映射（繁体）
    ALIAS_TO_STANDARD: Dict[str, str] = {
        # ===== 文彭（吳門印派开创者）=====
        "文壽承": "文彭",
        "文國博": "文彭",
        "文三橋": "文彭",
        "三橋": "文彭",
        "文休承": "文彭",    # 刻写错误
        "待詔公子": "文彭",  # 身份称谓，不作标准名
        "休承郡博": "文彭",
        # ===== 文徵明 =====
        "文徵仲": "文徵明",
        "衡山": "文徵明",
        "文衡山": "文徵明",
        # ===== 何震（何主臣）=====
        "何主臣": "何震",
        "何長卿": "何震",
        "何雪漁": "何震",
        "雪漁": "何震",
        "雪渔": "何震",      # 简体
        "主臣": "何震",
        "長卿": "何震",      # 字
        # ===== 丁敬（浙派开创者）=====
        "丁敬身": "丁敬",
        "龍泓": "丁敬",
        "硯林": "丁敬",
        "龍泓山人": "丁敬",
        # ===== 程邃（皖派，黃山人，字穆倩，號六水）=====
        # 注意：不要把其他"程"姓人（如程孟長/程雲來/程與繩）也归到这里
        "程穆倩": "程邃",
        "程六水": "程邃",
        "穆倩": "程邃",
        "六水": "程邃",
        # ===== 程原（程孟長，何震弟子）=====
        "程孟長": "程原",
        "程孟長原": "程原",
        "孟長": "程原",
        "程稚昭": "程原",  # 別名（待考）
        # ===== 程雲來（歙人，醫家）=====
        "程雲來": "程雲來",
        "程林": "程雲來",  # 雲來字林
        # ===== 程與繩（雲來之子）=====
        "程與繩": "程與繩",
        "與繩": "程與繩",
        "其武": "程與繩",  # 與繩字其武
        # ===== 蘇宣 ======
        "蘇爾宣": "蘇宣",
        "爾宣": "蘇宣",
        # ===== 梁千秋 ======
        "梁大年": "梁千秋",
        "梁袠": "梁千秋",
        "梁千秋袠": "梁千秋",
        "千秋袠": "梁千秋",
        # ===== 黃學（黃濟叔）=====
        "黃濟叔": "黃學",
        "黃山松": "黃學",
        "黃炳猷": "黃學",
        "山松": "黃學",
        # ===== 汪關 ======
        "汪尹子": "汪關",
        "汪杲叔": "汪關",
        "汪宏度": "汪關",
        "汪泓": "汪關",
        "汪宗周": "汪關",
        "汪徽": "汪關",
        "汪先之": "汪關",
        "尹子": "汪關",
        "杲叔": "汪關",
        # ===== 祝允明 ======
        "祝希哲": "祝允明",
        "枝山": "祝允明",
        "希哲": "祝允明",
        # ===== 周亮工 ======
        "周櫟園": "周亮工",
        "櫟園": "周亮工",
        "櫟園先生": "周亮工",
        # ===== 萬年少 ======
        "萬壽祺": "萬年少",
        "萬年少壽祺": "萬年少",
        "慧壽": "萬年少",
        "沙門慧壽": "萬年少",
        "彭城萬年少": "萬年少",
        # ===== 顧苓 ======
        "顧雲美": "顧苓",
        "雲美": "顧苓",
        # ===== 張風 ======
        "張大風": "張風",
        "大風": "張風",
        # ===== 葉銘 ======
        "葉東amer": "葉銘",  # OCR 错误变体
        # ===== 黃子環 ======
        "黃子環": "黃子環",
        "黃聖期": "黃子環",
    }

    # 标准名 → 别名集合
    STANDARD_TO_ALIASES: Dict[str, List[str]] = {}

    @classmethod
    def init_alias_table(cls):
        for alias, standard in cls.ALIAS_TO_STANDARD.items():
            if standard not in cls.STANDARD_TO_ALIASES:
                cls.STANDARD_TO_ALIASES[standard] = []
            if alias not in cls.STANDARD_TO_ALIASES[standard]:
                cls.STANDARD_TO_ALIASES[standard].append(alias)

    @classmethod
    def normalize(cls, name: str) -> NormalizationResult:
        """将别名归一化为标准人物名。"""
        if not hasattr(cls, "_initialized"):
            cls.init_alias_table()
            cls._initialized = True

        stripped = name.strip()
        if stripped in cls.ALIAS_TO_STANDARD:
            std = cls.ALIAS_TO_STANDARD[stripped]
            return NormalizationResult(
                original=stripped,
                normalized=std,
                entity_type="PERSON",
                alias_used=stripped,
                confidence=1.0,
            )
        return NormalizationResult(
            original=stripped,
            normalized=stripped,
            entity_type="PERSON",
            confidence=0.5,  # 未知名称，无法判断
        )

    @classmethod
    def get_standard_name(cls, name: str) -> str:
        """直接返回标准名。"""
        return cls.normalize(name).normalized

    @classmethod
    def get_all_aliases(cls, standard_name: str) -> List[str]:
        """获取某标准人物的所有别名。"""
        if not hasattr(cls, "_initialized"):
            cls.init_alias_table()
            cls._initialized = True
        return cls.STANDARD_TO_ALIASES.get(standard_name, [])


class PlaceNormalizer:
    """
    地理名称标准化。

    《印人传》中同一地名常有不同写法（如"蘇州"/"吳門"、"杭州"/"錢塘"等），
    统一归一为标准地名。
    """

    ALIAS_TO_STANDARD: Dict[str, str] = {
        # ===== 蘇州 ======
        "吳門": "蘇州",
        "吳郡": "蘇州",
        "江蘇": "蘇州",
        # ===== 杭州 ======
        "錢塘": "杭州",
        "武林": "杭州",
        "西湖": "杭州",
        "兩浙": "杭州",
        "西泠": "杭州",
        "錢塘武林": "杭州",
        # ===== 徽州 ======
        "新安": "徽州",
        "皖": "徽州",
        "黃山": "徽州",
        "休寧": "徽州",
        "婺源": "婺源",
        "屯溪": "徽州",
        # ===== 揚州 ======
        "廣陵": "揚州",
        "維揚": "揚州",
        "江都": "揚州",
        # ===== 嘉興 ======
        "嘉禾": "嘉興",
        "乍浦": "嘉興",
        # ===== 常熟 ======
        "虞山": "常熟",
        # ===== 常州 ======
        "毗陵": "常州",
        "武進": "常州",
        "錫山": "常州",
        "梁谿": "常州",
        # ===== 绍兴 ======
        "山陰": "紹興",
        "會稽": "紹興",
        # ===== 福州 ======
        "莆田": "福州",
        "蒲田": "福州",
        "侯官": "福州",
        "閩": "福州",
        "榕城": "福州",
        # ===== 南京 ======
        "金陵": "南京",
        "白下": "南京",
        "秣陵": "南京",
        "江寧": "南京",
        "留都": "南京",
        "南監": "南京",
        "上元": "南京",
        "都門": "南京",
        "京師": "南京",
        "白門": "南京",
        # ===== 如皋 ======
        "東皋": "如皋",
        # ===== 其他 ======
        "京口": "鎮江",
        "丹霞": "鎮江",
        "長汀": "福建長汀",
        "吳興": "湖州",
        "菱湖": "湖州",
        "天都": "黃山",
        "涇陽": "涇陽",
        "梧州": "梧州",
        "天津": "天津",
        "東萊": "山東萊州",
        "青州": "山東青州",
        "江右": "江西",
        "關中": "陝西",
        "小桃源": "武夷山",
        "公路浦": "公路浦",
        "東林書院": "東林書院",
        "南司馬": "南京",
    }

    @classmethod
    def normalize(cls, name: str) -> NormalizationResult:
        stripped = name.strip()
        if stripped in cls.ALIAS_TO_STANDARD:
            return NormalizationResult(
                original=stripped,
                normalized=cls.ALIAS_TO_STANDARD[stripped],
                entity_type="PLACE",
                alias_used=stripped,
                confidence=1.0,
            )
        return NormalizationResult(
            original=stripped,
            normalized=stripped,
            entity_type="PLACE",
            confidence=0.5,
        )

    @classmethod
    def get_standard_name(cls, name: str) -> str:
        return cls.normalize(name).normalized


class SchoolNormalizer:
    """
    篆刻流派名称标准化。
    """

    ALIAS_TO_STANDARD: Dict[str, str] = {
        "吳門": "吳門印派",
        "吳門印派": "吳門印派",
        "浙": "浙派",
        "浙派": "浙派",
        "錢塘派": "浙派",
        "皖": "皖派",
        "皖派": "皖派",
        "徽派": "皖派",
        "新安派": "皖派",
        "秦漢": "秦漢印風",
        "秦漢印風": "秦漢印風",
        "秦漢印": "秦漢印風",
        "文人篆刻": "文人篆刻",
        "漳海派": "漳海派",
        "漳海": "漳海派",
        "莆田派": "莆田派",
        "婁東派": "婁東派",
        "婁東": "婁東派",
        "學山堂": "婁東派",
        "新安派": "皖派",
    }

    @classmethod
    def normalize(cls, name: str) -> NormalizationResult:
        stripped = name.strip()
        if stripped in cls.ALIAS_TO_STANDARD:
            return NormalizationResult(
                original=stripped,
                normalized=cls.ALIAS_TO_STANDARD[stripped],
                entity_type="SCHOOL",
                alias_used=stripped,
                confidence=1.0,
            )
        return NormalizationResult(
            original=stripped,
            normalized=stripped,
            entity_type="SCHOOL",
            confidence=0.5,
        )


class EntityNormalizer:
    """
    统一实体归一化入口。

    对五类实体（PERSON / PLACE / PERIOD / STYLE / SCHOOL）执行标准化处理。
    """

    def __init__(self):
        self._person = PersonNormalizer()
        self._place = PlaceNormalizer()
        self._school = SchoolNormalizer()

    def normalize(self, name: str, entity_type: str) -> NormalizationResult:
        """
        对实体执行归一化。

        Args:
            name: 实体名称
            entity_type: 实体类型（PERSON/PLACE/PERIOD/STYLE/SCHOOL）
        """
        if entity_type == "PERSON":
            return self._person.normalize(name)
        elif entity_type == "PLACE":
            return self._place.normalize(name)
        elif entity_type == "SCHOOL":
            return self._school.normalize(name)
        else:
            return NormalizationResult(
                original=name.strip(),
                normalized=name.strip(),
                entity_type=entity_type,
                confidence=1.0,
            )

    def normalize_entities(self, entities: List[Tuple[str, str]]) -> List[NormalizationResult]:
        """
        批量归一化实体列表。

        Args:
            entities: [(name, type), ...] 列表
        Returns:
            NormalizationResult 列表
        """
        return [self.normalize(name, etype) for name, etype in entities]

    def deduplicate_by_normalized(
        self, entities: List[Tuple[str, str]]
    ) -> List[Tuple[str, str, str]]:
        """
        基于归一化结果去重。

        返回 [(标准名, 类型, 原名列表)]，将所有别名合并为一个标准实体。
        """
        normalized_groups: Dict[Tuple[str, str], List[str]] = {}
        for name, etype in entities:
            result = self.normalize(name, etype)
            key = (result.normalized, etype)
            if key not in normalized_groups:
                normalized_groups[key] = []
            if result.original not in normalized_groups[key]:
                normalized_groups[key].append(result.original)

        return [
            (std, etype, ",".join(aliases))
            for (std, etype), aliases in normalized_groups.items()
        ]
