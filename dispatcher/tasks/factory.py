# ~/projects/deepseek_dispatcher-new/dispatcher/tasks/factory.py

from typing import Dict, Type, Callable, Any
# 修正导入：现在从 dispatcher.tasks.inference_task 导入的是 InferenceTask 类
from dispatcher.tasks.inference_task import InferenceTask

# 引入我们统一的日志工具
from common.logging_utils import get_logger
# 引入配置，现在导入 settings 对象本身 (用于实例化需要参数的任务类，例如 InferenceTask)
from config.settings import settings

logger = get_logger("task_factory")

class TaskFactory:
    # 修正：将 _registered_tasks 声明为类属性，并且直接在类中初始化
    # 现在存储的是任务类 (Type[Any])，而不是直接的 callable 函数
    _registered_tasks: Dict[str, Type[Any]] = {}

    def __init__(self):
        # 确保在工厂初始化时注册任务，避免重复注册
        if not TaskFactory._registered_tasks: # 检查是否已经注册过
            self._register_tasks()
        logger.info("TaskFactory 初始化。")

    @classmethod
    def register_task(cls, task_type: str, task_class: Type[Any]): # 接受任务类 Type
        """
        注册一个任务类到工厂。
        """
        if task_type in cls._registered_tasks:
            logger.warning(f"任务类型 '{task_type}' 已经被注册，将被覆盖。")
        cls._registered_tasks[task_type] = task_class # 注册任务类
        logger.debug(f"已注册任务类型: '{task_type}'")

    def _register_tasks(self):
        """
        内部方法：在这里注册所有可用的任务类。
        """
        # 修正：注册 InferenceTask 类
        # 这里的 "inference_task" 应该是你的 API 传入的任务类型字符串
        self.register_task("inference_task", InferenceTask)
        # 如果有其他任务类型，可以在这里继续注册
        logger.info("所有任务已注册到 TaskFactory。")

    @classmethod # 将方法改为类方法
    def get_task_callable(cls, task_type: str) -> Callable[..., Any]:
        """
        根据任务类型获取对应的任务实例的执行方法。
        此方法会在内部实例化任务类并返回其 execute 方法。
        Args:
            task_type: 任务类型字符串 (例如: "inference_task")。
        Returns:
            任务实例的 execute 方法 (一个可调用对象)。
        Raises:
            ValueError: 如果任务类型未知或任务实例化失败。
            TypeError: 如果任务类没有实现 execute 方法。
        """
        task_class = cls._registered_tasks.get(task_type)
        if not task_class:
            logger.error(f"未知的任务类型: '{task_type}'")
            raise ValueError(f"未知的任务类型: {task_type}")

        task_instance = None
        try:
            # 根据任务类型实例化任务类
            if task_type == "inference_task":
                # InferenceTask 的构造函数需要 model_name
                # 从 settings 中获取 MODEL_NAME
                model_name = settings.MODEL_NAME
                task_instance = task_class(model_name=model_name)
            else:
                # 对于其他任务，尝试通用实例化 (如果 __init__ 允许无参数)
                task_instance = task_class()
        except Exception as e:
            logger.error(f"任务类 '{task_type}' 实例化失败: {e}. 请检查构造函数参数。", exc_info=True)
            raise ValueError(f"任务类 '{task_type}' 实例化失败。") from e

        # 确保实例具有可执行的 'execute' 方法
        if not hasattr(task_instance, 'execute') or not callable(getattr(task_instance, 'execute')):
            logger.error(f"任务类 '{task_type}' 的实例没有可执行的 'execute' 方法。")
            raise TypeError(f"任务类 '{task_type}' 的实例没有可执行的 'execute' 方法。")

        # 返回实例化后的任务对象的 execute 方法
        return task_instance.execute

    @property
    def TASK_REGISTRY(self) -> Dict[str, Type[Any]]:
        return self._registered_tasks
