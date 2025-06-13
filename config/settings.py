# ~/projects/deepseek_dispatcher-new/config/settings.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Dict, Any # 确保导入了所有需要的类型提示

# 使用 pydantic-settings 替代 pydantic.BaseSettings (Pydantic v2+)
# SettingsConfigDict 用于配置设置来源
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',         # 从 .env 文件加载环境变量
        env_file_encoding='utf-8',
        extra='ignore'           # 忽略 .env 中未在类中定义的额外变量
    )

    # --- Redis 配置 ---
    # 修正：Redis 连接 URL，使用 Docker Compose 服务名称
    REDIS_URL: str = "redis://deepseek_dispatcher-redis:6379/0"
    TASK_QUEUE_NAME: str = "deepseek_tasks"     # RQ 队列名称，默认值

    # --- 大模型 API 配置 ---
    DASHSCOPE_API_KEY: Optional[str] = None # DashScope API Key
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1" # DashScope API Base URL
    DEEPSEEK_API_KEY: Optional[str] = None  # DeepSeek API Key

    # --- 模型相关配置 ---
    MODEL_NAME: str = "deepseek-chat" # 默认模型名称 (您原始文件是 qwen-turbo，这里我根据 deepseek 项目名改为 deepseek-chat)
    MODEL_TEMPERATURE: float = 0.7
    MODEL_TOP_P: float = 0.8
    MODEL_MAX_TOKENS: int = 100 # 新增此行
    
    # 如果您的 MODEL_PARAMS 结构是固定的，可以这样定义，或者在代码中使用这些单独的字段组合
    # MODEL_PARAMS: Dict[str, Any] = {
    #     "temperature": 0.7,
    #     "top_p": 0.8,
    #     "max_tokens": 100 # 这是一个新的参数，如果需要请在 .env 中设置
    # }

    # --- 日志和结果目录配置 ---
    LOGS_DIR: str = "logs"     # 日志文件目录
    RESULTS_DIR: str = "results" # 结果文件目录

    # --- 日志级别配置 ---
    LOG_LEVEL: str = "INFO" # 日志级别 (e.g., INFO, DEBUG, WARNING, ERROR)

    # --- FastAPI/Uvicorn 服务器配置 ---
    FLASK_HOST: str = "0.0.0.0" # 监听地址
    FLASK_PORT: int = 8000       # 监听端口
    FLASK_DEBUG: bool = False    # 是否开启调试模式 (Pydantic 会自动将 "true"/"false" 转换为布尔值)
    FLASK_ENV: str = "development" # 运行环境 (development, production等)

    # --- 限流配置 ---
    # RATELIMIT_STORAGE_URI 默认值可以指向 REDIS_URL
    RATELIMIT_STORAGE_URI: str = "redis://deepseek_dispatcher-redis:6379/0" # 限流存储 URI，默认指向 Redis URL，修正连接
    DEFAULT_RATELIMIT: str = "1000 per hour" # 默认限流速率

    # --- 告警配置 (对应 common/alert_utils.py) ---
    ENABLE_ALERT: bool = False # 是否启用告警，默认禁用
    SMTP_SERVER: Optional[str] = None # SMTP 服务器地址
    SMTP_PORT: int = 465 # SMTP 端口，默认 SSL 端口
    EMAIL_USER: Optional[str] = None # 发件人邮箱
    EMAIL_PASS: Optional[str] = None # 发件人邮箱密码或授权码
    ALERT_EMAIL: Optional[str] = None # 告警接收邮箱
    DINGTALK_WEBHOOK: Optional[str] = None # 钉钉机器人 Webhook URL

    # --- Flask Secret Key (如果您的项目未来会引入 Flask Session 或其他需要密钥的功能) ---
    FLASK_SECRET_KEY: Optional[str] = None # Flask 应用的密钥

    # --- RQ 任务参数配置（用于 dispatcher/core/dispatcher.py）---
    TASK_RESULT_TTL: int = 86400 # 任务结果在 Redis 中保留的时长（秒），默认 1 天
    TASK_FAILURE_TTL: int = 604800 # 失败任务结果在 Redis 中保留的时长（秒），默认 7 天
    TASK_JOB_TIMEOUT: int = 300 # 任务执行超时时间（秒），默认 5 分钟

    # --- 新增：任务重试策略配置 ---
    TASK_MAX_RETRIES_DEFAULT: int = 3 # 默认队列最大重试次数
    TASK_RETRY_INTERVAL_DEFAULT: int = 60 # 默认队列重试间隔 (秒)

    TASK_MAX_RETRIES_HIGH: int = 1 # 高优先级队列最大重试次数
    TASK_RETRY_INTERVAL_HIGH: int = 10 # 高优先级队列重试间隔 (秒)

    TASK_MAX_RETRIES_LOW: int = 5 # 低优先级队列最大重试次数
    TASK_RETRY_INTERVAL_LOW: int = 120 # 低优先级队列重试间隔 (秒)


