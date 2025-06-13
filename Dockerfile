# ~/projects-native/deepseek_dispatcher-new/Dockerfile

# 直接从本地标签的 Python 镜像构建，确保不进行外部网络拉取
# 将 FROM 指令指向新的、更明确的本地标签
FROM my-local-python:3.12-slim

# 基础设置
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# 统一容器内的工作目录为 /app
WORKDIR /app

# --- 关键修改：更稳健地替换 APT 镜像源为国内源（使用 USTC）---
# 移除原始 sources.list (如果存在)，然后创建新的 sources.list
RUN rm -f /etc/apt/sources.list && \
    echo "deb https://mirrors.ustc.edu.cn/debian/ bookworm main contrib non-free" > /etc/apt/sources.list && \
    echo "deb https://mirrors.ustc.edu.cn/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.ustc.edu.cn/debian/ bookworm-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.ustc.edu.cn/debian/ bookworm-backports main contrib non-free" >> /etc/apt/sources.list
# ----------------------------------------

# 系统依赖
# 安装 supervisord、curl、gdb、python3-dbg 和 redis-tools
# 确保每行末尾都有反斜杠 '\'，除了最后一行
RUN apt-get update && apt-get install -y \
    supervisor \
    curl \
    gdb \
    python3-dbg \
    redis-tools \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
    # ^^^^ 修正：确保 redis-tools 后有一个反斜杠，且 apt-get clean 在同一 RUN 命令中

# Python 依赖
# 先复制 requirements.txt 以利用 Docker 缓存
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 项目代码复制到容器的 /app 目录
# 注意：这应该在复制依赖之后，以避免不必要的缓存失效
COPY . /app

# 添加等待 Redis 的 Python 脚本
COPY wait_for_redis.py /usr/local/bin/wait_for_redis.py
RUN chmod +x /usr/local/bin/wait_for_redis.py

# Supervisor 配置：
# 假设你的本地 supervisor/ 目录包含所有进程配置文件（如 worker_high.conf, dispatcher.conf）
# 以及一个主配置文件 supervisord.conf
# 将整个 supervisor/ 目录的内容复制到容器的 /etc/supervisor/ 目录
# 这样，/etc/supervisor/supervisord.conf 和 /etc/supervisor/conf.d/*.conf 都能被正确加载
COPY supervisor/ /etc/supervisor/

# 日志目录：在容器的 /app/logs 和 /var/log/supervisor 目录下创建日志目录，并确保写入权限
# Supervisord 的日志通常会写到 /var/log/supervisor
# 你的应用日志会写到 /app/logs
RUN mkdir -p /app/logs /var/log/supervisor && \
    chmod -R 777 /app/logs /var/log/supervisor

# 启动命令：运行 supervisord 以前台模式 (-n)
# -c 指定主配置文件的路径
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
