# ~/projects/deepseek_dispatcher-new/common/alert_utils.py

import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr # 导入 formataddr 用于正确格式化地址
import requests # 用于钉钉/企业微信等 Webhook
import json
import os # 引入 os 模块，用于获取环境变量以备用

# 引入我们新的日志工具
from common.logging_utils import get_logger
# 引入配置，现在导入 settings 对象本身
try:
    from config.settings import settings
except ImportError:
    # 如果 config.settings 不存在，作为临时方案，可以直接从 os.environ 读取
    # 但推荐使用 config/settings.py 来统一管理配置
    print("警告: 无法从 config.settings 导入 settings。将直接从环境变量读取告警配置。")
    class MockSettings:
        def __getattr__(self, name):
            return os.getenv(name)
    settings = MockSettings()


logger = get_logger("alert_utils")

def send_email_alert(subject: str, message: str):
    """
    发送邮件告警。
    依赖于 .env 中的 SMTP_SERVER, SMTP_PORT, EMAIL_USER, EMAIL_PASS, ALERT_EMAIL。
    """
    # 检查告警是否启用
    enable_alert_status = False
    if isinstance(settings.ENABLE_ALERT, str):
        enable_alert_status = settings.ENABLE_ALERT.lower() == 'true'
    elif isinstance(settings.ENABLE_ALERT, bool):
        enable_alert_status = settings.ENABLE_ALERT

    if not enable_alert_status:
        logger.info("邮件告警未启用或配置不正确 (ENABLE_ALERT 不是 'true' 或 True)，跳过发送。")
        return

    # 检查必要配置是否完整
    sender_email = settings.EMAIL_USER # 发件人邮箱地址
    # 确保 ALERT_EMAIL 是一个列表，如果配置的是逗号分隔的字符串
    receivers_str = settings.ALERT_EMAIL if settings.ALERT_EMAIL else ""
    receivers_emails = [r.strip() for r in receivers_str.split(',') if r.strip()] # 收件人邮箱地址列表

    # 打印日志以帮助调试
    logger.debug(f"邮件告警配置检查：SMTP_SERVER={settings.SMTP_SERVER}, SMTP_PORT={settings.SMTP_PORT}, EMAIL_USER={sender_email}, ALERT_EMAIL={settings.ALERT_EMAIL}")

    if not all([sender_email, receivers_emails, settings.SMTP_SERVER, settings.EMAIL_PASS, settings.SMTP_PORT]):
        logger.warning("邮件告警配置不完整，无法发送。请检查 .env 中的 EMAIL_USER, ALERT_EMAIL, SMTP_SERVER, SMTP_PORT, EMAIL_PASS。")
        return

    # 正确格式化 From 头，包含显示名称和邮箱地址
    # "DeepSeek Dispatcher" 是显示名称，sender_email 是实际的邮箱地址
    from_header = formataddr(("DeepSeek Dispatcher", sender_email))

    msg = MIMEText(message, 'plain', 'utf-8')
    msg['From'] = from_header # 使用正确格式化的 From 头
    msg['To'] = Header(",".join(receivers_emails), 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')

    smtp_obj = None # 初始化为 None
    try:
        # 将端口转换为整数，因为环境变量通常是字符串
        smtp_port = int(settings.SMTP_PORT)

        # 根据端口选择不同的 SMTP 连接方式
        if smtp_port == 465: # SSL/TLS
            logger.info(f"尝试通过 SMTP_SSL 连接到 {settings.SMTP_SERVER}:{smtp_port}")
            smtp_obj = smtplib.SMTP_SSL(settings.SMTP_SERVER, smtp_port, timeout=10)
        elif smtp_port == 587 or smtp_port == 25: # STARTTLS (587) 或普通 (25，不推荐)
            logger.info(f"尝试通过 SMTP 连接到 {settings.SMTP_SERVER}:{smtp_port}，并尝试 STARTTLS")
            smtp_obj = smtplib.SMTP(settings.SMTP_SERVER, smtp_port, timeout=10)
            if smtp_obj.has_extn('STARTTLS'): # 检查是否支持 STARTTLS
                smtp_obj.starttls() # 启用TLS加密
                logger.info("STARTTLS 已启用。")
            else:
                logger.warning("SMTP 服务器不支持 STARTTLS。将尝试非加密连接。")
        else:
            logger.warning(f"未知或不支持的 SMTP 端口 {smtp_port}。尝试使用 SMTP_SSL 连接。")
            smtp_obj = smtplib.SMTP_SSL(settings.SMTP_SERVER, smtp_port, timeout=10)


        # smtp_obj.set_debuglevel(1) # 调试模式，会打印详细的 SMTP 交互日志

        logger.info(f"尝试登录邮箱：{sender_email}")
        smtp_obj.login(sender_email, settings.EMAIL_PASS) # 使用授权码登录，注意这里使用 sender_email
        logger.info("邮箱登录成功。")

        logger.info(f"尝试发送邮件到：{receivers_emails}")
        # sendmail 方法的第一个参数是实际发送方邮箱地址，第二个参数是接收方邮箱地址列表
        smtp_obj.sendmail(sender_email, receivers_emails, msg.as_string())
        logger.info(f"邮件告警发送成功，主题: '{subject}'，收件人: {', '.join(receivers_emails)}")

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"邮件告警发送失败: 认证失败。请检查邮箱用户名和授权码是否正确。错误: {e}")
    except smtplib.SMTPServerDisconnected as e:
        logger.error(f"邮件告警发送失败: SMTP 服务器断开连接。请检查服务器地址和端口。错误: {e}")
    except smtplib.SMTPException as e:
        logger.error(f"邮件告警发送失败: SMTP 协议错误。错误: {e}", exc_info=True)
    except TimeoutError:
        logger.error(f"邮件告警发送失败: 连接到 SMTP 服务器超时。请检查网络连接或SMTP配置。")
    except Exception as e:
        logger.error(f"发送邮件时发生未知错误: {e}", exc_info=True)
    finally:
        if smtp_obj:
            try:
                smtp_obj.quit()
                logger.debug("SMTP 连接已关闭。")
            except Exception as e:
                logger.warning(f"关闭 SMTP 连接时发生错误: {e}")


