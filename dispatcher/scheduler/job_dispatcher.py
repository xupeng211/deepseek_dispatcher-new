# dispatcher/scheduler/job_dispatcher.py

from dispatcher.queues.queue_config import QUEUE_MAP
# from dispatcher.queues.retry_config import default_retry # 移除此行，我们将直接在 enqueue 中配置重试
from dispatcher.tasks.example_task import unreliable_task
from typing import Any # 新增导入
from rq import Queue # 确保导入
from rq.job import Job # 新增导入

# 定义重试配置
RETRY_CONFIG = {
    "max": 3,
    "interval": [10, 30, 60] # 重试间隔，秒
}

def dispatch_job(priority: str = 'default', **kwargs: Any) -> Job: # 调整参数签名，更灵活地传递 kwargs
    queue = QUEUE_MAP.get(priority, QUEUE_MAP['default'])
    
    # 将 job_id 传递给任务，以便在 task_wrapper 中记录
    job_id = str(uuid.uuid4()) # 为每个任务生成一个唯一的 ID
    kwargs['job_id'] = job_id

    job = queue.enqueue(
        unreliable_task,
        kwargs=kwargs, # 传递所有 kwargs
        retry_intervals=RETRY_CONFIG["interval"], # 直接使用重试间隔列表
        result_ttl=86400, # 任务结果在 Redis 中保留 1 天
        failure_ttl=604800, # 失败任务结果在 Redis 中保留 7 天
        job_timeout=300 # 任务超时时间 300 秒
    )
    return job

# 确保导入 uuid 模块，因为它在 dispatch_job 中被使用
import uuid
