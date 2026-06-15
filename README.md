# 印脉知鉴 · 印人传历史人物知识图谱与问答系统

> 来自中国北京语言大学（北语 BLCU）历史系徐鹏老师《知识图谱》课程结课项目  
> 把周亮工《印人传》《续印人传》这部篆刻家传集合在现代问答系统里，提供「问得到、看得见」的古籍知识服务。

把这两个字留给读到此仓库的人：清 印学家周亮工写下印人传时，篆刻是手艺、传是体面；
今天我们用 LLM + RDF + 向量检索把它交给电脑，让「文彭的老师是谁」「何震与丁敬有什么关系」这种问题，
能得到一段既能在图谱上点出来、又能附上原文出处的回答。

---

## 这是什么

本项目以**清代周亮工《印人传》三卷及《续印人传》四卷**为语料，
构建了一个**纯本地运行**的古籍历史人物知识图谱问答系统，覆盖：

| 层级 | 内容 |
|---|---|
| 抽取层 | 规则正则 + LLM 少样本 抽取人名 / 字号 / 流派 / 关系 |
| 图谱层 | OWL 本体 + RDF/Turtle + ctext/CBDB 实体链接与消歧 |
| 推理层 | LangGraph 问答 Agent，集成 SPARQL 查询 + RAG 原文检索 |
| 展示层 | 古风 D3.js 单页前端（人物卡片 / 关系网络 / 问答 / 图分析） |

**已预生成的数据**：`data/output/linked_graph.ttl`（合并 ctext/cBDB 后约 70 个印人、200+ 三元组）
已随仓库一起发布 —— **克隆仓库后不需要跑抽取流程，就能直接问答。**

---

## 下载即跑（推荐路径）

> 适用：想先看到东西，再决定要不要折腾的人。
> 需要：Python 3.10+、一个 LLM 的 API Key（问句改写 + 答案生成 + 可选 Embedding）。

### 1. 克隆并安装

```bash
git clone https://github.com/YANHAN-BLCU/yinrenzhuan-kg.git
cd yinrenzhuan-kg

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. 准备 API Key（自己提供，没有写死在代码里）

复制模板：

```bash
cp .env.example .env
```

打开 `.env`，至少填一个 LLM Key（兼容 OpenAI 协议即可）：

```ini
# 主体 LLM（问句规范化 + 答案合成）—— 必填
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# 向量 Embedding（用于 RAG 原文检索）—— 强烈建议填
EMBEDDING_API_KEY=sk-your-siliconflow-key
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL=BAAI/bge-m3

# 本地 Ollama —— 可选，删掉就关掉
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=qwen2.5:7b
```

`.env` 已被 `.gitignore` 排除，**绝不会被提交到 git**。仓库里只有 `.env.example` 占位符。

#### 推荐的省钱 / 免费组合

| 服务 | 用在哪 | 为什么推荐 |
|---|---|---|
| [DeepSeek](https://platform.deepseek.com/) | `OPENAI_API_KEY` | 1 元钱能跑几千次中文问答，质量与 GPT-4 相当 |
| [SiliconFlow](https://siliconflow.cn/) | `EMBEDDING_API_KEY` | 注册送 2000 万 token 免费额度，BAAI/bge-m3 中文检索效果最好 |
| Ollama + Qwen2.5:7b | SPARQL 生成 | 完全离线，免费，但需单独装 |

> **没有 LLM 能跑吗？** 能。图谱、SPARQL 工具、前端可视化、中心性/社区分析都能用。
> 只有「问句改写」「自然语言答案合成」「RAG 原文检索」三项会降级为规则匹配。

### 3. 启动

```bash
python src/main.py
```

打开浏览器访问 <http://127.0.0.1:8000>。

第一次启动会做的事：
- 加载 `data/output/linked_graph.ttl`（< 1 秒）
- 尝试加载 FAISS RAG 索引；没建过会 warn，不影响使用
- 监听 `0.0.0.0:8000`

试试这些问题：
- 「文彭的老师是谁」
- 「何震和丁敬之间有什么关系」
- 「吴门印派有哪些人」
- 「浙派的传承」

---

## （可选）重建 RAG 索引

> 让自然语言回答附上《印人传》原文片段，提升答案可信度。

需要：填好 `EMBEDDING_API_KEY`。

```bash
# 一次性构建 FAISS 索引（约 1–2 分钟，依赖网络）
curl -X POST http://127.0.0.1:8000/api/build_index

