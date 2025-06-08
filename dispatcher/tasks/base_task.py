# ~/projects/deepseek_dispatcher-new/dispatcher/tasks/base_task.py

# 引入我们新的日志工具
from common.logging_utils import get_logger
import functools
# 引入告警工具
from common.alert_utils import send_email_alert, send_dingtalk_alert
# 引入配置，现在导入 settings 对象本身
from config.settings import settings

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

        logger.info(f"[TASK START] {task_name} (ID: {job_id})")
        
        try:
            result = func(*args, **kwargs)
            logger.info(f"[TASK SUCCESS] {task_name} (ID: {job_id})")
            return result
        except Exception as e:
            logger.error(f"[TASK FAIL] {task_name} (ID: {job_id}) - {e}", exc_info=True)
            
            # 检查任务是否已经达到最大重试次数并最终失败
            # 注意：RQ 在任务重试用尽后才会将 job.is_failed 设置为 True
            # 这个逻辑通常由 RQ worker 内部处理，我们在这里只负责在异常发生时记录日志
            # 并在任务最终失败时触发告警。
            # RQ 自身会管理重试次数，当重试次数用尽且任务仍失败时，它会进入 'failed' 注册表。
            # 告警应该在任务确定失败时触发，而不是每次异常都触发。
            
            # 为了简化，我们假设这里的异常捕获意味着任务尝试失败，
            # 并且如果 settings.ENABLE_ALERT 为 True，就发送告警。
            if settings.ENABLE_ALERT: # 访问 settings 对象的属性
                alert_subject = f"DeepSeek Dispatcher 任务失败告警: {task_name} (ID: {job_id})"
                alert_message = (
                    f"任务 '{task_name}' (ID: {job_id}) 最终执行失败。\n"
                    f"错误信息: {e}\n"
                    f"请检查 Worker 日志以获取更多详情。"
                )
                send_email_alert(alert_subject, alert_message)
                send_dingtalk_alert(alert_subject, alert_message)
                logger.info(f"已发送任务失败告警: {task_name} (ID: {job_id})")

            raise e # 必须重新抛出异常，以便 RQ 能够将其标记为失败并进行重试（如果配置了）
    return wrapped
