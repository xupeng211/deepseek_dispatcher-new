# ~/projects/deepseek_dispatcher-new/services/ai_service.py

from ai_executor.factory import ExecutorFactory
from services.exceptions import ServiceExecutionError
from common.logging_utils import get_logger
# 不需要直接导入 settings，因为 ExecutorFactory 内部已经处理了
# from config.settings import settings # 这一行不需要，如果存在请删除

logger = get_logger("ai_service")

class AIService:
    """
    提供AI推理服务，负责选择合适的AI模型执行器并执行推理。
    """

    def __init__(self):
        # 初始化 ExecutorFactory，它会根据配置选择可用的执行器
        self.executor_factory = ExecutorFactory()
        logger.info("AIService 已初始化。")

    def execute(self, query: str, model_name: str = None) -> str:
        """
        执行AI推理。
        Args:
            query (str): 输入给AI模型的查询文本。
            model_name (str, optional): 指定要使用的模型名称。如果为None，则使用默认/可用模型。
        Returns:
            str: AI模型的推理结果。
        Raises:
            ServiceExecutionError: 如果推理失败。
        """
        logger.info(f"AIService 接收到查询: '{query[:50]}...' (长度: {len(query)})")
        try:
            # 通过 ExecutorFactory 获取并运行合适的执行器
            # model_name 参数现在传递给 factory.run
            result = self.executor_factory.run(query, model_name=model_name) 
            logger.info("AIService 推理执行成功。")
            return result
        except ServiceExecutionError as e:
            logger.error(f"AIService 推理失败: {e}", exc_info=True)
            raise ServiceExecutionError(f"AI 服务执行失败: {str(e)}")
        except Exception as e:
            logger.critical(f"AIService 发生意外错误: {e}", exc_info=True)
            raise ServiceExecutionError(f"AI 服务发生意外错误: {str(e)}")

