# ai_executor/factory.py
from ai_executor.exceptions import ModelExecutionError
from ai_executor.dashscope import DashScopeExecutor
from ai_executor.deepseek import DeepSeekExecutor
# 假设 config.settings 存在并包含以下配置
# from config.settings import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, MODEL_NAME, MODEL_PARAMS

# 为了代码的可运行性，这里提供一个简化的占位符配置
class MockSettings:
    DASHSCOPE_API_KEY = "your-dashscope-key"
    DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    MODEL_NAME = "qwen-turbo"
    MODEL_PARAMS = {"temperature": 0.7}

config_settings = MockSettings() # 在实际项目中，您应该从 config.settings 导入

class ExecutorFactory:
    """执行器工厂（管理多模型，支持自动降级）"""

    def __init__(self):
        self.executors = [
            DashScopeExecutor(
                api_key=config_settings.DASHSCOPE_API_KEY,
                base_url=config_settings.DASHSCOPE_BASE_URL,
                model=config_settings.MODEL_NAME,
                params=config_settings.MODEL_PARAMS
            ),
            DeepSeekExecutor(api_key="your-deepseek-key"),
            # 后续扩展 OpenAIExecutor...
        ]

    def run(self, prompt: str) -> str:
        for executor in self.executors:
            try:
                return executor.run(prompt)
            except ModelExecutionError as e:
                print(f"[Fallback] 模型 {type(executor).__name__} 失败: {str(e)}")
                continue
        raise ModelExecutionError("所有模型执行失败")
