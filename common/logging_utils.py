# ~/projects/deepseek_dispatcher-new/common/logging_utils.py

import logging
from logging.handlers import TimedRotatingFileHandler
import os

def get_logger(name: str, log_dir: str = "logs", level: str = "INFO"):
    """
    创建一个按天切分日志的 logger：
    - name: logger 名称
    - log_dir: 日志文件目录（相对于项目根）
    - level: 日志级别
    """
    # 获取项目根目录的绝对路径
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 构建日志目录的绝对路径
    full_log_dir = os.path.join(project_root, log_dir)

    if not os.path.exists(full_log_dir):
        os.makedirs(full_log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 日志格式：时间 进程ID 日志级别 Logger名称:行号 信息
    formatter = logging.Formatter(
        "%(asctime)s [%(process)d] %(levelname)s [%(name)s:%(lineno)d] %(message)s"
    )

    # 按天切分文件：logs/<name>.log，每天0点切分，保留最近7天
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(full_log_dir, f"{name}.log"),
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d" # 日志文件后缀格式

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 避免重复添加 handler，这非常关键
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger