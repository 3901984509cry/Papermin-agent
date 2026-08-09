# =============================================================================
# tools/parse_pdf.py — 工具①：PDF 论文解析（升级版）
# 优化：正则匹配章节编号 + 扩充关键词，兼容 Nature/IEEE/ACM/中文格式
# =============================================================================

import json
import re
import os
import pymupdf as fitz
from langchain.tools import Tool
from config import MEMORY_DIR

PARSED_PAPER_PATH = MEMORY_DIR / "parsed_paper.json"

# ── 章节关键词（小写精确匹配）────────────────────────────────────────────────
SECTION_KEYWORDS = [
    # 通用英文
    "abstract", "introduction", "related work", "background",
    "preliminaries", "problem formulation",
    "method", "methods", "methodology", "approach", "model", "framework",
    "experiment", "experiments", "experimental", "evaluation", "results",
    "discussion", "analysis", "ablation",
    "conclusion", "conclusions", "summary",
    "reference", "references", "bibliography",
    # Nature / Science 专属
    "online methods", "extended data", "supplementary",
    "main text", "figures", "tables",
    # ACM / IEEE 专属
    "motivation", "system design", "implementation", "limitations",
    "future work", "acknowledgment", "appendix",
    # 中文论文
    "摘要", "引言", "相关工作", "背景", "方法", "模型",
    "实验", "结果", "讨论", "分析", "结论", "参考文献",
]

# ── 正则：匹配各种章节编号格式 ────────────────────────────────────────────────
SECTION_NUMBER_PATTERNS = [
    r"^(\d+\.?\s+)[A-Z]",           # "1. Introduction" / "1 Introduction"
    r"^([IVX]+\.\s+)[A-Z]",         # "IV. EXPERIMENT"
    r"^(§\s*\d+\s+)[A-Z]",          # "§ 2 Method"
    r"^(\d+\.\d+\.?\s+)[A-Z]",      # "2.1 Overview"
    r"^(第[一二三四五六七八九十百]+[章节])",   # "第一章" "第三节"
]

def _detect_section_by_keyword(text_head: str):
    """关键词匹配检测章节"""
    text_lower = text_head.lower()
    for kw in SECTION_KEYWORDS:
        if kw in text_lower:
            return kw
    return None


def _detect_section_by_regex(text_head: str):
    """正则匹配章节编号，适配 Nature/IEEE 等非标准格式"""
    for line in text_head.split("\n")[:5]:
        line = line.strip()
        if not line:
            continue
        for pattern in SECTION_NUMBER_PATTERNS:
            m = re.match(pattern, line)
            if m:
                # 提取标题关键词（去掉编号前缀）
                title = re.sub(r"^[\d§IVXivx\.\s一二三四五六七八九十章节]+", "", line).strip().lower()
                if title:
                    return title[:30]  # 截断防止过长
    return None


def _detect_section(text_head: str):
    """综合检测：先试关键词，再试正则"""
    result = _detect_section_by_keyword(text_head[:300])
    if result:
        return result
    result = _detect_section_by_regex(text_head[:300])
    return result


def parse_pdf(file_path: str) -> str:
    """
    解析 PDF 论文，按章节切分文本并存储为 JSON。
    支持英文/中文论文，兼容 Nature、IEEE、ACM 等多种格式。
    """
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        return f"❌ 无法打开 PDF：{e}，请检查文件路径是否正确"

    sections    = {}
    cur_section = "preamble"
    prev_section = None

    for page_num, page in enumerate(doc):
        text = page.get_text()
        if not text.strip():
            continue

        detected = _detect_section(text)
        if detected and detected != cur_section:
            cur_section = detected

        key = cur_section
        sections[key] = sections.get(key, "") + f"\n[第{page_num+1}页]\n" + text

    if not sections:
        return "❌ PDF 解析结果为空，可能是扫描版 PDF（需先 OCR 处理）"

    # 过滤过短章节（少于 100 字，可能是误识别）
    sections = {k: v for k, v in sections.items() if len(v.strip()) >= 100}

    with open(PARSED_PAPER_PATH, "w", encoding="utf-8") as f:
        json.dump(sections, f, ensure_ascii=False, indent=2)

    summary = [f"  · {k}（{len(v)}字）" for k, v in sections.items()]
    return (
        f"✅ PDF 解析完成！共识别 {len(sections)} 个章节：\n"
        + "\n".join(summary)
        + "\n\n📌 提示：可以使用 retrieve_from_kb 工具检索具体内容"
    )


parse_pdf_tool = Tool(
    name="parse_pdf",
    func=parse_pdf,
    description=(
        "解析上传的 PDF 论文文件，提取各章节文本并存入知识库。"
        "输入：PDF 文件的完整路径（字符串）。"
        "用户上传论文或提到'解析/读取论文'时调用此工具。"
    ),
)
