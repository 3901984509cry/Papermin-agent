# PaperMind — 快速启动指南
#
## 目录结构

```
papermind/
├── config.py            ← ⚠️ 第一步：填写 API Key
├── main.py              ← 启动入口
├── agent.py             ← Agent 核心逻辑
├── self_correction.py   ← Self-Correction 纠错
├── requirements.txt     ← 依赖清单
├── tools/
│   ├── parse_pdf.py     ← 工具①：PDF 解析
│   ├── knowledge_base.py← 工具②③⑦：向量知识库
│   ├── search_arxiv.py  ← 工具④：arXiv 搜索
│   ├── generate_notes.py← 工具⑤：生成 Word 笔记
│   └── knowledge_map.py ← 工具⑥：生成知识图谱
├── memory/              ← 自动创建：存放向量索引和文本块
└── output/              ← 自动创建：存放生成的文件
```

## 安装步骤

```bash
# 1. 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate         # Windows
# 2. 进入文件夹
cd "C:\Users\lenovo\Desktop\cry.穷的文件夹\PaperMind_代码\papermind"
# 3.设置镜像网站
set HF_ENDPOINT=https://hf-mirror.com
# 4. 安装依赖
pip install -r requirements.txt
# 5. 填写配置（必做）
# 打开 config.py，填写：
# - VOLC_API_KEY   = "你的火山引擎 API Key"
# - VOLC_MODEL_ID  = "你的 Endpoint ID"
# 6.运行
python main.py
#一键启动！！！
venv\Scripts\activate
cd "C:\Users\lenovo\Desktop\cry.穷的文件夹\PaperMind_代码\papermind"
set HF_ENDPOINT=https://hf-mirror.com
python main.py

```

## ⚠️ 需要填写的位置汇总

| 文件 | 变量 | 说明 |
|------|------|------|
| config.py | VOLC_API_KEY | 火山引擎 API Key |
| config.py | VOLC_MODEL_ID | 豆包模型 Endpoint ID |
| config.py | EMBEDDING_MODEL | 可选：换用学术 Embedding 模型 |
| agent.py | k=8（memory） | 可选：调整记忆保留轮数 |
| tools/generate_notes.py | font.name | 可选：修改 Word 字体 |
| tools/search_arxiv.py | proxies | 可选：配置网络代理 |

## 获取火山引擎 API Key

1. 登录 https://console.volcengine.com
2. 进入「豆包大模型」→「API Key 管理」→ 创建 Key
3. 进入「推理接入点」→ 创建接入点 → 复制 Endpoint ID
