# dispatcher/dispatcher.py
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List # 导入 List

from redis import Redis
from rq import Queue
from rq.job import Job
from rq.exceptions import NoSuchJobError, InvalidJobOperationError
from rq.worker import Worker

from logger.logger import get_logger
from config.settings import REDIS_URL, TASK_QUEUE_NAME

# 导入 RQ 任务函数
from dispatcher.tasks import generate_text_task

logger = get_logger(__name__)

class TaskDispatchError(Exception):
    """任务调度相关异常"""
    pass

class TaskDispatcher:
    def __init__(self, redis_url: str = REDIS_URL, queue_name: str = TASK_QUEUE_NAME) -> None:
        """
        初始化 TaskDispatcher。
        Args:
            redis_url (str): Redis 连接 URL。
            queue_name (str): RQ 队列名称。
        """
        try:
            self.redis_conn: Redis = Redis.from_url(redis_url)
            self.queue: Queue = Queue(name=queue_name, connection=self.redis_conn)
            logger.info(f"TaskDispatcher 已初始化，连接到 Redis: {redis_url}, 队列: '{queue_name}'")
        except Exception as e:
            logger.error(f"初始化 TaskDispatcher 失败，无法连接到 Redis: {e}", exc_info=True)
            raise TaskDispatchError("无法连接到 Redis") from e

    def enqueue_task(self, task_data: Dict[str, Any], trace_id: str) -> str:
        """
        将 AI 任务放入 RQ 队列。
        Args:
            task_data (Dict[str, Any]): 包含 'prompt' 和 'model_kwargs' 等的任务数据。
            trace_id (str): 用于追踪任务的唯一 ID。
        Returns:
            str: RQ Job ID。
        Raises:
            TaskDispatchError: 任务入队失败时抛出。
        """
        task_id: str = str(uuid.uuid4()) # 为每个任务生成一个唯一的 ID
        try:
            job: Job = self.queue.enqueue(
                generate_text_task,
                task_data,
                trace_id,
                task_id,
                job_id=task_id, # 将任务 ID 设置为 RQ 的 job_id
                result_ttl=86400, # 结果保留 24 小时
                failure_ttl=86400 # 失败结果保留 24 小时
            )
            logger.info(f"任务已成功入队，Job ID={job.id}, Trace ID={trace_id}")
            return job.id
        except Exception as e:
            logger.error(f"任务入队失败 (Trace ID: {trace_id}): {e}", exc_info=True)
            raise TaskDispatchError(f"任务入队失败: {e}") from e

    def get_task_status(self, job_id: str) -> Dict[str, Any]:
        """
        获取 RQ 任务的状态。
        Args:
            job_id (str): RQ Job ID。
        Returns:
            Dict[str, Any]: 包含任务状态、结果、错误等信息的字典。
        """
        try:
            job: Job = Job.fetch(job_id, connection=self.redis_conn)
            status: str = job.get_status()
            result: Optional[Any] = job.result if job.is_finished else None
            error: Optional[str] = job.exc_info if job.is_failed else None

            # 检查任务是否在失败队列中
            if job.is_failed and job_id in self.queue.failed_job_registry:
                status = "failed"
            # 检查任务是否在完成队列中
            elif job.is_finished and job_id in self.queue.finished_job_registry:
                status = "finished"
            # 检查任务是否在队列中等待
            elif job.is_queued and job_id in self.queue.get_jobs():
                status = "queued"
            # 检查任务是否正在执行
            elif job.is_started and job_id in self.queue.started_job_registry:
                status = "started"
            # 检查任务是否被调度 (enqueue_at)
            elif job.is_scheduled and job_id in self.queue.scheduled_job_registry:
                status = "scheduled"

            logger.debug(f"获取任务 {job_id} 状态: {status}")
            return {
                "job_id": job.id,
                "status": status,
                "result": result,
                "error": error,
                "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "finished_at": job.ended_at.isoformat() if job.ended_at else None
            }
        except NoSuchJobError:
            logger.warning(f"未找到 Job ID: {job_id}")
            return {"job_id": job_id, "status": "not_found"}
        except Exception as e:
            logger.error(f"获取任务 {job_id} 状态失败: {e}", exc_info=True)
            return {"job_id": job_id, "status": "error", "message": str(e)}

    def get_queue_metrics(self) -> Dict[str, Any]:
        """
        获取队列的基本指标。
        Returns:
            Dict[str, Any]: 包含队列指标的字典。
        """
        queued_jobs: int = self.queue.count
        started_jobs: int = self.queue.started_job_registry.count
        finished_jobs: int = self.queue.finished_job_registry.count
        failed_jobs: int = self.queue.failed_job_registry.count
        scheduled_jobs: int = self.queue.scheduled_job_registry.count
        deferred_jobs: int = self.queue.deferred_job_registry.count

        logger.debug("获取队列指标。")
        return {
            "queue_name": self.queue.name,
            "queued_jobs": queued_jobs,
            "started_jobs": started_jobs,
            "finished_jobs": finished_jobs,
            "failed_jobs": failed_jobs,
            "scheduled_jobs": scheduled_jobs,
            "deferred_jobs": deferred_jobs,
            "total_jobs_in_queue": queued_jobs + started_jobs + finished_jobs + failed_jobs + scheduled_jobs + deferred_jobs
        }

    def get_jobs_in_registry(self, registry_type: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        获取指定注册表（queued, started, finished, failed, scheduled, deferred）中的任务列表。
        Args:
            registry_type (str): 注册表类型 ('queued', 'started', 'finished', 'failed', 'scheduled', 'deferred')。
            page (int): 页码。
            per_page (int): 每页数量。
        Returns:
            Dict[str, Any]: 包含任务 ID 列表、总数和分页信息的字典。
        """
        registry = None
        job_ids: List[str] = []
        total: int = 0

        if registry_type == 'queued':
            job_ids = [job.id for job in self.queue.get_jobs(offset=(page - 1) * per_page, length=per_page)]
            total = self.queue.count
        elif registry_type == 'started':
            registry = self.queue.started_job_registry
        elif registry_type == 'finished':
            registry = self.queue.finished_job_registry
        elif registry_type == 'failed':
            registry = self.queue.failed_job_registry
        elif registry_type == 'scheduled':
            registry = self.queue.scheduled_job_registry
        elif registry_type == 'deferred':
            registry = self.queue.deferred_job_registry
        else:
            raise ValueError("无效的注册表类型。")

        if registry:
            total = registry.count
            job_ids = registry.get_job_ids((page - 1) * per_page, per_page)

        jobs_info: List[Dict[str, Any]] = []
        for job_id in job_ids:
            try:
                job: Job = Job.fetch(job_id, connection=self.redis_conn)
                jobs_info.append({
                    "job_id": job.id,
                    "status": job.get_status(),
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
                    "description": job.description
                })
            except NoSuchJobError:
                jobs_info.append({"job_id": job_id, "status": "not_found", "description": "Job data not found in Redis"})
            except Exception as e:
                jobs_info.append({"job_id": job_id, "status": "error", "description": f"Failed to fetch job data: {e}"})

        logger.debug(f"获取 {registry_type} 注册表任务列表，共 {total} 个。")
        return {
            "registry_type": registry_type,
            "total_jobs": total,
            "current_page": page,
            "per_page": per_page,
            "jobs": jobs_info
        }

    def get_workers_status(self) -> Dict[str, Any]:
        """
        获取所有 RQ Worker 的状态和信息。
        Returns:
            Dict[str, Any]: 包含 Worker 状态列表和总数的字典。
        """
        workers: List[Worker] = Worker.all(connection=self.redis_conn)
        worker_info: List[Dict[str, Any]] = []
        for worker in workers:
            worker_info.append({
                "name": worker.name,
                "state": worker.get_state(),
                "current_job_id": worker.get_current_job_id(),
                "queues": [q.name for q in worker.queues],
                "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
                "pid": worker.pid
            })
        logger.debug("获取所有 Worker 状态。")
        return {"workers": worker_info, "total_workers": len(worker_info)}