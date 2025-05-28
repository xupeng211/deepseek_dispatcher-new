# web/app.py
import uuid  # F401: 'uuid' imported but unused - 实际使用，但之前可能未导入
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, status, Query
from pydantic import BaseModel, Field
from rq.job import Job

from config.settings import (
    REDIS_URL,
    TASK_QUEUE_NAME,
    DASHSCOPE_API_KEY,
    MODEL_NAME,  # 确保被使用，例如在 GenerateTextRequest 的 Field 中
    MODEL_PARAMS,  # 确保被使用
    FLASK_HOST,
    FLASK_PORT,
    FLASK_DEBUG,
    FLASK_ENV,
    DEEPSEEK_API_KEY,
    # 移除未使用的导入，例如 RATELIMIT_STORAGE_URI, DEFAULT_RATELIMIT, LOGS_DIR, RESULTS_DIR
)
from dispatcher.core.dispatcher import TaskDispatcher, TaskDispatchError
from logger.logger import get_logger

# 初始化日志
logger = get_logger(__name__)


# 初始化 FastAPI 应用
app = FastAPI(
    title="DeepSeek Dispatcher API",
    description="API for dispatching and managing DeepSeek LLM inference tasks.",
    version="1.0.0",
)

# 初始化 TaskDispatcher 实例
# 建议在应用启动时初始化一次，而不是每个请求都创建新实例
# 这样可以重用 Redis 连接池等资源
task_dispatcher = TaskDispatcher()


# --- Pydantic 模型用于请求和响应验证 ---
class GenerateTextRequest(BaseModel):
    """
    请求体模型，用于生成文本任务。
    """
    prompt: str = Field(..., min_length=1, description="The prompt for text generation.")
    max_tokens: int = Field(100, ge=1, le=2048, description="Maximum number of tokens to generate.")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="Sampling temperature for text generation.")
    top_p: float = Field(0.8, ge=0.0, le=1.0, description="Nucleus sampling parameter for text generation.")
    model_name: Optional[str] = Field(MODEL_NAME, description="The LLM model to use for generation.")

    # 解决 Pydantic 警告
    model_config = {
        'protected_namespaces': ()
    }


class TaskStatusResponse(BaseModel):
    """
    任务状态响应模型。
    """
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    enqueued_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class EnqueueResponse(BaseModel):
    """
    任务入队响应模型。
    """
    message: str
    job_id: str  # 对应 TaskDispatcher 的 job_id
    trace_id: str


class QueueMetricsResponse(BaseModel):
    """
    队列指标响应模型。
    """
    queue_name: str
    queued_jobs: int
    started_jobs: int
    finished_jobs: int
    failed_jobs: int
    scheduled_jobs: int
    deferred_jobs: int
    total_jobs_in_queue: int


class JobInfo(BaseModel):
    """
    单个任务信息模型。
    """
    job_id: str
    status: str
    created_at: Optional[str] = None
    enqueued_at: Optional[str] = None
    description: Optional[str] = None


class JobsListResponse(BaseModel):
    """
    任务列表响应模型。
    """
    registry_type: str
    total_jobs: int
    current_page: int
    per_page: int
    jobs: List[JobInfo]


class WorkerInfo(BaseModel):
    """
    单个 Worker 信息模型。
    """
    name: str
    state: str
    current_job_id: Optional[str] = None
    queues: List[str]
    last_heartbeat: Optional[str] = None
    pid: Optional[int] = None


class WorkersStatusResponse(BaseModel):
    """
    Worker 状态响应模型。
    """
    workers: List[WorkerInfo]
    total_workers: int


# --- API 端点 ---

