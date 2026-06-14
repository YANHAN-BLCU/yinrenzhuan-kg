"""
问句规范化节点。
把用户的多种自然语言变体改写为标准的查询问句，
确保下游 entity 抽取和 SPARQL 模板能稳定工作。
"""
import logging
import httpx

logger = logging.getLogger(__name__)


# Few-shot 示例：训练 LLM 把变体改写为标准问句
NORMALIZER_PROMPT = """你是一个中文问句规范化助手。任务：把用户关于《印人传》篆刻家知识图谱的多种问法，统一改写为符合以下标准模板的中文问句（保持简明，不改变核心语义）。

# 支持的标准问句模板（必须用以下其中一种输出）
1. 查人物概况（最常用）："{{人名}}是谁？"
2. 查人物的老师："{{人名}}的师父是谁？"
3. 查人物的学生："{{人名}}的弟子有哪些？"
4. 查人物的流派："{{人名}}属于哪个流派？"
5. 查流派的成员："{{流派名}}有哪些人？"（流派名要简洁，如"皖派"，不要加"流派"二字）
6. 查人物关系："{{人名1}}和{{人名2}}是什么关系？"
7. 查人物路径："{{人名1}}和{{人名2}}的最短关系路径是什么？"
8. 未知/观点/闲聊：保留原样（不要改写）。

# 重要规则
- "X 是谁"、"谁是 X"、"X 是何许人"、"X 是什么人" → 模板 1："X是谁？"
- 仅给一个人名（如"文彭"）→ 模板 1："文彭是谁？"
- "X 的字/号/生卒年/籍贯/朝代" → 模板 1 即可（"X是谁？"查概况，包含所有属性）
- 不要把"皖派"拆解成"皖"+"派"，作为一个整体保留
- 保持人名原样（不添加"先生"、"印人"等后缀）
- 问号 "？" 用全角
- 如果原句包含非人物、非流派的观点性内容（"你觉得"、"好不好"），保留原样不要改写

# 示例
原句: "皖派都有谁啊"
改写: 皖派有哪些人？

原句: "谁属于皖派"
改写: 皖派有哪些人？

原句: "何震的老师是？"
改写: 何震的师父是谁？

原句: "文彭的字号是啥"
改写: 文彭是谁？

原句: "何震的字是什么"
改写: 何震是谁？

原句: "文彭是谁？"
改写: 文彭是谁？

原句: "谁是文彭"
改写: 文彭是谁？

原句: "文彭"
改写: 文彭是谁？

原句: "文彭和何震"
改写: 文彭和何震是什么关系？

原句: "文彭和何震是谁？"
改写: 文彭和何震是什么关系？

原句: "文彭与何震"
改写: 文彭和何震是什么关系？

原句: "介绍下文彭和何震"
改写: 文彭和何震是什么关系？

原句: "何震是何许人也"
改写: 何震是谁？

原句: "你了解篆刻吗？"
改写: 你了解篆刻吗？

# 你的任务
原句: "{question}"
改写:"""


class QuestionNormalizer:
    """基于 LLM 的问句规范化器。"""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._cache: dict = {}  # 简单缓存，避免重复调用

    def normalize(self, question: str) -> str:
        """
        把任意中文问句改写为标准模板问句。
        失败时返回原句（不影响下游）。
        """
        if not self.enabled or not question:
            return question

        # 缓存命中
        if question in self._cache:
            return self._cache[question]

        try:
            from backend.utils.config import (
                OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL,
            )
            if not OPENAI_API_KEY:
                return question

            prompt = NORMALIZER_PROMPT.format(question=question)
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions",
                    json={
                        "model": OPENAI_MODEL,
                        "messages": [
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 80,
                        "temperature": 0.0,
                    },
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                )
            if resp.status_code == 200:
                rewritten = resp.json()["choices"][0]["message"]["content"].strip()
                # 清理常见前缀
                for prefix in ["改写:", "改写：", "答:", "答：", "输出:", "输出："]:
                    if rewritten.startswith(prefix):
                        rewritten = rewritten[len(prefix):].strip()
                # 提取第一个非空行（避免 LLM 给出多个候选项）
                rewritten = rewritten.split("\n")[0].strip()
                # 去掉残留的英文双引号（避免带引号字符串进入下游）
                rewritten = rewritten.strip('"\'「」')
                if rewritten and len(rewritten) <= 100:
                    self._cache[question] = rewritten
                    logger.info(f"[NORMALIZE] '{question}' -> '{rewritten}'")
                    return rewritten
        except Exception as e:
            import traceback
            logger.warning(f"[NORMALIZE] LLM failed: {type(e).__name__}: {e}")
            logger.debug(traceback.format_exc())

        return question
