# 印人传 · 历史人物知识图谱与问答系统

基于清代周亮工《印人传》构建的古籍历史人物知识问答系统，覆盖知识抽取、知识图谱构建、实体链接、知识补充、RAG 检索增强、问答推理与前端可视化展示。

> 将古籍中的非结构化知识转化为可查询、可推理、可展示的结构化知识服务。

---

## 项目简介

《印人传》是清代周亮工所著的篆刻家传记合集，记录了明清两代印人的生平、师承、流派与篆刻艺术。本项目以《印人传》为语料，构建一套**纯本地运行**的历史人物知识图谱问答系统，实现从古文文本到结构化知识的全流程转化。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│  文本层                                                          │
│  《印人传》原文  │  ctext 人物条目  │  cbdb 人物条目              │
├─────────────────────────────────────────────────────────────────┤
│  抽取层                                                          │
│  规则预处理  │  Trie 字典匹配  │  正则关系抽取  │  大模型兜底      │
├─────────────────────────────────────────────────────────────────┤
│  图谱层                                                          │
│  RDF/Turtle 构建  │  实体链接(ctext/cbdb)  │  知识融合与消歧      │
├─────────────────────────────────────────────────────────────────┤
│  推理层                                                          │
│  LangGraph 问答 Agent  │  SPARQL 查询  │  RAG 向量检索           │
├─────────────────────────────────────────────────────────────────┤
│  展示层                                                          │
│  网页前端  │  D3.js 关系网络可视化  │  图分析结果展示             │
└─────────────────────────────────────────────────────────────────┘
```

## 核心功能

### 1. 知识抽取

采用**"古文预处理 → Trie 字典匹配 → 正则关系抽取 → 知识库补全"**的混合方案：

- **古文预处理**：繁简转换、异体字规范化（opencc）
- **Trie 字典匹配**：高效匹配人名、地名、字号、官职，解决重叠人名问题
- **正则关系抽取**：师生、学派归属、籍贯、字号等关系的上下文验证
- **知识库补全**：硬编码核心三元组，确保图谱质量基础
- **大模型兜底**：调用 Qwen2.5-Instruct（Ollama 本地部署）对复杂描述句进行关系推理

**抽取实体类型**：

| 类型 | 示例 | 方法 |
|------|------|------|
| 人物（印人） | 文彭、何震、丁敬 | Trie 字典匹配 |
| 字号 | 寿承（字）、三桥（号） | 正则模板匹配 |
| 地名 | 苏州、吴门、杭州、西泠 | Trie 字典匹配 |
| 时间 | 嘉靖、万历、明末、清初 | 正则词表匹配 |
| 流派/印风 | 吴门印派、浙派、秦汉印风 | 正则词典匹配 |
| 官职/身份 | 秀才、知州、隐士 | 正则 + NER 补充 |

**抽取关系体系**：

| 类别 | 关系 | 谓词 | 示例 |
|------|------|------|------|
| 亲属 | 父子 | `:fatherOf` / `:sonOf` | 文徵明 → 文彭 |
| 师承 | 师徒 | `:teacherOf` / `:studentOf` | 何震 → 苏宣 |
| 交游 | 交往 | `:friendOf` | 文彭 ↔ 祝允明 |
| 流派 | 开创 | `:foundedSchool` | 文彭 → 吴门印派 |
| 流派 | 归属 | `:belongsToSchool` | 丁敬 → 浙派 |
| 流派 | 继承 | `:inheritedFrom` | 何震 ← 文彭 |

### 2. 本体与 RDF 知识图谱

基于 OWL 设计本体类层次，输出标准 RDF/Turtle 格式：

```
Thing
├── Person（人物）
├── Place（地点）
├── TimePeriod（时期）
├── School（流派）
├── Style（印风）
├── Work（作品）
├── Artifact（实物）
└── Evidence（抽取证据）
```

**示例三元组**：

```turtle
ex:WenPeng a ex:Person ;
    ex:personName "文彭" ;
    ex:styleName "寿承" ;
    ex:hao "三桥" ;
    ex:birthYear 1498 ;
    ex:deathYear 1575 ;
    ex:nativePlace "苏州" ;
    ex:dynasty "明" .

