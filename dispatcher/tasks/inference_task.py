# dispatcher/tasks/inference_task.py

from dispatcher.core.base import BaseTask
from ai_executor.factory import ExecutorFactory
from ai_executor.executor import ModelExecutionError  # 导入您定义的异常类
from typing import Dict, Any # 新增：导入Dict和Any用于execute_task的类型提示


class InferenceTask(BaseTask):
    """AI推理任务（替换原有generate_text_task）"""

    def run(self) -> dict:
        # 从 payload 中提取任务数据和追踪 ID
        task_data = self.payload.get("task_data", {})
        trace_id = self.payload.get("trace_id", "")

        # 从 task_data 提取 prompt
        prompt = task_data.get("prompt", "")

        # model_kwargs 在当前重构中不会直接传递给 executor.run()。
        # 它们应该在 ExecutorFactory 初始化时（通过 config.settings）
        # 传递给具体的执行器（如 DashScopeExecutor 的 params 参数）。
        # 如果未来需要动态地在运行时根据 payload 调整模型参数，
        # 则 BaseExecutor.run 接口或 ExecutorFactory 需要进一步设计来支持。
        # 这里保留提取，以防未来扩展或用于日志记录。
        # F841: local variable 'model_kwargs' is assigned to but never used
        model_kwargs = task_data.get("model_kwargs", {})  # noqa: F841

        # 初始化执行器工厂
        executor_factory = ExecutorFactory()

        result = ""
        status = "failed"  # 默认状态为失败

        try:
            # 使用 ExecutorFactory 执行推理，这会尝试多个模型并自动降级
            result = executor_factory.run(prompt)
            status = "success"  # 成功则更新状态
        except ModelExecutionError as e:
            # 捕获模型执行异常，记录错误信息并设置状态
            print(f"[ERROR] Inference task failed for prompt '{prompt}': {str(e)}")
            result = f"模型推理失败: {str(e)}"
            status = "error"  # 或者您可以定义更具体的错误状态码
        except Exception as e:
            # 捕获其他未知异常
            print(f"[CRITICAL] Unexpected error during inference task for prompt '{prompt}': {str(e)}")
            result = f"任务执行过程中发生未知错误: {str(e)}"
            status = "critical_error"

        return {
            "task_id": self.task_id,
            "trace_id": trace_id,
            "result": result,
            "status": status  # 根据执行结果返回最终状态
        }

# --- 新增的 execute_task 函数 ---
def execute_task(task_type: str, job_id: str, payload: Dict[str, Any]):
    """
    根据任务类型执行具体的任务。
    这个函数将被 RQ worker 调用。
    它负责实例化并运行 InferenceTask。
    """
    # 这里假设我们只处理 "inference" 类型的任务
    if task_type == "inference":
        # 实例化 InferenceTask，并传递 job_id 和 payload
        # BaseTask 的 __init__ 预期接收 job_id 和 payload
        inference_task = InferenceTask(job_id=job_id, payload=payload)
        task_result = inference_task.run()
        print(f"任务执行完成 | TaskID: {job_id} | Type: {task_type} | Status: {task_result['status']}")
        return task_result
    else:
        error_msg = f"未知的任务类型: {task_type}"
        print(f"[ERROR] {error_msg}")
        return {"task_id": job_id, "status": "failed", "error": error_msg}