# 或者本地重建（更稳）
python -c "from src.run_pipeline import run_pipeline; run_pipeline(skip_rag=False, skip_linking=True, skip_analysis=True)"
```

成功后会在 `data/output/` 看到 `yinrenchuan_faiss.index` + `.meta.json`。
下次启动服务时 RAG 自动加载。

---

## （可选）从零重建图谱

> 适用：想改抽取规则、想试新模型、想加新材料。
> 会用 LLM 重新跑一遍抽取 → 链接 → 中心性 → 社区发现，**慢且吃 API 配额**。

```bash
# 完整流程（约 20–40 分钟，依赖 LLM）
python src/run_pipeline.py

# 不调 LLM，纯规则抽取（快但漏召）
python src/run_pipeline.py --use-rules-only

# 只跑部分阶段
python src/run_pipeline.py --skip-linking --skip-analysis --skip-rag
```

输出文件全部落在 `data/output/`，下一次 `python src/main.py` 启动就会自动加载新版。

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│  文本层                                                               │
│  印人傳.txt  +  續印人傳.txt   │   ctext 人物条目   │   CBDB 人物条目    │
├─────────────────────────────────────────────────────────────────────┤
│  抽取层                                                               │
│  TextProcessor 断句  │  NER (LLM 优先 · 规则兜底)  │  关系抽取          │
├─────────────────────────────────────────────────────────────────────┤
│  图谱层                                                               │
│  RDF/Turtle  │  实体链接(ctext/cBDB)  │  消歧打分  │  知识融合          │
├─────────────────────────────────────────────────────────────────────┤
│  推理层                                                               │
│  LangGraph StateGraph                                                  │
│  问句规范化 → 意图分类 → 工具 or SPARQL → RAG 兜底 → 答案合成        │
├─────────────────────────────────────────────────────────────────────┤
│  展示层                                                               │
│  index.html + static/  │  D3.js 力导向图  │  FastAPI 后端             │
└─────────────────────────────────────────────────────────────────────┘
```

### 知识图谱本体（OWL）

```
Thing
├── Person           印人（明 / 清）
│   ├── styleName    字（如"寿承"）
│   ├── hao          号（如"三桥"）
│   ├── nativePlace  籍贯
│   └── dynasty      朝代
├── Place            地名
├── TimePeriod       时期
├── School           流派（吴门印派、浙派、徽派、皖派…）
├── Style            印风
├── Work             作品
├── Artifact         实物
└── Evidence         抽取证据（每条事实都附原文 + 置信度 + 抽取方法）
```

### 关系体系

| 类别 | 关系 | RDF 谓词 | 示例 |
|---|---|---|---|
| 亲属 | 父子 | `hasFather` / `hasSon` | 文徵明 → 文彭 |
| 师承 | 师徒 | `hasStudent` / `hasTeacher` | 何震 ← 文彭 |
| 交游 | 交往 | `hasFriend` | 文彭 ↔ 祝允明 |
| 流派 | 开创 | `hasFounder` | 文彭 → 吴门印派 |
| 流派 | 归属 | `belongsToSchool` | 丁敬 → 浙派 |
| 继承 | 取法 | `inheritedFrom` | 何震 ← 文彭 |

### 消歧规则（链接到 ctext/CBDB 时按此打分）

1. 字号精确匹配（+4）
2. 时间一致性（+2）
3. 关系一致性（+2）
4. 地域一致性（+1）
5. 朝代一致性（+1）

冲突时原文抽取结果优先，外部数据以 `:sameAs` 关联，不覆盖。

### 问答工作流（LangGraph StateGraph）

```
用户提问
  ↓
normalize_question   ← LLM 改写"皖派都有谁啊"为"皖派的代表人物"
  ↓
parse_intent         ← 意图分类（属性 / 关系 / 路径 / 流派 / 自由）
  ↓
decide_tool_or_sparql
  ↓                              ↓
call_local_tools                generate_sparql ← LLM
  ↓                              ↓
answer_from_tools              execute_sparql
  ↓                              ↓
        ← 验证 ←   ← 成功 / 失败
  ↓
  RAG 兜底（若 SPARQL 失败或结果空） ← Embedding 检索原文
  ↓
compose_answer        ← LLM 合成自然语言回答
```

---

## 目录结构

