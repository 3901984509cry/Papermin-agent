# tools/search_arxiv.py — 优化版：arXiv API + Semantic Scholar 回退
import requests
import time
import random
from typing import List, Dict, Optional
from langchain.tools import Tool

# =============================================================================
# 配置
# =============================================================================
ARXIV_API_URL = "http://export.arxiv.org/api/query"
SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # 秒
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
]


# =============================================================================
# arXiv API 搜索（无速率限制，但返回格式需解析）
# =============================================================================
def search_arxiv_via_arxiv(query: str, max_results: int = 3) -> Optional[List[Dict]]:
    """使用 arXiv 原生 API（稳定，无限制）"""
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(ARXIV_API_URL, params=params, headers=headers, timeout=15)
            resp.raise_for_status()

            # 解析 arXiv 返回的 XML（使用简单字符串匹配，避免引入 xml 库）
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.content)

            # 命名空间
            ns = {"arxiv": "http://arxiv.org/schemas/atom"}
            entries = root.findall("entry")

            papers = []
            for entry in entries[:max_results]:
                title = entry.find("title").text.strip().replace("\n", " ")
                abstract = entry.find("summary").text.strip().replace("\n", " ")[:300]
                published = entry.find("published")
                year = published.text[:4] if published is not None else "未知"

                authors = [a.find("name").text for a in entry.findall("author")]
                author_str = "、".join(authors[:3]) + (" 等" if len(authors) > 3 else "")

                # 获取 arXiv ID
                arxiv_id = entry.find("id").text.split("/abs/")[-1]
                link = f"https://arxiv.org/abs/{arxiv_id}"

                papers.append({
                    "title": title,
                    "year": year,
                    "authors": author_str,
                    "abstract": abstract,
                    "link": link,
                    "pdf": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                    "source": "arXiv"
                })
            return papers if papers else None

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF[attempt])
                continue
            print(f"[ArXiv API] 失败: {e}")
            return None
    return None


# =============================================================================
# Semantic Scholar 回退搜索（增强重试和头部）
# =============================================================================
def search_arxiv_via_semantic(query: str, max_results: int = 3) -> Optional[List[Dict]]:
    """回退到 Semantic Scholar API（带重试和身份标识）"""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "x-email": "your-email@example.com",  # 建议替换为真实邮箱，提高限额
    }
    params = {
        "query": query,
        "limit": max_results,
        "fields": "title,authors,year,abstract,externalIds,openAccessPdf",
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(SEMANTIC_SCHOLAR_URL, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            if not data:
                return None

            papers = []
            for paper in data:
                title = paper.get("title", "未知标题")
                year = paper.get("year", "未知年份")
                authors = paper.get("authors", [])
                author_str = "、".join(a["name"] for a in authors[:3])
                if len(authors) > 3:
                    author_str += " 等"
                abstract = (paper.get("abstract") or "")[:300]
                ids = paper.get("externalIds", {})
                arxiv_id = ids.get("ArXiv")
                doi = ids.get("DOI")
                link = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else (
                    f"https://doi.org/{doi}" if doi else "链接不可用")
                pdf_url = paper.get("openAccessPdf", {}).get("url")
                papers.append({
                    "title": title,
                    "year": year,
                    "authors": author_str,
                    "abstract": abstract,
                    "link": link,
                    "pdf": pdf_url,
                    "source": "Semantic Scholar"
                })
            return papers
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF[attempt] * (attempt + 1))
                continue
            print(f"[Semantic Scholar] 失败: {e}")
            return None
    return None


# =============================================================================
# 主搜索函数（混合策略）
# =============================================================================
def search_arxiv(query: str, max_results: int = 3) -> str:
    """
    智能搜索论文：
      1. 优先使用 arXiv 官方 API（无限制）
      2. 若失败则回退到 Semantic Scholar
      3. 若均失败则返回友好错误提示
    """
    # 预处理查询：保留英文关键词，转换为小写
    clean_query = query.strip().lower()
    if not clean_query:
        return "❌ 请提供有效的搜索关键词"

    # 1. 尝试 arXiv API
    papers = search_arxiv_via_arxiv(clean_query, max_results)
    source = "arXiv"

    # 2. 回退到 Semantic Scholar
    if not papers:
        papers = search_arxiv_via_semantic(clean_query, max_results)
        source = "Semantic Scholar"

    if not papers:
        return f"❌ 搜索「{query}」失败：暂时无法连接学术数据库，请稍后重试或尝试更具体的关键词。"

    # 格式化输出
    results = []
    for i, p in enumerate(papers, 1):
        pdf_line = f"\n   📥 PDF：{p['pdf']}" if p.get("pdf") else ""
        results.append(
            f"📄 论文 {i}：{p['title']} ({p['year']})\n"
            f"   👤 作者：{p['authors']}\n"
            f"   📝 摘要：{p['abstract']}...\n"
            f"   🔗 链接：{p['link']}{pdf_line}"
        )

    return (f"🔍 搜索「{query}」找到 {len(results)} 篇（数据源：{source}）：\n\n"
            + "\n\n".join(results))


# =============================================================================
# LangChain Tool 包装
# =============================================================================
search_arxiv_tool = Tool(
    name="search_arxiv",
    func=search_arxiv,
    description=(
        "在学术数据库搜索相关论文（优先 arXiv，自动回退 Semantic Scholar）。"
        "输入：英文搜索关键词，如 'attention mechanism transformer'。"
        "当用户需要延伸阅读、了解某领域相关工作、查找参考文献时调用。"
    ),
)