# ~/projects/deepseek_dispatcher-new/ai_executor/deepseek.py

import requests
from typing import Optional
from ai_executor.base import BaseExecutor
from ai_executor.executor import ModelExecutionError

# 引入我们新的日志工具
from common.logging_utils import get_logger
# 引入配置
from config.settings import settings

# 获取一个名为 "deepseek_executor" 的 logger
logger = get_logger("deepseek_executor")

class DeepSeekExecutor(BaseExecutor):
    """DeepSeek 模型执行器（通过 API 调用）"""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        # 从 settings 获取 API Key 和 Base URL
        self.api_key = api_key or settings.DEEPSEEK_API_KEY # 优先使用传入的，否则使用配置
        self.base_url = base_url or "https://api.deepseek.com/v1/chat/completions" # DeepSeek 的 Base URL 暂时保持硬编码，如果需要从配置中读取，可以在 settings 中添加 DEEPSEEK_BASE_URL
        if not self.api_key:
            logger.error("DeepSeek API Key 未设置，模型调用将失败。")
            raise ValueError("DeepSeek API Key 必须设置。")
        logger.info(f"DeepSeekExecutor 初始化，Base URL: {self.base_url}")

    def run(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": settings.MODEL_NAME,  # 从 settings 获取模型名称
            "messages": [{"role": "user", "content": prompt}],
            "temperature": settings.MODEL_TEMPERATURE,  # 从 settings 获取温度参数
            "top_p": settings.MODEL_TOP_P # 从 settings 获取 top_p 参数
        }
        logger.debug(f"向 DeepSeek API 发送请求，prompt 长度: {len(prompt)}")
        try:
            resp = requests.post(self.base_url, json=payload, headers=headers, timeout=60) # 增加超时设置
            resp.raise_for_status()  # 如果请求失败 (状态码 4xx 或 5xx)，会抛出 HTTPError
            response_content = resp.json()["choices"][0]["message"]["content"]
            logger.info("DeepSeek API 请求成功，返回内容长度: %d", len(response_content))
            return response_content
        except requests.exceptions.Timeout as e:
            logger.error(f"DeepSeek API 请求超时: {e}", exc_info=True)
            raise ModelExecutionError(f"DeepSeek API 请求超时: {str(e)}")
        except requests.exceptions.RequestException as e:  # 更具体地捕获 requests 相关的异常
            logger.error(f"DeepSeek API 请求失败: {e}", exc_info=True)
            raise ModelExecutionError(f"DeepSeek API 请求失败: {str(e)}")
        except (KeyError, IndexError) as e:  # 捕获解析响应时可能发生的错误
            logger.error(f"DeepSeek API 响应格式错误: {e}. 原始响应: {resp.text if 'resp' in locals() else 'N/A'}", exc_info=True)
            raise ModelExecutionError(f"DeepSeek API 响应格式错误: {str(e)}")
        except Exception as e:  # 其他所有意外错误
            logger.critical(f"DeepSeek 执行器发生未知错误: {e}", exc_info=True)
            raise ModelExecutionError(f"DeepSeek 执行器发生未知错误: {str(e)}")

