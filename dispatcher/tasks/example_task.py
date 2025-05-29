# dispatcher/tasks/example_task.py

from .base_task import task_wrapper
import logging # 确保导入 logging
logger = logging.getLogger(__name__) # 确保定义 logger

@task_wrapper
def unreliable_task(should_fail: bool, job_id: str = "unknown_job"): # 添加 job_id 参数，并设置默认值
    # 可以在这里使用 job_id 进行日志记录或其他操作
    logger.info(f"--- Inside unreliable_task for job ID: {job_id} ---")
    if should_fail:
        # 这里会模拟任务失败，并抛出异常
        raise RuntimeError(f"模拟失败任务 for Job ID: {job_id}")
    return "任务成功"