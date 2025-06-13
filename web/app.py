# ~/projects/deepseek_dispatcher-new/web/app.py

import uuid
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel, Field
from rq.job import Job
from redis import Redis # 导入 Redis 用于健康检查

# 导入我们统一的日志工具
from common.logging_utils import get_logger
# 导入配置
from config.settings import settings # 导入 settings 对象

# TaskDispatcher 和 TaskDispatchError 现在从 dispatcher.core.dispatcher 正确导入
from dispatcher.core.dispatcher import TaskDispatcher, TaskDispatchError
# 导入 task_wrapper 和 TaskFactory
from dispatcher.tasks.base_task import task_wrapper
from dispatcher.tasks.factory import TaskFactory


# 初始化日志，为 FastAPI 应用获取一个 logger
# 日志将写入到 logs/fastapi_app.log 文件中
api_logger = get_logger("fastapi_app", log_dir=settings.LOGS_DIR, level=settings.LOG_LEVEL)


# 初始化 FastAPI 应用
app = FastAPI(
    title="DeepSeek Dispatcher API",
    description="API for dispatching and managing DeepSeek LLM inference tasks.",
    version="1.0.0",
)

# 初始化 TaskDispatcher 实例
# 建议在应用启动时初始化一次，而不是每个请求都创建新实例
# 这样可以重用 Redis 连接池等资源
task_dispatcher = TaskDispatcher(
    redis_url=settings.REDIS_URL, # 使用 settings 中的 Redis URL
    queue_name=settings.TASK_QUEUE_NAME # 使用 settings 中的队列名称
)
# 初始化 TaskFactory 实例
task_factory = TaskFactory()


# --- Pydantic 模型用于请求和响应验证 ---
class GenerateTextRequest(BaseModel):
    """
    请求体模型，用于生成文本任务。
    """
    prompt: str = Field(..., min_length=1, description="The prompt for text generation.")
    # 从 settings 获取默认值，但允许请求中覆盖
    max_tokens: Optional[int] = Field(settings.MODEL_MAX_TOKENS, description="The maximum number of tokens to generate.")
    temperature: Optional[float] = Field(settings.MODEL_TEMPERATURE, description="The sampling temperature (0.0 - 1.0). Higher values make output more random.")
    top_p: Optional[float] = Field(settings.MODEL_TOP_P, description="The nucleus sampling parameter (0.0 - 1.0).")
    model_name: Optional[str] = Field(settings.MODEL_NAME, description="The specific model name to use for inference.")
    priority: Optional[str] = Field('default', description="Task priority (high, default, low).")
    # 新增：用于测试任务失败的标志。默认值为 False。
    should_fail_for_test: Optional[bool] = Field(False, description="Set to true to force this task to fail for testing retry and alert.")


class TaskStatusResponse(BaseModel):
    """
    响应体模型，用于查询任务状态。
    """
    job_id: str = Field(..., description="The unique ID of the task job.")
    status: str = Field(..., description="The current status of the task (e.g., queued, started, finished, failed).")
    result: Optional[str] = Field(None, description="The result of the task, if available.")
    error: Optional[str] = Field(None, description="Error message, if the task failed.")


class EnqueueResponse(BaseModel):
    """
    响应体模型，用于任务入队成功。
    """
    job_id: str = Field(..., description="The unique ID of the enqueued task job.")
    status: str = Field(..., description="Status of the enqueue operation (always 'enqueued' if successful).")


class QueueMetricsResponse(BaseModel):
    """
    响应体模型，用于队列指标。
    """
    queued_tasks: Dict[str, int] = Field(..., description="Number of tasks in each queue (high, default, low).")
    started_tasks: Dict[str, int] = Field(..., description="Number of started tasks for each queue.")
    failed_tasks: Dict[str, int] = Field(..., description="Number of failed tasks for each queue.")
    finished_tasks: Dict[str, int] = Field(..., description="Number of finished tasks for each queue.")


class WorkerStatus(BaseModel):
    """
    单个 worker 的状态模型。
    """
    name: str = Field(..., description="Worker name.")
    state: str = Field(..., description="Worker state (e.g., busy, idle, suspended).")
    current_job: Optional[str] = Field(None, description="ID of the job currently being processed by the worker.")
    successful_jobs: int = Field(..., description="Number of jobs successfully processed by the worker.")
    failed_jobs: int = Field(..., description="Number of jobs failed by the worker.")


class AllWorkersStatusResponse(BaseModel):
    """
    所有 worker 状态的响应模型。
    """
    workers: List[WorkerStatus] = Field(..., description="List of worker statuses.")
    total_workers: int = Field(..., description="Total number of workers.")


