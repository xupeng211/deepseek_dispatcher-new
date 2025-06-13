# ~/projects/deepseek_dispatcher-new/dispatcher/queues/queue_config.py

from redis import Redis
from rq import Queue
from rq.job import Retry # 修正：从 rq.job 导入 Retry 类，兼容 rq 1.x 版本

# 引入配置
from config.settings import settings

# 初始化 Redis 连接
# 从 settings.REDIS_URL 获取 Redis 连接字符串
redis_conn = Redis.from_url(settings.REDIS_URL)

# 定义不同优先级的 RQ 队列
# 这些队列将共享同一个 Redis 连接
QUEUE_MAP = {
    'high': Queue('high', connection=redis_conn),
    'default': Queue('default', connection=redis_conn),
    'low': Queue('low', connection=redis_conn),
}

# 定义任务的重试策略
# 这些策略将在 TaskDispatcher 中应用到不同的队列或任务类型
default_retry = Retry(max=settings.TASK_MAX_RETRIES_DEFAULT, interval=settings.TASK_RETRY_INTERVAL_DEFAULT)
high_priority_retry = Retry(max=settings.TASK_MAX_RETRIES_HIGH, interval=settings.TASK_RETRY_INTERVAL_HIGH)
low_priority_retry = Retry(max=settings.TASK_MAX_RETRIES_LOW, interval=settings.TASK_RETRY_INTERVAL_LOW)


# 可以在这里添加其他队列相关的配置，例如：
# QUEUE_NAMES = ['high', 'default', 'low']
