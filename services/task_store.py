from services.base import BaseService

class InMemoryTaskStore(BaseService):
    def __init__(self):
        self.store = {}

    def execute(self, task_id: str, result: str):
        self.store[task_id] = result

    def get_result(self, task_id: str):
        return self.store.get(task_id, "无结果")