ex:WenPeng rel:foundedSchool ex:WuMenYinPai .
ex:WenPeng rel:father ex:WenZhengming .
```

每条事实附带抽取证据元数据（来源、原文、置信度、抽取方法）。

### 3. 实体链接与知识补充

融合外部数据库补充《印人传》中缺失的生卒年、籍贯、官职等信息：

- **ctext**（中国哲学书电子化计划）— 人物条目匹配
- **cbdb**（中国历代人物传记资料库，哈佛大学）— 人物 ID、亲属关系、社会关系

**消歧规则**（按优先级）：
1. 字号精确匹配
2. 时间一致性（生卒年/活跃期交叉验证）
3. 关系一致性（父子/师承关系须一致）
4. 地域一致性（籍贯相同或相邻）
5. 朝代一致性
6. 综合加权打分（别名 4 分 + 时间 2 分 + 关系 2 分 + 地域 1 分 + 朝代 1 分）

所有回填数据以 `:sameAs` 关联，标注来源（ctext/cbdb），冲突时原文数据优先。

### 4. 图结构分析

基于 NetworkX 实现，无需独立图数据库：

| 分析项 | 指标 | 说明 |
|------|------|------|
| 度中心性 | Top-N 人物 | 交游/师承关系最丰富的人物 |
| 介数中心性 | 桥梁人物 | 连接不同群体的关键人物 |
| PageRank | 影响力排名 | 综合影响力评估 |
| 社区发现 | Louvain 算法 | 师承/交游群体划分 |
| 流派分析 | 各流派核心人物 | 按 `:belongsToSchool` 分组分析 |
| 最短路径 | 两人关系链 | 师承/交游的最短路径 |
| 流派演化 | 传承路径 | 流派间影响力传递 |

### 5. RAG 检索增强

- 基于 FAISS 构建《印人传》全文向量索引
- 对 SPARQL 查询失败或结果不足时，通过 RAG 检索相关原文段落作为补充
- 支持语义检索，匹配古文中的同义表述

### 6. 问答系统（LangGraph Agent）

基于 LangGraph `StateGraph` 构建的问答工作流：

```
用户提问
  ↓
parse_intent — 意图识别（查属性/查关系/查路径/自由问答）
  ↓
decide_tool_or_sparql — 判断是否可用本地工具直接回答
  ↓                          ↓
call_local_tools         generate_sparql — 大模型生成 SPARQL
  ↓                          ↓
generate_answer          execute_sparql
  ↓                      ↓       ↓
  ← ← ← ← ←        success   fallback_answer
```

**本地工具**：
- `get_person_info` — 查询人物基本信息（字、号、生卒年、籍贯）
- `get_person_relations` — 查询人物关系（师承、亲属、交游）
- `get_school_members` — 查询流派成员
- `get_path_between` — 查询两人之间的关系路径

**支持的问题类型**：
- "文彭的老师是谁？" — 属性查询
- "何震和丁敬之间有什么关系？" — 关系路径查询
- "吴门印派有哪些代表人物？" — 流派查询
- "浙派的传承脉络是怎样的？" — 流派演化分析

### 7. 网页前端

纯前端实现（单个 `index.html`），采用古典印学风格设计：

- **人物卡片** — 展示人物基本信息、字号、生卒年
- **关系网络可视化** — D3.js 力导向图，可交互浏览师承、交游、流派关系
- **问答界面** — 自然语言输入，结构化结果展示
- **图分析面板** — 中心性排名、社区发现结果
- **古典美学 UI** — 朱砂红、宣纸白、墨黑配色，Noto Serif SC 字体

---

## 项目结构

```
印人传/
├── index.html                    # 网页前端（单文件，含 D3.js 可视化）
├── 印人傳.txt                    # 《印人传》原文（繁体，清代周亮工著）
├── 印人傳.epub                   # 《印人传》电子书
├── 项目方案.md                   # 完整技术文档（1000+ 行）
├── 前端设计参考.md               # 前端设计规范与参考
├── README.md                     # 本文件
└── src/                          # 后端 Python 代码
    ├── main.py                   # FastAPI 服务入口
    ├── run_pipeline.py           # 知识图谱构建流水线
    ├── requirements.txt          # Python 依赖
    └── backend/
        ├── extraction/           # 知识抽取模块
        │   ├── text_processor.py     # 文本预处理
        │   ├── ner_rules.py          # NER 规则（字典匹配）
        │   ├── relation_extractor.py # 关系抽取
        │   ├── llm_extractor.py     # 大模型兜底抽取
        │   └── knowledge_base.py     # 核心知识库（硬编码三元组）
        ├── rdf/                   # RDF 图谱模块
        │   ├── ontology.py            # 本体定义（OWL）
        │   ├── turtle_writer.py       # Turtle 序列化
        │   └── rdf_store.py          # RDF 存储与 SPARQL 查询
        ├── linking/               # 实体链接模块
        │   ├── ctext_client.py        # ctext.org API
        │   ├── cbdb_client.py         # CBDB API
        │   ├── linker.py              # 实体链接器
        │   └── knowledge_merger.py    # 知识融合
        ├── graph_analysis/        # 图分析模块
        │   ├── centrality.py          # 中心性分析
        │   ├── community.py           # 社区发现（Louvain）
        │   └── path_finder.py         # 最短路径查询
        ├── qa/                    # 问答系统模块
        │   ├── state.py               # LangGraph 状态定义
        │   ├── nodes.py               # 工作流节点
        │   ├── workflow.py            # LangGraph 工作流
        │   ├── tools.py               # 本地工具集
        │   ├── sparql_generator.py    # SPARQL 生成
        │   └── rag/                   # RAG 模块
        │       ├── embedding.py       # 向量嵌入
        │       ├── vector_index.py   # FAISS 索引
        │       └── retriever.py      # 检索器
        └── utils/
            └── config.py              # 配置管理
