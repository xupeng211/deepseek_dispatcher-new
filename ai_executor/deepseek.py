# ai_executor/deepseek.py
import requests
from typing import Optional
from ai_executor.base import BaseExecutor # 确保从正确的路径导入
from ai_executor.exceptions import ModelExecutionError # 确保从正确的路径导入

class DeepSeekExecutor(BaseExecutor):
    """DeepSeek 模型执行器（通过 API 调用）"""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url or "https://api.deepseek.com/v1/chat/completions"

    def run(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": "deepseek-chat", # 注意这里的模型名称是硬编码的
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7 # 温度参数也是硬编码的
        }
        try:
            resp = requests.post(self.base_url, json=payload, headers=headers)
            resp.raise_for_status() # 如果请求失败 (状态码 4xx 或 5xx)，会抛出 HTTPError
            return resp.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e: # 更具体地捕获 requests 相关的异常
            raise ModelExecutionError(f"DeepSeek API 请求失败: {str(e)}")
        except (KeyError, IndexError) as e: # 捕获解析响应时可能发生的错误
            raise ModelExecutionError(f"DeepSeek API 响应格式错误: {str(e)}")
        except Exception as e: # 其他所有意外错误
            # 考虑记录原始异常类型 e.__class__.__name__
            raise ModelExecutionError(f"DeepSeek 执行器发生未知错误: {str(e)}")