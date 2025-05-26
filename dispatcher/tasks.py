# dispatcher/tasks.py
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, Union, List # 导入 List 和 Union

from ai_executor.executor import AIExecutor, AIExecutorError
from logger.logger import get_logger
from config.settings import RESULTS_DIR

logger = get_logger("deepseek_dispatcher.tasks")

def _save_task_result(task_id: str, trace_id: str, data: Dict[str, Any], status: str, result: Optional[Any] = None, error: Optional[str] = None) -> None:
    """
    内部函数：保存任务结果到文件。
    Args:
        task_id (str): 任务的唯一 ID。
        trace_id (str): 用于追踪任务的唯一 ID。
        data (Dict[str, Any]): 原始输入任务数据。
        status (str): 任务状态（如 "completed", "failed"）。
        result (Optional[Any]): 任务执行的成功结果，默认为 None。
        error (Optional[str]): 任务执行失败的错误信息，默认为 None。
    Returns:
        None
    """
    try:
        today_dir: str = os.path.join(RESULTS_DIR, datetime.now().strftime("%Y-%m-%d"))
        os.makedirs(today_dir, exist_ok=True)
        file_path: str = os.path.join(today_dir, f"task_{task_id}.json")

        output_data: Dict[str, Any] = {
            "task_id": task_id,
            "trace_id": trace_id,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "input_data": data,
            "result": result,
            "error": error
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        logger.info(f"任务 {task_id} 结果已保存至: {file_path}")
    except Exception as e:
        logger.error(f"保存任务 {task_id} 结果失败: {e}", exc_info=True)

def generate_text_task(task_data: Dict[str, Any], trace_id: str, task_id: str) -> Dict[str, Union[str, Any]]:
    """
    RQ 后台任务函数：接收任务数据，调用 AI 模型，并保存结果。
    此函数将被 RQ Worker 实际执行。
    Args:
        task_data (Dict[str, Any]): 包含 'prompt' 和 'model_kwargs' 等的任务数据。
        trace_id (str): 用于追踪任务的唯一 ID。
        task_id (str): 任务的唯一 ID。
    Returns:
        Dict[str, Union[str, Any]]: 包含任务状态和结果的字典。
    Raises:
        AIExecutorError: AI 模型执行失败时抛出。
        Exception: 任务处理过程中发生未知错误时抛出。
    """
    logger.info(f"开始处理任务: {task_id} (trace_id: {trace_id})，输入数据: {task_data.get('prompt', '')[:50]}...")
    executor: Optional[AIExecutor] = None # 初始化为None，确保在finally块中可以判断
    try:
        executor = AIExecutor()
        messages: List[Dict[str, str]] = [{"role": "user", "content": task_data.get("prompt", "")}]
        model_kwargs: Dict[str, Any] = task_data.get("model_kwargs", {})

        completion_result: str = executor.generate_completion(messages, **model_kwargs)

        _save_task_result(task_id, trace_id, task_data, "completed", completion_result)
        logger.info(f"任务 {task_id} 处理成功。")
        return {"status": "success", "result": completion_result}

    except AIExecutorError as e:
        error_message: str = f"AI 模型执行失败: {e}"
        logger.error(f"任务 {task_id} 处理失败: {error_message}", exc_info=True)
        _save_task_result(task_id, trace_id, task_data, "failed", error=error_message)
        raise # 重新抛出异常，RQ 会将其标记为失败，并放入失败队列
    except Exception as e:
        error_message: str = f"任务处理过程中发生未知错误: {e}"
        logger.error(f"任务 {task_id} 处理失败: {error_message}", exc_info=True)
        _save_task_result(task_id, trace_id, task_data, "failed", error=error_message)
        raise # 重新抛出异常，RQ 会将其标记为失败，并放入失败队列