```

## 技术栈

| 模块 | 技术 | 说明 |
|------|------|------|
| 后端框架 | FastAPI + Uvicorn | RESTful API 服务 |
| 文本预处理 | Python + opencc | 繁简转换、异体字规范化 |
| 实体抽取 | Trie 字典匹配 | 人名、地名、字号高效匹配 |
| 关系抽取 | 正则规则 + 上下文验证 | 师生、学派、籍贯等关系 |
| 大模型 | Qwen2.5-Instruct（Ollama） | 本地部署，兜底抽取与问答生成 |
| RDF 存储 | rdflib | Python RDF 库，Turtle 格式 |
| SPARQL 查询 | rdflib SPARQL | 图谱查询语言 |
| 向量检索 | FAISS + sentence-transformers | 原文向量索引 |
| 图分析 | NetworkX + python-louvain | 中心性、PageRank、社区发现 |
| 问答编排 | LangGraph | StateGraph 工作流 |
| 前端 | HTML + CSS + D3.js | 单文件，力导向图可视化 |
| 外部数据 | ctext + CBDB | 实体链接与知识补充（预留接口）|

**全部功能基于 Python 及其生态库实现，无需独立图数据库或中间件。**

---

## 核心史料

### 《印人传》简介

- **作者**：周亮工（1612-1672），字元亮，号栎园，河南祥符人
- **成书**：明末清初
- **内容**：记录明清两代篆刻家（印人）的生平、师承、流派与艺术成就
- **特点**：以印论人，以人传印，兼具艺术批评与传记文学价值
- **版本**：叶铭刊本（宣统二年仁和叶铭谨记）

### 主要人物（示例）

| 人物 | 字 | 号 | 时期 | 流派 | 关系 |
|------|---|---|------|------|------|
| 文彭 | 寿承 | 三桥 | 明 | 吴门印派（开创） | 文徵明长子 |
| 文徵明 | 徵仲 | 衡山 | 明 | — | 文彭之父 |
| 何震 | 主臣 | 长卿 | 明 | 徽派 | 文彭弟子 |
| 丁敬 | 敬身 | 砚林 | 清 | 浙派（开创） | — |
| 祝允明 | 希哲 | 枝山 | 明 | — | 文彭交游 |

---

## 使用方式

### 后端服务

```bash
cd src
pip install -r requirements.txt
python main.py
# 服务运行于 http://127.0.0.1:8000
# API 文档: http://127.0.0.1:8000/docs
```

### 知识图谱构建

```bash
cd src
python run_pipeline.py
# 输出: data/output/knowledge_graph.ttl
```

### 浏览前端

```bash
# 直接在浏览器中打开
start index.html
```

### 阅读项目方案

完整技术文档见 `项目方案.md`，包含：
- 知识抽取方案（规则 + 大模型混合抽取）
- 本体与 RDF 设计（OWL 类层次 + 属性定义）
- 实体链接与消歧规则
- 图结构分析方案
- LangGraph 问答系统设计
- 前端设计规范

---

## 相关资源

| 资源 | 链接 | 说明 |
|------|------|------|
| ctext | https://ctext.org | 中国哲学书电子化计划 |
| CBDB | https://cbdb.fas.harvard.edu | 中国历代人物传记资料库（哈佛大学） |
| Ollama | https://ollama.com | 本地大模型运行平台 |
| rdflib | https://rdflib.readthedocs.io | Python RDF 库文档 |
| LangGraph | https://langchain-ai.github.io/langgraph/ | 问答工作流编排 |

---

> 本项目为课程设计作品，所有知识抽取与推理结果均标注置信度与来源，可追溯至《印人传》原文。
