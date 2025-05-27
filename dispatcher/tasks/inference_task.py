from dispatcher.core.base import BaseTask

class InferenceTask(BaseTask):
    """AI推理任务（替换原有generate_text_task）"""
    
    def run(self) -> dict:
        task_data = self.payload.get("task_data", {})
        trace_id = self.payload.get("trace_id", "")
        
        # 从task_data提取参数
        prompt = task_data.get("prompt", "")
        model_kwargs = task_data.get("model_kwargs", {})
        
        # 实际推理逻辑（示例）
        result = f"Processed: {prompt} with {model_kwargs}"
        
        return {
            "task_id": self.task_id,
            "trace_id": trace_id,
            "result": result,
            "status": "success"
        }
