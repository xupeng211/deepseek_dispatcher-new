# ~/projects/deepseek_dispatcher-new/dispatcher/tasks/__init__.py

# 这个 __init__.py 文件可以保持为空，
# 或者只包含 package-level 的声明，例如：
# __all__ = ["inference_task", "factory", "base_task"]

# 移除此处可能存在的对 InferenceTask 或 execute_task 的直接导入，
# 因为它们现在是通过 dispatcher.tasks.factory 间接使用的，
# 或者 inference_task.py 中不再有 InferenceTask 类。

