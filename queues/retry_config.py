# ~/projects/deepseek_dispatcher-new/dispatcher/queues/retry_config.py

from typing import List, Dict, Any
from rq import Retry # 导入 RQ 的 Retry 类，以便在外部引用时更准确

class RetryConfig:
    """
    定义任务重试策略的配置类。
    """
    def __init__(self, max_retries: int, interval: List[int]):
        """
        Args:
            max_retries (int): 最大重试次数。
            interval (List[int]): 重试间隔列表（秒）。
                                  例如：[10, 30, 60] 表示第一次重试等待 10 秒，
                                  第二次等待 30 秒，第三次等待 60 秒。
                                  列表长度应至少等于 max_retries。
        """
        if len(interval) < max_retries:
            # 如果重试间隔列表长度不足，补充最后一个间隔
            self.interval = interval + [interval[-1]] * (max_retries - len(interval))
        else:
            self.interval = interval[:max_retries] # 只取前 max_retries 个间隔

        self.max_retries = max_retries

    def to_dict(self) -> Dict[str, Any]:
        """将重试配置转换为字典格式，方便 RQ 使用。"""
        # 返回一个可以直接用于 RQ Job 的 retry 参数的 Retry 对象
        return Retry(max=self.max_retries, interval=self.interval)

# 定义不同优先级的重试策略实例
# 这些策略将在 job_dispatcher 中被引用

# 高优先级任务重试策略：快速重试几次，不等待太久
high_priority_retry = RetryConfig(
    max_retries=3,
    interval=[5, 15, 30] # 5秒，15秒，30秒
)

# 默认优先级任务重试策略：适中重试次数和间隔
default_retry = RetryConfig(
    max_retries=5,
    interval=[10, 30, 60, 120, 300] # 10秒，30秒，1分钟，2分钟，5分钟
)

# 低优先级任务重试策略：更多重试次数，间隔更长
low_priority_retry = RetryConfig(
    max_retries=10,
    interval=[30, 60, 180, 300, 600, 900, 1200, 1800, 2700, 3600] # 30秒到1小时
)

# 聚合所有重试策略到一个字典中，供其他模块导入
RETRY_STRATEGIES = {
    'high': high_priority_retry.to_dict(),
    'default': default_retry.to_dict(),
    'low': low_priority_retry.to_dict(),
}

# 如果有其他特殊的任务类型，可以添加更多重试策略
# example_special_retry = RetryConfig(max_retries=2, interval=[1, 2])
