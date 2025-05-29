FROM python:3.12-slim

# 基础设置
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
EXPOSE 8000

# 系统依赖
RUN apt-get update && apt-get install -y \
    redis-server supervisor curl net-tools && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 项目代码
COPY . /app

# Python 依赖
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Supervisor 配置
COPY supervisor/ /etc/supervisor/conf.d/

# 日志目录
RUN mkdir -p /app/logs /var/log/supervisor

# 启动命令
CMD ["supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]