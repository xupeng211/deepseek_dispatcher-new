# ~/projects/deepseek_dispatcher-new/ai_executor/factory.py

# 导入 settings 实例，而不是整个 config.settings 模块
from config.settings import settings
# 从 ai_executor.executor 导入具体的执行器类和 ModelExecutionError
from ai_executor.executor import BaseExecutor, DeepSeekExecutor, DashScopeExecutor, MockExecutor, ModelExecutionError
from services.exceptions import ServiceExecutionError # ServiceExecutionError 也可能用到
from common.logging_utils import get_logger

logger = get_logger("ai_executor")

class ExecutorFactory:
    """
    负责创建和管理不同AI模型的执行器。
    通过配置自动选择合适的执行器，并提供API密钥等参数。
    """

    def __init__(self):
        self.executors: Dict[str, BaseExecutor] = {} # 明确类型提示
        # 根据配置文件初始化各种执行器
        if settings.DASHSCOPE_API_KEY:
            self.executors['dashscope'] = DashScopeExecutor(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url=settings.DASHSCOPE_BASE_URL,
                model_name=settings.MODEL_NAME, # 使用统一的 MODEL_NAME
                temperature=settings.MODEL_TEMPERATURE,
                top_p=settings.MODEL_TOP_P,
                max_tokens=settings.MODEL_MAX_TOKENS # 使用统一的 MODEL_MAX_TOKENS
            )
            logger.info("DashScope Executor 已初始化。")

        if settings.DEEPSEEK_API_KEY:
            self.executors['deepseek'] = DeepSeekExecutor(
                api_key=settings.DEEPSEEK_API_KEY,
                model_name=settings.MODEL_NAME, # 使用统一的 MODEL_NAME
                temperature=settings.MODEL_TEMPERATURE,
                top_p=settings.MODEL_TOP_P,
                max_tokens=settings.MODEL_MAX_TOKENS # 使用统一的 MODEL_MAX_TOKENS
            )
            logger.info("DeepSeek Executor 已初始化。")

        if not self.executors:
            # 如果没有配置任何真实模型，则使用 MockExecutor
            self.executors['mock'] = MockExecutor(
                model_name=settings.MODEL_NAME, # 保持与 settings 一致
                temperature=settings.MODEL_TEMPERATURE,
                top_p=settings.MODEL_TOP_P,
                max_tokens=settings.MODEL_MAX_TOKENS
            )
            logger.warning("未配置任何大模型API密钥，使用 Mock Executor。请在 .env 文件中设置 DASHSCOPE_API_KEY 或 DEEPSEEK_API_KEY。")

    def get_executor(self, model_name: str = None) -> BaseExecutor:
        """
        根据模型名称获取对应的执行器。
        如果未指定模型或指定模型不可用，则尝试按顺序返回可用的执行器。
        """
        if model_name and model_name in self.executors:
            logger.debug(f"使用指定的模型执行器: {model_name}")
            return self.executors[model_name]

        # 尝试返回默认（优先 DeepSeek，其次 DashScope，最后 Mock）
        if 'deepseek' in self.executors:
            logger.debug("使用 DeepSeek Executor (默认)。")
            return self.executors['deepseek']
        elif 'dashscope' in self.executors:
            logger.debug("使用 DashScope Executor (默认)。")
            return self.executors['dashscope']
        elif 'mock' in self.executors:
            logger.warning("使用 Mock Executor (无可用真实模型)。")
            return self.executors['mock']
        
        logger.error("没有可用的模型执行器。")
        raise ServiceExecutionError("没有可用的模型执行器。请检查 API 密钥配置。")

    def run(self, prompt: str, model_name: str = None) -> str:
        """
        使用选择的执行器运行推理。
        """
        executor = self.get_executor(model_name)
        logger.info(f"正在使用模型执行器: {executor.__class__.__name__} (模型: {executor.model_name}) 进行推理，prompt 长度: {len(prompt)}")
        try:
            return executor.execute(prompt)
        except ModelExecutionError as e:
            logger.error(f"模型执行错误: {e}", exc_info=True)
            raise ServiceExecutionError(f"模型执行错误: {str(e)}") # 转换为服务层面的错误
        except Exception as e:
            logger.critical(f"执行器意外错误: {e}", exc_info=True)
            raise ServiceExecutionError(f"执行器发生意外错误: {str(e)}")