@app.post("/api/dispatch-task", response_model=EnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
async def dispatch_task_route(
    request_data: GenerateTextRequest,
    x_trace_id: Optional[str] = Query(None, alias="X-Trace-ID", description="Optional trace ID for the request.")
):
    """
    HTTP API 接口：接收任务请求并将其放入 RQ 队列。
    """
    trace_id = x_trace_id if x_trace_id else str(uuid.uuid4())
    # 关键修正：使用 extra 参数传递 trace_id
    logger.info("收到任务调度请求", extra={"trace_id": trace_id})

    try:
        # 准备 task_data 字典，传递给 TaskDispatcher 的 enqueue_task
        task_data = {
            "prompt": request_data.prompt,
            "model_kwargs": {
                "max_tokens": request_data.max_tokens,
                "temperature": request_data.temperature,
                "top_p": request_data.top_p,
                "model_name": request_data.model_name,
            }
        }
        # 修正 enqueue_task 的调用方式，明确指定任务类型为 "inference"
        job_id = task_dispatcher.enqueue_task(
            task_type="inference",  # 与 TASK_REGISTRY 中的键匹配
            task_data=task_data,
            trace_id=trace_id
        )
        # 关键修正：使用 extra 参数传递 job_id 和 trace_id
        logger.info("任务已成功入队", extra={"job_id": job_id, "trace_id": trace_id})
        return EnqueueResponse(
            message="Task enqueued successfully",
            job_id=job_id,
            trace_id=trace_id
        )
    except TaskDispatchError as e:
        # 关键修正：使用 extra 参数传递 trace_id 和 error 信息
        logger.error(f"调度请求处理失败: {e}", exc_info=True, extra={"trace_id": trace_id, "error_details": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue task: {str(e)}"
        )
    except Exception as e:
        # 关键修正：使用 extra 参数传递 trace_id 和 error 信息
        logger.error(f"处理调度请求时发生未知错误: {e}", exc_info=True, extra={"trace_id": trace_id, "error_details": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@app.get("/api/task-status/{job_id}", response_model=TaskStatusResponse)
async def get_task_status_route(job_id: str):
    """
    HTTP API 接口：获取指定 Job ID 的任务状态。
    """
    # 关键修正：使用 extra 参数传递 job_id
    logger.info("收到查询任务状态请求", extra={"job_id": job_id})
    try:
        status_info = task_dispatcher.get_task_status(job_id)
        if status_info.get("status") == "not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        
        # 将 TaskDispatcher 返回的字典直接映射到 Pydantic 模型
        return TaskStatusResponse(**status_info)
    except Exception as e:
        # 关键修正：使用 extra 参数传递 job_id 和 error 信息
        logger.error(f"查询任务状态失败，Job ID: {job_id}: {e}", exc_info=True, extra={"job_id": job_id, "error_details": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )


@app.get("/api/queue-metrics", response_model=QueueMetricsResponse)
async def get_queue_metrics_route():
    """
    HTTP API 接口：获取 RQ 队列的指标概览。
    """
    logger.info("收到查询队列指标请求。")  # 此处无需 extra
    try:
        metrics = task_dispatcher.get_queue_metrics()
        return QueueMetricsResponse(**metrics)
    except Exception as e:
        logger.error(f"获取队列指标失败: {e}", exc_info=True, extra={"error_details": str(e)})  # 修正：使用 extra
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue metrics: {str(e)}"
        )


@app.get("/api/queue-jobs/{registry_type}", response_model=JobsListResponse)
async def get_queue_jobs_route(
    registry_type: str,
    page: int = Query(1, ge=1, description="Page number for job list."),
    per_page: int = Query(20, ge=1, le=100, description="Number of jobs per page.")
):
    """
    HTTP API 接口：获取特定注册表（queued, started, finished, failed, scheduled, deferred）中的任务列表。
    """
    if registry_type not in ['queued', 'started', 'finished', 'failed', 'scheduled', 'deferred']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid registry_type. Must be one of: 'queued', 'started', 'finished', 'failed', 'scheduled', 'deferred'."
        )

    # 关键修正：使用 extra 参数传递 registry_type, page, per_page
    logger.info(f"收到查询 {registry_type} 队列任务列表请求", extra={"registry_type": registry_type, "page": page, "per_page": per_page})
    try:
        jobs_list = task_dispatcher.get_jobs_in_registry(registry_type, page, per_page)
        return JobsListResponse(**jobs_list)
    except Exception as e:
        # 关键修正：使用 extra 参数传递 registry_type 和 error 信息
        logger.error(f"获取 {registry_type} 队列任务列表失败: {e}", exc_info=True, extra={"registry_type": registry_type, "error_details": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get jobs from {registry_type} registry: {str(e)}"
        )


@app.get("/api/workers-status", response_model=WorkersStatusResponse)
async def get_workers_status_route():
    """
    HTTP API 接口：获取所有 RQ Worker 的状态。
    """
    logger.info("收到查询 Worker 状态请求。")  # 此处无需 extra
    try:
        workers_status = task_dispatcher.get_workers_status()
        return WorkersStatusResponse(**workers_status)
    except Exception as e:
        logger.error(f"获取 Worker 状态失败: {e}", exc_info=True, extra={"error_details": str(e)})  # 修正：使用 extra
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get worker status: {str(e)}"
        )


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    健康检查端点。
    """
    logger.info("Health check requested.")  # 此处无需 extra
    try:
        # 尝试 ping Redis 连接以确保其可用
        task_dispatcher.redis_conn.ping()
        return {"status": "healthy", "redis_connection": "ok"}
    except Exception as e:
        logger.error("Health check failed: Redis connection error", exc_info=True, extra={"error_details": str(e)})  # 修正：使用 extra
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: Redis connection failed ({str(e)})"
        )


# --- 应用程序启动和关闭事件 (可选，但推荐用于资源管理) ---
@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI application starting up.")  # 此处无需 extra


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FastAPI application shutting down.")  # 此处无需 extra
    # 可以在这里添加应用关闭时的清理逻辑
    # 例如，关闭 Redis 连接 (如果 TaskDispatcher 内部没有自动处理)
    if hasattr(task_dispatcher, 'redis_conn') and task_dispatcher.redis_conn:
        task_dispatcher.redis_conn.close()
        logger.info("Redis connection closed.")  # 此处无需 extra


# 如果直接运行此文件，则启动 Uvicorn 服务器
if __name__ == "__main__":
    import uvicorn
    logger.info(f"启动 Uvicorn 服务器在 {FLASK_HOST}:{FLASK_PORT}...")
    uvicorn.run(app, host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)

