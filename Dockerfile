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

# 修改 Supervisor 配置复制路径
# 将 supervisord.conf 复制到 /etc/supervisor/supervisord.conf
COPY supervisor/supervisord.conf /etc/supervisor/supervisord.conf

# 日志目录
RUN mkdir -p /app/logs /var/log/supervisor /var/run/supervisor && \
    chown -R root:root /var/run/supervisor /var/log/supervisor # 确保权限正确

# 复制并赋予启动脚本可执行权限
COPY scripts/supervisor_test.sh /app/supervisor_test.sh
RUN chmod +x /app/supervisor_test.sh

# 修改启动命令：使用新的测试脚本
CMD ["/app/supervisor_test.sh"]