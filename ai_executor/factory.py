# ai_executor/factory.py
from ai_executor.executor import ModelExecutionError
from ai_executor.dashscope import DashScopeExecutor
from ai_executor.deepseek import DeepSeekExecutor
# 导入你的真实配置，替换原来的 MockSettings
import config.settings # <--- 导入整个 settings 模块


class ExecutorFactory:
    """执行器工厂（管理多模型，支持自动降级）"""

    def __init__(self):
        # 将原来直接使用全局变量的方式，改为从 config.settings 模块中获取
        # 这样可以确保在工厂实例化时，settings 已经被正确加载（通过 .env）
        self.executors = [
            DashScopeExecutor(
                api_key=config.settings.DASHSCOPE_API_KEY, # 使用 config.settings.DASHSCOPE_API_KEY
                base_url=config.settings.DASHSCOPE_BASE_URL,
                model=config.settings.MODEL_NAME,
                params=config.settings.MODEL_PARAMS
            ),
            DeepSeekExecutor(api_key=config.settings.DEEPSEEK_API_KEY), # 使用 config.settings.DEEPSEEK_API_KEY
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