# --- FastAPI 路由定义 ---
@app.post("/generate", response_model=EnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_text(
    request: GenerateTextRequest,
    background_tasks: BackgroundTasks # 引入 background_tasks
):
    """
    提交一个文本生成任务到队列。
    """
    api_logger.info(f"收到文本生成请求，prompt 长度: {len(request.prompt)}")

    # 准备传递给 TaskDispatcher 的 task_data
    # 这将作为 task_details['payload'] 传递给 execute 方法
    task_data_for_inference_task = {
        "prompt": request.prompt,
        # 修正：直接访问 request.should_fail_for_test，因为已经在 Pydantic 模型中定义
        "should_fail_for_test": request.should_fail_for_test,
        "model_kwargs": {
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        },
        "model_name": request.model_name # 将 model_name 传递给任务
    }

    try:
        # 修正：将 enqueue_task 修改为 dispatch
        job = task_dispatcher.dispatch(
            task_callable=task_factory.get_task_callable("inference_task"),   # 任务类型，与 TaskFactory 中的注册键一致
            payload=task_data_for_inference_task,  # 传递完整的 payload
            priority=request.priority,
            job_id=str(uuid.uuid4()) # 生成一个新的 job_id
        )
        api_logger.info(f"任务 {job.id} 已成功入队。")
        return EnqueueResponse(job_id=job.id, status="enqueued")
    except TaskDispatchError as e:
        api_logger.error(f"任务调度失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch task: {str(e)}"
        )
    except Exception as e:
        api_logger.critical(f"处理 /generate 请求时发生未知错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@app.get("/tasks/{job_id}/status", response_model=TaskStatusResponse)
async def get_task_status(job_id: str):
    """
    获取指定任务的当前状态和结果。
    """
    api_logger.info(f"查询任务状态请求，Job ID: {job_id}")
    try:
        status_info = task_dispatcher.get_task_status(job_id)
        api_logger.info(f"任务 {job_id} 状态: {status_info['status']}")
        return TaskStatusResponse(
            job_id=job_id,
            status=status_info.get("status", "unknown"),
            result=status_info.get("result"),
            error=status_info.get("error")
        )
    except TaskDispatchError as e:
        api_logger.error(f"获取任务状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )
    except Exception as e:
        api_logger.critical(f"处理 /tasks/{job_id}/status 请求时发生未知错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@app.get("/metrics", response_model=QueueMetricsResponse)
async def get_queue_metrics():
    """
    获取 RQ 队列的指标（排队中、已开始、已失败、已完成的任务数）。
    """
    api_logger.info("获取队列指标请求。")
    try:
        metrics = task_dispatcher.get_queue_metrics()
        api_logger.info(f"队列指标: {metrics}")
        # 注意：这里返回的 metrics 结构应该匹配 QueueMetricsResponse 的定义
        # 如果 metrics 是平铺的，需要调整 Pydantic 模型或这里进行映射
        return QueueMetricsResponse(
            queued_tasks={q_name: m['queued_jobs'] for q_name, m in metrics.items()},
            started_tasks={q_name: m['started_jobs'] for q_name, m in metrics.items()},
            failed_tasks={q_name: m['failed_jobs'] for q_name, m in metrics.items()},
            finished_tasks={q_name: m['finished_jobs'] for q_name, m in metrics.items()}
        )
    except TaskDispatchError as e:
        api_logger.error(f"获取队列指标失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue metrics: {str(e)}"
        )
    except Exception as e:
        api_logger.critical(f"处理 /metrics 请求时发生未知错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@app.get("/workers/status", response_model=AllWorkersStatusResponse)
async def get_workers_status():
    """
    获取所有 RQ worker 的状态。
    """
    api_logger.info("获取 worker 状态请求。")
    try:
        workers_info = task_dispatcher.get_workers_status()
        api_logger.info(f"Worker 状态: {workers_info}")
        workers_list = [WorkerStatus(**w) for w in workers_info.get("workers", [])]
        return AllWorkersStatusResponse(
            workers=workers_list,
            total_workers=workers_info.get("total_workers", 0)
        )
    except TaskDispatchError as e:
        api_logger.error(f"获取 worker 状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get worker status: {str(e)}"
        )
    except Exception as e:
        api_logger.critical(f"处理 /workers/status 请求时发生未知错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    健康检查端点。
    """
    api_logger.info("Health check requested.")
    try:
        # 尝试 ping Redis 连接以确保其可用
        redis_conn = Redis.from_url(settings.REDIS_URL) # 从 settings 获取 Redis URL
        redis_conn.ping()
        return {"status": "healthy", "redis_connection": "ok"}
    except Exception as e:
        api_logger.error(f"Health check failed: Redis connection error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: Redis connection failed ({str(e)})"
        )


# --- 应用程序启动和关闭事件 (可选，但推荐用于资源管理) ---
@app.on_event("startup")
async def startup_event():
    api_logger.info("FastAPI application starting up.")

@app.on_event("shutdown")
async def shutdown_event():
    api_logger.info("FastAPI application shutting down.")
    # 可以在这里添加应用关闭时的清理逻辑
    # 例如，关闭 Redis 连接 (如果 TaskDispatcher 内部没有自动处理)
    if hasattr(task_dispatcher, 'redis_conn') and task_dispatcher.redis_conn:
        try:
            task_dispatcher.redis_conn.close()
            api_logger.info("Redis connection closed.")
        except Exception as e:
            api_logger.warning(f"关闭 Redis 连接时发生错误: {e}")


# 如果直接运行此文件 (例如使用 `python app.py`)，则会启动 Uvicorn 服务器
if __name__ == "__main__":
    import uvicorn
    # 从 settings 获取 host 和 port
    uvicorn.run(app, host=settings.FLASK_HOST, port=settings.FLASK_PORT, debug=settings.FLASK_DEBUG)

