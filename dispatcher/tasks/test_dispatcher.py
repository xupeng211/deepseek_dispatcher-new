from dispatcher.core.dispatcher import TaskDispatcher

dispatcher = TaskDispatcher()

# 提交推理任务
task_id = dispatcher.enqueue_task(
    task_type="inference",
    task_data={
        "prompt": "今天的A股走势",
        "model_kwargs": {"temperature": 0.7}
    },
    trace_id="trace_123456"
)

# 检查任务状态
status = dispatcher.get_task_status(task_id)
print(status)
