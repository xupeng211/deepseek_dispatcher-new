#!/bin/bash

set -e

echo "Starting Supervisor..."
# 启动 Supervisor 以前台模式运行
supervisord -n -c /etc/supervisor/supervisord.conf &

# 等待 Supervisor 启动并创建 socket 文件
echo "Waiting for Supervisor to start..."
for i in $(seq 1 10); do
    if [ -f /var/run/supervisor.sock ]; then
        echo "Supervisor socket found. Services should be starting."
        break
    fi
    echo "Attempt $i: Supervisor socket not found yet, waiting..."
    sleep 1
done

# 检查 Supervisor 状态
echo "=== Supervisor Status ==="
supervisorctl status
echo "========================="

# 保持容器运行，以便可以查看日志和进入容器调试
echo "Container is running. Check logs with 'docker logs dispatcher' or attach with 'docker exec -it dispatcher bash'."
tail -f /dev/null # 保持容器在前台运行，防止退出
