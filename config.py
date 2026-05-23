# =============================================================================
# config.py — PaperMind 全局配置
# ⚠️ 标注的位置需要根据你的实际情况填写
# =============================================================================

# ── 火山引擎 API 配置 ─────────────────────────────────────────────────────────
# 登录路径：火山引擎控制台 -> 豆包大模型 -> API Key 管理 -> 创建 API Key
VOLC_API_KEY  = "ark-526c597e-e0a7-4716-8fae-94adf33015b6-52aa3"           # ⚠️ 填写你的火山引擎 API Key

# 登录路径：火山引擎控制台 -> 豆包大模型 -> 推理接入点 -> 创建接入点 -> 复制 Endpoint ID
# 格式示例：ep-20240101120000-abcde
VOLC_MODEL_ID = "ep-20260518212219-742cq"   # ⚠️ 填写你的模型 Endpoint ID

# 火山引擎 OpenAI 兼容接口地址（一般无需修改）
VOLC_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

# ── 模型参数 ──────────────────────────────────────────────────────────────────
MODEL_TEMPERATURE = 0.3    # 温度（0=严谨，1=发散），论文理解推荐 0.2~0.4
MODEL_MAX_TOKENS  = 4096   # 单次最大输出 token 数

# ── Embedding 模型 ────────────────────────────────────────────────────────────
# 首次运行会自动从 HuggingFace 下载（需联网）
# 学术场景可换成 "allenai/scibert_scivocab_uncased"（效果更好但更慢）
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # ⚠️ 可按需修改

# ── 知识库路径（自动创建，通常无需修改）──────────────────────────────────────
KB_INDEX_PATH  = "memory/faiss.index"
KB_CHUNKS_PATH = "memory/chunks.json"

# ── RAG 检索参数 ──────────────────────────────────────────────────────────────
TOP_K_RETRIEVAL = 5     # 每次检索返回的段落数
CHUNK_SIZE      = 300   # 切块大小（字符数）
CHUNK_OVERLAP   = 80    # 相邻块重叠字符数（保证上下文连贯）

# ── 输出目录 ──────────────────────────────────────────────────────────────────
OUTPUT_DIR = r"C:\Users\lenovo\Desktop\cry.穷的文件夹\PaperMind_代码\papermind\output"   # 生成的 docx/html 文件存放位置
