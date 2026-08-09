# =============================================================================
# tools/knowledge_base.py — 向量知识库（双索引 + 查询语言对齐版）
# 优化：中文问题自动翻译为英文再检索，解决跨语言语义匹配弱问题
# =============================================================================

import json
import os
import re
from pathlib import Path

import numpy as np
import faiss
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from sentence_transformers import SentenceTransformer
from config import (
    EMBEDDING_MODEL, TOP_K_RETRIEVAL, CHUNK_SIZE, CHUNK_OVERLAP,
    VOLC_API_KEY, VOLC_MODEL_ID, VOLC_BASE_URL, MEMORY_DIR
)

# ── 路径常量 ──────────────────────────────────────────────────────────────────
PAPER_INDEX_PATH  = str(MEMORY_DIR / "paper.index")
PAPER_CHUNKS_PATH = str(MEMORY_DIR / "paper_chunks.json")
MEM_INDEX_PATH    = str(MEMORY_DIR / "user_memory.index")
MEM_CHUNKS_PATH   = str(MEMORY_DIR / "user_memory_chunks.json")
PARSED_PAPER_PATH = str(MEMORY_DIR / "parsed_paper.json")

# ── 全局变量 ──────────────────────────────────────────────────────────────────
print(f"📦 正在加载 Embedding 模型：{EMBEDDING_MODEL}")
_embedder     = SentenceTransformer(EMBEDDING_MODEL)
_paper_index  = None
_paper_chunks = []

# 翻译缓存，避免重复调用 LLM
_translate_cache = {}


# ── 语言检测与翻译 ────────────────────────────────────────────────────────────

def _is_chinese(text: str) -> bool:
    """判断文本是否主要为中文"""
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return chinese_chars / max(len(text), 1) > 0.2


def _translate_to_english(query: str) -> str:
    """
    将中文查询翻译成英文，提升英文论文的检索匹配率。
    使用缓存避免重复调用 LLM。
    """
    if not _is_chinese(query):
        return query  # 已是英文，直接返回

    if query in _translate_cache:
        return _translate_cache[query]

    try:
        translator = ChatOpenAI(
            model       = VOLC_MODEL_ID,
            api_key     = VOLC_API_KEY,
            base_url    = VOLC_BASE_URL,
            temperature = 0,
            max_tokens  = 200,
        )
        result = translator.invoke(
            f"Translate the following Chinese text to English. "
            f"Output only the translation, no explanation:\n{query}"
        )
        translated = result.content.strip()
        _translate_cache[query] = translated
        print(f"🌐 查询翻译：{query} → {translated}")
        return translated
    except Exception as e:
        print(f"⚠️  翻译失败，使用原始查询：{e}")
        return query  # 翻译失败时降级使用原始查询


# ── 索引操作 ──────────────────────────────────────────────────────────────────

def _read_index(path: str):
    """通过 Python 文件接口读取，兼容 Windows 中文路径。"""
    data = np.frombuffer(Path(path).read_bytes(), dtype=np.uint8)
    return faiss.deserialize_index(data)


def _write_index(index, path: str):
    """通过 Python 文件接口写入，避免 FAISS 原生接口的路径编码限制。"""
    data = faiss.serialize_index(index)
    Path(path).write_bytes(data.tobytes())

def _get_dim():
    return _embedder.get_sentence_embedding_dimension()


def _load_paper_index():
    global _paper_index, _paper_chunks
    if os.path.exists(PAPER_INDEX_PATH) and os.path.exists(PAPER_CHUNKS_PATH):
        _paper_index = _read_index(PAPER_INDEX_PATH)
        with open(PAPER_CHUNKS_PATH, "r", encoding="utf-8") as f:
            _paper_chunks = json.load(f)
        print(f"✅ 已加载论文索引（{len(_paper_chunks)} 块）")
    else:
        _paper_index  = faiss.IndexFlatL2(_get_dim())
        _paper_chunks = []


