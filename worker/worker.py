# worker/worker.py
import os
import time
import logging
from rq import Worker, Queue
from redis import Redis # 修正：Connection 现在从 redis 库导入
from config.settings import REDIS_URL, TASK_QUEUE_NAME, LOG_LEVEL
from services.llm_service import generate_text_from_llm

# 配置日志
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_worker():
    """
    启动 RQ Worker 来处理队列中的任务。
    """
    # 确保 Redis URL 指向正确的容器内服务名
    # 在 Docker Compose 环境中，'redis' 是 Redis 服务的 hostname
    redis_connection = Redis.from_url(REDIS_URL)

    # 创建一个 RQ 队列实例
    queue = Queue(TASK_QUEUE_NAME, connection=redis_connection)

    logger.info(f"Worker started. Listening on queue: {TASK_QUEUE_NAME}")
    logger.info(f"Connecting to Redis at: {REDIS_URL}")

    # 启动 Worker
    # with Connection(redis_connection): # 修正：不再需要 Connection 上下文管理器
    worker = Worker([queue], connection=redis_connection)
    worker.work()

if __name__ == "__main__":
    # 确保日志和结果目录存在
    os.makedirs(os.path.join(os.getcwd(), 'logs'), exist_ok=True)
    os.makedirs(os.path.join(os.getcwd(), 'results'), exist_ok=True)
    run_worker()
