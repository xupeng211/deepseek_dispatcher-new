# ~/projects/deepseek_dispatcher-new/ai_executor/executor.py

import requests
from typing import Optional, Any, Dict
from abc import ABC, abstractmethod # 导入抽象基类
from common.logging_utils import get_logger

# 引入配置
from config.settings import settings

logger = get_logger("executor")

class ModelExecutionError(Exception):
    """自定义模型执行错误异常"""
    pass

class BaseExecutor(ABC):
    """
    所有AI模型执行器的抽象基类。
    定义了执行AI推理的通用接口。
    """
    def __init__(self, model_name: str, temperature: float, top_p: float, max_tokens: int):
        self.model_name = model_name
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        logger.debug(f"初始化 BaseExecutor，模型: {model_name}, 温度: {temperature}, Top P: {top_p}, Max Tokens: {max_tokens}")

    @abstractmethod
    def execute(self, prompt: str) -> str:
        """
        抽象方法：执行AI推理并返回结果。
        所有子类必须实现此方法。
        """
        pass


class DeepSeekExecutor(BaseExecutor):
    """DeepSeek 模型执行器（通过 API 调用）"""
    def __init__(self, api_key: str, model_name: str, temperature: float, top_p: float, max_tokens: int):
        super().__init__(model_name, temperature, top_p, max_tokens)
        self.api_key = api_key
        # DeepSeek API 的基础 URL 保持硬编码，因为它通常是固定的
        self.base_url = "https://api.deepseek.com/v1/chat/completions" 
        
        if not self.api_key:
            logger.error("DeepSeek API Key 未设置，模型调用将失败。")
            raise ValueError("DeepSeek API Key 必须设置。")
        logger.info(f"DeepSeekExecutor 初始化，模型: {self.model_name}, Base URL: {self.base_url}")

    def execute(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens # 传入 max_tokens
        }
        logger.debug(f"向 DeepSeek API 发送请求，prompt 长度: {len(prompt)}")
        try:
            resp = requests.post(self.base_url, json=payload, headers=headers, timeout=settings.TASK_JOB_TIMEOUT) # 使用配置的超时时间
            resp.raise_for_status()  # 如果请求失败 (状态码 4xx 或 5xx)，会抛出 HTTPError
            response_content = resp.json()["choices"][0]["message"]["content"]
            logger.info("DeepSeek API 请求成功，返回内容长度: %d", len(response_content))
            return response_content
        except requests.exceptions.Timeout as e:
            logger.error(f"DeepSeek API 请求超时: {e}", exc_info=True)
            raise ModelExecutionError(f"DeepSeek API 请求超时: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API 请求失败: {e}", exc_info=True)
            raise ModelExecutionError(f"DeepSeek API 请求失败: {str(e)}")
        except (KeyError, IndexError) as e:
            logger.error(f"DeepSeek API 响应格式错误: {e}. 原始响应: {resp.text if 'resp' in locals() else 'N/A'}", exc_info=True)
            raise ModelExecutionError(f"DeepSeek API 响应格式错误: {str(e)}")
        except Exception as e:
            logger.critical(f"DeepSeek 执行器发生未知错误: {e}", exc_info=True)
            raise ModelExecutionError(f"DeepSeek 执行器发生未知错误: {str(e)}")


class DashScopeExecutor(BaseExecutor):
    """DashScope (阿里云) 模型执行器（通过 API 调用）"""
    def __init__(self, api_key: str, base_url: str, model_name: str, temperature: float, top_p: float, max_tokens: int):
        super().__init__(model_name, temperature, top_p, max_tokens)
        self.api_key = api_key
        self.base_url = base_url # DashScope 的 Base URL 可以从配置中读取
        
        if not self.api_key:
            logger.error("DashScope API Key 未设置，模型调用将失败。")
            raise ValueError("DashScope API Key 必须设置。")
        logger.info(f"DashScopeExecutor 初始化，模型: {self.model_name}, Base URL: {self.base_url}")

    def execute(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens # 传入 max_tokens
        }
        logger.debug(f"向 DashScope API 发送请求，prompt 长度: {len(prompt)}")
        try:
            resp = requests.post(self.base_url, json=payload, headers=headers, timeout=settings.TASK_JOB_TIMEOUT) # 使用配置的超时时间
            resp.raise_for_status()
            response_content = resp.json()["output"]["choices"][0]["message"]["content"]
            logger.info("DashScope API 请求成功，返回内容长度: %d", len(response_content))
            return response_content
        except requests.exceptions.Timeout as e:
            logger.error(f"DashScope API 请求超时: {e}", exc_info=True)
            raise ModelExecutionError(f"DashScope API 请求超时: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"DashScope API 请求失败: {e}", exc_info=True)
            raise ModelExecutionError(f"DashScope API 请求失败: {str(e)}")
        except (KeyError, IndexError, TypeError) as e: # 捕获解析响应时可能发生的错误
            logger.error(f"DashScope API 响应格式错误: {e}. 原始响应: {resp.text if 'resp' in locals() else 'N/A'}", exc_info=True)
            raise ModelExecutionError(f"DashScope API 响应格式错误: {str(e)}")
        except Exception as e:
            logger.critical(f"DashScope 执行器发生未知错误: {e}", exc_info=True)
            raise ModelExecutionError(f"DashScope 执行器发生未知错误: {str(e)}")


class MockExecutor(BaseExecutor):
    """模拟执行器，用于测试和无真实API时的占位。"""
    def __init__(self, model_name: str = "mock-model", temperature: float = 0.7, top_p: float = 0.8, max_tokens: int = 100):
        super().__init__(model_name, temperature, top_p, max_tokens)
        logger.info("MockExecutor 已初始化。")

    def execute(self, prompt: str) -> str:
        logger.info(f"MockExecutor 正在模拟执行推理，prompt 长度: {len(prompt)}")
        # 模拟一些处理时间
        import time
        time.sleep(1)
        # 返回一个模拟的响应
        return f"这是 MockExecutor 对您的 prompt: '{prompt[:50]}...' 的模拟响应。您请求的 max_tokens: {self.max_tokens}。"