# 创建 Settings 类的实例，这将自动从环境变量和 .env 文件加载配置
settings = Settings()

# 示例用法 (仅用于测试)
if __name__ == '__main__':
    # 为了在直接运行此文件时加载 .env，确保 python-dotenv 已安装
    from dotenv import load_dotenv
    load_dotenv() # 在这里加载 .env 文件，以便直接运行 settings.py 进行测试

    print("--- 当前配置 ---")
    print(f"Redis URL: {settings.REDIS_URL}")
    print(f"Task Queue Name: {settings.TASK_QUEUE_NAME}")
    print(f"DashScope API Key: {'*' * len(settings.DASHSCOPE_API_KEY) if settings.DASHSCOPE_API_KEY else '未设置'}")
    print(f"DashScope Base URL: {settings.DASHSCOPE_BASE_URL}")
    print(f"DeepSeek API Key: {'*' * len(settings.DEEPSEEK_API_KEY) if settings.DEEPSEEK_API_KEY else '未设置'}")
    print(f"Model Name: {settings.MODEL_NAME}")
    print(f"Model Temperature: {settings.MODEL_TEMPERATURE}")
    print(f"Model Top P: {settings.MODEL_TOP_P}")
    print(f"Model Max Tokens: {settings.MODEL_MAX_TOKENS}")
    print(f"Logs Directory: {settings.LOGS_DIR}")
    print(f"Results Directory: {settings.RESULTS_DIR}")
    print(f"Log Level: {settings.LOG_LEVEL}")
    print(f"FastAPI Host: {settings.FLASK_HOST}")
    print(f"FastAPI Port: {settings.FLASK_PORT}")
    print(f"FastAPI Debug: {settings.FLASK_DEBUG}")
    print(f"FastAPI Env: {settings.FLASK_ENV}")
    print(f"Ratelimit Storage URI: {settings.RATELIMIT_STORAGE_URI}")
    print(f"Default Ratelimit: {settings.DEFAULT_RATELIMIT}")
    print(f"启用告警: {settings.ENABLE_ALERT}")
    print(f"SMTP Server: {settings.SMTP_SERVER}")
    print(f"Alert Email: {settings.ALERT_EMAIL}")
    print(f"DingTalk Webhook: {'*' * len(settings.DINGTALK_WEBHOOK) if settings.DINGTALK_WEBHOOK else '未设置'}")
    print(f"FLASK_SECRET_KEY: {'*' * len(settings.FLASK_SECRET_KEY) if settings.FLASK_SECRET_KEY else '未设置'}")
    print(f"Task Result TTL: {settings.TASK_RESULT_TTL}")
    print(f"Task Failure TTL: {settings.TASK_FAILURE_TTL}")
    print(f"Task Job Timeout: {settings.TASK_JOB_TIMEOUT}")
    print(f"Task Max Retries Default: {settings.TASK_MAX_RETRIES_DEFAULT}")
    print(f"Task Retry Interval Default: {settings.TASK_RETRY_INTERVAL_DEFAULT}")
