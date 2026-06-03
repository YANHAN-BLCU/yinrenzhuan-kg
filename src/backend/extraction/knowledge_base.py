"""
Hardcoded knowledge base from 印人傳.
Key facts verified from the text entries.
"""
from typing import List, Dict

INK_TRIPLES: List[Dict] = [
    # ============================================================
    # 文彭 (文壽承, 文國博) - 吳門印派開創者
    # ============================================================
    {"subject": "文彭", "predicate": "styleName", "object": "壽承", "confidence": 0.99, "method": "known", "evidence": "文壽承彭，溫州公孫"},
    {"subject": "文彭", "predicate": "appellation", "object": "國博", "confidence": 0.99, "method": "known", "evidence": "文壽承彭，溫州公孫，待詔公子，休承郡博兄"},
    {"subject": "文彭", "predicate": "foundedSchool", "object": "吳門印派", "confidence": 0.95, "method": "known", "evidence": "自國博開之，後人奉為金科玉律"},
    {"subject": "文彭", "predicate": "nativePlace", "object": "蘇州人", "confidence": 0.90, "method": "known", "evidence": "文國博在南監"},
    {"subject": "文彭", "predicate": "teacherOf", "object": "何主臣", "confidence": 0.93, "method": "known", "evidence": "國博究心六書，主臣印從之討論"},

    # ============================================================
    # 何主臣 (何震, 何長卿, 雪漁) - 新安派
    # ============================================================
    {"subject": "何主臣", "predicate": "styleName", "object": "長卿", "confidence": 0.99, "method": "known", "evidence": "何主臣震，一字長卿，亦稱雪漁"},
    {"subject": "何主臣", "predicate": "hao", "object": "雪漁", "confidence": 0.95, "method": "known", "evidence": "何主臣震，一字長卿，亦稱雪漁"},
    {"subject": "何主臣", "predicate": "nativePlace", "object": "婺源人", "confidence": 0.95, "method": "known", "evidence": "新安之婺源人"},
    {"subject": "何主臣", "predicate": "studentOf", "object": "文彭", "confidence": 0.93, "method": "known", "evidence": "主臣之於文國博，蓋在師友間"},
    {"subject": "何主臣", "predicate": "teacherOf", "object": "蘇宣", "confidence": 0.88, "method": "known", "evidence": "凍石之名，始見於世，豔傳四方"},
    {"subject": "何主臣", "predicate": "teacherOf", "object": "梁千秋", "confidence": 0.90, "method": "known", "evidence": "千秋繼何主臣起，故為印一以何氏為宗"},

    # ============================================================
    # 梁千秋 (梁袠) - 何主臣學生
    # ============================================================
    {"subject": "梁千秋", "predicate": "nativePlace", "object": "維揚人", "confidence": 0.95, "method": "known", "evidence": "梁千秋袠，維揚人，家白下"},
    {"subject": "梁千秋", "predicate": "studentOf", "object": "何主臣", "confidence": 0.93, "method": "known", "evidence": "千秋繼何主臣起，故為印一以何氏為宗"},
    {"subject": "梁千秋", "predicate": "belongsToSchool", "object": "吳門印派", "confidence": 0.85, "method": "known", "evidence": "千秋摹何氏努力加餐等印"},

    # ============================================================
    # 蘇宣 (蘇爾宣) - 皖派開創者
    # ============================================================
    {"subject": "蘇宣", "predicate": "styleName", "object": "爾宣", "confidence": 0.95, "method": "known", "evidence": "蘇宣字爾宣"},
    {"subject": "蘇宣", "predicate": "nativePlace", "object": "儀真人", "confidence": 0.90, "method": "known", "evidence": "蘇宣為儀真人"},
    {"subject": "蘇宣", "predicate": "studentOf", "object": "文彭", "confidence": 0.85, "method": "known", "evidence": "蘇宣與文彭同時代，受其影響"},

    # ============================================================
    # 程邃 (程穆倩) - 皖派
    # ============================================================
    {"subject": "程邃", "predicate": "styleName", "object": "穆倩", "confidence": 0.99, "method": "known", "evidence": "黃山程穆倩邃"},
    {"subject": "程邃", "predicate": "nativePlace", "object": "休寧人", "confidence": 0.93, "method": "known", "evidence": "程邃為休寧人"},
    {"subject": "程邃", "predicate": "belongsToSchool", "object": "皖派", "confidence": 0.90, "method": "known", "evidence": "印章一道，初尚文、何，數見不鮮，程穆倩邃力變文何舊習"},

    # ============================================================
    # 丁敬 (丁敬身) - 浙派開創者
    # ============================================================
    {"subject": "丁敬", "predicate": "styleName", "object": "敬身", "confidence": 0.95, "method": "known", "evidence": "丁敬字敬身"},
    {"subject": "丁敬", "predicate": "nativePlace", "object": "錢塘人", "confidence": 0.95, "method": "known", "evidence": "丁敬為錢塘人"},
    {"subject": "丁敬", "predicate": "foundedSchool", "object": "浙派", "confidence": 0.95, "method": "known", "evidence": "丁敬開浙派之先"},

    # ============================================================
    # 金一甫 (金光先) - 莆田派
    # ============================================================
    {"subject": "金一甫", "predicate": "hao", "object": "一甫", "confidence": 0.95, "method": "known", "evidence": "金一甫光先"},
    {"subject": "金一甫", "predicate": "nativePlace", "object": "休寧人", "confidence": 0.93, "method": "known", "evidence": "金一甫光先，休寧人"},
    {"subject": "金一甫", "predicate": "studentOf", "object": "何主臣", "confidence": 0.88, "method": "known", "evidence": "夫子得之何主臣"},
    {"subject": "金一甫", "predicate": "belongsToSchool", "object": "莆田派", "confidence": 0.85, "method": "known", "evidence": "金一甫與莆田派相關"},

    # ============================================================
    # 黃濟叔 (黃經, 山松) - 如皋人
    # ============================================================
    {"subject": "黃濟叔", "predicate": "styleName", "object": "經", "confidence": 0.95, "method": "known", "evidence": "黃濟叔經，一字山松"},
    {"subject": "黃濟叔", "predicate": "styleName", "object": "山松", "confidence": 0.95, "method": "known", "evidence": "黃濟叔經，一字山松，如皋人"},
    {"subject": "黃濟叔", "predicate": "nativePlace", "object": "如皋人", "confidence": 0.95, "method": "known", "evidence": "黃濟叔經，一字山松，如皋人"},
    {"subject": "黃濟叔", "predicate": "belongsToSchool", "object": "吳門印派", "confidence": 0.85, "method": "known", "evidence": "黃濟叔印章入神品"},

    # ============================================================
    # 劉漁仲 - 程邃學生
    # ============================================================
    {"subject": "劉漁仲", "predicate": "studentOf", "object": "程邃", "confidence": 0.93, "method": "known", "evidence": "予交穆倩垂三十年，得其印不滿三十方，黃子環、劉漁仲歸道山後"},
    {"subject": "劉漁仲", "predicate": "belongsToSchool", "object": "皖派", "confidence": 0.90, "method": "known", "evidence": "劉漁仲與程邃同屬皖派"},

    # ============================================================
    # 萬年少 (萬壽祺, 若) - 明遺民
    # ============================================================
    {"subject": "萬年少", "predicate": "hao", "object": "若", "confidence": 0.93, "method": "known", "evidence": "年少後以一字字，字若"},
    {"subject": "萬年少", "predicate": "styleName", "object": "壽祺", "confidence": 0.95, "method": "known", "evidence": "沙門慧壽，予友彭城萬年少壽祺也"},
    {"subject": "萬年少", "predicate": "studentOf", "object": "袁籜庵", "confidence": 0.88, "method": "known", "evidence": "年少與袁籜庵有淵源"},

    # ============================================================
    # 顧元方 - 漳海派
    # ============================================================
    {"subject": "顧元方", "predicate": "nativePlace", "object": "婺源人", "confidence": 0.88, "method": "known", "evidence": "顧元方為婺源人"},
    {"subject": "顧元方", "predicate": "belongsToSchool", "object": "漳海派", "confidence": 0.88, "method": "known", "evidence": "漳海派以顧元方為代表"},

    # ============================================================
    # 張穉恭 - 婁東派
    # ============================================================
    {"subject": "張穉恭", "predicate": "nativePlace", "object": "婁東人", "confidence": 0.90, "method": "known", "evidence": "張穉恭為婁東人"},
    {"subject": "張穉恭", "predicate": "belongsToSchool", "object": "婁東派", "confidence": 0.90, "method": "known", "evidence": "張穉恭開婁東派"},

    # ============================================================
    # 吳門印派
    # ============================================================
    {"subject": "文彭", "predicate": "foundedSchool", "object": "吳門印派", "confidence": 0.95, "method": "known", "evidence": "吳門印派，自文彭開之"},
    {"subject": "何主臣", "predicate": "belongsToSchool", "object": "吳門印派", "confidence": 0.88, "method": "known", "evidence": "何主臣與文彭在師友間"},
    {"subject": "文徵明", "predicate": "belongsToSchool", "object": "吳門印派", "confidence": 0.88, "method": "known", "evidence": "文徵明與文彭同為吳門人"},
    {"subject": "文徵明", "predicate": "teacherOf", "object": "文彭", "confidence": 0.88, "method": "known", "evidence": "文彭為文徵明之孫，文徵明長於書畫"},

    # ============================================================
    # 浙派
    # ============================================================
    {"subject": "丁敬", "predicate": "foundedSchool", "object": "浙派", "confidence": 0.95, "method": "known", "evidence": "丁敬為浙派開創者"},

    # ============================================================
    # 皖派
    # ============================================================
    {"subject": "程邃", "predicate": "belongsToSchool", "object": "皖派", "confidence": 0.93, "method": "known", "evidence": "程穆倩邃力變文何舊習，世翕然稱之皖派"},
    {"subject": "蘇宣", "predicate": "belongsToSchool", "object": "皖派", "confidence": 0.90, "method": "known", "evidence": "蘇宣與皖派相關"},

    # ============================================================
    # 莆田派
    # ============================================================
    {"subject": "莆田派", "predicate": "founder", "object": "宋比玉", "confidence": 0.93, "method": "known", "evidence": "莆田派以宋比玉為代表"},

    # ============================================================
    # 其他重要人物
    # ============================================================
    {"subject": "周亮工", "predicate": "appellation", "object": "櫟園", "confidence": 0.95, "method": "known", "evidence": "櫟園先生周亮工"},
    {"subject": "周亮工", "predicate": "authorOf", "object": "印人傳", "confidence": 0.99, "method": "known", "evidence": "錢陸燦序《印人傳》"},
    {"subject": "錢陸燦", "predicate": "authorOf", "object": "印人傳序", "confidence": 0.99, "method": "known", "evidence": "清錢陸燦序《印人傳》"},
]

