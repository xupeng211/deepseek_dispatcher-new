import openai
import os
from typing import Dict, Any, List, Optional # 导入 Optional

from config.settings import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, MODEL_NAME, MODEL_PARAMS
from logger.logger import get_logger

logger = get_logger("deepseek_dispatcher.ai_executor")

class AIExecutorError(Exception):
    """AI 模型执行相关异常"""
    pass

class AIExecutor:
    def __init__(self) -> None:
        """
        初始化 AIExecutor，配置 OpenAI 客户端以连接到 DashScope API。
        Raises:
            AIExecutorError: 当 DASHSCOPE_API_KEY 或 DASHSCOPE_BASE_URL 未设置时抛出。
        """
        api_key: Optional[str] = DASHSCOPE_API_KEY
        base_url: Optional[str] = DASHSCOPE_BASE_URL

        if not api_key:
            raise AIExecutorError("DASHSCOPE_API_KEY is not set in environment variables.")
        if not base_url:
            raise AIExecutorError("DASHSCOPE_BASE_URL is not set in environment variables.")

        try:
            # 初始化 OpenAI 客户端，指向 DashScope API
            # 移除了 'proxies=None' 参数，因为当前 openai 库版本不接受此参数。
            # 由于底层网络问题已解决，不再需要在此处显式配置代理。
            self.client: openai.OpenAI = openai.OpenAI(
                api_key=api_key,
                base_url=base_url,
            )
            logger.info("AIExecutor 已初始化，连接到 DashScope API。")
        except Exception as e:
            logger.error(f"初始化 AIExecutor 失败: {e}", exc_info=True)
            raise AIExecutorError(f"初始化 AIExecutor 失败: {e}") from e

    def generate_completion(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """
        生成文本补全。
        Args:
            messages (List[Dict[str, str]]): 对话消息列表，例如 [{"role": "user", "content": "Hello"}]。
            **kwargs (Any): 额外的模型参数，如 max_tokens, temperature, top_p, model_name。
                            这些参数会覆盖 MODEL_PARAMS 中的默认值。
        Returns:
            str: 生成的文本。
        Raises:
            AIExecutorError: 模型调用失败时抛出。
        """
        model_name: str = kwargs.pop("model_name", MODEL_NAME)

        # 从 MODEL_PARAMS 获取默认值，并允许 kwargs 覆盖
        final_model_params: Dict[str, Any] = {
            "max_tokens": kwargs.pop("max_tokens", MODEL_PARAMS.get("max_tokens")),
            "temperature": kwargs.pop("temperature", MODEL_PARAMS.get("temperature")),
            "top_p": kwargs.pop("top_p", MODEL_PARAMS.get("top_p")),
        }

        # 移除 None 值的参数，因为有些模型 API 不接受 None 值作为参数
        final_model_params = {k: v for k, v in final_model_params.items() if v is not None}

        # 确保 kwargs 中没有剩余的非标准参数
        if kwargs:
            logger.warning(f"检测到未使用的模型参数: {kwargs}")

        try:
            # 记录消息内容的前50个字符，避免日志过长
            log_messages_preview: str = messages[0]['content'][:50] + "..." if messages and messages[0]['content'] else "无内容"
            logger.info(f"调用 AI 模型: {model_name}, 消息: {log_messages_preview}, 参数: {final_model_params}")

            chat_completion = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                **final_model_params
            )
            response_content: str = chat_completion.choices[0].message.content
            logger.info(f"AI 模型调用成功，生成内容: {response_content[:100]}...") # 记录前100个字符
            return response_content
        except openai.APIError as e:
            logger.error(f"调用 OpenAI API 失败: {e}", exc_info=True)
            raise AIExecutorError(f"AI API 调用失败: {e}") from e
        except Exception as e:
            logger.error(f"生成文本补全时发生未知错误: {e}", exc_info=True)
            raise AIExecutorError(f"生成文本补全时发生未知错误: {e}") from e