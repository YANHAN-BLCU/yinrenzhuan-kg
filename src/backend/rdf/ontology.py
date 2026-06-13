"""
印人传知识图谱本体（Ontology）。

基于 OWL DL 设计的领域本体，为知识图谱提供规范的数据模型约束。

类层次（OWL Class）：
    Thing（顶层）
    ├── HistoricPerson        — 历史人物（印人）
    ├── Location             — 地理实体
    ├── Era                 — 历史时期
    ├── CalligraphyStyle    — 书法/篆刻风格
    ├── SealEngravingSchool — 篆刻流派
    ├── SealWork            — 篆刻作品
    ├── Evidence            — 抽取证据

对象属性（Object Property）：
    kinship:hasFather / kinship:hasSon         — 亲属（父子）
    kinship:hasAncestor / kinship:hasDescendant — 祖孙
    education:hasTeacher / education:hasStudent — 师承
    social:hasFriend                         — 交游
    social:influencedBy                      — 影响
    school:hasFounder / school:hasMember     — 流派（开创/隶属）
    school:inheritedFrom                     — 流派继承
    location:locatedIn                       — 所在地点
    era:livedInPeriod                        — 所处时期
    style:hasStyle                           — 拥有风格
    sameAs                                   — 等同关系（外部数据库）

数据属性（Data Property）：
    人物：birthYear, deathYear, nativePlace, dynasty, occupation, officialRank,
          appellation, biography, masterpiece, styleDescription
    流派：schoolName, period, region, description
    风格：styleName, styleDescription
    地点：placeName, placeType
    作品：workTitle, creationPeriod
    证据：sourceText, confidence, extractionMethod, dataSource
"""
from rdflib import Namespace, URIRef, Literal, RDF, RDFS, OWL
from rdflib.namespace import XSD

# ============================================================
# 命名空间
# ============================================================
INK = Namespace("http://example.org/inkperson/")      # 本体主命名空间
REL = Namespace("http://example.org/inkperson/relation/")  # 关系命名空间
CTEXT = Namespace("http://example.org/ctext/")         # ctext 外部链接
CBDB = Namespace("http://example.org/cbdb/")           # CBDB 外部链接

EX = INK   # 别名

# ============================================================
# 类定义
# ============================================================
CLASSES = {
    # 核心类
    "Thing": OWL.Class,
    "HistoricPerson": None,      # 历史人物
    "Location": None,           # 地理实体
    "Era": None,                # 历史时期
    "CalligraphyStyle": None,   # 书法/篆刻风格
    "SealEngravingSchool": None,# 篆刻流派
    "SealWork": None,           # 篆刻作品
    # 辅助类
    "Place": None,              # 地点（同 Location，兼容旧名）
    "TimePeriod": None,         # 时期（同 Era，兼容旧名）
    "Style": None,              # 风格（同 CalligraphyStyle，兼容旧名）
    "Work": None,               # 作品（同 SealWork，兼容旧名）
    "Evidence": None,           # 抽取证据
    "Relation": OWL.ObjectProperty,
}

# ============================================================
# 数据属性（DatatypeProperty）
# ============================================================
PROPERTIES_DATATYPE = {
    # --- HistoricPerson ---
    "personName":         ("HistoricPerson", "string"),  # 标准姓名
    "styleName":          ("HistoricPerson", "string"),  # 字
    "hao":                ("HistoricPerson", "string"),  # 号
    "birthYear":          ("HistoricPerson", "integer"), # 生年
    "deathYear":          ("HistoricPerson", "integer"), # 卒年
    "birthYearString":    ("HistoricPerson", "string"),  # 生年（字符串）
    "deathYearString":    ("HistoricPerson", "string"),  # 卒年（字符串）
    "nativePlace":        ("HistoricPerson", "string"),  # 籍贯
    "dynasty":            ("HistoricPerson", "string"),  # 朝代
    "occupation":         ("HistoricPerson", "string"),  # 职业/身份
    "officialRank":       ("HistoricPerson", "string"),  # 官职
    "appellation":         ("HistoricPerson", "string"),  # 其他称谓/别名
    "biography":          ("HistoricPerson", "string"),  # 生平简介
    "masterpiece":        ("HistoricPerson", "string"),  # 代表作品
    "styleDescription":   ("HistoricPerson", "string"),  # 篆刻风格描述
    # --- SealEngravingSchool ---
    "schoolName":         ("SealEngravingSchool", "string"), # 流派名
    "period":             ("SealEngravingSchool", "string"), # 活跃时期
    "region":             ("SealEngravingSchool", "string"), # 主要地区
    "description":        ("SealEngravingSchool", "string"), # 描述
    "founder":            ("SealEngravingSchool", "string"), # 开创者（字符串，引用人物名）
    # --- CalligraphyStyle ---
    "styleName":          ("CalligraphyStyle", "string"),   # 风格名
    "styleDescription":   ("CalligraphyStyle", "string"),  # 风格描述
    # --- Location ---
    "placeName":         ("Location", "string"),          # 地名
    "placeType":          ("Location", "string"),          # 地点类型（城市/省份等）
    # --- Era ---
    "periodName":         ("Era", "string"),              # 时期名称
    "startYear":          ("Era", "integer"),              # 开始年份
    "endYear":            ("Era", "integer"),               # 结束年份
    # --- SealWork ---
    "workTitle":          ("SealWork", "string"),          # 作品名
    "creationPeriod":     ("SealWork", "string"),          # 创作时期
    "material":           ("SealWork", "string"),          # 材质
    # --- Evidence（证据）---
    "confidence":         ("Evidence", "float"),            # 置信度
    "sourceText":         ("Evidence", "string"),          # 原文证据
    "extractionMethod":   ("Evidence", "string"),          # 抽取方法
    "dataSource":         ("Thing", "string"),             # 数据来源
}

