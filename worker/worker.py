# worker/worker.py
import os
# import time  # F401: 'time' imported but unused - 移除，因为它在当前代码中未使用
import logging  # F401: 'logging' imported but unused - 实际有使用，保留
from redis import Redis
from rq import Worker, Queue
from config.settings import REDIS_URL, TASK_QUEUE_NAME, LOG_LEVEL

# 这里的导入是旧的 llm_service，现在应该使用 dispatcher.tasks.execute.execute_task
# from services.llm_service import generate_text_from_llm # F401: 'generate_text_from_llm' imported but unused - 移除未使用的导入

# 导入任务执行函数
from dispatcher.tasks.execute import execute_task


# 配置日志
# 注意：logger/logger.py 模块已经提供了统一的日志配置。
# 这里的 basicConfig 可能会与 get_logger 的配置冲突或被覆盖。
# 建议只使用 get_logger 来获取和配置日志。
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
    # with Connection(redis_connection): # 修正：不再需要 Connection 上下文管理器，且 Connection 未导入
    worker = Worker([queue], connection=redis_connection)
    worker.work()


if __name__ == "__main__":
    # 确保日志和结果目录存在
    os.makedirs(os.path.join(os.getcwd(), 'logs'), exist_ok=True)
    os.makedirs(os.path.join(os.getcwd(), 'results'), exist_ok=True)
    run_worker()