def _save_paper_index():
    _write_index(_paper_index, PAPER_INDEX_PATH)
    with open(PAPER_CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(_paper_chunks, f, ensure_ascii=False, indent=2)


def _load_mem_index():
    if os.path.exists(MEM_INDEX_PATH) and os.path.exists(MEM_CHUNKS_PATH):
        idx = _read_index(MEM_INDEX_PATH)
        with open(MEM_CHUNKS_PATH, "r", encoding="utf-8") as f:
            chunks = json.load(f)
    else:
        idx    = faiss.IndexFlatL2(_get_dim())
        chunks = []
    return idx, chunks


def _save_mem_index(idx, chunks):
    _write_index(idx, MEM_INDEX_PATH)
    with open(MEM_CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)


def clear_paper_index():
    """换论文时调用，只清空论文索引，用户笔记保留"""
    global _paper_index, _paper_chunks
    _paper_index  = faiss.IndexFlatL2(_get_dim())
    _paper_chunks = []
    for path in [PAPER_INDEX_PATH, PAPER_CHUNKS_PATH]:
        if os.path.exists(path):
            os.remove(path)
    print("🗑️  论文索引已清空（用户笔记保留）")


# ── 核心功能 ──────────────────────────────────────────────────────────────────

def build_kb_from_parsed_paper(query:str = "") -> str:
    """读取 parsed_paper.json，向量化写入论文索引（含去重）"""
    global _paper_index, _paper_chunks

    if not os.path.exists(PARSED_PAPER_PATH):
        return "❌ 找不到解析文件，请先调用 parse_pdf 解析论文"

    with open(PARSED_PAPER_PATH, "r", encoding="utf-8") as f:
        sections = json.load(f)

    # 每次重置，防止重复积累
    _paper_index  = faiss.IndexFlatL2(_get_dim())
    _paper_chunks = []
    existing_set  = set()
    added = 0

    for section_name, text in sections.items():
        for i in range(0, len(text), CHUNK_SIZE - CHUNK_OVERLAP):
            chunk = text[i: i + CHUNK_SIZE].strip()
            if len(chunk) < 50:
                continue
            chunk_with_meta = f"[章节：{section_name}]\n{chunk}"
            # 哈希去重
            if chunk_with_meta in existing_set:
                continue
            existing_set.add(chunk_with_meta)
            vec = _embedder.encode(
                [chunk_with_meta], convert_to_numpy=True
            ).astype("float32")
            _paper_index.add(vec)
            _paper_chunks.append(chunk_with_meta)
            added += 1

    _save_paper_index()
    return f"✅ 知识库构建完成，共写入 {added} 个文本块（已去重）"


def retrieve_from_kb(query: str) -> str:
    """
    同时检索论文索引和用户笔记索引，合并排序返回。
    中文查询自动翻译为英文后再做向量检索。
    """
    global _paper_index, _paper_chunks

    if _paper_index is None:
        _load_paper_index()

    # ── 语言对齐：中文查询翻译为英文 ─────────────────────────────────────────
    english_query = _translate_to_english(query)
    # 同时保留原始查询用于中文笔记检索
    queries = [english_query]
    if english_query != query:
        queries.append(query)  # 双查询：英文+原始中文

    results = []

    # ── 检索论文索引（使用英文查询）─────────────────────────────────────────
    if _paper_index is not None and _paper_index.ntotal > 0:
        q    = _embedder.encode([english_query], convert_to_numpy=True).astype("float32")
        k    = min(TOP_K_RETRIEVAL, _paper_index.ntotal)
        D, I = _paper_index.search(q, k=k)
        for dist, idx in zip(D[0], I[0]):
            if idx < len(_paper_chunks):
                results.append((1 / (1 + dist), _paper_chunks[idx], "论文"))

    # ── 检索用户笔记索引（使用原始查询，支持中文笔记）──────────────────────
    mem_index, mem_chunks = _load_mem_index()
    if mem_index.ntotal > 0:
        q    = _embedder.encode([query], convert_to_numpy=True).astype("float32")
        k    = min(2, mem_index.ntotal)
        D, I = mem_index.search(q, k=k)
        for dist, idx in zip(D[0], I[0]):
            if idx < len(mem_chunks):
                results.append((1 / (1 + dist), mem_chunks[idx], "用户笔记"))

    if not results:
        return "❌ 未检索到相关内容，请先加载论文或尝试换用其他关键词"

    results.sort(key=lambda x: x[0], reverse=True)
    parts = []
    for rank, (score, text, source) in enumerate(results[:5], 1):
        parts.append(
            f"【相关段落 {rank}】（相似度：{score:.2f} | 来源：{source}）\n{text}"
        )
    return "\n\n---\n\n".join(parts)


def save_to_memory(content: str) -> str:
    """永久保存到用户笔记索引（换论文不受影响）"""
    mem_index, mem_chunks = _load_mem_index()
    tagged = f"[用户笔记]\n{content}"
    if tagged in mem_chunks:
        return "⚠️ 该内容已存在，无需重复保存"
    vec = _embedder.encode([tagged], convert_to_numpy=True).astype("float32")
    mem_index.add(vec)
    mem_chunks.append(tagged)
    _save_mem_index(mem_index, mem_chunks)
    return f"✅ 已永久保存到用户笔记库（共 {len(mem_chunks)} 条，换论文不会丢失）"


# ── LangChain Tools ───────────────────────────────────────────────────────────
retrieve_from_kb_tool = Tool(
    name="retrieve_from_kb",
    func=retrieve_from_kb,
    description=(
        "从知识库检索相关段落（同时搜索当前论文和历史用户笔记）。"
        "中文问题会自动翻译为英文后检索，提升英文论文的匹配效果。"
        "输入：问题或关键词。回答论文内容问题时优先调用。"
    ),
)

build_kb_tool = Tool(
    name="build_kb",
    func=build_kb_from_parsed_paper,
    description=(
        "将已解析的论文文本构建为向量知识库。"
        "输入：任意字符串触发即可。必须在 parse_pdf 之后调用。"
    ),
)

save_to_memory_tool = Tool(
    name="save_to_memory",
    func=save_to_memory,
    description=(
        "将重要内容永久保存到用户笔记库，换论文后依然可以检索到。"
        "输入：要保存的内容（建议格式：论文名 | 关键内容）。"
        "用户说'记住这个'时调用。"
    ),
)