# ============================================================
# 对象属性（ObjectProperty）
# ============================================================
PROPERTIES_OBJECT = {
    # --- 亲属关系（kinship）---
    "hasFather":          ("HistoricPerson", "HistoricPerson"),
    "hasSon":             ("HistoricPerson", "HistoricPerson"),
    "hasAncestor":        ("HistoricPerson", "HistoricPerson"),
    "hasDescendant":      ("HistoricPerson", "HistoricPerson"),
    # 兼容旧名
    "fatherOf":           ("HistoricPerson", "HistoricPerson"),
    "sonOf":              ("HistoricPerson", "HistoricPerson"),
    # --- 师承关系（education）---
    "hasTeacher":         ("HistoricPerson", "HistoricPerson"),
    "hasStudent":         ("HistoricPerson", "HistoricPerson"),
    "inheritedFrom":      ("HistoricPerson", "HistoricPerson"),
    # 兼容旧名
    "teacherOf":          ("HistoricPerson", "HistoricPerson"),
    "studentOf":          ("HistoricPerson", "HistoricPerson"),
    # --- 交游关系（social）---
    "hasFriend":          ("HistoricPerson", "HistoricPerson"),
    "influencedBy":       ("HistoricPerson", "HistoricPerson"),
    # 兼容旧名
    "friendOf":           ("HistoricPerson", "HistoricPerson"),
    "brotherOf":          ("HistoricPerson", "HistoricPerson"),
    # --- 流派关系（school）---
    "hasFounder":         ("SealEngravingSchool", "HistoricPerson"),
    "hasMember":          ("SealEngravingSchool", "HistoricPerson"),
    "inheritsFrom":       ("SealEngravingSchool", "SealEngravingSchool"),
    # 兼容旧名
    "foundedSchool":      ("HistoricPerson", "SealEngravingSchool"),
    "belongsToSchool":    ("HistoricPerson", "SealEngravingSchool"),
    # --- 位置关系（location）---
    "locatedIn":          ("HistoricPerson", "Location"),
    "fromPlace":          ("HistoricPerson", "Location"),
    # --- 时期关系（era）---
    "livedInPeriod":      ("HistoricPerson", "Era"),
    "hasPeriod":          ("HistoricPerson", "Era"),
    # --- 风格关系（style）---
    "hasStyle":           ("HistoricPerson", "CalligraphyStyle"),
    "hasCalligraphyStyle": ("HistoricPerson", "CalligraphyStyle"),
    # --- 作品关系（work）---
    "createdWork":        ("HistoricPerson", "SealWork"),
    # --- 外部链接 ---
    "sameAs":             ("Thing", "Thing"),
    "ctextId":            ("HistoricPerson", "string"),
    "cbdbId":             ("HistoricPerson", "string"),
    "ctextReference":     ("HistoricPerson", "Thing"),
    "cbdbReference":      ("HistoricPerson", "Thing"),
    # --- 证据关系 ---
    "extractedBy":        ("Evidence", "HistoricPerson"),
    "source":             ("Evidence", "Thing"),
}


