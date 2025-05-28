# tests/ai_executor_tests/test_ai_executor.py
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
import sys

from ai_executor.base import BaseExecutor
from ai_executor.factory import ExecutorFactory
from ai_executor.exceptions import ModelExecutionError


class TestAIExecutor(unittest.TestCase):

    def setUp(self):
        # 捕获标准输出，以静默测试中的 print 语句
        self.held_stdout = sys.stdout
        sys.stdout = StringIO()

    def tearDown(self):
        # 恢复标准输出
        sys.stdout = self.held_stdout

    # 这个测试用例仍然跳过，因为它旨在进行真实的 API 调用，而我们现在专注于单元测试的隔离。
    def test_deepseek_executor_success(self):
        print("\nSkipping live DeepSeek API test (now handled by mocking in other tests).")
        pass

    # 关键修改：@patch 的目标是 ai_executor.factory 模块中导入的 DashScopeExecutor 和 DeepSeekExecutor
    # 使用 autospec=True 确保模拟对象具有与原始类相同的签名
    @patch('ai_executor.factory.DashScopeExecutor', autospec=True)
    @patch('ai_executor.factory.DeepSeekExecutor', autospec=True)
    def test_executor_factory_fallback(self, MockDeepSeekExecutorClass, MockDashScopeExecutorClass):
        # 配置模拟执行器实例的行为。
        # MockDashScopeExecutorClass.return_value 是当 ExecutorFactory 实例化 DashScopeExecutor 时会得到的对象。
        mock_dashscope_instance = MockDashScopeExecutorClass.return_value
        mock_dashscope_instance.run.side_effect = ModelExecutionError("Mocked failure from first executor")
        
        mock_deepseek_instance = MockDeepSeekExecutorClass.return_value
        mock_deepseek_instance.run.return_value = "Mock response from DeepSeek"
        
        # 实例化 ExecutorFactory。此时，它的 __init__ 将会使用我们上面 patch 过的类来创建执行器实例。
        factory = ExecutorFactory()
        
        prompt = "Test fallback mechanism"
        response = factory.run(prompt)
        
        # 验证结果
        self.assertEqual(response, "Mock response from DeepSeek")
        
        # 验证工厂是否尝试实例化了这些模拟类
        MockDashScopeExecutorClass.assert_called_once()
        MockDeepSeekExecutorClass.assert_called_once()

        # 验证模拟执行器实例的 run 方法是否被调用
        mock_dashscope_instance.run.assert_called_once_with(prompt)
        mock_deepseek_instance.run.assert_called_once_with(prompt)

    # 关键修改：@patch 的目标与上面一致
    @patch('ai_executor.factory.DashScopeExecutor', autospec=True)
    @patch('ai_executor.factory.DeepSeekExecutor', autospec=True)
    def test_executor_factory_all_fail(self, MockDeepSeekExecutorClass, MockDashScopeExecutorClass):
        # 配置两个模拟执行器实例都失败
        mock_dashscope_instance = MockDashScopeExecutorClass.return_value
        mock_dashscope_instance.run.side_effect = ModelExecutionError("Mocked failure from executor 1")
        
        mock_deepseek_instance = MockDeepSeekExecutorClass.return_value
        mock_deepseek_instance.run.side_effect = ModelExecutionError("Mocked failure from executor 2")
        
        # 实例化 ExecutorFactory
        factory = ExecutorFactory()
        
        prompt = "Test all fail scenario"
        
        # 验证异常抛出
        with self.assertRaises(ModelExecutionError) as context:
            factory.run(prompt)
        
        self.assertIn("所有模型执行失败", str(context.exception))
        
        # 验证工厂是否尝试实例化了这些模拟类
        MockDashScopeExecutorClass.assert_called_once()
        MockDeepSeekExecutorClass.assert_called_once()
        
        # 验证模拟执行器实例的 run 方法是否被调用
        mock_dashscope_instance.run.assert_called_once_with(prompt)
        mock_deepseek_instance.run.assert_called_once_with(prompt)

