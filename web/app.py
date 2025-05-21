# web/app.py
from flask import Flask, jsonify, request # 确保导入了 request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from redis import Redis # 用于 Limiter 存储连接测试

from logger.logger import get_logger
from config.settings import (
    REDIS_URL, FLASK_HOST, FLASK_PORT, FLASK_DEBUG, FLASK_ENV,
    DEFAULT_RATELIMIT
)
from dispatcher.dispatcher import register_dispatcher_routes

logger = get_logger(__name__)

def create_app():
    """
    Flask 应用工厂函数，用于创建和配置 Flask 应用实例。
    """
    app = Flask(__name__)

    # 1. 加载配置
    # 配置已通过 config.settings 从环境变量加载
    logger.info("应用配置已加载。")

    # 2. 初始化 Flask-Limiter (请求限流)
    try:
        # 尝试连接 Redis，确保 Limiter 可以正常工作
        # 注意: Limiter 内部会处理 Redis 连接池，这里只是启动前的连接测试
        test_redis_conn = Redis.from_url(REDIS_URL)
        test_redis_conn.ping()
        
        limiter = Limiter(
            key_func=get_remote_address,
            default_limits=[DEFAULT_RATELIMIT], # 应用全局默认限流
            storage_uri=REDIS_URL,
            app=app # 绑定到 Flask 应用实例
        )
        logger.info(f"Flask-Limiter 已初始化，使用 Redis 存储: {REDIS_URL}")
    except Exception as e:
        logger.error(f"Flask-Limiter 初始化失败: {e}", exc_info=True)
        # 在生产环境中，这里可以选择抛出异常，阻止应用启动，确保限流服务可用
        # 但在开发过程中，为了灵活性，可以暂时允许启动
        raise # 强制抛出异常，确保 Redis 连接问题在启动时被发现

    # 3. 注册蓝图和路由
    register_dispatcher_routes(app) # 注册调度器相关的 API 路由
    logger.info("Dispatcher 路由已注册。")

    # 4. 定义根路由
    @app.route("/")
    def index():
        logger.info("收到对根路径 '/' 的请求。")
        return jsonify({"message": "Deepseek Dispatcher Service is running!", "status": "OK"}), 200

    # 5. 错误处理
    @app.errorhandler(404)
    def not_found(error):
        logger.warning(f"404 Not Found: {request.path}")
        return jsonify({"error": "Not Found", "message": f"The requested URL {request.path} was not found."}), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        logger.error(f"500 Internal Server Error: {error}", exc_info=True)
        return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500

    logger.info("Flask 应用创建完成。")
    return app

if __name__ == "__main__":
    # 在开发模式下运行 Flask 应用
    app = create_app()
    logger.info(f"Flask 应用正在 {FLASK_ENV} 环境下运行。")
    logger.info(f"监听地址: {FLASK_HOST}:{FLASK_PORT}, Debug 模式: {FLASK_DEBUG}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)