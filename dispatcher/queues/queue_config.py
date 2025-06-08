# ~/projects/deepseek_dispatcher-new/dispatcher/queues/queue_config.py

from redis import Redis
from rq import Queue

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

# 可以在这里添加其他队列相关的配置，例如：
# QUEUE_NAMES = ['high', 'default', 'low']
