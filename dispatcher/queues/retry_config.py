# dispatcher/queues/retry_config.py

from rq import Retry

# 默认重试策略：最多3次，间隔10s
default_retry = Retry(max=3, interval=[10, 30, 60])

# 可拓展为按任务级别设定不同重试策略
