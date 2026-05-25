# 基于 LangChain 的企业内部知识库 RAG 问答系统

这是一个面向企业内部知识管理场景的 RAG 问答系统，支持知识库管理、文档上传解析、向量化入库、检索增强问答、参考来源追踪、对话历史查询、用户权限管理等功能。系统围绕“企业文档知识沉淀与自然语言问答”展开，覆盖从文档入库到问答检索的完整应用链路。

项目采用前后端分离架构：

- 前端：Vue 3 + Vite + Element Plus + Pinia + Vue Router
- 后端：Flask + SQLAlchemy + JWT
- RAG 组件：LangChain + ChromaDB + Ollama
- 数据库：MySQL 8

## 核心设计与技术亮点

- 多轮上下文检索：问答接口会读取同一会话最近几轮历史，并将追问改写为独立检索问题，提升省略指代类问题的召回效果。
- 流式问答输出：提供 SSE 流式问答接口，前端可边生成边展示回答，降低长回答场景下的等待感。
- 检索结果重排：采用“向量召回 TopN + 轻量 Rerank + TopK 入 Prompt”的检索流程，融合向量相似度、关键词覆盖、文件名命中和短语命中。
- 来源引用增强：RAG 上下文按来源编号组织，回答中要求标注来源编号，前端展示文件名、片段序号与可选相似度。
- 向量检索封装：将 Chroma 向量库创建与检索逻辑下沉到 VectorService，支持带相似度分数的检索并提供降级方案。
- RAG 评测集：提供检索评测脚本，对比 Rerank 前后的 Hit@K、Hit@1、MRR 和关键词覆盖率，便于量化优化效果。
- 本地部署配置化：支持通过 `.env` 配置数据库、Ollama 模型、Chroma 持久化目录和 RAG 历史轮数，避免把本地环境信息写死在源码中。
- 仓库清理规范：通过 `.gitignore` 排除 `node_modules`、`__pycache__`、上传文件、Chroma 持久化数据等运行时产物。

## 1. 功能概览

- 用户登录与身份认证
- 管理员首页统计看板
- 知识库新增、编辑、删除、列表查询
- 文档上传、向量化、删除、分页查询
- 基于知识库的 RAG 智能问答
- SSE 流式回答输出
- 多轮追问问题改写与上下文补全
- 向量召回后的 Rerank 重排
- 回答参考来源、片段序号与相似度展示
- RAG 检索评测与指标统计
- 对话历史分页查询与按会话查看
- 普通用户 / 管理员权限隔离

前端主要页面包括：

- 登录
- 首页统计
- 知识库管理
- 文档管理
- 用户管理
- 智能问答
- 对话历史

## 2. 项目结构

```text
.
├─README.md
├─项目源码
│  ├─EnterpriseQA
│  │  ├─client                # 前端项目
│  │  │  ├─index.html
│  │  │  ├─package.json
│  │  │  ├─vite.config.js
│  │  │  ├─public
│  │  │  └─src
│  │  │     ├─api                      # 接口请求封装
│  │  │     ├─assets                   # 静态资源
│  │  │     ├─components               # 公共组件
│  │  │     ├─router                   # 路由配置
│  │  │     ├─stores                   # Pinia 状态管理
│  │  │     ├─views                    # 页面视图
│  │  │     ├─App.vue
│  │  │     ├─main.js
│  │  │     └─style.css
│  │  └─server                # 后端项目
│  │     ├─app.py                      # Flask 启动入口
│  │     ├─config.py                   # 数据库、Ollama、Chroma 等配置
│  │     ├─requirements.txt
│  │     ├─chroma_data                 # Chroma 向量库持久化数据（运行时生成）
│  │     ├─models                      # 数据库模型
│  │     │  ├─chat_history.py
│  │     │  ├─document.py
│  │     │  ├─knowledge_base.py
│  │     │  └─user.py
│  │     ├─routes                      # 后端接口路由
│  │     │  ├─auth.py
│  │     │  ├─chat.py
│  │     │  ├─document.py
│  │     │  ├─knowledge_base.py
│  │     │  ├─stats.py
│  │     │  └─user.py
│  │     ├─services                    # RAG 与向量化服务
│  │     │  ├─rag_service.py
│  │     │  ├─rerank_service.py
│  │     │  └─vector_service.py
│  │     ├─evaluation                  # RAG 检索评测集与评测脚本
│  │     │  ├─rag_eval_set.json
│  │     │  └─evaluate_rag.py
│  │     ├─sql
│  │     ├─static
│  │     ├─templates
│  │     ├─test_docs                   # 测试文档
│  │     ├─uploads                        # 上传后的知识文档存储目录（运行时生成）
│  │     └─utils
│  │        ├─auth.py
│  │        └─response.py
│  └─数据库脚本
│     └─db_enterprise_qa.sql  # MySQL 初始化脚本
└─知识库文档                   # 示例知识文档
   ├─产品使用指南
   ├─公司规章制度
   └─技术开发规范
```

## 3. 运行环境要求

建议环境：

