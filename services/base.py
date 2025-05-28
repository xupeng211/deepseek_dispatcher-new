# services/base.py
from abc import ABC, abstractmethod


class BaseService(ABC):
    @abstractmethod
    def execute(self, *args, **kwargs):
        pass


class ServiceExecutionError(Exception):
    """业务服务执行错误"""
    pass

