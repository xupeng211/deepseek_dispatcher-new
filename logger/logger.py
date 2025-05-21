# logger/logger.py
import logging
import os
from logging.handlers import RotatingFileHandler
from config.settings import LOG_LEVEL, LOGS_DIR # 注意：这里是 LOGS_DIR

def get_logger(name="deepseek_dispatcher"):
    """
    配置并返回一个 Logger 实例。
    建议所有模块使用此接口获取 Logger，以保持一致的格式和级别。
    日志会同时输出到控制台和文件。
    """
    logger = logging.getLogger(name)

    # 避免重复添加 handlers
    if not logger.handlers:
        logger.setLevel(LOG_LEVEL)

        # 确保日志目录存在
        os.makedirs(LOGS_DIR, exist_ok=True)
        log_file_path = os.path.join(LOGS_DIR, "app.log")

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
            backupCount=5,              # 最多保留 5 个备份文件
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
