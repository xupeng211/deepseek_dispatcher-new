# web/app.py
import os
import json
import logging
import uuid # 导入 uuid 模块用于生成 trace_id
from flask import Flask, request, jsonify
from rq import Queue
from redis import Redis # 修正：直接从 redis 库导入 Redis
from config.settings import REDIS_URL, TASK_QUEUE_NAME, LOG_LEVEL
from dispatcher.tasks import generate_text_task # 确保导入的是 generate_text_task

# 配置日志
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    """
    创建并配置 Flask 应用实例。
    """
    app = Flask(__name__)

    # 初始化 Redis 连接
    # 在 Docker Compose 环境中，'redis' 是 Redis 服务的 hostname
    app.redis_conn = Redis.from_url(REDIS_URL)
    # 创建一个 RQ 队列实例
    app.task_queue = Queue(TASK_QUEUE_NAME, connection=app.redis_conn)

    logger.info(f"Flask app initialized. Connecting to Redis at: {REDIS_URL}")
    logger.info(f"Using task queue: {TASK_QUEUE_NAME}")

    @app.route('/')
    def index():
        """
        根路由，用于简单检查服务是否运行。
        """
        return "LLM Dispatcher is running!"

    @app.route('/generate', methods=['POST'])
    def generate():
        """
        接收生成请求，并将任务加入 RQ 队列。
        """
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        prompt = data.get('prompt')
        max_tokens = data.get('max_tokens', 100)
        temperature = data.get('temperature', 0.7)
        top_p = data.get('top_p', 0.9)

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        # 生成唯一的 trace_id 和 task_id (作为 RQ 的 job_id)
        trace_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        
        # 准备传递给 RQ 任务的 task_data 字典
        task_data = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "model_kwargs": { # 将模型参数也打包到 model_kwargs 中，以便 AIExecutor 使用
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p
            }
        }

        try:
            # 将任务加入 RQ 队列，传递 task_data, trace_id, task_id
            job = app.task_queue.enqueue(
                generate_text_task, # 调用 dispatcher.tasks 中的 generate_text_task
                task_data,
                trace_id,
                task_id, # 将生成的 task_id 作为 RQ 的 job_id
                job_timeout=300 # 设置任务超时时间，例如 5 分钟
            )
            logger.info(f"Task enqueued with ID: {job.id}, Trace ID: {trace_id}")
            return jsonify({
                "message": "Task enqueued successfully!",
                "task_id": job.id, # 返回 RQ 的 job_id
                "trace_id": trace_id # 返回 trace_id
            }), 202 # 202 Accepted 表示请求已接受，任务正在处理
        except Exception as e:
            logger.error(f"Error enqueuing task: {e}", exc_info=True)
            return jsonify({"error": "Failed to enqueue task", "details": str(e)}), 500

    @app.route('/task_status/<task_id>', methods=['GET'])
    def task_status(task_id):
        """
        检查指定任务 ID 的状态和结果。
        """
        try:
            job = app.task_queue.fetch_job(task_id)
            if job:
                status = job.get_status()
                result = job.result
                
                # 如果任务成功，result 是一个字典 {"status": "success", "result": completion_result}
                # 我们需要提取其中的 'result' 键
                final_result = None
                if status == 'finished' and isinstance(result, dict) and 'result' in result:
                    final_result = result['result']
                elif status == 'failed' and isinstance(result, dict) and 'error' in result:
                    final_result = result['error'] # 如果失败，显示错误信息
                else:
                    final_result = result # 其他状态直接显示原始结果

                logger.info(f"Task {task_id} status: {status}, result: {str(final_result)[:100] if isinstance(final_result, str) else final_result}")
                return jsonify({
                    "task_id": task_id,
                    "status": status,
                    "result": final_result
                })
            else:
                return jsonify({"error": "Task not found"}), 404
        except Exception as e:
            logger.error(f"Error fetching task status for {task_id}: {e}", exc_info=True)
            return jsonify({"error": "Failed to retrieve task status", "details": str(e)}), 500

    return app

if __name__ == '__main__':
    # 确保日志和结果目录存在 (如果本地直接运行，而不是通过 Docker)
    os.makedirs(os.path.join(os.getcwd(), 'logs'), exist_ok=True)
    os.makedirs(os.path.join(os.getcwd(), 'results'), exist_ok=True)
    
    # 在 Docker 中，waitress-serve 会调用 create_app() 并运行应用
    # 所以这里不需要 app.run()
    pass