def send_dingtalk_alert(title: str, text_content: str):
    """
    发送钉钉机器人告警。
    依赖于 .env 中的 DINGTALK_WEBHOOK。
    """
    # 修正：判断 settings.ENABLE_ALERT 的布尔值，避免 AttributeError
    enable_alert_status = False
    if isinstance(settings.ENABLE_ALERT, str):
        enable_alert_status = settings.ENABLE_ALERT.lower() == 'true'
    elif isinstance(settings.ENABLE_ALERT, bool):
        enable_alert_status = settings.ENABLE_ALERT

    if not enable_alert_status:
        logger.info("钉钉告警未启用或配置不正确 (ENABLE_ALERT 不是 'true' 或 True)，跳过发送。")
        return

    if not settings.DINGTALK_WEBHOOK:
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
        response = requests.post(settings.DINGTALK_WEBHOOK, headers=headers, data=json.dumps(data), timeout=10)
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
# 注意：直接运行此文件需要您手动设置 ENABLE_ALERT 为 True
# 并提供有效的 SMTP 或 DINGTALK_WEBHOOK 信息
# 在 KT4 中，这些将从 .env 文件加载

# 以下是用于直接运行此文件进行测试的临时模拟配置，
# 实际运行你的项目时，settings 对象会从 .env 文件加载真实配置。
# 在你的项目中，请确保 config/settings.py 能够正确加载 .env 文件，
# 例如使用 `python-dotenv` 库。
if __name__ == '__main__':
    # 导入 dotenv 库并加载 .env 文件，以便直接运行此脚本时也能获取配置
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("已加载 .env 文件中的环境变量。")
    except ImportError:
        print("警告: 无法导入 python-dotenv。请确保已安装 'pip install python-dotenv'。")
        print("告警配置将直接从系统环境变量或已存在的进程环境变量中读取。")

    print("开始尝试发送测试告警...")
    # 发送邮件告警
    # 确保 .env 中的 ENABLE_ALERT=true, 且邮件配置正确
    send_email_alert("DeepSeek Dispatcher 测试邮件告警", "这是一封来自 DeepSeek Dispatcher 项目的测试邮件。\n如果收到此邮件，说明邮件告警功能已配置并正常工作。")

    # 发送钉钉告警 (如果需要测试钉钉，请取消注释)
    # 确保 .env 中的 ENABLE_ALERT=true, 且 DINGTALK_WEBHOOK 配置正确
    # send_dingtalk_alert("DeepSeek Dispatcher 测试钉钉告警", "这是一条来自 DeepSeek Dispatcher 项目的测试钉钉消息。")

    print("测试告警尝试完毕。请检查你的收件箱和终端输出。")
