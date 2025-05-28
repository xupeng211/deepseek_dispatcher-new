# ai_executor/factory.py
from ai_executor.exceptor import ModelExecutionError
from ai_executor.dashscope import DashScopeExecutor
from ai_executor.deepseek import DeepSeekExecutor
# 导入你的真实配置，替换原来的 MockSettings
from config.settings import (
    DASHSCOPE_API_KEY,
    DEEPSEEK_API_KEY,
    DASHSCOPE_BASE_URL,
    MODEL_NAME,
    MODEL_PARAMS
)


class ExecutorFactory:
    """执行器工厂（管理多模型，支持自动降级）"""

    def __init__(self):
        self.executors = [
            DashScopeExecutor(
                api_key=DASHSCOPE_API_KEY,
                base_url=DASHSCOPE_BASE_URL,
                model=MODEL_NAME,
                params=MODEL_PARAMS
            ),
            DeepSeekExecutor(api_key=DEEPSEEK_API_KEY),
            # 后续扩展 OpenAIExecutor...
        ]

    def run(self, prompt: str) -> str:
        for executor in self.executors:
            try:
                return executor.run(prompt)
            except ModelExecutionError as e:
                # 这里的 print 语句在单元测试中会被静默，但在实际运行中会输出
                print(f"[Fallback] 模型 {type(executor).__name__} 失败: {str(e)}")
                continue
        raise ModelExecutionError("所有模型执行失败")

