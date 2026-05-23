# =============================================================================
# self_correction.py — Self-Correction 三层纠错机制
# 功能：检测回答中的事实性声明，回源验证，防止幻觉输出
# =============================================================================

import re
from langchain_openai import ChatOpenAI
from tools.knowledge_base import retrieve_from_kb
from config import VOLC_API_KEY, VOLC_MODEL_ID, VOLC_BASE_URL

# ── 触发词模式 ────────────────────────────────────────────────────────────────
TRIGGER_PATTERNS = [
    r"\d+\.?\d*\s*%",
    r"\d+\.?\d*\s*(倍|次|层|个|篇)",
    r"准确率|精确率|召回率|F1",
    r"优于|高于|低于|超过|相比",
    r"论文(提出|声称|证明|表明|显示)",
    r"实验结果(表明|显示|证明)",
]


def _get_llm():
    return ChatOpenAI(
        model=VOLC_MODEL_ID, api_key=VOLC_API_KEY,
        base_url=VOLC_BASE_URL, temperature=0, max_tokens=2048,
    )


def _contains_factual_claims(text: str) -> bool:
    return any(re.search(p, text) for p in TRIGGER_PATTERNS)


def _extract_key_claims(text: str) -> list:
    sentences = re.split(r"[。\n]", text)
    claims = []
    for sent in sentences:
        sent = sent.strip()
        if len(sent) > 10:
            for p in TRIGGER_PATTERNS:
                if re.search(p, sent):
                    claims.append(sent)
                    break
    return claims[:3]


def _verify_with_source(claim: str):
    source = retrieve_from_kb(claim)
    if "❌" in source:
        return False, ""
    nums_claim  = set(re.findall(r"\d+\.?\d*", claim))
    nums_source = set(re.findall(r"\d+\.?\d*", source))
    if nums_claim and not nums_claim.intersection(nums_source):
        return False, source
    return True, source


def _regenerate_answer(original_query: str, source_chunks: str) -> str:
    """
    发现矛盾时：以原文段落为约束，重新生成回答（真正的纠错）。
    """
    llm = _get_llm()
    prompt = (
        f"你是一个严谨的学术助手。请根据以下论文原文段落，"
        f"重新回答用户的问题。只能使用原文中明确出现的信息，"
        f"不要添加原文未提及的内容。\n\n"
        f"【论文原文段落】\n{source_chunks}\n\n"
        f"【用户问题】\n{original_query}\n\n"
        f"【重新生成的回答】"
    )
    try:
        result = llm.invoke(prompt)
        return result.content.strip()
    except Exception as e:
        return f"（重新生成失败：{e}，请参考原文核实）"


def self_correct(answer: str, original_query: str = "") -> str:
    """
    三层纠错：
    第一层：触发检测
    第二层：原文回溯
    第三层：一致性校验 → 不一致时真正重新生成答案（升级点）
    """
    # 第一层
    if not _contains_factual_claims(answer):
        return answer + "\n\n_[无事实性声明，免纠错]_"

    claims = _extract_key_claims(answer)
    if not claims:
        return answer + "\n\n_[✅ 已扫描，无需核实]_"

    # 第二层 + 第三层
    verified_count    = 0
    inconsistent      = []
    source_refs       = []
    bad_source_chunks = []

    for claim in claims:
        is_ok, source_text = _verify_with_source(claim)
        if is_ok:
            verified_count += 1
            m = re.search(r"\[章节：(.+?)\]", source_text)
            if m:
                source_refs.append(f"章节「{m.group(1)}」")
        else:
            inconsistent.append(claim)
            if source_text:
                bad_source_chunks.append(source_text)

    # ── 有矛盾：重新生成 ──────────────────────────────────────────────────
    if inconsistent and bad_source_chunks and original_query:
        print(f"⚠️  发现 {len(inconsistent)} 条矛盾声明，正在重新生成回答...")
        combined_sources = "\n\n---\n\n".join(bad_source_chunks)
        new_answer = _regenerate_answer(original_query, combined_sources)
        return (
            new_answer
            + "\n\n---\n"
            + f"🔄 原答案含 {len(inconsistent)} 条未验证声明，已根据原文重新生成\n"
            + f"✅ 内容来源：{('、'.join(set(source_refs))) or '论文原文'}"
        )

    # ── 全部验证通过 ──────────────────────────────────────────────────────
    refs_str = "、".join(set(source_refs)) if source_refs else "论文原文"
    footer = f"\n\n---\n✅ 已校验 {verified_count} 条声明 | 来源：{refs_str}"

    if inconsistent and not bad_source_chunks:
        footer += (
            f"\n⚠️ {len(inconsistent)} 条声明未在原文找到对应段落，"
            "建议追问「这个数据在论文哪里？」"
        )

    return answer + footer