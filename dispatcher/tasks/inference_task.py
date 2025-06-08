# ~/projects/deepseek_dispatcher-new/dispatcher/tasks/inference_task.py

from dispatcher.core.base import BaseTask
from ai_executor.factory import ExecutorFactory
from ai_executor.executor import ModelExecutionError  # 导入您定义的异常类
from typing import Dict, Any # 新增：导入Dict和Any用于execute_task的类型提示
from common.logging_utils import get_logger

logger = get_logger("inference_task")


class InferenceTask(BaseTask):
    """AI推理任务（替换原有generate_text_task）"""

    def run(self) -> dict:
        # 从 payload 中提取任务数据和追踪 ID
        task_data = self.payload.get("task_data", {})
        trace_id = self.payload.get("trace_id", "")
        model_name = self.payload.get("model_name", "default-model") # 从 payload 获取 model_name

        # 从 task_data 提取 prompt 和 model_kwargs
        prompt = task_data.get("prompt", "")
        model_kwargs = task_data.get("model_kwargs", {})

        # 初始化执行器工厂
        # ExecutorFactory 现在使用 settings 来获取 API Key 和 Base URL
        executor_factory = ExecutorFactory()

        result = ""
        status = "failed"  # 默认状态为失败
        error_message = None # 用于存储错误信息

        logger.info(f"开始执行推理任务 {self.task_id} (Trace ID: {trace_id})，模型: {model_name}, prompt 长度: {len(prompt)}")
        logger.debug(f"模型参数: {model_kwargs}")

        try:
            # 使用 ExecutorFactory 获取并执行推理
            # ExecutorFactory.get_executor 会根据 model_name 和 settings 返回合适的执行器
            # execute 方法将接收 prompt 和其他 model_kwargs
            # 这里的 model_kwargs 会被传递给 execute() 方法，用于覆盖默认的模型参数
            executor = executor_factory.get_executor(model_name, **model_kwargs)
            
            # 确保 execute 方法能够接收并处理 model_kwargs
            # 注意：BaseExecutor.execute 的签名是 execute(self, prompt: str) -> str
            # 如果要传递 model_kwargs，需要调整 execute 方法或在 executor_factory.get_executor 时注入
            # 在目前的 Executor 设计中，model_kwargs 应该在 ExecutorFactory 初始化时传递给具体执行器
            # 或通过其自身的 __init__ 方法设置。
            # 因此，这里的 execute(prompt) 是正确的调用方式，model_kwargs 已在 executor 初始化时处理。
            result = executor.execute(prompt)
            status = "finished"  # 成功则更新状态
            logger.info(f"推理任务 {self.task_id} 执行成功。")
        except ModelExecutionError as e:
            # 捕获模型执行异常，记录错误信息并设置状态
            logger.error(f"推理任务 {self.task_id} 失败 (ModelExecutionError): {str(e)}", exc_info=True)
            result = f"模型推理失败: {str(e)}"
            status = "failed"
            error_message = str(e)
        except Exception as e:
            # 捕获其他未知异常
            logger.critical(f"推理任务 {self.task_id} 过程中发生未知错误: {str(e)}", exc_info=True)
            result = f"任务执行过程中发生未知错误: {str(e)}"
            status = "failed"
            error_message = str(e)

        return {
            "task_id": self.task_id,
            "trace_id": trace_id,
            "result": result,
            "status": status,  # 根据执行结果返回最终状态
            "error": error_message # 包含错误信息
        }

# --- 新增的 execute_task 函数 ---
def execute_task(task_type: str, job_id: str, payload: Dict[str, Any]):
    """
    根据任务类型执行具体的任务。
    这个函数将被 RQ worker 调用。
    它负责实例化并运行 InferenceTask。
    """
    logger.info(f"RQ Worker 接收到任务: {job_id}, 类型: {task_type}")
    # 这里假设我们只处理 "inference" 类型的任务
    if task_type == "inference":
        # 实例化 InferenceTask，并传递 job_id 和 payload
        inference_task = InferenceTask(job_id=job_id, payload=payload)
        task_result = inference_task.run()
        logger.info(f"任务 {job_id} 执行完毕，状态: {task_result['status']}")
        return task_result
    else:
        logger.error(f"不支持的任务类型: {task_type} for job {job_id}")
        return {
            "task_id": job_id,
            "trace_id": payload.get("trace_id", ""),
            "result": None,
            "status": "failed",
            "error": f"不支持的任务类型: {task_type}"
        }

