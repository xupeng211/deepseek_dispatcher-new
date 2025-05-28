# ai_executor/exceptions.py
class ModelExecutionError(Exception):
    """模型执行异常基类（所有执行器异常需封装为此类）"""
    pass