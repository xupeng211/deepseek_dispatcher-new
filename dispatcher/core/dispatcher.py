# ~/projects/deepseek_dispatcher-new/dispatcher/core/dispatcher.py

from rq import Queue, Connection, Retry
from redis import Redis
from typing import Dict, Any, Optional
from rq.job import Job
import time
import json # 用于序列化非 JSON 安全的数据

# 引入我们新的日志工具
from common.logging_utils import get_logger
# 引入配置
from config.settings import settings

# 引入 TaskFactory 来获取可执行的任务函数
from dispatcher.tasks.factory import TaskFactory
# 引入队列配置
from dispatcher.queues.queue_config import QUEUE_MAP, redis_conn # 使用 redis_conn 来获取 Redis 实例
# 引入重试配置
from dispatcher.queues.retry_config import RETRY_STRATEGIES # **这里现在正确地导入了 RETRY_STRATEGIES**

# 获取一个名为 "dispatcher" 的 logger
logger = get_logger("dispatcher")

class TaskDispatchError(Exception):
    """自定义的任务调度异常"""
    pass

class TaskDispatcher:
    def __init__(self):
        # Redis 连接由 queue_config.py 中的 redis_conn 提供
        self.redis_conn = redis_conn
        logger.info("TaskDispatcher 初始化完成。")

    def enqueue_task(self, task_type: str, task_data: Dict[str, Any], trace_id: str, priority: str = 'default') -> str:
        """
        将任务添加到 RQ 队列中。

        Args:
            task_type (str): 任务的类型（例如："inference"）。
            task_data (Dict[str, Any]): 包含任务所需数据的字典（例如：{"prompt": "...", "model_kwargs": {...}}）。
            trace_id (str): 请求的追踪ID。
            priority (str): 任务优先级 ('high', 'default', 'low')。

        Returns:
            str: RQ Job ID。

        Raises:
            TaskDispatchError: 如果任务调度失败。
        """
        logger.info(f"正在准备入队任务，类型: {task_type}, 优先级: {priority}, Trace ID: {trace_id}")
        
        try:
            # 获取对应的任务函数
            task_callable = TaskFactory.get_task_callable(task_type)

            # 获取对应优先级的 RQ 队列
            queue = QUEUE_MAP.get(priority, QUEUE_MAP['default'])

            # 获取重试策略
            retry_config = RETRY_STRATEGIES.get(priority) # 直接获取 Retry 对象，而不是 RetryConfig 实例

            # 为任务添加 job_id，便于追踪。这个 job_id 会传递给 task_callable
            job_id = f"{task_type}-{trace_id}-{int(time.time() * 1000)}" # 结合 trace_id 和时间戳生成唯一ID
            task_data['job_id'] = job_id # 将 job_id 也加入 task_data，以便任务函数获取

            # 将 task_data 作为 kwargs 传递给任务函数
            job = queue.enqueue(
                task_callable,
                kwargs=task_data, # 将整个 task_data 字典作为 kwargs 传递
                job_id=job_id,
                result_ttl=settings.TASK_RESULT_TTL, # 结果TTL，从配置中读取
                failure_ttl=settings.TASK_FAILURE_TTL, # 失败TTL，从配置中读取
                job_timeout=settings.TASK_JOB_TIMEOUT, # 任务超时，从配置中读取
                retry=retry_config # 直接传递 RQ 的 Retry 对象
            )

            logger.info(f"任务已成功入队，Job ID: {job.id}, 类型: {task_type}, 队列: {queue.name}")
            return job.id
        except Exception as e:
            logger.error(f"任务调度失败: {e}", exc_info=True)
            raise TaskDispatchError(f"任务调度失败: {str(e)}")

    def get_task_status(self, job_id: str) -> Dict[str, Any]:
        """
        获取指定 Job ID 的任务状态。
        """
        logger.debug(f"查询任务状态，Job ID: {job_id}")
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
        except Exception:
            logger.warning(f"任务 {job_id} 未找到或无法获取。")
            return {"job_id": job_id, "status": "not_found", "error": "Task not found."}
        
        status_info = {
            "job_id": job.id,
            "status": job.get_status(), # 获取任务状态 (queued, started, finished, failed, deferred, stopped)
            "result": None,
            "error": None,
            "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        }

        if job.is_finished:
            try:
                # RQ 任务结果默认是 JSON 序列化的，如果结果包含非 JSON 安全类型，可能需要特殊处理
                # 这里假设结果是可 JSON 序列化的
                status_info["result"] = job.result
            except Exception as e:
                logger.warning(f"获取任务结果时发生错误，Job ID: {job_id}: {e}", exc_info=True)
                status_info["result"] = "Failed to retrieve result: " + str(e)
        elif job.is_failed:
            status_info["error"] = str(job.exc_info) # 失败信息

        logger.debug(f"任务 {job_id} 状态: {status_info['status']}")
        return status_info

    def get_queue_metrics(self) -> Dict[str, Any]:
        """
        获取所有 RQ 队列的指标概览。
        """
        metrics = {
            "queue_name": "overall", # 可以根据需要汇总或列出所有队列
            "queued_jobs": 0,
            "started_jobs": 0,
            "finished_jobs": 0,
            "failed_jobs": 0,
            "scheduled_jobs": 0, # 新增调度任务数量
            "deferred_jobs": 0,  # 新增延迟任务数量
            "total_jobs_in_queue": 0,
        }
        
        # 遍历所有队列获取指标
        for priority, queue in QUEUE_MAP.items():
            metrics["queued_jobs"] += queue.count # 队列中等待的任务
            metrics["started_jobs"] += queue.started_job_registry.count # 正在运行的任务
            metrics["finished_jobs"] += queue.finished_job_registry.count # 已完成的任务
            metrics["failed_jobs"] += queue.failed_job_registry.count # 失败的任务
            metrics["scheduled_jobs"] += queue.scheduled_job_registry.count # 调度中的任务
            metrics["deferred_jobs"] += queue.deferred_job_registry.count # 延迟的任务
            # 总任务数量，这里只加了 queued_jobs，其他 registry 应该通过其 count 属性获取
            metrics["total_jobs_in_queue"] += queue.count + \
                                           queue.started_job_registry.count + \
                                           queue.finished_job_registry.count + \
                                           queue.failed_job_registry.count + \
                                           queue.scheduled_job_registry.count + \
                                           queue.deferred_job_registry.count

        logger.info("获取队列指标成功。")
        return metrics

    def get_jobs_in_registry(self, registry_type: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        获取特定注册表中的任务列表。
        registry_type: 'queued', 'started', 'finished', 'failed', 'scheduled', 'deferred'
        """
        # 验证 registry_type 的有效性
        valid_registry_types = ['queued', 'started', 'finished', 'failed', 'scheduled', 'deferred']
        if registry_type not in valid_registry_types:
            raise ValueError(f"Invalid registry_type: {registry_type}. Must be one of {valid_registry_types}")

        all_jobs_info = []
        
        for priority, queue in QUEUE_MAP.items():
            job_ids = []
            if registry_type == 'queued':
                job_ids = queue.get_job_ids() # 从队列本身获取 queued jobs
            else:
                # 对于其他注册表类型，通过 RQ 的注册表对象获取
                registry = getattr(queue, f"{registry_type}_job_registry", None)
                if registry:
                    job_ids = registry.get_job_ids()
            
            # Fetch job details for the current batch of IDs
            for job_id in job_ids:
                try:
                    job = Job.fetch(job_id, connection=self.redis_conn)
                    all_jobs_info.append({
                        "job_id": job.id,
                        "status": job.get_status(),
                        "created_at": job.created_at.isoformat() if job.created_at else None,
                        "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
                        "description": job.description # job.description 可能是任务函数名
                    })
                except Exception as e:
                    logger.warning(f"获取任务 {job_id} 详情失败: {e}", exc_info=True)
                    # 如果任务获取失败，可以返回部分信息或跳过
                    all_jobs_info.append({
                        "job_id": job_id,
                        "status": "unknown",
                        "error": str(e),
                        "description": "Failed to fetch job details"
                    })
        
        # 对所有获取到的任务进行去重和排序（如果需要）
        # 这里使用 job_id 去重，并按 created_at 降序排序（最新创建的在前）
        # 更好的做法是使用字典来去重，然后转换为列表
        unique_jobs_map = {job['job_id']: job for job in all_jobs_info}
        sorted_jobs = sorted(
            unique_jobs_map.values(),
            key=lambda x: x.get('created_at', '0000-00-00T00:00:00') if x.get('created_at') else '', # Handle None created_at
            reverse=True
        )
        total_jobs = len(sorted_jobs)
        
        # 手动分页
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        paginated_jobs = sorted_jobs[start_index:end_index]

        logger.info(f"获取 {registry_type} 队列任务列表成功，总数: {total_jobs}, 页码: {page}, 每页: {per_page}")
        return {
            "registry_type": registry_type,
            "total_jobs": total_jobs,
            "current_page": page,
            "per_page": per_page,
            "jobs": paginated_jobs
        }

    def get_workers_status(self) -> Dict[str, Any]:
        """
        获取所有 RQ Worker 的状态。
        """
        workers_info = []
        # 获取所有活跃的 Worker
        # 注意：Queue.all() 返回的是所有队列，需要遍历每个队列的 worker
        
        all_workers = set() # 用 set 来避免重复的 worker (如果一个 worker 监听多个队列)
        for queue in QUEUE_MAP.values():
            for worker in queue.workers:
                all_workers.add(worker) # Add the worker object itself

        for worker in all_workers:
            # worker.name, worker.state, worker.current_job, worker.queues, worker.last_heartbeat, worker.pid
            workers_info.append({
                "name": worker.name,
                "state": worker.state,
                "current_job_id": worker.current_job.id if worker.current_job else None,
                "queues": [q.name for q in worker.queues],
                "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
                "pid": worker.pid,
            })
        total_workers = len(workers_info)
        logger.info(f"获取 Worker 状态成功，总 Worker 数: {total_workers}")
        return {"workers": workers_info, "total_workers": total_workers}

