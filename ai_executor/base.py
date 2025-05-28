# ai_executor/base.py
from abc import ABC, abstractmethod


class BaseExecutor(ABC):
    """模型执行器抽象协议（所有执行器必须实现 run 方法）"""

    @abstractmethod
    def run(self, prompt: str) -> str:
        """核心执行方法：输入 prompt，返回模型生成结果"""
        raise NotImplementedError

