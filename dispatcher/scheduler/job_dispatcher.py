# ~/projects/deepseek_dispatcher-new/dispatcher/scheduler/job_dispatcher.py

from dispatcher.queues.queue_config import QUEUE_MAP
from dispatcher.tasks.example_task import unreliable_task # 确保这个任务函数存在且可被导入
from typing import Any
from rq import Queue
from rq.job import Job
import uuid # 确保导入 uuid 模块，因为它在 dispatch_job 中被使用

# 引入我们新的日志工具
from common.logging_utils import get_logger

# 获取一个名为 "dispatcher" 的 logger
logger = get_logger("dispatcher")

# 当前的重试配置，这将在阶段 1.3.1 被优化为更灵活的策略
RETRY_CONFIG = {
    "max": 3,
    "interval": [10, 30, 60] # 重试间隔，秒
}

def dispatch_job(task_name: str, priority: str = 'default', **kwargs: Any) -> Job:
    """
    根据优先级派发任务到对应的 RQ 队列。

    Args:
        task_name (str): 要执行的任务函数（字符串形式，例如 'dispatcher.tasks.example_task.unreliable_task'）。
                         注意：RQ 需要能通过这个字符串找到并导入到任务函数。
        priority (str): 任务优先级，可以是 'high', 'default', 'low'。
        **kwargs (Any): 传递给任务函数的其他参数。
    Returns:
        Job: RQ 任务对象。
    """
    queue = QUEUE_MAP.get(priority, QUEUE_MAP['default'])
    
    # 为每个任务生成一个唯一的 ID，并传递给任务函数，便于追踪
    job_id = str(uuid.uuid4())
    kwargs['job_id'] = job_id

    logger.info(f"正在派发任务: {task_name}, 优先级={priority}, job_id={job_id}, 参数={kwargs}")

    # 使用当前的重试配置，这些将在阶段 1.3.1 被更灵活地处理
    job = queue.enqueue(
        task_name, # 注意这里是 task_name 字符串，RQ 会去加载它
        kwargs=kwargs, # 传递所有 kwargs，包括 job_id
        retry_intervals=RETRY_CONFIG["interval"], # 直接使用重试间隔列表
        result_ttl=86400, # 任务结果在 Redis 中保留 1 天 (秒)
        failure_ttl=604800, # 失败任务结果在 Redis 中保留 7 天 (秒)
        job_timeout=300 # 任务超时时间 300 秒 (秒)
    )
    logger.info(f"任务 {job.id} 已派发到 {priority} 队列")
    return job