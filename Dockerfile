FROM python:3.12-slim

# 基础设置
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# 统一容器内的工作目录为 /app
WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y \
    redis-server supervisor curl net-tools && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 项目代码复制到容器的 /app 目录
COPY . /app

# Python 依赖
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Supervisor 配置：复制本地的 supervisor/ 目录的所有内容到容器的 /etc/supervisor/conf.d/ 目录
COPY supervisor/ /etc/supervisor/conf.d/

# 日志目录：在容器的 /app 和 /var/log/supervisor 目录下创建日志目录
RUN mkdir -p /app/logs /var/log/supervisor

# 启动命令：直接运行 supervisord 以前台模式
CMD ["supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]