- Windows 10/11
- Anaconda 或 Miniconda
- Python 3.11
- Node.js 18 及以上
- MySQL 8.x
- Ollama

说明：

- 后端依赖来自 `项目源码/EnterpriseQA/server/requirements.txt`
- 前端开发服务器默认端口为 3000
- 后端默认启动端口为 5000
- 前端已配置代理，将 `/api` 转发到 `http://127.0.0.1:5000`
- 下文命令默认从项目根目录执行，进入子目录后的命令会单独说明

## 4. 一键理解运行依赖

这个项目成功运行需要 4 个部分同时满足：

1. MySQL 已启动，并已导入数据库脚本
2. Ollama 已启动，并已拉取大模型与向量模型
3. 后端 Python 依赖已安装
4. 前端 Node.js 依赖已安装

如果其中任何一个没有准备好，项目都可能启动失败。

## 5. 后端启动步骤

### 5.1 创建 Anaconda 虚拟环境

在项目根目录打开 Anaconda Prompt 或 PowerShell：

```powershell
conda create -n enterpriseqa python=3.11 -y
conda activate enterpriseqa
```

### 5.2 进入后端目录

```powershell
cd "项目源码\EnterpriseQA\server"
```

### 5.3 安装后端依赖

```powershell
pip install -r requirements.txt
```

依赖包括：

- flask
- flask-cors
- flask-sqlalchemy
- pymysql
- PyJWT
- langchain
- langchain-community
- langchain-chroma
- langchain-ollama
- chromadb
- python-docx
- pypdf
- python-dotenv

### 5.4 启动后端

```powershell
python app.py
```

默认访问地址：

```text
http://127.0.0.1:5000
```

## 6. 数据库初始化

### 6.1 启动 MySQL 服务

如果 MySQL 已作为 Windows 服务安装，可以在 PowerShell 中执行：

```powershell
Start-Service MySQL
```

检查服务状态：

```powershell
Get-Service MySQL
```

如果 `Status` 显示为 `Running`，说明 MySQL 已启动。

### 6.2 导入数据库脚本

数据库脚本位置：

- `项目源码/数据库脚本/db_enterprise_qa.sql`

默认数据库配置位于 `项目源码/EnterpriseQA/server/config.py`，对应默认值如下：

- 数据库地址：127.0.0.1
- 端口：3306
- 用户名：root
- 密码：123456
- 数据库名：db_enterprise_qa

如果本地 MySQL 密码不是 `123456`，建议不要直接改源码。可以复制后端目录中的 `.env.example`，新建 `.env` 后按需修改：

```powershell
copy "项目源码\EnterpriseQA\server\.env.example" "项目源码\EnterpriseQA\server\.env"
```

也可以在启动前临时设置环境变量：

```powershell
$env:MYSQL_HOST="127.0.0.1"
$env:MYSQL_PORT="3306"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="你的MySQL密码"
$env:MYSQL_DATABASE="db_enterprise_qa"
```

导入 SQL 的典型方式：

```powershell
mysql -u root -p
```

进入 MySQL 后执行：

```sql
source 项目源码/数据库脚本/db_enterprise_qa.sql;
```

### 6.3 默认测试账号

数据库脚本中已包含初始化用户：

- 管理员账号：admin / 123456
- 普通用户账号：user1 / 123456
- 普通用户账号：user2 / 123456

说明：数据库中密码字段保存的是 MD5 值，初始化明文密码均为 123456。

## 7. Ollama 准备

后端默认依赖以下两个 Ollama 模型：

- 对话模型：qwen3:4b
- 向量模型：qwen3-embedding:4b

默认配置在 `项目源码/EnterpriseQA/server/config.py` 中，默认服务地址：

```text
http://localhost:11434
```

请先安装 Ollama，并执行：

```powershell
ollama pull qwen3:4b
ollama pull qwen3-embedding:4b
```

如果你想改模型名称，也可以在启动后端前设置环境变量：

```powershell
$env:OLLAMA_BASE_URL="http://localhost:11434"
$env:OLLAMA_LLM_MODEL="qwen3:4b"
$env:OLLAMA_EMBED_MODEL="qwen3-embedding:4b"
```

## 8. RAG 检索与评测配置

默认 RAG 参数位于 `项目源码/EnterpriseQA/server/config.py`，也可以通过 `.env` 调整：

```text
RETRIEVER_TOP_K=4
RERANK_ENABLED=true
RERANK_CANDIDATE_K=12
RAG_HISTORY_TURNS=3
```

含义说明：

- `RETRIEVER_TOP_K`：最终进入 Prompt 的片段数量。
- `RERANK_ENABLED`：是否启用召回后的轻量重排。
- `RERANK_CANDIDATE_K`：向量检索初始召回候选数，重排后再截取 TopK。
- `RAG_HISTORY_TURNS`：多轮问答中用于问题改写的最近历史轮数。

执行 RAG 检索评测：

```powershell
cd "项目源码\EnterpriseQA\server"
python evaluation\evaluate_rag.py
```

评测脚本会对比基础向量检索与 Rerank 后的效果，输出以下指标：

