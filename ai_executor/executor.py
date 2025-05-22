# ai_executor/executor.py
import openai # 导入 openai 库，DashScope 兼容 OpenAI API
import os # 确保导入 os
from typing import Dict, Any # 确保导入 Dict, Any
import logging # 确保导入 logging

from config.settings import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, MODEL_NAME, MODEL_PARAMS
from logger.logger import get_logger

logger = get_logger("deepseek_dispatcher.ai_executor")

class AIExecutorError(Exception):
    """AI 模型执行相关异常"""
    pass

class AIExecutor:
    def __init__(self):
        # 从环境变量或配置文件获取 API Key 和 Base URL
        api_key = DASHSCOPE_API_KEY
        base_url = DASHSCOPE_BASE_URL

        if not api_key:
            raise AIExecutorError("DASHSCOPE_API_KEY is not set in environment variables.")
        if not base_url:
            raise AIExecutorError("DASHSCOPE_BASE_URL is not set in environment variables.")

        try:
            # 初始化 OpenAI 客户端，指向 DashScope API
            # 确认这里没有 'proxies' 参数
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url,
            )
            logger.info("AIExecutor 已初始化，连接到 DashScope API。")
        except Exception as e:
            logger.error(f"初始化 AIExecutor 失败: {e}", exc_info=True)
            raise AIExecutorError(f"初始化 AIExecutor 失败: {e}") from e

    def generate_completion(self, messages: list[Dict[str, str]], **kwargs) -> str:
        """
        生成文本补全。
        Args:
            messages (list[Dict[str, str]]): 对话消息列表，例如 [{"role": "user", "content": "Hello"}]
            **kwargs: 额外的模型参数，如 max_tokens, temperature, top_p, model_name。
        Returns:
            str: 生成的文本。
        Raises:
            AIExecutorError: 模型调用失败时抛出。
        """
        model_name = kwargs.pop("model_name", MODEL_NAME)
        # 从 MODEL_PARAMS 获取默认值，并允许 kwargs 覆盖
        final_model_params = {
            "max_tokens": kwargs.pop("max_tokens", MODEL_PARAMS.get("max_tokens")),
            "temperature": kwargs.pop("temperature", MODEL_PARAMS.get("temperature")),
            "top_p": kwargs.pop("top_p", MODEL_PARAMS.get("top_p")),
        }
        # 确保 kwargs 中没有剩余的非标准参数
        if kwargs:
            logger.warning(f"检测到未使用的模型参数: {kwargs}")

        try:
            logger.info(f"调用 AI 模型: {model_name}, 消息: {messages[0]['content'][:50]}..., 参数: {final_model_params}")
            chat_completion = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                **final_model_params
            )
            response_content = chat_completion.choices[0].message.content
            logger.info(f"AI 模型调用成功，生成内容: {response_content[:100]}...")
            return response_content
        except openai.APIError as e:
            logger.error(f"调用 OpenAI API 失败: {e}", exc_info=True)
            raise AIExecutorError(f"AI API 调用失败: {e}") from e
        except Exception as e:
            logger.error(f"生成文本补全时发生未知错误: {e}", exc_info=True)
            raise AIExecutorError(f"生成文本补全时发生未知错误: {e}") from e
