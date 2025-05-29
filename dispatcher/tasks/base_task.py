# dispatcher/tasks/base_task.py

import logging
import functools # 新增导入
from datetime import datetime # 新增导入

logger = logging.getLogger(__name__)

def task_wrapper(func):
    @functools.wraps(func) # 添加这一行
    def wrapped(*args, **kwargs):
        # 尝试从 kwargs 中获取 job_id，用于日志追踪
        job_id = kwargs.get('job_id', 'unknown_job') 
        task_name = func.__name__

        logger.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [TASK START] {task_name} (ID: {job_id})")
        
        try:
            result = func(*args, **kwargs)
            logger.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [TASK SUCCESS] {task_name} (ID: {job_id})")
            return result
        except Exception as e:
            # 重新抛出异常，让 RQ 能够捕获并处理重试
            logger.error(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [TASK FAIL] {task_name} (ID: {job_id}) - {e}", exc_info=True)
            raise e # 必须抛出异常才能触发重试
    return wrapped
