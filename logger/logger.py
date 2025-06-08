# logger/logger.py
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path # 导入 Path 模块，用于处理文件路径和创建目录

# 从 config.settings 导入 settings 对象，而不是直接导入 LOG_LEVEL 和 LOGS_DIR
from config.settings import settings


def get_logger(name="deepseek_dispatcher"):
    """
    配置并返回一个 Logger 实例。
    建议所有模块使用此接口获取 Logger，以保持一致的格式和级别。
    日志会同时输出到控制台和文件。
    """
    logger = logging.getLogger(name)

    # 避免重复添加 handlers
    if not logger.handlers:
        # 从 settings 对象获取 LOG_LEVEL
        logger.setLevel(settings.LOG_LEVEL)

        # 确保日志目录存在
        # 从 settings 对象获取 LOGS_DIR，并使用 Path 对象进行操作
        log_dir_path = Path(settings.LOGS_DIR)
        log_dir_path.mkdir(parents=True, exist_ok=True) # 使用 Path.mkdir 创建目录
        log_file_path = log_dir_path / "app.log" # 使用 Path 对象拼接路径

        # Console Handler (控制台输出)
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File Handler (文件输出，带滚动功能)
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,  # 最多保留 5 个备份文件
            encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


# 在模块加载时初始化一个全局的 logger 实例，方便其他模块直接导入
# 例如：from logger.logger import main_logger
main_logger = get_logger("deepseek_dispatcher.main")


if __name__ == '__main__':
    # 这是一个简单的测试，确保日志配置正确工作
    test_logger = get_logger("test_module")
    test_logger.info("This is an info message from the test module.")
    test_logger.warning("This is a warning message.")
    test_logger.error("This is an error message.", exc_info=True)
    try:
        1 / 0
    except ZeroDivisionError:
        test_logger.exception("An exception occurred!")
