# dispatcher/tasks.py
import os
import time
from typing import Dict, Any

# 如果 DeepSeek API 客户端在 services 目录下
from services.deepseek_service import DeepSeekService
from logger.logger import get_logger
from config.settings import DEEPSEEK_API_KEY, MODEL_NAME

logger = get_logger(__name__)

# 初始化 DeepSeekService
deepseek_service = DeepSeekService(api_key=DEEPSEEK_API_KEY, model=MODEL_NAME)

def execute_task(task_type: str, task_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    RQ Worker 实际执行的任务函数。
    根据 task_type 分发到不同的处理逻辑。
    """
    logger.info(f"Worker 收到任务 | TaskID: {task_id} | TaskType: {task_type} | TraceID: {payload.get('trace_id')}")

    if task_type == "inference":
        prompt = payload.get("task_data", {}).get("prompt")
        max_tokens = payload.get("task_data", {}).get("max_tokens", 500)
        temperature = payload.get("task_data", {}).get("temperature", 0.7)
        top_p = payload.get("task_data", {}).get("top_p", 0.8)

        if not prompt:
            logger.error(f"任务 {task_id} 缺少 'prompt' 参数")
            return {"status": "failed", "error": "Missing 'prompt' in task_data"}

        try:
            # 调用 DeepSeekService 进行推理
            response_text = deepseek_service.generate_text(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p
            )
            logger.info(f"任务 {task_id} 完成 | TraceID: {payload.get('trace_id')}")
            return {"status": "completed", "generated_text": response_text}
        except Exception as e:
            logger.error(f"DeepSeek API 调用失败 | TaskID: {task_id} | Error: {e}", exc_info=True)
            return {"status": "failed", "error": f"DeepSeek API Error: {e}"}
    else:
        logger.warning(f"未知任务类型: {task_type} | TaskID: {task_id}")
        return {"status": "failed", "error": f"Unknown task type: {task_type}"}