# ============================================================
# URI 辅助函数
# ============================================================
def get_person_uri(name: str) -> URIRef:
    """获取人物 URI：ex:person/文彭"""
    if not name:
        return EX["unknown"]
    key = name.strip().replace(" ", "_")
    return EX[f"person/{key}"]


def get_school_uri(name: str) -> URIRef:
    """获取流派 URI：ex:school/浙派"""
    if not name:
        return EX["unknown_school"]
    key = name.strip().replace(" ", "_")
    return EX[f"school/{key}"]


def get_place_uri(name: str) -> URIRef:
    """获取地点 URI：ex:place/苏州"""
    if not name:
        return EX["unknown_place"]
    key = name.strip().replace(" ", "_")
    return EX[f"place/{key}"]


def get_style_uri(name: str) -> URIRef:
    """获取风格 URI：ex:style/元朱文"""
    if not name:
        return EX["unknown_style"]
    key = name.strip().replace(" ", "_")
    return EX[f"style/{key}"]


def get_era_uri(name: str) -> URIRef:
    """获取时期 URI：ex:era/嘉靖"""
    if not name:
        return EX["unknown_era"]
    key = name.strip().replace(" ", "_")
    return EX[f"era/{key}"]


def get_work_uri(name: str) -> URIRef:
    """获取作品 URI：ex:work/月印无心"""
    if not name:
        return EX["unknown_work"]
    key = name.strip().replace(" ", "_")
    return EX[f"work/{key}"]


def get_evidence_uri(subject: str, predicate: str) -> URIRef:
    """获取证据 URI：ex:evidence/文彭_teacherOf"""
    key = f"{subject}_{predicate}".strip().replace(" ", "_")
    return EX[f"evidence/{key}"]


def get_relation_uri(predicate: str) -> URIRef:
    """获取关系命名空间下的谓词 URI。"""
    return REL[predicate]


# ============================================================
# Schema谓词 → RDF属性名 映射
# ============================================================
SCHEMA_TO_RDF = {
    # kinship
    "kinship:fatherOf":       "hasFather",
    "kinship:sonOf":           "hasSon",
    "kinship:ancestorOf":      "hasAncestor",
    "kinship:descendantOf":    "hasDescendant",
    # education
    "education:teacherOf":      "hasTeacher",
    "education:studentOf":      "hasStudent",
    "education:inheritedFrom":  "inheritedFrom",
    # social
    "social:friendOf":         "hasFriend",
    "social:influencedBy":     "influencedBy",
    # school
    "school:founderOf":         "hasFounder",
    "school:belongsTo":         "belongsToSchool",
    # attribute
    "attribute:hasStyleName":  "styleName",
    "attribute:hasHao":        "hao",
    "attribute:hasAppellation":"appellation",
    "attribute:nativePlace":   "nativePlace",
    "attribute:dynasty":       "dynasty",
    # legacy
    "fatherOf":                "hasFather",
    "sonOf":                   "hasSon",
    "teacherOf":               "hasTeacher",
    "studentOf":               "hasStudent",
    "friendOf":                "hasFriend",
    "influencedBy":            "influencedBy",
    "foundedSchool":           "hasFounder",
    "belongsToSchool":         "belongsToSchool",
    "nativePlace":             "nativePlace",
    "fromPlace":               "locatedIn",
    "inheritedFrom":           "inheritedFrom",
}


def normalize_predicate(pred: str) -> str:
    """将 Schema 谓词或旧谓词映射到标准 RDF 属性名。"""
    return SCHEMA_TO_RDF.get(pred.strip(), pred.strip())


def get_object_uri(obj: str, predicate: str) -> URIRef:
    """根据谓词类型返回正确的对象 URI。"""
    pred = normalize_predicate(predicate)
    if pred in {"hasFather", "hasSon", "hasAncestor", "hasDescendant",
                "hasTeacher", "hasStudent", "hasFriend", "influencedBy",
                "inheritedFrom"}:
        return get_person_uri(obj)
    elif pred in {"hasFounder", "belongsToSchool"}:
        return get_school_uri(obj)
    elif pred == "locatedIn":
        return get_place_uri(obj)
    elif pred in {"livedInPeriod", "hasPeriod"}:
        return get_era_uri(obj)
    elif pred in {"hasStyle", "hasCalligraphyStyle"}:
        return get_style_uri(obj)
    elif pred == "createdWork":
        return get_work_uri(obj)
    return get_person_uri(obj)