- `Hit@K`：TopK 片段中是否命中预期来源。
- `Hit@1`：排序第一的片段是否命中预期来源。
- `MRR`：预期来源首次出现排名的倒数均值，越高表示相关片段越靠前。
- `关键词覆盖率`：TopK 片段对标准关键词的覆盖比例。

评测结果会输出到 `项目源码/EnterpriseQA/server/evaluation/results/`，可用于量化 Rerank 优化效果。

基于当前示例知识库的本地评测结果：

- 评测样本数：28 条
- TopK 来源命中率：Rerank 前后均为 100.0%
- Top1 答案关键词覆盖率：84.8% -> 90.5%，提升 5.7 个百分点
- Top1 答案片段命中率：78.6% -> 89.3%

可用于简历的表达：

```text
构建 28 条 RAG 检索评测集，对比基础向量检索与 Rerank 后效果；在保持 TopK 来源命中率 100% 的同时，将 Top1 答案关键词覆盖率由 84.8% 提升至 90.5%。
```

## 9. 前端启动步骤

### 9.1 进入前端目录

```powershell
cd "项目源码\EnterpriseQA\client"
```

### 9.2 安装依赖

```powershell
npm install
```

### 9.3 启动前端开发服务

```powershell
npm run dev
```

默认访问地址：

```text
http://127.0.0.1:3000
```

说明：Vite 已在 `vite.config.js` 中配置代理，访问 `/api` 时会自动转发到后端 `http://127.0.0.1:5000`。

## 10. 推荐启动顺序

建议按以下顺序启动：

1. 启动 MySQL：`Start-Service MySQL`
2. 启动 Ollama
3. 激活 conda 环境并启动后端
4. 启动前端
5. 浏览器访问前端页面并登录

## 11. 快速启动命令汇总

### 11.1 后端

```powershell
conda activate enterpriseqa
cd "项目源码\EnterpriseQA\server"
python app.py
```

### 11.2 前端

```powershell
cd "项目源码\EnterpriseQA\client"
npm install
npm run dev
```

## 12. 常见问题排查

### 12.1 python app.py 启动失败

优先检查以下问题：

- 当前是否已激活正确的 conda 环境
- 是否已执行 pip install -r requirements.txt
- MySQL 是否启动
- 数据库是否已导入 db_enterprise_qa.sql
- MySQL 账号密码是否与配置一致
- Ollama 是否已启动
- 对应模型是否已 pull

### 12.2 npm run dev 启动失败

优先检查以下问题：

- 是否已安装 Node.js
- 是否已先执行 npm install
- Node.js 版本是否过低
- 网络是否导致依赖安装不完整

建议先执行：

```powershell
node -v
npm -v
```

### 12.3 登录成功但问答失败

通常是以下原因之一：

- Ollama 未启动
- 向量模型不存在
- 知识库中没有可用文档
- 文档上传后向量化失败

### 12.4 页面能打开但接口报错

优先检查：

- 后端是否正常监听 5000 端口
- 前端是否运行在 3000 端口
- 是否存在跨域或代理异常
- 浏览器开发者工具 Network 面板返回的具体错误信息

## 13. 关于示例数据

仓库中包含：

- 数据库初始化脚本：`项目源码/数据库脚本/db_enterprise_qa.sql`
- 示例知识文档：`知识库文档/`
- 后端测试文档：`项目源码/EnterpriseQA/server/test_docs/`

建议按以下方式准备知识库数据：

- 先导入数据库完成基础表结构和用户初始化
- 登录管理员账号，在“文档管理”页面上传 `知识库文档/` 或 `test_docs/` 中的示例文件
- 上传成功后，系统会自动解析文档、生成文本分块，并写入 Chroma 向量库
- `uploads/` 和 `chroma_data/` 属于运行时数据目录，会在本地运行过程中生成，不建议作为源码提交

## 14. 主要接口概览

后端接口统一以 /api 开头，主要包括：

- /api/auth：登录、用户信息
- /api/knowledge_base：知识库管理
- /api/document：文档管理与上传
- /api/chat：智能问答、流式问答、历史会话
- /api/user：用户管理
- /api/stats：统计信息

## 15. 权限说明

- 管理员：可访问首页统计、知识库管理、文档管理、用户管理
- 普通用户：可使用智能问答、查看自己的对话历史

前端路由中对管理员页面做了权限控制，后端接口也做了登录校验和管理员校验。

## 16. 开发建议

- 不要直接在 base 环境中安装后端依赖
- 推荐固定使用独立 conda 环境
- 修改数据库或 Ollama 配置时，优先使用环境变量覆盖
- 新增知识文档后，优先在页面中上传，让系统自动完成向量化

## 17. 后续可完善项

- 增加统一日志输出与错误日志落盘
- 增加接口文档
- 增加自动化测试
- 增加 Docker 部署方式
- 增加流式输出、Rerank 与 RAG 评测集

如果你当前的后端或前端仍然启动失败，建议把终端报错完整贴出来，再按报错逐项修复。这个项目大多数启动失败都集中在依赖未安装、MySQL 未就绪、Ollama 未启动三类问题上。
