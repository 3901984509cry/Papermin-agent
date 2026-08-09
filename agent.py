# =============================================================================
# agent.py — PaperMind 主 Agent（流式输出升级版）
# =============================================================================

import queue
import threading
from typing import Generator, Any

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.callbacks import BaseCallbackHandler

from config import (
    VOLC_API_KEY, VOLC_MODEL_ID, VOLC_BASE_URL,
    MODEL_TEMPERATURE, MODEL_MAX_TOKENS
)
from tools.parse_pdf      import parse_pdf_tool
from tools.knowledge_base import retrieve_from_kb_tool, build_kb_tool, save_to_memory_tool
from tools.search_arxiv   import search_arxiv_tool
from tools.generate_notes import generate_notes_tool
from tools.knowledge_map  import build_knowledge_map_tool
from self_correction      import self_correct

ALL_TOOLS = [
    parse_pdf_tool, build_kb_tool, retrieve_from_kb_tool,
    search_arxiv_tool, generate_notes_tool,
    build_knowledge_map_tool, save_to_memory_tool,
]

# ── Prompt ────────────────────────────────────────────────────────────────────
PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是 PaperMind，专为本科生设计的智能科研论文理解 Agent。

工作原则：
1. 论文内容问题必须先调用 retrieve_from_kb 检索原文依据，不得凭空回答
2. 置信度标注：有原文依据=正常回答+来源；推断=加[Agent推断]；背景知识=加[背景知识]
3. 用户要笔记时调用 generate_notes_doc；要知识图谱时调用 build_knowledge_map
4. 用户说「我想学习XX」时，调用 search_arxiv 推荐延伸论文
5. 用户说「记住这个」时，调用 save_to_memory 永久保存"""),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])


# ── 流式回调处理器 ─────────────────────────────────────────────────────────────
class StreamingQueueCallback(BaseCallbackHandler):
    """将 LLM 生成的 token 实时放入队列，供 Gradio 流式读取"""

    def __init__(self, token_queue: queue.Queue):
        self.q = token_queue

    def on_llm_new_token(self, token: str, **kwargs):
        self.q.put(("token", token))

    def on_llm_end(self, *args, **kwargs):
        pass

    def on_tool_start(self, serialized, input_str, **kwargs):
        tool_name = serialized.get("name", "工具")
        self.q.put(("tool_start", f"\n\n⚙️ 正在调用 `{tool_name}`...\n"))

    def on_tool_end(self, output, **kwargs):
        self.q.put(("tool_end", ""))

    def on_agent_finish(self, *args, **kwargs):
        self.q.put(("done", None))

    def on_chain_error(self, error, **kwargs):
        self.q.put(("error", str(error)))


# ── LLM & Memory ─────────────────────────────────────────────────────────────
def create_llm(streaming: bool = False, callbacks=None):
    kwargs = dict(
        model=VOLC_MODEL_ID, api_key=VOLC_API_KEY, base_url=VOLC_BASE_URL,
        temperature=MODEL_TEMPERATURE, max_tokens=MODEL_MAX_TOKENS,
    )
    if streaming:
        kwargs["streaming"] = True
    if callbacks:
        kwargs["callbacks"] = callbacks
    return ChatOpenAI(**kwargs)


def create_memory():
    return ConversationBufferWindowMemory(
        k=8, memory_key="chat_history",
        return_messages=True,
        input_key="input", output_key="output",
    )


# ── Agent 构建 ────────────────────────────────────────────────────────────────
def build_agent() -> AgentExecutor:
    llm    = create_llm()
    memory = create_memory()
    agent  = create_openai_tools_agent(llm, ALL_TOOLS, PROMPT)
    return AgentExecutor(
        agent=agent, tools=ALL_TOOLS, memory=memory,
        verbose=True, max_iterations=8,
        handle_parsing_errors=True,
    )


# ── 普通调用（含 Self-Correction）────────────────────────────────────────────
def ask(agent_executor: AgentExecutor, user_input: str) -> str:
    try:
        result     = agent_executor.invoke({"input": user_input})
        raw        = result.get("output", "")
        return self_correct(raw, original_query=user_input)
    except Exception as e:
        return (
            f"❌ Agent 执行出错：{e}\n"
            "💡 请检查 .env 或系统环境变量中的 API Key 和 Endpoint ID"
        )


# ── 流式调用（生成器，供 Gradio 使用）────────────────────────────────────────
def ask_stream(agent_executor: AgentExecutor, user_input: str) -> Generator[str, None, None]:
    """
    流式调用 Agent，逐 token yield 文本。
    在后台线程运行 Agent，主线程从队列读取 token。
    """
    token_queue = queue.Queue()
    callback    = StreamingQueueCallback(token_queue)

    # 创建带流式回调的 LLM
    streaming_llm = create_llm(streaming=True, callbacks=[callback])

    # 构建带流式 LLM 的临时 agent
    stream_agent = create_openai_tools_agent(streaming_llm, ALL_TOOLS, PROMPT)
    stream_executor = AgentExecutor(
        agent=stream_agent, tools=ALL_TOOLS,
        memory=agent_executor.memory,   # 共享记忆
        verbose=False, max_iterations=8,
        handle_parsing_errors=True,
    )

    full_answer = []

    def _run():
        try:
            result = stream_executor.invoke({"input": user_input})
            raw    = result.get("output", "")
            # Self-Correction 在后台执行，结果放入队列
            corrected = self_correct(raw, original_query=user_input)
            # 将 Self-Correction 附加内容推入队列
            sc_part = corrected[len(raw):]
            if sc_part:
                token_queue.put(("token", sc_part))
        except Exception as e:
            token_queue.put(("error", f"\n❌ 出错：{e}"))
        finally:
            token_queue.put(("done", None))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    accumulated = ""
    while True:
        try:
            msg_type, content = token_queue.get(timeout=60)
        except queue.Empty:
            yield "\n❌ 响应超时，请重试"
            break

        if msg_type == "done":
            break
        elif msg_type == "error":
            yield content
            break
        elif msg_type in ("token", "tool_start"):
            accumulated += content
            yield accumulated

    thread.join(timeout=5)
