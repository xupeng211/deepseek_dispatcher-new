#!/bin/bash

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo ">>> [1/5] 启动 Redis 服务（如本地未运行）"
if ! pgrep -x "redis-server" > /dev/null; then
    redis-server --daemonize yes
    echo "Redis 已启动"
else
    echo "Redis 已在运行"
fi

echo ">>> [2/5] 创建 logs 目录"
mkdir -p logs

echo ">>> [3/5] 启动 RQ Workers（后台运行）"
QUEUE_LIST=("high" "default" "low")
for QUEUE in "${QUEUE_LIST[@]}"; do
    echo "  -> 启动 worker [$QUEUE]"
    # 使用完整的虚拟环境路径来运行 rq worker
    nohup "$PROJECT_ROOT"/.venv_dispatcher_new/bin/rq worker "$QUEUE" --with-scheduler > "logs/worker_$QUEUE.log" 2>&1 &
done

sleep 2

echo ">>> [4/5] 派发测试任务（模拟失败触发重试）"
# 关键修改：设置 PYTHONPATH 环境变量，确保 Python 能够找到 'dispatcher' 模块
PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" "$PROJECT_ROOT"/.venv_dispatcher_new/bin/python dispatcher/tests/test_retry_mechanism.py

echo ">>> [5/5] 所有 worker 启动完毕，任务已派发"
echo ">>> 查看日志：tail -f logs/worker_high.log"