# dispatcher/queues/queue_config.py

from rq import Queue
from redis import Redis

redis_conn = Redis()

# 定义多级队列
high_priority_queue = Queue('high', connection=redis_conn)
default_queue = Queue('default', connection=redis_conn)
low_priority_queue = Queue('low', connection=redis_conn)

# 队列注册表
QUEUE_MAP = {
    'high': high_priority_queue,
    'default': default_queue,
    'low': low_priority_queue,
}
