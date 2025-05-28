# services/log_service.py
from services.base import BaseService
import datetime


class LogService(BaseService):
    def execute(self, message: str, level: str = "INFO"):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level.upper()}] {message}")

