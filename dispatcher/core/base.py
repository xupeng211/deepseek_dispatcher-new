from abc import ABC, abstractmethod

class BaseTask(ABC):
    """所有任务的抽象基类，定义通用接口"""
    
    def __init__(self, task_id: str, payload: dict):
        self.task_id = task_id
        self.payload = payload

    @abstractmethod
    def run(self) -> dict:
        """执行任务主逻辑"""
        pass

    def to_dict(self) -> dict:
        """序列化任务信息"""
        return {
            "task_id": self.task_id,
            "payload": self.payload,
            "type": self.__class__.__name__
        }
