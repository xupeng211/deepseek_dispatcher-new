# ~/projects/deepseek_dispatcher-new/common/alert_utils.py

import smtplib
from email.mime.text import MIMEText
from email.header import Header
import requests # 用于钉钉/企业微信等 Webhook
import json

# 引入我们新的日志工具
from common.logging_utils import get_logger
# 引入配置，现在导入 settings 对象本身
from config.settings import settings

logger = get_logger("alert_utils")

def send_email_alert(subject: str, message: str):
    """
    发送邮件告警。
    需要配置 SMTP 服务器信息、发件人邮箱和密码、收件人邮箱。
    """
    if not settings.ENABLE_ALERT: # 访问 settings 对象的属性
        logger.info("邮件告警已禁用，跳过发送。")
        return

    sender = settings.EMAIL_USER # 访问 settings 对象的属性
    receivers = [settings.ALERT_EMAIL] # 访问 settings 对象的属性

    if not sender or not receivers[0] or not settings.SMTP_SERVER or not settings.EMAIL_PASS:
        logger.warning("邮件告警配置不完整，无法发送。请检查 EMAIL_USER, ALERT_EMAIL, SMTP_SERVER, EMAIL_PASS。")
        return

    msg = MIMEText(message, 'plain', 'utf-8')
    msg['From'] = Header(f"DeepSeek Dispatcher <{sender}>", 'utf-8')
    msg['To'] = Header(",".join(receivers), 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')

    try:
        smtp_obj = smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT) # 访问 settings 对象的属性
        # smtp_obj.set_debuglevel(1) # 调试模式，会打印详细的 SMTP 交互日志
        smtp_obj.login(settings.EMAIL_USER, settings.EMAIL_PASS) # 访问 settings 对象的属性
        smtp_obj.sendmail(sender, receivers, msg.as_string())
        logger.info(f"邮件告警发送成功，主题: '{subject}'，收件人: {settings.ALERT_EMAIL}")
    except smtplib.SMTPException as e:
        logger.error(f"邮件告警发送失败: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"发送邮件时发生未知错误: {e}", exc_info=True)

def send_dingtalk_alert(title: str, text_content: str):
    """
    发送钉钉机器人告警。
    需要配置钉钉机器人的 Webhook URL。
    """
    if not settings.ENABLE_ALERT: # 访问 settings 对象的属性
        logger.info("钉钉告警已禁用，跳过发送。")
        return

    if not settings.DINGTALK_WEBHOOK: # 访问 settings 对象的属性
        logger.warning("未配置 DINGTALK_WEBHOOK，无法发送钉钉告警。")
        return

    headers = {'Content-Type': 'application/json;charset=utf-8'}
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": f"## {title}\n\n{text_content}"
        },
        "at": {
            "atMobiles": [], # 需要 @ 的手机号列表，例如 ["138xxxxxxxx"]
            "isAtAll": False # 是否 @ 所有人
        }
    }

    try:
        response = requests.post(settings.DINGTALK_WEBHOOK, headers=headers, data=json.dumps(data), timeout=10) # 访问 settings 对象的属性
        response.raise_for_status() # 检查 HTTP 响应状态
        result = response.json()
        if result.get('errcode') == 0:
            logger.info(f"钉钉告警发送成功，主题: '{title}'")
        else:
            logger.error(f"钉钉告警发送失败，错误码: {result.get('errcode')}, 错误信息: {result.get('errmsg')}")
    except requests.exceptions.Timeout as e:
        logger.error(f"钉钉告警请求超时: {e}", exc_info=True)
    except requests.exceptions.RequestException as e:
        logger.error(f"钉钉告警发送失败: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"发送钉钉告警时发生未知错误: {e}", exc_info=True)

# 示例用法 (仅用于测试，实际使用时会通过配置来启用)
if __name__ == '__main__':
    # 注意：直接运行此文件需要您手动设置 ENABLE_ALERT 为 True
    # 并提供有效的 SMTP 或 DINGTALK_WEBHOOK 信息
    # 在 KT4 中，这些将从 .env 文件加载
    
    # 模拟配置
    class MockSettings:
        ENABLE_ALERT = True
        # 邮件配置 (请替换为实际可用的配置)
        SMTP_SERVER = "smtp.example.com"
        SMTP_PORT = 465 # 或 587
        EMAIL_USER = "your_email@example.com"
        EMAIL_PASS = "your_email_password"
        ALERT_EMAIL = "alert_recipient@example.com"
        # 钉钉配置 (请替换为实际可用的 Webhook URL)
        DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=YOUR_DINGTALK_TOKEN"

    # 临时覆盖 settings
    import sys
    sys.modules['config.settings'] = MockSettings()

    logger.info("尝试发送测试告警...")
    # send_email_alert("测试邮件告警", "这是一封来自 DeepSeek Dispatcher 的测试告警邮件。")
    # send_dingtalk_alert("测试钉钉告警", "这是一条来自 DeepSeek Dispatcher 的测试告警消息。")
    logger.info("测试告警尝试完毕。")
