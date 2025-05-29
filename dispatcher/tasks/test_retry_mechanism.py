# dispatcher/tests/test_retry_mechanism.py

from dispatcher.scheduler.job_dispatcher import dispatch_job

if __name__ == "__main__":
    # 提交失败任务到 high 队列
    job = dispatch_job(priority="high", should_fail=True)
    print(f"已派发任务 ID: {job.id}")
