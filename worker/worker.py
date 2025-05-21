# worker/worker.py
import os
import sys
from redis import Redis
from rq import Worker, Queue, Connection
from rq_scheduler import Scheduler
from datetime import timedelta # 用于 scheduler 的默认 interval

# 导入日志配置，确保 worker 进程也有正确的日志输出
from logger.logger import get_logger
from config.settings import REDIS_URL, TASK_QUEUE_NAME, LOG_LEVEL

# 设置 worker 进程的日志
logger = get_logger("deepseek_dispatcher.worker")

def run_worker():
    """
    启动 RQ Worker 进程。
    此函数将被 Docker Compose 或 Supervisor 等工具调用。
    """
    try:
        redis_conn = Redis.from_url(REDIS_URL)
        logger.info(f"Worker 尝试连接 Redis: {REDIS_URL}")
        redis_conn.ping() # 尝试ping以测试连接
        logger.info("Worker 已成功连接到 Redis。")
    except Exception as e:
        logger.error(f"Worker 无法连接到 Redis: {e}", exc_info=True)
        sys.exit(1) # 连接失败则退出

    # 指定 Worker 监听的队列
    # 可以监听多个队列，例如：queues = [Queue(TASK_QUEUE_NAME, connection=redis_conn), Queue('urgent_tasks', connection=redis_conn)]
    queues = [Queue(TASK_QUEUE_NAME, connection=redis_conn)]

    # 确保 worker 能够发现任务函数
    # RQ Worker 在执行任务时需要能够导入任务函数。
    # 你的任务函数在 `dispatcher.tasks` 模块中。
    # 当你在项目根目录执行 `rq worker` 或 `python worker/worker.py` 时，
    # Python 的模块搜索路径通常能找到 `dispatcher` 包。

    with Connection(redis_conn):
        # 创建 Worker 实例
        # 可以传入 --with-scheduler 参数来启动内嵌的调度器
        worker = Worker(queues, connection=redis_conn)
        logger.info(f"RQ Worker 启动，监听队列: {', '.join([q.name for q in queues])}")
        logger.info(f"Worker PID: {os.getpid()}")

        # 启动 Worker
        worker.work(with_scheduler=True) # 启用内嵌调度器来处理定时任务

if __name__ == '__main__':
    # 如果直接运行 worker.py，则启动 worker
    run_worker()