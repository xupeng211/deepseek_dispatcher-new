# minimal_app.py
# 这是一个最简单的 FastAPI 应用，用于测试框架本身是否能在容器内启动。

from fastapi import FastAPI
import os
import logging

# 为了确保日志能够输出到控制台，我们在这里手动配置一个基础的日志
# Uvicorn 默认会设置自己的 logger，但这里可以作为一个备用或补充
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("minimal_app_startup")

logger.info("Minimal FastAPI app is starting...")

app = FastAPI(title="Minimal Test App")

@app.get("/")
async def read_root():
    logger.info("Root endpoint / was accessed.")
    return {"status": "ok", "message": "Minimal FastAPI app is running!"}

@app.get("/healthz")
async def health_check():
    logger.info("Healthz endpoint /healthz was accessed.")
    return {"status": "OK"}

logger.info("Minimal FastAPI app instance created.")

# 尝试读取一个环境变量，如果不存在也不会崩溃
test_env_var = os.getenv("TEST_ENV_VAR", "Not Set")
logger.info(f"TEST_ENV_VAR value: {test_env_var}")
