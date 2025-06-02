# worker/worker.py
import os
import logging
from redis import Redis
from rq import Worker, Queue
from config.settings import REDIS_URL, TASK_QUEUE_NAME, LOG_LEVEL # 确保从 config.settings 导入

# 导入任务执行函数 (根据我们之前的修改，execute_task 应该从 dispatcher.tasks 导入)
from dispatcher.tasks import execute_task # <--- **关键修改：修正导入路径**

# 配置日志
# 这里的 basicConfig 确保了 worker.py 自身的日志输出
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_worker():
    """
    启动 RQ Worker 来处理队列中的任务。
    """
    # 打印环境变量用于调试，确认 REDIS_URL 是否正确加载
    logger.info(f"Worker process starting. REDIS_URL from settings: {REDIS_URL}")
    logger.info(f"Worker process starting. TASK_QUEUE_NAME from settings: {TASK_QUEUE_NAME}")
    logger.info(f"Worker process starting. LOG_LEVEL from settings: {LOG_LEVEL}")

    try:
        # 确保 Redis URL 指向正确的容器内服务名
        redis_connection = Redis.from_url(REDIS_URL)
        # 尝试 ping Redis 确认连接
        redis_connection.ping()
        logger.info("Successfully connected to Redis.")
    except Exception as e:
        logger.error(f"Failed to connect to Redis at {REDIS_URL}: {e}", exc_info=True)
        # 如果连接失败，这里可以考虑退出或抛出异常，让 Supervisor 重启
        raise

    # 创建一个 RQ 队列实例
    queue = Queue(TASK_QUEUE_NAME, connection=redis_connection)

    logger.info(f"Worker started. Listening on queue: {TASK_QUEUE_NAME}")
    logger.info(f"Connecting to Redis at: {REDIS_URL}")

    # 启动 Worker
    worker = Worker([queue], connection=redis_connection)
    worker.work()


if __name__ == "__main__":
    # 确保日志和结果目录存在
    # 注意：这些目录应该由 Dockerfile 或 Supervisor 启动脚本创建，这里作为双重检查
    os.makedirs(os.path.join(os.getcwd(), 'logs'), exist_ok=True)
    os.makedirs(os.path.join(os.getcwd(), 'results'), exist_ok=True)
    run_worker()