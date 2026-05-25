"""
项目配置文件
包含数据库、Ollama、Chroma等配置信息
"""
import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if load_dotenv:
    # 支持在server目录放置.env，避免把本地密钥和数据库密码写入源码
    load_dotenv(os.path.join(BASE_DIR, '.env'))
    load_dotenv(os.path.join(os.getcwd(), '.env'))


class Config:
    """基础配置类"""

    # Flask密钥，用于JWT签名
    SECRET_KEY = os.environ.get('SECRET_KEY', 'enterprise-qa-secret-key-2024')

    # MySQL数据库配置（端口3306，密码123456）
    MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '123456')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'db_enterprise_qa')

    # SQLAlchemy数据库连接URI
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT Token有效期（秒），默认24小时
    JWT_EXPIRATION = 86400

    # Ollama配置
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_LLM_MODEL = os.environ.get('OLLAMA_LLM_MODEL', 'qwen3:4b')
    OLLAMA_EMBED_MODEL = os.environ.get('OLLAMA_EMBED_MODEL', 'qwen3-embedding:4b')

    # ChromaDB持久化存储路径
    CHROMA_PERSIST_DIR = os.environ.get(
        'CHROMA_PERSIST_DIR',
        os.path.join(BASE_DIR, 'chroma_data')
    )

    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 最大上传文件大小：50MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'md', 'docx'}

    # 文档分块配置
    CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE', 500))        # 默认每个分块的字符数
    CHUNK_OVERLAP = int(os.environ.get('CHUNK_OVERLAP', 50))   # 默认分块之间的重叠字符数
    CHUNK_STRATEGIES = {
        'txt': {
            'chunk_size': int(os.environ.get('TXT_CHUNK_SIZE', CHUNK_SIZE)),
            'chunk_overlap': int(os.environ.get('TXT_CHUNK_OVERLAP', CHUNK_OVERLAP)),
            'separators': ['\n\n', '\n', '。', '！', '？', '；', ';', '.', '!', '?', ' ', '']
        },
        'pdf': {
            'chunk_size': int(os.environ.get('PDF_CHUNK_SIZE', 450)),
            'chunk_overlap': int(os.environ.get('PDF_CHUNK_OVERLAP', 80)),
            'separators': ['\n\n', '\n', '。', '！', '？', '；', ';', '.', '!', '?', ' ', '']
        },
        'md': {
            'chunk_size': int(os.environ.get('MD_CHUNK_SIZE', 800)),
            'chunk_overlap': int(os.environ.get('MD_CHUNK_OVERLAP', 100)),
            'separators': ['\n\n', '\n', '。', '！', '？', '；', ';', '.', '!', '?', ' ', '']
        },
        'docx': {
            'chunk_size': int(os.environ.get('DOCX_CHUNK_SIZE', 700)),
            'chunk_overlap': int(os.environ.get('DOCX_CHUNK_OVERLAP', 100)),
            'separators': ['\n\n', '\n', '。', '！', '？', '；', ';', '.', '!', '?', ' ', '']
        }
    }

    # 向量化批处理配置
    EMBED_BATCH_SIZE = 10   # 每批发送给Ollama的分块数量
    EMBED_MAX_RETRIES = 3   # 嵌入失败最大重试次数

    # RAG检索配置
    RETRIEVER_TOP_K = int(os.environ.get('RETRIEVER_TOP_K', 4))     # 检索返回的相似文档数量
    RERANK_CANDIDATE_K = int(os.environ.get('RERANK_CANDIDATE_K', 12))  # 初始向量召回候选数
    RERANK_ENABLED = os.environ.get('RERANK_ENABLED', 'true').lower() == 'true'
    HYBRID_SEARCH_ENABLED = os.environ.get('HYBRID_SEARCH_ENABLED', 'true').lower() == 'true'
    HYBRID_KEYWORD_CANDIDATE_K = int(os.environ.get('HYBRID_KEYWORD_CANDIDATE_K', 12))
    HYBRID_KEYWORD_SCAN_LIMIT = int(os.environ.get('HYBRID_KEYWORD_SCAN_LIMIT', 2000))
    HYBRID_RRF_K = int(os.environ.get('HYBRID_RRF_K', 60))
    BM25_K1 = float(os.environ.get('BM25_K1', 1.5))
    BM25_B = float(os.environ.get('BM25_B', 0.75))
    BM25_INCLUDE_METADATA = os.environ.get('BM25_INCLUDE_METADATA', 'true').lower() == 'true'
    RAG_HISTORY_TURNS = int(os.environ.get('RAG_HISTORY_TURNS', 3))  # 多轮问答使用的历史轮数
