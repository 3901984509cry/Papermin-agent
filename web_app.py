"""
PaperMind Web 界面 - 稳定兼容版
安装依赖：pip install "gradio>=3.50,<4.0"
启动方式：python web_app.py
访问地址：http://localhost:7860
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gradio as gr
from agent import build_agent, ask
from tools.knowledge_base import build_kb_from_parsed_paper, clear_paper_index
from tools.parse_pdf import parse_pdf
from config import MEMORY_DIR, OUTPUT_DIR

# ── 全局状态 ──────────────────────────────────────────────────────────────────
_agent      = None
_paper_name = "未加载"


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

def get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MEMORY_DIR, exist_ok=True)

# ── 核心函数 ──────────────────────────────────────────────────────────────────

def load_paper(pdf_path):
    global _paper_name
    if not pdf_path:
        return "❌ 请先上传 PDF 文件", "未加载"

    # 👇 关键修复：将 Gradio 文件对象转为路径字符串
    if hasattr(pdf_path, 'name'):  # Gradio 3.x 返回的文件对象有 name 属性
        pdf_path = pdf_path.name

    try:
        get_agent()
        clear_paper_index()
        parse_result = parse_pdf(pdf_path)  # 现在传入的是字符串路径
        kb_result = build_kb_from_parsed_paper()
        _paper_name = Path(pdf_path).stem
        return f"{parse_result}\n\n{kb_result}", f"📄 {_paper_name}"
    except Exception as e:
        return f"❌ 加载失败：{e}", "加载失败"

def chat_fn(message, history):
    if not message or not message.strip():
        return history, ""
    history = history or []
    try:
        response = ask(get_agent(), message)
    except Exception as e:
        response = f"❌ 出错：{e}"
    history.append([message, response])
    return history, ""


def clear_fn():
    if _agent:
        try:
            _agent.memory.clear()
        except Exception:
            pass
    return [], "✅ 对话记忆已清空"


def get_files():
    if not os.path.exists(OUTPUT_DIR):
        return "output/ 目录为空"
    files = sorted(
        [f for f in Path(OUTPUT_DIR).iterdir() if f.is_file()],
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )
    if not files:
        return "output/ 目录为空，生成笔记或知识图谱后文件会出现在这里"
    lines = []
    icons = {".docx": "📝", ".html": "🌐", ".md": "📋"}
    for f in files[:15]:
        icon = icons.get(f.suffix.lower(), "📄")
        size = f.stat().st_size
        size_s = f"{size/1024:.1f}KB" if size > 1024 else f"{size}B"
        lines.append(f"{icon} {f.name}  ({size_s})")
    return "\n".join(lines)


def quick_fn(prompt, history):
    return chat_fn(prompt, history)


# ── 快捷提问 ──────────────────────────────────────────────────────────────────
QUICK = [
    ("🎯 核心贡献",  "这篇论文的核心贡献是什么？"),
    ("🔬 研究方法",  "作者提出了什么方法，核心原理是什么？"),
    ("📊 实验结果",  "论文的主要实验结果如何？"),
    ("🤔 方法动机",  "作者为什么选择这个方法而不是其他方法？"),
    ("⚠️ 局限性",    "这篇论文有哪些局限性？"),
    ("📝 生成笔记",  "帮我生成这篇论文的完整精读笔记文档"),
    ("🗺️ 知识图谱",  "帮我画这篇论文核心概念的知识图谱"),
    ("📚 延伸阅读",  "推荐3篇与这篇论文最相关的延伸阅读"),
]

# ── 界面 ──────────────────────────────────────────────────────────────────────
with gr.Blocks(title="PaperMind") as demo:

    gr.Markdown("""
# 📘 PaperMind — 智能科研论文理解 Agent
基于火山引擎豆包大模型 · LangChain · RAG · Self-Correction · 长期记忆
""")

    with gr.Row():

        # ── 左侧面板 ──────────────────────────────────────────────────────
        with gr.Column(scale=1, min_width=260):

            gr.Markdown("### 📂 论文管理")
            pdf_upload = gr.File(
                label="上传 PDF 论文（换论文时自动清空旧索引）",
                file_types=[".pdf"],
                type="file",
            )
            load_btn   = gr.Button("🚀 解析 + 建立知识库", variant="primary")
            paper_info = gr.Textbox(
                label="当前论文",
                value="未加载",
                interactive=False,
            )
            load_log = gr.Textbox(
                label="加载日志",
                value="等待加载论文...",
                lines=5,
                interactive=False,
            )

            gr.Markdown("---")
            gr.Markdown("### ⚡ 快捷提问")
            quick_buttons = []
            for label, _ in QUICK:
                b = gr.Button(label, size="sm")
                quick_buttons.append(b)

            gr.Markdown("---")
            gr.Markdown("### 📁 已生成文件")
            files_box   = gr.Textbox(
                label="output/ 目录",
                value=get_files(),
                lines=6,
                interactive=False,
            )
            refresh_btn = gr.Button("🔄 刷新", size="sm")

        # ── 右侧对话区 ────────────────────────────────────────────────────
        with gr.Column(scale=2):

            gr.Markdown("### 💬 智能对话")
            chatbot = gr.Chatbot(
                value=[],
                height=500,
                label="",
                show_copy_button=True,
            )
            msg_box = gr.Textbox(
                placeholder="输入问题，Enter 发送...",
                label="",
                lines=2,
            )
            with gr.Row():
                send_btn  = gr.Button("发送 ↑", variant="primary")
                clear_btn = gr.Button("🗑️ 清空记忆")

            status_box = gr.Textbox(
                label="",
                value="",
                interactive=False,
                max_lines=1,
            )

            gr.Markdown("""
---
**回答标注说明**

| 标注 | 含义 |
|------|------|
| ✅ 已校验 \| 来源：章节xxx | 有原文依据，置信度高 |
| [Agent推断，建议核实] | 基于论文的逻辑推断 |
| ⚠️ 未在原文找到明确依据 | 请以论文原文为准 |

> 💡 工具调用详情在终端可见 · 生成文件保存至 output/ 目录
> 💡 换论文时旧论文内容自动清空，用 `save_to_memory` 保存的笔记永久保留
""")

    # ── 事件绑定 ──────────────────────────────────────────────────────────────
    load_btn.click(
        fn=load_paper,
        inputs=[pdf_upload],
        outputs=[load_log, paper_info],
    )

    msg_box.submit(
        fn=chat_fn,
        inputs=[msg_box, chatbot],
        outputs=[chatbot, msg_box],
    )

    send_btn.click(
        fn=chat_fn,
        inputs=[msg_box, chatbot],
        outputs=[chatbot, msg_box],
    )

    clear_btn.click(
        fn=clear_fn,
        outputs=[chatbot, status_box],
    )

    refresh_btn.click(
        fn=get_files,
        outputs=[files_box],
    )

    for btn, (_, prompt) in zip(quick_buttons, QUICK):
        btn.click(
            fn=lambda h, p=prompt: quick_fn(p, h),
            inputs=[chatbot],
            outputs=[chatbot, msg_box],
        )


# ── 启动 ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("⏳ 正在初始化 Agent...")
    try:
        get_agent()
        print("✅ Agent 初始化完成")
    except Exception as e:
        print(f"⚠️  Agent 初始化失败：{e}")
        print("   请检查 .env 或系统环境变量中的 VOLC_API_KEY 和 VOLC_MODEL_ID")

    demo.launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
        inbrowser=_env_flag("GRADIO_INBROWSER", True),
        share=_env_flag("GRADIO_SHARE", False),
    )
