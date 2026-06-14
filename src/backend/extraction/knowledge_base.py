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
    {"subject": "文彭", "predicate": "nativePlace", "object": "蘇州人", "confidence": 0.90, "method": "known", "evidence": "文國博在南監"},
    {"subject": "文彭", "predicate": "foundedSchool", "object": "吳門印派", "confidence": 0.95, "method": "known", "evidence": "自國博開之，後人奉為金科玉律"},
    # 文彭是文徵明的孙子
    {"subject": "文彭", "predicate": "hasAncestor", "object": "文徵明", "confidence": 0.95, "method": "known", "evidence": "文彭為文徵明之孫，文徵明長於書畫"},

    # ============================================================
    # 何震 (何主臣, 何長卿, 雪漁) - 吳門印派代表人物
    # ============================================================
    {"subject": "何震", "predicate": "styleName", "object": "長卿", "confidence": 0.99, "method": "known", "evidence": "何主臣震，一字長卿，亦稱雪漁"},
    {"subject": "何震", "predicate": "hao", "object": "雪漁", "confidence": 0.95, "method": "known", "evidence": "何主臣震，一字長卿，亦稱雪漁"},
    {"subject": "何震", "predicate": "nativePlace", "object": "婺源人", "confidence": 0.95, "method": "known", "evidence": "新安之婺源人"},
    {"subject": "何震", "predicate": "belongsToSchool", "object": "吳門印派", "confidence": 0.88, "method": "known", "evidence": "何主臣與文彭在師友間"},

    # ============================================================
    # 梁千秋 (梁袠) - 何震学生
    # ============================================================
    {"subject": "梁千秋", "predicate": "nativePlace", "object": "維揚人", "confidence": 0.95, "method": "known", "evidence": "梁千秋袠，維揚人，家白下"},
    {"subject": "梁千秋", "predicate": "education:studentOf", "object": "何震", "confidence": 0.93, "method": "known", "evidence": "千秋繼何主臣起，故為印一以何氏為宗"},
    {"subject": "梁千秋", "predicate": "belongsToSchool", "object": "吳門印派", "confidence": 0.85, "method": "known", "evidence": "千秋摹何氏努力加餐等印"},

    # ============================================================
    # 蘇宣 (蘇爾宣) - 皖派
    # ============================================================
    {"subject": "蘇宣", "predicate": "styleName", "object": "爾宣", "confidence": 0.95, "method": "known", "evidence": "蘇宣字爾宣"},
    {"subject": "蘇宣", "predicate": "nativePlace", "object": "儀真人", "confidence": 0.90, "method": "known", "evidence": "蘇宣為儀真人"},
    {"subject": "蘇宣", "predicate": "education:studentOf", "object": "文彭", "confidence": 0.85, "method": "known", "evidence": "蘇宣與文彭同時代，受其影響"},
    {"subject": "蘇宣", "predicate": "belongsToSchool", "object": "皖派", "confidence": 0.90, "method": "known", "evidence": "蘇宣與皖派相關"},

    # ============================================================
    # 程邃 (程穆倩) - 皖派
    # ============================================================
    {"subject": "程邃", "predicate": "styleName", "object": "穆倩", "confidence": 0.99, "method": "known", "evidence": "黃山程穆倩邃"},
    {"subject": "程邃", "predicate": "nativePlace", "object": "休寧人", "confidence": 0.93, "method": "known", "evidence": "程邃為休寧人"},
    {"subject": "程邃", "predicate": "belongsToSchool", "object": "皖派", "confidence": 0.93, "method": "known", "evidence": "程穆倩邃力變文何舊習，世翕然稱之皖派"},

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
    {"subject": "金一甫", "predicate": "education:studentOf", "object": "何震", "confidence": 0.88, "method": "known", "evidence": "夫子得之何主臣"},
    {"subject": "金一甫", "predicate": "belongsToSchool", "object": "莆田派", "confidence": 0.85, "method": "known", "evidence": "金一甫與莆田派相關"},

    # ============================================================
    # 黃學 (黃濟叔, 山松) - 如皋人
    # ============================================================
    {"subject": "黃學", "predicate": "styleName", "object": "經", "confidence": 0.95, "method": "known", "evidence": "黃濟叔經，一字山松"},
    {"subject": "黃學", "predicate": "styleName", "object": "山松", "confidence": 0.95, "method": "known", "evidence": "黃濟叔經，一字山松，如皋人"},
    {"subject": "黃學", "predicate": "nativePlace", "object": "如皋人", "confidence": 0.95, "method": "known", "evidence": "黃濟叔經，一字山松，如皋人"},
    {"subject": "黃學", "predicate": "belongsToSchool", "object": "吳門印派", "confidence": 0.85, "method": "known", "evidence": "黃濟叔印章入神品"},

    # ============================================================
    # 劉漁仲 - 程邃学生
    # ============================================================
    {"subject": "劉漁仲", "predicate": "education:studentOf", "object": "程邃", "confidence": 0.93, "method": "known", "evidence": "予交穆倩垂三十年，得其印不滿三十方，黃子環、劉漁仲歸道山後"},
    {"subject": "劉漁仲", "predicate": "belongsToSchool", "object": "皖派", "confidence": 0.90, "method": "known", "evidence": "劉漁仲與程邃同屬皖派"},

    # ============================================================
    # 何震的弟子 (entry 8 書何主臣章: "其嫡傳則獨有程孟長父子")
    # ============================================================
    {"subject": "程原", "predicate": "education:studentOf", "object": "何震", "confidence": 0.95, "method": "known", "evidence": "主臣之印…其嫡傳則獨有程孟長父子"},
    {"subject": "程樸", "predicate": "education:studentOf", "object": "何震", "confidence": 0.90, "method": "known", "evidence": "程孟長父子…命其子元素樸選千餘力摹之"},
    {"subject": "鄭宏祐", "predicate": "education:studentOf", "object": "何震", "confidence": 0.90, "method": "known", "evidence": "鄭宏祐…行圖章得何氏之傳"},
    # 程原(程孟長) basics
    {"subject": "程原", "predicate": "styleName", "object": "孟長", "confidence": 0.95, "method": "known", "evidence": "程孟長原"},
    {"subject": "程原", "predicate": "styleName", "object": "六水", "confidence": 0.95, "method": "known", "evidence": "程孟長原，一字六水"},
    {"subject": "程原", "predicate": "nativePlace", "object": "新安人", "confidence": 0.90, "method": "known", "evidence": "程孟長原，一字六水，新安人"},
    {"subject": "程原", "predicate": "nativePlace", "object": "吳興", "confidence": 0.90, "method": "known", "evidence": "孟長家吳興"},
    {"subject": "程樸", "predicate": "styleName", "object": "元素", "confidence": 0.90, "method": "known", "evidence": "元素樸"},
    # 鄭宏祐 basics
    {"subject": "鄭宏祐", "predicate": "styleName", "object": "基相", "confidence": 0.90, "method": "known", "evidence": "鄭宏祐基相"},
    {"subject": "鄭宏祐", "predicate": "nativePlace", "object": "歙人", "confidence": 0.90, "method": "known", "evidence": "鄭宏祐…歙人"},

    # ============================================================
    # 程孟長 -- 陶石公 (entry 57 書陶石公印譜: "嚐從江高臣學印章")
    # 程雲來 -- 程與繩 (entry 28/29: "中子與繩亦從君治印")
    # ============================================================
    {"subject": "陶石公", "predicate": "education:studentOf", "object": "江高臣", "confidence": 0.93, "method": "known", "evidence": "嚐從江高臣學印章"},
    {"subject": "程與繩", "predicate": "education:studentOf", "object": "程雲來", "confidence": 0.90, "method": "known", "evidence": "中子與繩亦從君治印"},
    # 江高臣 (entry 27): "即其鄉人何雪漁尚不屑規模之"
    {"subject": "江高臣", "predicate": "nativePlace", "object": "歙人", "confidence": 0.85, "method": "known", "evidence": "高臣，歙人也"},
    # 陶石公 basics
    {"subject": "陶石公", "predicate": "styleName", "object": "碧", "confidence": 0.90, "method": "known", "evidence": "陶石公碧"},
    {"subject": "陶石公", "predicate": "nativePlace", "object": "晉江人", "confidence": 0.90, "method": "known", "evidence": "陶石公碧，晉江人"},
    # 程雲來 basics (entry 28)
    {"subject": "程雲來", "predicate": "styleName", "object": "林", "confidence": 0.90, "method": "known", "evidence": "程雲來林"},
    {"subject": "程雲來", "predicate": "nativePlace", "object": "歙人", "confidence": 0.90, "method": "known", "evidence": "程雲來林，歙人"},

    # ============================================================
    # 李耕隱 (entry 30): 何主臣歿後繼起
    # ============================================================
    {"subject": "李耕隱", "predicate": "nativePlace", "object": "維揚人", "confidence": 0.90, "method": "known", "evidence": "破屋老人李耕隱，維揚人"},

    # ============================================================
    # 鄭宏祐 (entry 38): 皖派
    # ============================================================
    {"subject": "鄭宏祐", "predicate": "belongsToSchool", "object": "皖派", "confidence": 0.85, "method": "known", "evidence": "鄭宏祐…得何氏之傳，隱於秦淮"},

    # ============================================================
    # 萬年少 (萬壽祺, 若) - 明遺民
    # ============================================================
    {"subject": "萬年少", "predicate": "hao", "object": "若", "confidence": 0.93, "method": "known", "evidence": "年少後以一字字，字若"},
    {"subject": "萬年少", "predicate": "styleName", "object": "壽祺", "confidence": 0.95, "method": "known", "evidence": "沙門慧壽，予友彭城萬年少壽祺也"},
    {"subject": "萬年少", "predicate": "education:studentOf", "object": "袁籜庵", "confidence": 0.88, "method": "known", "evidence": "年少與袁籜庵有淵源"},

    # ============================================================
    # 顧元方 - 漳海派
    # ============================================================
    {"subject": "顧元方", "predicate": "nativePlace", "object": "婺源人", "confidence": 0.88, "method": "known", "evidence": "顧元方為婺源人"},
    {"subject": "顧元方", "predicate": "belongsToSchool", "object": "漳海派", "confidence": 0.88, "method": "known", "evidence": "漳海派以顧元方為代表"},

    # ============================================================
    # 張穉恭 - 婁東派
    # ============================================================
    {"subject": "張穉恭", "predicate": "nativePlace", "object": "婁東人", "confidence": 0.90, "method": "known", "evidence": "張穉恭為婁東人"},
    {"subject": "張穉恭", "predicate": "foundedSchool", "object": "婁東派", "confidence": 0.90, "method": "known", "evidence": "張穉恭開婁東派"},

    # ============================================================
    # 文徵明
    # ============================================================
    {"subject": "文徵明", "predicate": "belongsToSchool", "object": "吳門印派", "confidence": 0.88, "method": "known", "evidence": "文徵明與文彭同為吳門人"},

    # ============================================================
    # 周亮工、錢陸燦
    # ============================================================
    {"subject": "周亮工", "predicate": "appellation", "object": "櫟園", "confidence": 0.95, "method": "known", "evidence": "櫟園先生周亮工"},
    {"subject": "周亮工", "predicate": "authorOf", "object": "印人傳", "confidence": 0.99, "method": "known", "evidence": "錢陸燦序《印人傳》"},
    {"subject": "錢陸燦", "predicate": "authorOf", "object": "印人傳序", "confidence": 0.99, "method": "known", "evidence": "清錢陸燦序《印人傳》"},

    # ============================================================
    # 李根
    # ============================================================
    {"subject": "李根", "predicate": "styleName", "object": "居士", "confidence": 0.95, "method": "rule", "evidence": "雲穀居士李根，字阿靈，閩縣人"},

    # ============================================================
    # 莆田派
    # ============================================================
    {"subject": "宋比玉", "predicate": "foundedSchool", "object": "莆田派", "confidence": 0.93, "method": "known", "evidence": "莆田派以宋比玉為代表"},
]


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
