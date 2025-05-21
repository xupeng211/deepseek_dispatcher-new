# dispatcher/tasks.py
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import logging # 确保 logging 模块被导入

from ai_executor.executor import AIExecutor, AIExecutorError
from logger.logger import get_logger
from config.settings import RESULTS_DIR
# from services.llm_service import generate_text_from_llm # 如果 AIExecutor 内部处理 LLM 调用，则此导入不再需要

logger = get_logger("deepseek_dispatcher.tasks")

def _save_task_result(task_id: str, trace_id: str, data: Dict[str, Any], status: str, result: Optional[Any] = None, error: Optional[str] = None):
    """
    内部函数：保存任务结果到文件。
    """
    try:
        today_dir = os.path.join(RESULTS_DIR, datetime.now().strftime("%Y-%m-%d"))
        os.makedirs(today_dir, exist_ok=True)
        file_path = os.path.join(today_dir, f"task_{task_id}.json")

        output_data = {
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

# 将 process_ai_task 重命名为 generate_text_task，以匹配 web/app.py 中的调用
def generate_text_task(task_data: Dict[str, Any], trace_id: str, task_id: str):
    """
    RQ 后台任务函数：接收任务数据，调用 AI 模型，并保存结果。
    此函数将被 RQ Worker 实际执行。
    """
    logger.info(f"开始处理任务: {task_id} (trace_id: {trace_id})，输入数据: {task_data.get('prompt')[:50]}...")
    executor = None # 初始化为None，确保在finally块中可以判断
    try:
        # 确保 AIExecutor 每次任务执行时都重新初始化，以避免潜在的线程安全问题
        # 或者如果 AIExecutor 是无状态的，可以考虑缓存单例
        executor = AIExecutor()
        messages = [{"role": "user", "content": task_data.get("prompt")}]
        model_kwargs = task_data.get("model_kwargs", {})

        # 调用 AI 模型
        # 这里直接使用 AIExecutor.generate_completion，而不是 services.llm_service.generate_text_from_llm
        completion_result = executor.generate_completion(messages, **model_kwargs)

        # 保存成功结果
        _save_task_result(task_id, trace_id, task_data, "completed", completion_result)
        logger.info(f"任务 {task_id} 处理成功。")
        return {"status": "success", "result": completion_result}

    except AIExecutorError as e:
        error_message = f"AI 模型执行失败: {e}"
        logger.error(f"任务 {task_id} 处理失败: {error_message}", exc_info=True)
        _save_task_result(task_id, trace_id, task_data, "failed", error=error_message)
        # 重新抛出异常，RQ 会将其标记为失败，并放入失败队列
        raise
    except Exception as e:
        error_message = f"任务处理过程中发生未知错误: {e}"
        logger.error(f"任务 {task_id} 处理失败: {error_message}", exc_info=True)
        _save_task_result(task_id, trace_id, task_data, "failed", error=error_message)
        # 重新抛出异常，RQ 会将其标记为失败，并放入失败队列
        raise
