# tests/ai_executor_tests/test_ai_executor.py
import unittest
# 假设你的 ai_executor 模块可以在测试环境中被正确导入
from ai_executor.base import BaseExecutor
from ai_executor.deepseek import DeepSeekExecutor
from ai_executor.dashscope import DashScopeExecutor
from ai_executor.factory import ExecutorFactory
from ai_executor.exceptions import ModelExecutionError

# 模拟一个 BaseExecutor，用于测试工厂的降级逻辑
class MockExecutor(BaseExecutor):
    def __init__(self, should_fail: bool = False, fail_message: str = "Mock failure"):
        self._should_fail = should_fail
        self._fail_message = fail_message

    def run(self, prompt: str) -> str:
        if self._should_fail:
            raise ModelExecutionError(self._fail_message)
        return f"Mock response for: {prompt}"

class TestAIExecutor(unittest.TestCase):

    # 这个测试用例需要一个有效的 DeepSeek API Key
    # 在实际项目中，你应该使用环境变量或配置文件来管理 API Key
    # 或者在测试环境中mock掉外部API调用
    def test_deepseek_executor_success(self):
        # 这是一个示例，你需要替换为有效的 DeepSeek API Key
        # 为了避免真实API调用，通常会在这里使用mocking库
        # api_key = "YOUR_DEEPSEEK_API_KEY"
        # if api_key != "YOUR_DEEPSEEK_API_KEY": # 避免用占位符去调用
        #     executor = DeepSeekExecutor(api_key=api_key)
        #     response = executor.run("Hello, what is your name?")
        #     self.assertIsInstance(response, str)
        #     self.assertGreater(len(response), 0)
        print("\nSkipping live DeepSeek API test. Please uncomment and provide a valid API key to run.")
        pass # 暂时跳过，避免没有API Key导致测试失败

    def test_executor_factory_fallback(self):
        # 模拟第一个执行器失败，第二个执行器成功
        mock_failing_executor = MockExecutor(should_fail=True, fail_message="First executor always fails")
        mock_successful_executor = MockExecutor(should_fail=False)

        # 临时替换工厂的执行器列表
        original_executors = ExecutorFactory().executors # 备份原有执行器
        ExecutorFactory().executors = [mock_failing_executor, mock_successful_executor]

        factory = ExecutorFactory()
        prompt = "Test fallback mechanism"
        response = factory.run(prompt)

        self.assertEqual(response, "Mock response for: Test fallback mechanism")
        # 恢复原有执行器，避免影响其他测试
        ExecutorFactory().executors = original_executors

    def test_executor_factory_all_fail(self):
        # 模拟所有执行器都失败
        mock_failing_executor1 = MockExecutor(should_fail=True, fail_message="Executor 1 fails")
        mock_failing_executor2 = MockExecutor(should_fail=True, fail_message="Executor 2 fails")

        original_executors = ExecutorFactory().executors # 备份原有执行器
        ExecutorFactory().executors = [mock_failing_executor1, mock_failing_executor2]

        factory = ExecutorFactory()
        prompt = "Test all fail scenario"
        
        with self.assertRaises(ModelExecutionError) as cm:
            factory.run(prompt)
        
        self.assertIn("所有模型执行失败", str(cm.exception))
        # 恢复原有执行器
        ExecutorFactory().executors = original_executors

if __name__ == '__main__':
    unittest.main()
