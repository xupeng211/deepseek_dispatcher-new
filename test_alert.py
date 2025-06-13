# test_alert.py

import os
import sys

# 确保项目根目录在 Python 路径中，以便能找到 common/alert_utils.py 和 config/settings.py
# 假设你的项目结构是：
# project_root/
# ├── .env
# ├── common/
# │   └── alert_utils.py
# └── config/
#     └── settings.py
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 尝试加载 .env 文件中的环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("已加载 .env 文件中的环境变量。")
except ImportError:
    print("警告: 无法导入 python-dotenv。请确保已安装 'pip install python-dotenv'。")
    print("告警配置将直接从系统环境变量或已存在的进程环境变量中读取。")

# 导入告警工具函数
from common.alert_utils import send_email_alert

if __name__ == "__main__":
    print("开始测试邮件告警发送...")
    test_subject = "DeepSeek Dispatcher 告警测试邮件"
    test_message = "这是一封来自 DeepSeek Dispatcher 优化项目的手动告警测试邮件。\n如果收到此邮件，说明邮件告警功能正常工作。"

    send_email_alert(test_subject, test_message)

    print("测试告警发送函数已调用。请检查你的收件箱和控制台输出。")
