# PaperMind

PaperMind 是一个面向科研论文阅读的本地问答 Agent，支持 PDF 解析、RAG 检索、问答纠错、arXiv/Semantic Scholar 检索、Word 读书笔记和 HTML 知识图谱。

## 功能

- 上传或加载 PDF，按章节解析论文内容
- 使用 FAISS 和 Sentence Transformers 构建本地向量知识库
- 通过火山引擎豆包的 OpenAI 兼容接口进行论文问答
- 对含数值和事实性结论的回答回源校验
- 生成 Word 读书笔记和可交互 HTML 知识图谱
- 提供命令行和 Gradio Web 两种界面

## 环境要求

- Python 3.10 或 3.11（推荐 3.11）
- 可访问 Hugging Face，首次运行会下载 Embedding 模型
- 火山引擎 API Key 和模型 Endpoint ID

## 安装

```powershell
git clone https://github.com/3901984509cry/Papermin-agent.git
cd Papermin-agent

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Copy-Item .env.example .env
notepad .env
```

在 `.env` 中填写自己的配置：

```dotenv
VOLC_API_KEY=your_api_key
VOLC_MODEL_ID=your_endpoint_id
```

`.env` 已被 Git 忽略，请勿把真实 Key 写入代码或提交到仓库。

如果 Hugging Face 访问较慢，可以在启动前设置镜像：

```powershell
$env:HF_ENDPOINT = "https://hf-mirror.com"
```

## 启动

Web 界面：

```powershell
python web_app.py
```

浏览器访问 `http://127.0.0.1:7860`。

命令行界面：

```powershell
python main.py
```

也可以启动时直接传入论文路径：

```powershell
python main.py "C:\path\to\paper.pdf"
```

## 使用流程

1. 启动 Web 界面并上传一篇文本型 PDF。
2. 点击“解析 + 建立知识库”，等待本地 Embedding 模型完成向量化。
3. 使用右侧对话框提问，或使用核心贡献、研究方法、实验结果等快捷按钮。
4. 需要长期保留的信息可以让 Agent “记住”；换论文时当前论文索引会清空，用户记忆会保留。
5. 生成的读书笔记和知识图谱保存在 `output/`，论文解析结果和索引保存在 `memory/`。

扫描版 PDF 本身没有可提取的文本，需要先用 OCR 软件生成带文本层的 PDF。

## 项目结构

```text
Papermin-agent/
├── agent.py                 # Agent 核心逻辑
├── config.py                # 环境变量和运行目录配置
├── main.py                  # 命令行入口
├── self_correction.py       # 回源纠错
├── web_app.py               # Gradio Web 入口
├── requirements.txt         # Python 依赖
├── tools/
│   ├── generate_notes.py    # Word 笔记
│   ├── knowledge_base.py    # FAISS 知识库
│   ├── knowledge_map.py     # HTML 知识图谱
│   ├── parse_pdf.py         # PDF 解析
│   └── search_arxiv.py      # 论文检索
├── memory/                  # 自动生成的本地索引，不提交
└── output/                  # 自动生成的文档，不提交
```

## 可选配置

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `VOLC_BASE_URL` | `https://ark.cn-beijing.volces.com/api/v3` | OpenAI 兼容接口地址 |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | 本地 Embedding 模型 |
| `PAPERMIND_MEMORY_DIR` | 项目下的 `memory/` | 索引与解析结果目录 |
| `PAPERMIND_OUTPUT_DIR` | 项目下的 `output/` | 生成文件目录 |
| `MODEL_TEMPERATURE` | `0.3` | 模型温度 |
| `MODEL_MAX_TOKENS` | `4096` | 单次最大输出 token 数 |
| `GRADIO_SERVER_NAME` | `0.0.0.0` | Web 监听地址 |
| `GRADIO_SERVER_PORT` | `7860` | Web 监听端口 |
| `GRADIO_INBROWSER` | `true` | 启动时是否打开本机浏览器 |
| `GRADIO_SHARE` | `false` | 是否创建 Gradio 临时公网链接 |

## Linux 或服务器部署

```bash
git clone https://github.com/3901984509cry/Papermin-agent.git
cd Papermin-agent
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 后启动
python web_app.py
```

Web 服务默认监听 `0.0.0.0:7860`。云服务器还需要在安全组或防火墙中放行 7860 端口；不要把包含真实 Key 的 `.env` 放进镜像或公开日志。

## 常见问题

### `ModuleNotFoundError: No module named 'tools'`

确认使用的是仓库最新版本，且当前目录为仓库根目录。新版仓库必须包含完整的 `tools/` 目录和 `tools/__init__.py`。

### `ModuleNotFoundError: No module named 'gradio'`

重新激活虚拟环境并安装完整依赖：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
```

请使用仓库中的完整 `requirements.txt`，不要只单独安装 Gradio。项目已锁定与 Gradio 3.50 兼容的 FastAPI/Starlette 版本，避免首页出现模板 API 错误。

### PowerShell 禁止执行 `Activate.ps1`

不修改系统执行策略也可以直接使用虚拟环境中的 Python：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe web_app.py
```

### 首次启动停在 Embedding 模型下载

首次启动需要下载 `all-MiniLM-L6-v2`。确认可以访问 Hugging Face，或在同一个终端设置镜像后重试：

```powershell
$env:HF_ENDPOINT = "https://hf-mirror.com"
python web_app.py
```

### Windows 终端中的图标显示为问号

程序会自动避免 GBK 终端因图标字符崩溃。若希望完整显示图标，可在启动前启用 Python UTF-8 模式：

```powershell
$env:PYTHONUTF8 = "1"
python web_app.py
```

### 项目路径包含中文时 FAISS 索引失败

新版已通过 Python 文件接口读写 FAISS 索引，支持中文项目路径。若仍遇到索引文件错误，请确认 `memory/` 目录可写，并检查 `PAPERMIND_MEMORY_DIR` 是否指向有效目录。

### API 调用失败

依次检查：

1. `.env` 中的 `VOLC_API_KEY` 和 `VOLC_MODEL_ID` 是否填写且没有多余引号。
2. Endpoint 是否已在火山引擎控制台启用，模型和地域是否与接口地址匹配。
3. 当前网络是否能访问 `VOLC_BASE_URL`。
4. 旧 Key 若曾公开，必须撤销后使用新 Key。

### 端口 7860 已占用

在 `.env` 中设置其他端口后重启，例如 `GRADIO_SERVER_PORT=7861`；也可以先停止占用 7860 端口的进程。

## 部署自检

完成安装后建议运行：

```powershell
python -m pip check
python -m compileall -q .
python -c "import gradio, pymupdf, faiss, sentence_transformers; print('依赖导入成功')"
```

上述命令只检查依赖和源码；完整在线问答仍需要有效的火山引擎配置及网络连接。

## 数据与安全

- `memory/` 会保存解析后的论文文本、向量索引和用户记忆。
- `output/` 会保存生成的 `.docx` 和 `.html` 文件。
- 这两个目录的运行数据以及 `.env`、虚拟环境、缓存文件均不会提交到 Git。
- 如果 Key 曾经提交到公开仓库，仅删除代码中的 Key 不足以保证安全，必须到服务商控制台撤销旧 Key 并创建新 Key。