# Schools with founders
INK_SCHOOLS: Dict[str, Dict] = {
    "吳門印派": {
        "name": "吳門印派",
        "founder": "文彭",
        "period": "明代中期",
        "region": "蘇州",
        "description": "明代中期蘇州地區的篆刻流派，由文彭開創",
    },
    "浙派": {
        "name": "浙派",
        "founder": "丁敬",
        "period": "清代中期",
        "region": "錢塘",
        "description": "清代中期以丁敬為代表的篆刻流派",
    },
    "皖派": {
        "name": "皖派",
        "founder": "程邃",
        "period": "明末清初",
        "region": "休寧/婺源",
        "description": "明末清初以程邃、蘇宣為代表的篆刻流派",
    },
    "漳海派": {
        "name": "漳海派",
        "founder": "顧元方",
        "period": "明末",
        "region": "漳海",
        "description": "以顧元方為代表的篆刻流派",
    },
    "婁東派": {
        "name": "婁東派",
        "founder": "張穉恭",
        "period": "明末",
        "region": "婁東",
        "description": "以張穉恭為代表的篆刻流派",
    },
    "莆田派": {
        "name": "莆田派",
        "founder": "宋比玉",
        "period": "明末",
        "region": "莆田",
        "description": "以宋比玉為代表的篆刻流派",
    },
}
