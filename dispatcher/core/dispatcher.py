import uuid
import logging
from typing import Dict, Any

from redis import Redis
from rq import Queue
from rq.job import Job
from rq.worker import Worker 

from logger.logger import get_logger
from config.settings import REDIS_URL, TASK_QUEUE_NAME


logger = get_logger(__name__)


class TaskDispatchError(Exception):
    """任务调度相关异常"""
    pass


class TaskDispatcher:
    def __init__(self, redis_url: str = REDIS_URL, queue_name: str = TASK_QUEUE_NAME):
        try:
            self.redis_conn = Redis.from_url(redis_url)
            self.queue = Queue(name=queue_name, connection=self.redis_conn)
            logger.info(f"TaskDispatcher 初始化成功，队列: {queue_name}")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}", exc_info=True)
            raise TaskDispatchError(f"Redis连接失败: {e}") from e

    def enqueue_task(self, task_type: str, task_data: Dict[str, Any], trace_id: str) -> str:
        """
        将任务加入队列
        Args:
            task_type: 注册的任务类型（如 "inference"）
            task_data: 原始任务数据
            trace_id: 追踪ID
        """
        task_id = str(uuid.uuid4())
        payload = {
            "task_data": task_data,
            "trace_id": trace_id
        }

        try:
            self.queue.enqueue(
                "dispatcher.tasks.execute_task",
                task_type,
                task_id,
                payload,
                job_id=task_id,
                result_ttl=86400,
                failure_ttl=86400
            )
            logger.info(f"任务入队成功 | TaskID: {task_id} | TraceID: {trace_id}")
            return task_id
        except Exception as e:
            logger.error(f"任务入队失败 | TraceID: {trace_id} | Error: {e}")
            raise TaskDispatchError(f"任务入队失败: {e}") from e

    def get_task_status(self, job_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            status_info = {
                "job_id": job.id,
                "status": job.get_status(),
                "result": job.result if job.is_finished else None,
                "error": job.exc_info if job.is_failed else None,
                "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "finished_at": job.ended_at.isoformat() if job.ended_at else None,
            }
            logger.info(f"查询任务状态成功 | JobID: {job_id} | Status: {status_info['status']}")
            return status_info
        except Exception as e:
            logger.error(f"查询任务状态失败 | JobID: {job_id} | Error: {e}", exc_info=True)
            return {"job_id": job_id, "status": "not_found", "error": str(e)}

    def get_queue_metrics(self) -> Dict[str, Any]:
        """
        获取队列指标
        """
        try:
            queued_jobs = self.queue.count
            started_jobs = self.queue.started_job_registry.count
            finished_jobs = self.queue.finished_job_registry.count
            failed_jobs = self.queue.failed_job_registry.count
            scheduled_jobs = self.queue.scheduled_job_registry.count
            deferred_jobs = self.queue.deferred_job_registry.count
            total_jobs_in_queue = queued_jobs + started_jobs + finished_jobs + failed_jobs + scheduled_jobs + deferred_jobs

            metrics = {
                "queue_name": self.queue.name,
                "queued_jobs": queued_jobs,
                "started_jobs": started_jobs,
                "finished_jobs": finished_jobs,
                "failed_jobs": failed_jobs,
                "scheduled_jobs": scheduled_jobs,
                "deferred_jobs": deferred_jobs,
                "total_jobs_in_queue": total_jobs_in_queue,
            }
            logger.info(f"查询队列指标成功 | Queue: {self.queue.name}")
            return metrics
        except Exception as e:
            logger.error(f"获取队列指标失败 | Error: {e}", exc_info=True)
            raise TaskDispatchError(f"获取队列指标失败: {e}") from e

    def get_workers_status(self) -> Dict[str, Any]:
        """
        获取所有 Worker 的状态
        """
        try:
            workers = Worker.all(connection=self.redis_conn)
            worker_info_list = []
            for worker in workers:
                worker_info = {
                    "name": worker.name,
                    "state": worker.get_state(),
                    "current_job_id": worker.get_current_job_id(),
                    "queues": [q.name for q in worker.queues],
                    "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
                    "pid": worker.pid,
                }
                worker_info_list.append(worker_info)
            logger.info(f"查询 Worker 状态成功 | Workers: {len(worker_info_list)}")
            return {"workers": worker_info_list, "total_workers": len(worker_info_list)}
        except Exception as e:
            logger.error(f"获取 Worker 状态失败 | Error: {e}", exc_info=True)
            raise TaskDispatchError(f"获取 Worker 状态失败: {e}") from e