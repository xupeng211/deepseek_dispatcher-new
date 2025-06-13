# ~/projects-native/deepseek_dispatcher-new/wait_for_redis.py

#!/usr/bin/env python3

import sys
import time
from redis import Redis
from redis.exceptions import ConnectionError, TimeoutError as RedisTimeoutError # 导入 Redis 相关的 TimeoutError
import os # 引入 os 模块
from urllib.parse import urlparse # 引入 urlparse 用于解析 Redis URL

def wait_for_redis(host, port, db, timeout=120, interval=2): # 增加超时到 120 秒，间隔到 2 秒
    """
    等待 Redis 服务就绪。
    Args:
        host (str): Redis 主机名。
        port (int): Redis 端口。
        db (int): Redis 数据库编号。
        timeout (int): 等待超时时间（秒）。
        interval (int): 检查间隔（秒）。
    """
    start_time = time.time()
    redis_url = f"redis://{host}:{port}/{db}"
    sys.stdout.write(f"Waiting for Redis at {redis_url} to be ready (timeout={timeout}s)...\n")
    sys.stdout.flush()

    while True:
        try:
            # 尝试连接 Redis。 socket_connect_timeout 确保连接尝试不会无限期阻塞
            r = Redis.from_url(redis_url, socket_connect_timeout=5) # 增加 socket 连接超时
            r.ping() # 尝试发送 PING 命令，验证连接和 Redis 响应
            sys.stdout.write(f"Redis at {redis_url} is ready!\n")
            sys.stdout.flush()
            break
        except (ConnectionError, RedisTimeoutError, OSError) as e: # 捕获更广泛的连接错误，包括 DNS 解析失败的 OSError
            if time.time() - start_time > timeout:
                sys.stderr.write(f"Error: Redis at {redis_url} did not become ready within {timeout} seconds. Last error: {e}\n")
                sys.stderr.flush()
                sys.exit(1)
            sys.stdout.write(f"Redis not ready yet. Retrying in {interval}s... ({e})\n")
            sys.stdout.flush()
            time.sleep(interval)
        except Exception as e:
            sys.stderr.write(f"An unexpected error occurred while waiting for Redis: {e}\n")
            sys.stderr.flush()
            sys.exit(1)

if __name__ == "__main__":
    redis_url_env = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    parsed_url = urlparse(redis_url_env)
    
    redis_host = parsed_url.hostname if parsed_url.hostname else "localhost"
    redis_port = parsed_url.port if parsed_url.port else 6379
    redis_db = int(parsed_url.path.lstrip('/') or 0) # 从路径中获取db号

    wait_for_redis(redis_host, redis_port, redis_db)
    sys.exit(0) # 成功后退出
