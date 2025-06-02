# ~/projects/deepseek_dispatcher-new/dispatcher/tasks/base_task.py

# 引入我们新的日志工具
from common.logging_utils import get_logger
import functools # 保留 functools.wraps

# from common.alert_utils import send_mail # 阶段 1.3.2 告警时再引入

# 获取一个名为 "worker" 的 logger，日志将写入 logs/worker.log 并按天切分
logger = get_logger("worker")

def task_wrapper(func):
    """
    一个通用的任务包装器，用于日志记录和异常处理。
    """
    @functools.wraps(func) # 保持原函数的元数据，方便调试和内省
    def wrapped(*args, **kwargs):
        # 尝试从 kwargs 中获取 job_id，用于日志追踪
        job_id = kwargs.get('job_id', 'unknown_job') 
        task_name = func.__name__

        # 注意：日志中不再手动添加时间戳，因为 logger 的 formatter 会自动处理 %(asctime)s
        logger.info(f"[TASK START] {task_name} (ID: {job_id})")
        
        try:
            result = func(*args, **kwargs)
            logger.info(f"[TASK SUCCESS] {task_name} (ID: {job_id})")
            return result
        except Exception as e:
            # 重新抛出异常，让 RQ 能够捕获并处理重试
            # 在阶段 1.3.2，我们还会在这里添加最终失败的告警逻辑
            logger.error(f"[TASK FAIL] {task_name} (ID: {job_id}) - {e}", exc_info=True)
            raise e # 必须抛出异常才能触发 RQ 的重试机制和失败处理
    return wrapped