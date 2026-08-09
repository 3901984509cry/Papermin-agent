# =============================================================================
# main.py — PaperMind 启动入口
# 运行方式：python main.py
# =============================================================================

import os
import sys
from agent import build_agent, ask
from tools.knowledge_base import build_kb_from_parsed_paper
from tools.parse_pdf import parse_pdf


BANNER = """
╔══════════════════════════════════════════════════════════╗
║          📘  PaperMind  智能科研论文理解 Agent            ║
║      基于火山引擎豆包大模型 · LangChain ReAct 框架        ║
╠══════════════════════════════════════════════════════════╣
║  快捷命令：                                               ║
║    /load  <路径>   — 加载并解析 PDF 论文                  ║
║    /clear          — 清空对话记忆                         ║
║    /help           — 显示帮助                             ║
║    exit / quit     — 退出程序                             ║
╚══════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
📖 使用指南：

【第一步：加载论文】
  输入：/load /path/to/your/paper.pdf
  或直接说：解析这篇论文 /path/to/paper.pdf

【第二步：提问】
  · 这篇论文的核心贡献是什么？
  · 作者为什么选择 Transformer 而不是 RNN？
  · 帮我生成这篇论文的读书笔记文档
  · 给我推荐几篇关于注意力机制的相关论文
  · 帮我画一个关于 Transformer、BERT、GPT 的知识图谱
  · 记住：这篇论文的核心方法是多头自注意力

【输出文件位置】
  所有生成的 .docx 和 .html 文件保存在 output/ 目录
"""


def check_config():
    """启动前检查配置是否已填写"""
    from config import VOLC_API_KEY, VOLC_MODEL_ID

    errors = []
    if not VOLC_API_KEY:
        errors.append("❌ VOLC_API_KEY 未配置，请在 .env 或系统环境变量中设置")
    if not VOLC_MODEL_ID:
        errors.append("❌ VOLC_MODEL_ID 未配置，请在 .env 或系统环境变量中设置")

    if errors:
        print("\n".join(errors))
        print("\n📌 获取方式：登录 https://console.volcengine.com → 豆包大模型")
        sys.exit(1)


def handle_load_command(command: str, agent_executor) -> str:
    """处理 /load 命令：解析 PDF 并构建知识库"""
    parts = command.strip().split(maxsplit=1)
    if len(parts) < 2:
        return "❌ 请指定 PDF 路径，例如：/load /home/user/paper.pdf"

    pdf_path = parts[1].strip()

    if not os.path.exists(pdf_path):
        return f"❌ 文件不存在：{pdf_path}"

    print(f"\n⏳ 正在解析论文：{pdf_path}")
    parse_result = parse_pdf(pdf_path)
    print(parse_result)

    print("\n⏳ 正在构建向量知识库...")
    kb_result = build_kb_from_parsed_paper()
    print(kb_result)

    return f"\n✅ 论文已就绪！现在可以开始提问了。\n提示：试试问「这篇论文的核心贡献是什么？」"


def main():
    """主循环"""
    print(BANNER)
    check_config()

    print("⏳ 正在初始化 Agent（加载 Embedding 模型中，请稍候）...")
    agent_executor = build_agent()
    print("✅ Agent 初始化完成！\n")

    # 检查是否有命令行传入的 PDF 路径
    # ⚠️ 也可以直接在命令行运行：python main.py /path/to/paper.pdf
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        print(handle_load_command(f"/load {pdf_path}", agent_executor))

    # ── 主交互循环 ─────────────────────────────────────────────────────────────
    while True:
        try:
            user_input = input("\n你：").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 已退出 PaperMind")
            break

        if not user_input:
            continue

        # 退出命令
        if user_input.lower() in ("exit", "quit", "退出", "q"):
            print("👋 已退出 PaperMind")
            break

        # 帮助命令
        if user_input.lower() in ("/help", "help", "帮助"):
            print(HELP_TEXT)
            continue

        # 清空记忆命令
        if user_input.lower() == "/clear":
            agent_executor.memory.clear()
            print("✅ 对话记忆已清空")
            continue

        # 加载 PDF 命令
        if user_input.startswith("/load"):
            print(handle_load_command(user_input, agent_executor))
            continue

        # ── 正常问答（带 Self-Correction）──────────────────────────────────
        print("\nPaperMind：", end="", flush=True)
        response = ask(agent_executor, user_input)
        print(response)


if __name__ == "__main__":
    main()
