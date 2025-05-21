# dispatcher/dispatcher.py
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify, Blueprint
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from redis import Redis
from rq import Queue, registries
from rq.job import Job
from rq.exceptions import NoSuchJobError, InvalidJobOperationError

from logger.logger import get_logger
from config.settings import REDIS_URL, TASK_QUEUE_NAME, DEFAULT_RATELIMIT

# 导入 RQ 任务函数
from dispatcher.tasks import process_ai_task

logger = get_logger(__name__)

class TaskDispatchError(Exception):
    """任务调度相关异常"""
    pass

class TaskDispatcher:
    def __init__(self, redis_url: str = REDIS_URL, queue_name: str = TASK_QUEUE_NAME):
        try:
            self.redis_conn = Redis.from_url(redis_url)
            self.queue = Queue(name=queue_name, connection=self.redis_conn)
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
        task_id = str(uuid.uuid4()) # 为每个任务生成一个唯一的 ID
        try:
            # enqueue 的第一个参数是可调用的函数，后面是其参数
            job = self.queue.enqueue(
                process_ai_task,
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
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            status = job.get_status()
            result = job.result if job.is_finished else None
            error = job.exc_info if job.is_failed else None

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
        """获取队列的基本指标"""
        queued_jobs = self.queue.count
        started_jobs = self.queue.started_job_registry.count
        finished_jobs = self.queue.finished_job_registry.count
        failed_jobs = self.queue.failed_job_registry.count
        scheduled_jobs = self.queue.scheduled_job_registry.count
        deferred_jobs = self.queue.deferred_job_registry.count

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
            registry_type (str): 注册表类型 ('queued', 'started', 'finished', 'failed', 'scheduled', 'deferred')
            page (int): 页码
            per_page (int): 每页数量
        Returns:
            Dict[str, Any]: 包含任务 ID 列表、总数和分页信息的字典。
        """
        registry = None
        if registry_type == 'queued':
            # 注意: RQ 的 get_jobs() 返回的是 Job 对象的列表，不是 Registry
            # 要获取队列中的 job_id，需要手动遍历
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

        jobs_info = []
        for job_id in job_ids:
            try:
                job = Job.fetch(job_id, connection=self.redis_conn)
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
        """获取所有 RQ Worker 的状态和信息"""
        workers = registries.Worker.all(connection=self.redis_conn)
        worker_info = []
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


# --- Flask 路由注册函数 ---
# 定义一个蓝图来组织调度相关的 API 路由
dispatcher_bp = Blueprint('dispatcher_api', __name__, url_prefix='/api')

@dispatcher_bp.route("/dispatch-task", methods=["POST"])
@Limiter(key_func=get_remote_address, default_limits=[DEFAULT_RATELIMIT], storage_uri=REDIS_URL).exempt_when(lambda: False) # 假设限流在 app factory 中统一管理
def dispatch_task_route():
    """
    HTTP API 接口：接收任务请求并将其放入 RQ 队列。
    """
    trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
    logger.info(f"收到任务调度请求 (Trace ID: {trace_id})。")

    if not request.is_json:
        logger.warning(f"请求格式错误，非 JSON 格式 (Trace ID: {trace_id})。")
        return jsonify({"error": "Request must be JSON"}), 400

    task_data = request.get_json()
    if not task_data or "prompt" not in task_data:
        logger.warning(f"请求缺少必要参数 'prompt' (Trace ID: {trace_id})。")
        return jsonify({"error": "Missing 'prompt' in request body"}), 400

    try:
        dispatcher = TaskDispatcher() # 每次请求都创建一个新实例，确保最新的 Redis 连接
        job_id = dispatcher.enqueue_task(task_data, trace_id)
        return jsonify({
            "message": "Task enqueued successfully",
            "job_id": job_id,
            "trace_id": trace_id
        }), 202 # 202 Accepted 表示请求已接受，但处理尚未完成
    except TaskDispatchError as e:
        logger.error(f"调度请求处理失败: {e} (Trace ID: {trace_id})", exc_info=True)
        return jsonify({"error": f"Failed to enqueue task: {e}"}), 500
    except Exception as e:
        logger.error(f"处理调度请求时发生未知错误: {e} (Trace ID: {trace_id})", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@dispatcher_bp.route("/task-status/<job_id>", methods=["GET"])
def get_task_status_route(job_id: str):
    """
    HTTP API 接口：获取指定 Job ID 的任务状态。
    """
    logger.info(f"收到查询任务状态请求，Job ID: {job_id}")
    try:
        dispatcher = TaskDispatcher()
        status_info = dispatcher.get_task_status(job_id)
        if status_info.get("status") == "not_found":
            return jsonify(status_info), 404
        return jsonify(status_info), 200
    except Exception as e:
        logger.error(f"查询任务状态失败，Job ID: {job_id}: {e}", exc_info=True)
        return jsonify({"error": f"Failed to get task status: {e}"}), 500

@dispatcher_bp.route("/queue-metrics", methods=["GET"])
def get_queue_metrics_route():
    """
    HTTP API 接口：获取 RQ 队列的指标概览。
    """
    logger.info("收到查询队列指标请求。")
    try:
        dispatcher = TaskDispatcher()
        metrics = dispatcher.get_queue_metrics()
        return jsonify(metrics), 200
    except Exception as e:
        logger.error(f"获取队列指标失败: {e}", exc_info=True)
        return jsonify({"error": f"Failed to get queue metrics: {e}"}), 500

@dispatcher_bp.route("/queue-jobs/<registry_type>", methods=["GET"])
def get_queue_jobs_route(registry_type: str):
    """
    HTTP API 接口：获取特定注册表（queued, started, finished, failed, scheduled, deferred）中的任务列表。
    查询参数：page, per_page
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    logger.info(f"收到查询 {registry_type} 队列任务列表请求，页码: {page}, 每页: {per_page}。")
    try:
        dispatcher = TaskDispatcher()
        jobs_list = dispatcher.get_jobs_in_registry(registry_type, page, per_page)
        return jsonify(jobs_list), 200
    except ValueError as e:
        logger.warning(f"无效的注册表类型或查询参数: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"获取 {registry_type} 队列任务列表失败: {e}", exc_info=True)
        return jsonify({"error": f"Failed to get jobs from {registry_type} registry: {e}"}), 500

@dispatcher_bp.route("/workers-status", methods=["GET"])
def get_workers_status_route():
    """
    HTTP API 接口：获取所有 RQ Worker 的状态。
    """
    logger.info("收到查询 Worker 状态请求。")
    try:
        dispatcher = TaskDispatcher()
        workers_status = dispatcher.get_workers_status()
        return jsonify(workers_status), 200
    except Exception as e:
        logger.error(f"获取 Worker 状态失败: {e}", exc_info=True)
        return jsonify({"error": f"Failed to get worker status: {e}"}), 500

def register_dispatcher_routes(app: Flask):
    """
    注册调度器相关的蓝图到 Flask 应用。
    """
    app.register_blueprint(dispatcher_bp)
    logger.info("Dispatcher API 路由已注册到 Flask 应用。")