# ~/projects/deepseek_dispatcher-new/dispatcher/core/dispatcher.py

from rq import Queue, Connection
from redis import Redis
import uuid
from typing import Dict, Any, Union, Optional, Callable # 导入 Optional 和 Callable
from dispatcher.queues.queue_config import QUEUE_MAP, default_retry, high_priority_retry, low_priority_retry # 导入重试策略
from dispatcher.tasks.factory import TaskFactory # 确保导入 TaskFactory
from common.logging_utils import get_logger
from config.settings import settings # 从 config.settings 导入 settings 对象
from rq.job import Job # 导入 Job 类，用于 get_task_status
from dispatcher.tasks.base_task import task_wrapper # 导入 task_wrapper 装饰器

# 获取一个名为 "dispatcher.core" 的 logger
logger = get_logger("dispatcher.core")

class TaskDispatchError(Exception):
    """自定义任务调度错误异常"""
    pass

class TaskDispatcher:
    """
    负责任务的调度和状态查询。
    """
    # 修正：__init__ 方法现在接受 redis_url 和 queue_name
    def __init__(self, redis_url: str, queue_name: str):
        self.redis_conn = Redis.from_url(redis_url)
        logger.info(f"TaskDispatcher 初始化，Redis 连接到: {redis_url}")
        
        # 验证 Redis 连接
        try:
            self.redis_conn.ping()
            logger.info("Redis 连接成功 ping。")
        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            raise ConnectionError(f"无法连接到 Redis: {e}")

        self.task_factory = TaskFactory() # 初始化 TaskFactory
        self.default_queue_name = queue_name # 存储默认队列名称
        
        # 确保 QUEUE_MAP 中的 Queue 实例使用相同的 Redis 连接
        for q_name, q_obj in QUEUE_MAP.items():
            if not q_obj.connection or q_obj.connection.connection_pool != self.redis_conn.connection_pool:
                QUEUE_MAP[q_name] = Queue(name=q_name, connection=self.redis_conn)
                logger.debug(f"队列 '{q_name}' 已更新为使用 TaskDispatcher 的 Redis 连接。")


    # 修正：enqueue_task 方法，更名为 dispatch，并调整参数以匹配 web/app.py 中的调用
    def dispatch(self, task_callable: Callable[..., Any], payload: Dict[str, Any], priority: str = 'default', job_id: Optional[str] = None) -> Job:
        """
        将任务添加到 RQ 队列中。

        Args:
            task_callable (Callable): 从 TaskFactory 获取到的任务执行方法。
            payload (Dict[str, Any]): 传递给任务函数的实际数据 (例如：prompt, model_kwargs)。
            priority (str): 任务的优先级（'high', 'default', 'low'）。
            job_id (str, optional): 任务的唯一 ID。如果未提供，将自动生成。

        Returns:
            Job: RQ Job 对象。

        Raises:
            TaskDispatchError: 如果任务调度失败。
        """
        # 如果 job_id 未提供，则生成一个 UUID
        job_id = str(uuid.uuid4()) if job_id is None else job_id
        
        # 确保传入的 priority 是有效的
        if priority not in QUEUE_MAP:
            logger.warning(f"无效的优先级: '{priority}'。使用默认优先级。")
            priority = 'default'

        queue = QUEUE_MAP.get(priority) # 根据优先级获取队列对象
        
        logger.info(f"准备派发任务: 类型={task_callable.__name__}, ID={job_id}, 优先级={priority}")

        try:
            # 准备传递给任务函数的 kwargs。
            # task_details 将包含原始的 payload 和 job_id，以及任务类型等元数据
            task_details = {
                "task_type": task_callable.__name__, # 假设任务名称是 callable 的名称
                "job_id": job_id,
                "payload": { # 这里的 payload 是 web/app.py 中的 task_data_for_inference_task
                    "task_data": payload # 包含 prompt, model_kwargs, should_fail_for_test 等
                }
            }

            # 选择重试策略
            retry_strategy = default_retry
            if priority == "high":
                retry_strategy = high_priority_retry
            elif priority == "low":
                retry_strategy = low_priority_retry
            # 默认是 default_retry，无需额外设置

            # 使用 task_wrapper 包装任务函数，确保其能够处理异常和告警
            wrapped_task_callable = task_wrapper(task_callable)

            job = queue.enqueue(
                wrapped_task_callable, # 传递包装后的任务函数
                job_id=job_id,        # RQ 自身的 job_id 参数
                kwargs={'job_id': job_id, 'task_details': task_details}, # 将所有数据打包到 kwargs 传递给任务函数
                result_ttl=settings.TASK_RESULT_TTL, 
                failure_ttl=settings.TASK_FAILURE_TTL, 
                timeout=settings.TASK_JOB_TIMEOUT,
                retry=retry_strategy # 应用重试策略
            )
            logger.info(f"任务已成功入队，Job ID: {job.id}, 队列: {queue.name}")
            return job
        except Exception as e:
            logger.error(f"任务入队失败，任务类型: {task_callable.__name__}, Job ID: {job_id}: {e}", exc_info=True)
            raise TaskDispatchError(f"任务入队失败: {str(e)}")

    def get_task_status(self, job_id: str) -> Dict[str, Union[str, Any]]:
        """
        获取指定 Job ID 的任务状态和结果。
        """
        try:
            job = None
            # 遍历所有队列查找任务
            with Connection(self.redis_conn):
                for queue_name in QUEUE_MAP.keys():
                    try:
                        # 尝试从每个队列的默认注册表、已开始、已完成、已失败注册表中查找任务
                        job = Job.fetch(job_id, connection=self.redis_conn)
                        if job:
                            break
                    except Exception:
                        continue # 如果在一个队列中没找到，尝试下一个队列
            
            if not job:
                logger.warning(f"任务 {job_id} 未找到。")
                return {"job_id": job_id, "status": "not_found", "error": "Task not found."}

            status = job.get_status()
            result = None
            error = None

            if status == 'finished':
                # RQ 任务的 result 是任务函数返回的原始结果
                # InferenceTask.execute 返回的是 {"status": "success", "result": "..."}
                if job.result and isinstance(job.result, dict):
                    result = job.result.get("result", "无结果")
                    # 这里不再从 result 中获取 error，因为 finished 状态通常没有 error
                else:
                    result = job.result
            elif status == 'failed':
                error = str(job.exc_info) if job.exc_info else "Task failed with no specific error info."
            
            logger.info(f"查询任务状态成功，Job ID: {job_id}, 状态: {status}")
            return {
                "job_id": job_id,
                "status": status,
                "result": result,
                "error": error,
                "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "finished_at": job.ended_at.isoformat() if job.ended_at else None,
            }
        except Exception as e:
            logger.error(f"获取任务状态失败，Job ID: {job_id}: {e}", exc_info=True)
            raise TaskDispatchError(f"获取任务状态失败: {str(e)}")

    def get_queue_metrics(self) -> Dict[str, Dict[str, int]]:
        """
        获取所有队列的指标概览。
        """
        metrics = {}
        with Connection(self.redis_conn):
            for q_name, queue in QUEUE_MAP.items():
                metrics[q_name] = {
                    "queued_jobs": queue.count,
                    "started_jobs": queue.started_job_registry.count,
                    "finished_jobs": queue.finished_job_registry.count,
                    "failed_jobs": queue.failed_job_registry.count,
                    "scheduled_jobs": queue.scheduled_job_registry.count,
                    "deferred_jobs": queue.deferred_job_registry.count,
                    "total_jobs_in_queue": queue.count + \
                                           queue.started_job_registry.count + \
                                           queue.finished_job_registry.count + \
                                           queue.failed_job_registry.count + \
                                           queue.scheduled_job_registry.count + \
                                           queue.deferred_job_registry.count
                }
        logger.info("获取队列指标成功。")
        return metrics

    def get_jobs_in_registry(self, registry_type: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        获取特定注册表（queued, started, finished, failed, scheduled, deferred）中的任务列表。
        """
        jobs_list = []
        total_jobs = 0
        offset = (page - 1) * per_page

        with Connection(self.redis_conn):
            all_job_ids = []
            for q_name, queue in QUEUE_MAP.items():
                if registry_type == 'queued':
                    all_job_ids.extend(queue.job_ids)
                elif registry_type == 'started':
                    all_job_ids.extend(queue.started_job_registry.get_job_ids())
                elif registry_type == 'finished':
                    all_job_ids.extend(queue.finished_job_registry.get_job_ids())
                elif registry_type == 'failed':
                    all_job_ids.extend(queue.failed_job_registry.get_job_ids())
                elif registry_type == 'scheduled':
                    all_job_ids.extend(queue.scheduled_job_registry.get_job_ids())
                elif registry_type == 'deferred':
                    all_job_ids.extend(queue.deferred_job_registry.get_job_ids())
                else:
                    raise ValueError(f"无效的注册表类型: {registry_type}")

            unique_job_ids = sorted(list(set(all_job_ids)), reverse=True)
            total_jobs = len(unique_job_ids)
            paginated_job_ids = unique_job_ids[offset : offset + per_page]

            for job_id in paginated_job_ids:
                try:
                    job = Job.fetch(job_id, connection=self.redis_conn)
                    jobs_list.append({
                        "job_id": job.id,
                        "status": job.get_status(),
                        "created_at": job.created_at.isoformat() if job.created_at else None,
                        "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
                        "description": job.description,
                        "result": job.result if job.is_finished else None,
                        "error": str(job.exc_info) if job.is_failed and job.exc_info else None
                    })
                except Exception as e:
                    logger.warning(f"获取任务 {job_id} 详情失败: {e}")
                    jobs_list.append({
                        "job_id": job_id,
                        "status": "unknown",
                        "error": str(e)
                    })

        logger.info(f"获取 {registry_type} 注册表中的任务列表成功，共 {total_jobs} 个。")
        return {
            "registry_type": registry_type,
            "total_jobs": total_jobs,
            "current_page": page,
            "per_page": per_page,
            "jobs": jobs_list
        }

    def get_workers_status(self) -> Dict[str, Any]:
        """
        获取所有 RQ Worker 的状态。
        """
        workers_info = []
        with Connection(self.redis_conn):
            all_workers = set()
            for queue in QUEUE_MAP.values():
                for worker in queue.workers:
                    all_workers.add(worker)

        for worker in all_workers:
            workers_info.append({
                "name": worker.name,
                "state": worker.get_state(),
                "current_job_id": worker.get_current_job_id(),
                "queues": [q.name for q in worker.queues],
                "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
                "pid": worker.pid,
            })
        total_workers = len(workers_info)
        logger.info(f"获取 Worker 状态成功，总 Worker 数: {total_workers}")
        return {"workers": workers_info, "total_workers": total_workers}

# 可以在这里添加一些模块级别的测试代码，如果需要的话
if __name__ == '__main__':
    print("正在测试 TaskDispatcher...")
    dispatcher = TaskDispatcher(redis_url="redis://localhost:6379/0", queue_name="deepseek_tasks") # 修正测试初始化
    
    try:
        # 注意：这里的 task_type 要和 TaskFactory 中注册的类型匹配
        # factory.py 中注册的是 "inference_task"
        job_id = dispatcher.dispatch( # 修正：调用 dispatch 而不是 enqueue_task
            task_callable=dispatcher.task_factory.get_task_callable("inference_task"), # 从工厂获取 callable
            payload={ # 这里的 payload 对应 InferenceTask.execute 接收的 task_details['payload']['task_data']
                "prompt": "Hello, world from test!",
                "model_name": "deepseek-chat"
            },
            priority="default"
        ).id # dispatch 返回 Job 对象，需要获取 id
        print(f"任务已派发，Job ID: {job_id}")

        import time
        time.sleep(5)
        status_info = dispatcher.get_task_status(job_id)
        print(f"任务 {job_id} 的状态: {status_info['status']}, 结果: {status_info['result']}, 错误: {status_info['error']}")

        metrics = dispatcher.get_queue_metrics()
        print(f"队列指标: {metrics}")

        jobs_list = dispatcher.get_jobs_in_registry("queued")
        print(f"排队中的任务: {jobs_list['jobs']}")

    except Exception as e:
        print(f"测试 TaskDispatcher 失败: {e}")
