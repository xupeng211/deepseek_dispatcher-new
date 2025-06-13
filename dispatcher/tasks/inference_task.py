# dispatcher/tasks/inference_task.py

from typing import Dict
from dispatcher.tasks.base_task import BaseTask
from common.logging_utils import get_logger

logger = get_logger("inference_task")

class InferenceTask(BaseTask):
    """
    处理大模型推理任务的类。
    """
    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name
        # 这里可以初始化模型客户端，例如：
        # self.client = YourAIClient(api_key=settings.DEEPSEEK_API_KEY)

    def execute(self, job_id: str, task_details: Dict): # 修正：execute 方法签名与 dispatcher.dispatch 匹配
        """
        执行推理任务。
        :param job_id: 任务的 Job ID。
        :param task_details: 包含任务所有详细信息的字典。
                           例如: {"job_id": "...", "task_type": "...", "payload": {"task_data": {"prompt": "...", "should_fail_for_test": true}}}
        """
        # 从 task_details 中提取实际的 task_data
        # task_data_for_inference_task = task_details.get('payload', {}).get('task_data', {}) # 这是之前 web/app.py 传递过来的结构
        
        # 修正：直接从 task_details['payload'] 中获取 task_data_for_inference_task
        # 因为 dispatch 方法现在直接把 payload 参数（即 web/app.py 中的 task_data_for_inference_task）
        # 作为 kwargs={'payload': payload_from_web_app} 传给 RQ 任务的。
        # 而 execute 方法的 signature 则是 def execute(self, job_id, task_details)
        # 所以这里的 task_details 参数就是 dispatch 传递过来的 kwargs
        # 也就是 {'job_id': job_id, 'task_details': task_details_from_dispatch_method}
        # 而 task_details_from_dispatch_method 包含了 'payload' 键，对应 web/app.py 传过来的 task_data_for_inference_task
        
        # 修正：直接访问 task_details['payload'] 拿到 web/app.py 传入的 task_data_for_inference_task
        task_data = task_details.get('payload', {})


        prompt = task_data.get('prompt', '无提示')
        should_fail_for_test = task_data.get('should_fail_for_test', False)


        logger.info(f"开始执行推理任务 (ID: {job_id}), 模型: {self.model_name}, Prompt: {prompt[:50]}...")

        # --- 故意制造一个失败点，用于测试重试和告警 (KT3 验证) ---
        if should_fail_for_test:
            error_message = "这是一个人为的测试失败，用于验证任务重试和告警！"
            logger.error(f"故意制造异常触发任务失败: {error_message}")
            raise ValueError(error_message)
        # --- 故意制造失败点结束 ---

        try:
            # 模拟大模型推理耗时操作
            import time
            time.sleep(2) # 模拟推理时间

            # 假设这里是调用实际的推理服务
            # response = self.client.generate(prompt=prompt, **task_data.get('model_kwargs', {}))
            # result = response.text

            result = f"模拟推理结果：成功处理了 '{prompt}'"
            logger.info(f"推理任务执行成功 (ID: {job_id}), 结果: {result[:50]}...") # 打印部分结果

            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"推理任务执行失败 (ID: {job_id}): {e}", exc_info=True)
            raise # 重新抛出异常，让 RQ 捕获并触发重试/告警
