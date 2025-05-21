# config/settings.py
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# --- Redis 配置 ---
# REDIS_BROKER_URL 和 REDIS_BACKEND_URL 统一使用 REDIS_URL
# 修改为直接读取 REDIS_URL 环境变量
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TASK_QUEUE_NAME = os.getenv("TASK_QUEUE_NAME", "deepseek_tasks")

# --- 大模型 API 配置 ---
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen-plus")
MODEL_PARAMS = {
    "temperature": float(os.getenv("MODEL_TEMPERATURE", 0.7)),
    "top_p": float(os.getenv("MODEL_TOP_P", 0.8)), # 确保这里是 MODEL_TOP_P
}

# --- 日志和结果目录配置 ---
LOGS_DIR = os.getenv("LOGS_DIR", "logs")
RESULTS_DIR = os.getenv("RESULTS_DIR", "results")

# --- 日志级别配置 ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# --- Flask Web 应用配置 ---
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 8000))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
FLASK_ENV = os.getenv("FLASK_ENV", "development")

# --- 限流配置 (可选) ---
# 确保这里引用的是 REDIS_URL，并且如果 .env 中没有设置，会使用默认值
RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", REDIS_URL)
DEFAULT_RATELIMIT = os.getenv("DEFAULT_RATELIMIT", "1000 per hour") # 确保这里有默认值

# --- 环境验证 ---
if not DASHSCOPE_API_KEY:
    print("警告: DASHSCOPE_API_KEY 未设置。大模型 API 调用可能失败。")
if not REDIS_URL:
    raise ValueError("REDIS_URL 环境变量是必需的，请在 .env 文件中设置。")