```
.
├── README.md                          # 本文件
├── .env.example                       # 环境变量模板（必读）
├── requirements.txt                   # Python 依赖
├── index.html                         # 前端入口
├── static/                            # 前端资源（CSS / JS）
│   ├── css/{base,home,graph,qa}.css
│   └── js/{base,home,graph,qa,trad_sim,variant}.js
├── index_card/                        # 人物头像 PNG（前端用）
├── data/
│   └── output/                        # 知识图谱产物（提交预生成版）
│       ├── knowledge_graph.ttl        # 抽取后原始 RDF
│       ├── linked_graph.ttl           # 实体链接后 RDF（运行时加载）
│       └── yinrenchuan_faiss.*        # FAISS 索引（运行时构建）
├── 印人傳.txt                          # 《印人传》原文（繁体）
├── 續印人傳.txt                        # 《续印人传》原文（繁体）
└── src/
    ├── main.py                        # FastAPI 入口
    ├── run_pipeline.py                # 一键重建图谱
    └── backend/
        ├── extraction/                # 文本预处理 + NER + 关系抽取
        ├── rdf/                       # 本体 + RDF 存储 + Turtle 写入
        ├── linking/                   # ctext / CBDB 客户端 + 链接器
        ├── graph_analysis/            # 中心性 / 社区 / 路径
        └── qa/                        # LangGraph 问答工作流 + RAG
            ├── workflow.py
            ├── question_normalizer.py
            ├── sparql_generator.py
            ├── tools.py               # 本地工具
            └── rag/                   # Embedding + FAISS 检索
```

---

## API 速查

启动后访问 <http://127.0.0.1:8000/docs> 看 Swagger UI。

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET`  | `/api/health` | 健康检查 |
| `GET`  | `/api/info` | 服务信息 |
| `GET`  | `/api/persons` | 全部人物 |
| `GET`  | `/api/schools` | 全部流派 |
| `GET`  | `/api/school/{name}` | 流派成员 |
| `GET`  | `/api/graph` | 图数据（前端用） |
| `GET`  | `/api/analysis/centrality` | 中心性分析 |
| `GET`  | `/api/analysis/communities` | 社区发现 |
| `POST` | `/api/qa` | 自然语言问答 |
| `POST` | `/api/sparql` | 直接跑 SPARQL |
| `POST` | `/api/build_index` | 构建 FAISS RAG 索引 |
| `POST` | `/api/reload` | 重新加载图谱 |

`POST /api/qa` 请求体：

```json
{ "question": "文彭的老师是谁" }
```

返回体：

```json
{
  "question": "文彭的老师是谁",
  "answer": "文彭的老师是文徵明（长子是也），…",
  "intent": "query_teacher",
  "entities": [{"name": "文彭", "type": "person"}],
  "answer_source": "local_tool" | "sparql" | "rag" | "fallback"
}
```

---

## 技术栈

| 模块 | 技术 | 用途 |
|---|---|---|
| 后端 | FastAPI + Uvicorn | REST API |
| RDF | rdflib | 图谱存储 + SPARQL |
| 向量 | FAISS + sentence-transformers | 原文语义检索 |
| 抽取 | LLM (OpenAI 协议) + 正则 + 知识库 | NER + 关系 |
| 链接 | ctext.org + CBDB API | 外部知识融合 |
| 图分析 | NetworkX + python-louvain | 中心性 / 社区 / 最短路径 |
| 编排 | LangGraph | 问答工作流 |
| 前端 | 原生 HTML + CSS + D3.js | 古风可视化 |

**不需要**任何独立图数据库 / 中间件，开箱即用。

---

## 常见问题

**Q: 启动后浏览器是空白的？**  
A: 多半是 `/static/` 没被服务挂上。确认你拉的是最新代码（包含 `static/` 目录）。F12 看 404。

**Q: 问"文彭的老师是谁"返回 fallback_answer？**  
A: 没有填 `OPENAI_API_KEY`，或者 LLM 返回被网络防火墙挡了。先 `curl http://127.0.0.1:8000/api/health` 确认服务活着，再看终端日志。

**Q: 怎么换 LLM 服务？**  
A: 改 `.env` 里的 `OPENAI_BASE_URL` 和 `OPENAI_MODEL`，只要该服务兼容 OpenAI Chat Completion 协议就行。已测试 DeepSeek、通义、智谱、SiliconFlow、本地 Ollama。

**Q: 怎么加新材料？**  
A: 把新文本按 `印人傳.txt` 同样的格式放进 `data/raw/`，改 `src/backend/utils/config.py` 里的 `YINRENCHUAN_TXT` 路径，跑 `python src/run_pipeline.py`。

**Q: `RAG initialization failed` 是什么？**  
A: 没装 sentence-transformers 的中文模型，或者 `EMBEDDING_API_KEY` 没用。不影响问答主功能。

---

## 致谢

- 语料：[周亮工《印人传》《续印人传》](https://ctext.org/wiki.pl?if=gb&chapter=662139)
- 外部知识：[中国哲学书电子化计划 ctext](https://ctext.org)、[中国历代人物传记资料库 CBDB](https://cbdb.fas.harvard.edu)
- 古文预训练：[SikuRoBERTa](https://huggingface.co)
- 向量模型：[BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3)

---

> 本项目为北京语言大学《知识图谱》课程结课作业。  
> 所有抽取事实标注置信度与原文出处，冲突时原文优先。
