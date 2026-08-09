# =============================================================================
# tools/knowledge_map.py — 工具⑤：生成可交互知识图谱
# 功能：将概念列表生成为浏览器可打开的 HTML 知识图谱
# =============================================================================

import os
import json
from datetime import datetime
from langchain.tools import Tool
from config import OUTPUT_DIR


def build_knowledge_map(concepts_input: str) -> str:
    """
    根据概念列表生成可交互 HTML 知识图谱（使用 vis.js 渲染）。

    Args:
        concepts_input: 逗号分隔的概念列表，格式：
                        "概念A,概念B,概念C"
                        或带关系描述："概念A->概念B:关系描述,概念B->概念C:关系描述"
    Returns:
        生成结果描述（含文件路径）
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── 解析输入，构建节点和边 ─────────────────────────────────────────────────
    nodes = []
    edges = []
    concept_idx = {}

    if "->" in concepts_input:
        # 带关系描述模式："A->B:关系,B->C:关系"
        parts = concepts_input.split(",")
        all_concepts = set()
        edge_defs = []

        for part in parts:
            part = part.strip()
            if "->" in part:
                src, rest = part.split("->", 1)
                if ":" in rest:
                    tgt, label = rest.split(":", 1)
                else:
                    tgt, label = rest, ""
                all_concepts.add(src.strip())
                all_concepts.add(tgt.strip())
                edge_defs.append((src.strip(), tgt.strip(), label.strip()))

        for i, concept in enumerate(sorted(all_concepts)):
            concept_idx[concept] = i
            nodes.append({"id": i, "label": concept, "group": i % 5})

        for src, tgt, label in edge_defs:
            edges.append({
                "from":   concept_idx[src],
                "to":     concept_idx[tgt],
                "label":  label,
                "arrows": "to",
            })
    else:
        # 简单列表模式："概念A,概念B,概念C"
        concept_list = [c.strip() for c in concepts_input.split(",") if c.strip()]
        for i, concept in enumerate(concept_list):
            concept_idx[concept] = i
            nodes.append({"id": i, "label": concept, "group": i % 5})
        # 顺序连接
        for i in range(len(concept_list) - 1):
            edges.append({"from": i, "to": i + 1, "arrows": "to"})

    # ── 生成 HTML ──────────────────────────────────────────────────────────────
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>PaperMind 知识图谱</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
  <link  href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet">
  <style>
    body   {{ margin: 0; background: #0A2540; font-family: "微软雅黑", Arial, sans-serif; }}
    #title {{ color: #2DD4BF; text-align: center; padding: 16px 0 8px; font-size: 22px; font-weight: bold; }}
    #sub   {{ color: #94A3B8; text-align: center; font-size: 13px; margin-bottom: 12px; }}
    #graph {{ width: 100%; height: 80vh; background: #0F2137; border: 1px solid #1A4A7A; }}
    #tips  {{ color: #475569; text-align: center; font-size: 12px; padding: 8px; }}
  </style>
</head>
<body>
  <div id="title">📊 PaperMind 知识图谱</div>
  <div id="sub">生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 节点数：{len(nodes)} | 关系数：{len(edges)}</div>
  <div id="graph"></div>
  <div id="tips">💡 可拖拽节点 · 滚轮缩放 · 点击节点高亮关联</div>
  <script>
    var nodes = new vis.DataSet({json.dumps(nodes, ensure_ascii=False)});
    var edges = new vis.DataSet({json.dumps(edges, ensure_ascii=False)});
    var options = {{
      nodes: {{
        shape: "box",
        borderWidth: 2,
        font: {{ color: "#FFFFFF", size: 14, face: "微软雅黑" }},
        color: {{
          border: "#0D9488",
          background: "#1A4A7A",
          highlight: {{ border: "#2DD4BF", background: "#0D9488" }}
        }},
        shadow: true,
      }},
      edges: {{
        font: {{ color: "#94A3B8", size: 11 }},
        color: {{ color: "#2DD4BF", opacity: 0.7 }},
        smooth: {{ type: "curvedCW", roundness: 0.2 }},
      }},
      physics: {{
        stabilization: {{ iterations: 200 }},
        barnesHut: {{ gravitationalConstant: -5000, springLength: 150 }}
      }},
      interaction: {{ hover: true, tooltipDelay: 200 }},
    }};
    new vis.Network(document.getElementById("graph"), {{ nodes, edges }}, options);
  </script>
</body>
</html>"""

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(OUTPUT_DIR, f"知识图谱_{timestamp}.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return (
        f"✅ 知识图谱已生成！\n"
        f"   📁 文件路径：{os.path.abspath(output_path)}\n"
        f"   🔢 节点数量：{len(nodes)} 个概念\n"
        f"   🔗 关联数量：{len(edges)} 条关系\n"
        f"   💡 提示：用浏览器打开此 HTML 文件，可交互拖拽查看"
    )


build_knowledge_map_tool = Tool(
    name="build_knowledge_map",
    func=build_knowledge_map,
    description=(
        "根据概念列表生成可交互的 HTML 知识图谱，浏览器打开即可使用。\n"
        "输入格式一（简单列表）：'概念A,概念B,概念C'\n"
        "输入格式二（带关系）：'注意力机制->Transformer:演化自,Transformer->BERT:预训练应用'\n"
        "用户说'生成知识图谱'、'画概念图'、'可视化关系'时调用。"
    ),
)
