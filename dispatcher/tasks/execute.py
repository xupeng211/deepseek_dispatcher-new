from dispatcher.core.base import BaseTask
from dispatcher.tasks import TASK_REGISTRY

def execute_task(task_type: str, task_id: str, payload: dict) -> dict:
    """
    RQ Worker实际执行的通用入口
    """
    if task_type not in TASK_REGISTRY:
        raise ValueError(f"未注册的任务类型: {task_type}")
    
    task_class = TASK_REGISTRY[task_type]
    task_instance: BaseTask = task_class(task_id=task_id, payload=payload)
    
    try:
        return task_instance.run()
    except Exception as e:
        return {
            "task_id": task_id,
            "status": "failed",
            "error": str(e)
        }
