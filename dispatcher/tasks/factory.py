# ~/projects/deepseek_dispatcher-new/dispatcher/tasks/factory.py

from typing import Callable, Dict, Any
from dispatcher.tasks.inference_task import inference_task
from services.exceptions import ServiceExecutionError # Re-use the exception

# 引入我们新的日志工具
from common.logging_utils import get_logger
logger = get_logger("dispatcher") # Log to dispatcher log

class TaskFactory:
    """
    负责根据任务类型提供对应的可执行任务函数。
    """
    TASK_REGISTRY: Dict[str, Callable[..., Any]] = {
        "inference": inference_task, # 映射任务类型到实际的函数
        # 未来如果需要其他类型的任务，可以在这里添加，例如：
        # "embedding": embedding_task,
        # "translation": translation_task,
    }

    @classmethod
    def get_task_callable(cls, task_type: str) -> Callable[..., Any]:
        """
        根据任务类型获取对应的可执行函数。
        Args:
            task_type (str): 任务的类型标识符。
        Returns:
            Callable[..., Any]: 对应的任务函数。
        Raises:
            ServiceExecutionError: 如果任务类型未注册。
        """
        task_callable = cls.TASK_REGISTRY.get(task_type)
        if not task_callable:
            logger.error(f"未知的任务类型: {task_type}")
            raise ServiceExecutionError(f"未知的任务类型: {task_type}")
        logger.debug(f"获取任务函数: {task_type}")
        return task_callable
