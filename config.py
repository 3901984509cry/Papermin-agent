"""PaperMind runtime configuration.

Secrets are loaded from environment variables. A local ``.env`` file is
supported for development and is intentionally excluded from Git.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

# Windows 的 GBK 终端无法显示部分图标字符，默认行为会直接抛出
# UnicodeEncodeError。保留终端原编码，仅将无法编码的字符替换掉。
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(errors="replace")


def _project_path_from_env(name: str, default_name: str) -> Path:
    value = os.getenv(name, "").strip()
    path = Path(value).expanduser() if value else PROJECT_ROOT / default_name
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


# 火山引擎 OpenAI 兼容接口配置
VOLC_API_KEY = os.getenv("VOLC_API_KEY", "").strip()
VOLC_MODEL_ID = os.getenv("VOLC_MODEL_ID", "").strip()
VOLC_BASE_URL = os.getenv(
    "VOLC_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"
).strip()

# 模型参数
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.3"))
MODEL_MAX_TOKENS = int(os.getenv("MODEL_MAX_TOKENS", "4096"))

# 首次使用时会从 Hugging Face 下载 Embedding 模型
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
).strip()

# 数据目录。相对路径以项目根目录为基准，确保从任意工作目录启动都可用。
MEMORY_DIR = _project_path_from_env("PAPERMIND_MEMORY_DIR", "memory")
OUTPUT_DIR = _project_path_from_env("PAPERMIND_OUTPUT_DIR", "output")
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

KB_INDEX_PATH = str(MEMORY_DIR / "faiss.index")
KB_CHUNKS_PATH = str(MEMORY_DIR / "chunks.json")

# RAG 检索参数
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "5"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "300"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "80"))
