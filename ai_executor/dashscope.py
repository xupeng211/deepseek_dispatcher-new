# ai_executor/dashscope.py
import openai  # 确保 openai 库已安装
from ai_executor.base import BaseExecutor  # 确保从正确的路径导入
from ai_executor.executor import ModelExecutionError  # 确保从正确的路径导入


class DashScopeExecutor(BaseExecutor):
    """DashScope 执行器（兼容 OpenAI SDK）"""

    def __init__(self, api_key: str, base_url: str, model: str, params: dict):
        # 注意：如果使用的是 openai v1.x.x 以上版本，初始化方式如下
        # 如果是旧版本 (e.g., 0.28.x)，初始化方式可能是 openai.api_key = api_key 等
        # 这里假设是较新版本的 OpenAI SDK
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.params = params  # e.g. {"temperature": 0.7, "max_tokens": 1000}

    def run(self, prompt: str) -> str:
        try:
            resp = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                **self.params  # 将预设的参数解包传入
            )
            # 假设 resp.choices[0].message.content 总是存在且有效
            # 在实际生产中，可能需要更健壮的检查
            if resp.choices and resp.choices[0].message:
                return resp.choices[0].message.content
            else:
                raise ModelExecutionError("DashScope API 响应格式不完整或 choices 为空")
        except openai.APIError as e:  # 捕获 OpenAI SDK 特有的 API 错误
            raise ModelExecutionError(f"DashScope API 调用失败 (OpenAI SDK): {str(e)}")
        except Exception as e:  # 其他所有意外错误
            # 考虑记录原始异常类型 e.__class__.__name__
            raise ModelExecutionError(f"DashScope 执行器发生未知错误: {str(e)}")

