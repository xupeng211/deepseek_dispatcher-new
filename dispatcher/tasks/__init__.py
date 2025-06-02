# dispatcher/tasks/__init__.py

from .inference_task import InferenceTask, execute_task  # <--- **这里已修改：添加了 `, execute_task`**

TASK_REGISTRY = {
    "inference": InferenceTask,  # 简化的任务类型标识
}