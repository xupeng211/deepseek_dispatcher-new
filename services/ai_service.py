from services.base import BaseService
from ai_executor.factory import ExecutorFactory
from services.exceptions import ServiceExecutionError

class AIService(BaseService):
    def __init__(self):
        self.executor = ExecutorFactory()

    def execute(self, query: str) -> str:
        try:
            return self.executor.run(query)
        except Exception as e:
            raise ServiceExecutionError(f"AIService 执行失败: {str(e)}")