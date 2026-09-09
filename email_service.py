import os
import smtplib
import ssl
import random
import string
import logging
import json
import time
from threading import Lock
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

load_dotenv()

logger = logging.getLogger(__name__)

VERIFICATION_CODES_FILE = os.path.join(os.path.dirname(__file__), 'data', 'verification_codes.enc')
EMAIL_LIMITS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'email_limits.enc')
VERIFICATION_CODES_LOCK = Lock()
EMAIL_LIMITS_LOCK = Lock()

SMTP_SERVER = os.getenv('FEEDBACK_SMTP_SERVER', 'smtp.163.com')
SMTP_PORT = int(os.getenv('FEEDBACK_SMTP_PORT', 465))
SMTP_EMAIL = os.getenv('FEEDBACK_EMAIL', '')
SMTP_PASSWORD = os.getenv('FEEDBACK_EMAIL_PASSWORD', '')
USE_SSL = os.getenv('SMTP_USE_SSL', 'True').lower() == 'true'
CODE_EXPIRE_SECONDS = int(os.getenv('VERIFICATION_CODE_EXPIRE_SECONDS', 300))
CODE_LENGTH = int(os.getenv('VERIFICATION_CODE_LENGTH', 6))
DAILY_LIMIT = 10

ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY environment variable is required")

SALT_FILE = os.path.join(os.path.dirname(__file__), 'data', 'fernet_salt.bin')

def get_or_create_salt():
    if os.path.exists(SALT_FILE):
        with open(SALT_FILE, 'rb') as f:
            return f.read()
    else:
        salt = os.urandom(32)
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        with open(SALT_FILE, 'wb') as f:
            f.write(salt)
        return salt

SALT = get_or_create_salt()

key_material = ENCRYPTION_KEY.encode()
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=SALT,
    iterations=100000,
)
fernet_key = base64.urlsafe_b64encode(kdf.derive(key_material))
cipher = Fernet(fernet_key)

def encrypt_data(data):
    json_str = json.dumps(data, ensure_ascii=False, default=str)
    return cipher.encrypt(json_str.encode('utf-8'))

def decrypt_data(encrypted_data):
    decrypted = cipher.decrypt(encrypted_data)
    return json.loads(decrypted.decode('utf-8'))

logger.info(f"邮件服务配置: {SMTP_SERVER}:{SMTP_PORT}, 邮箱: {SMTP_EMAIL}")

def ensure_data_dir():
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir

def load_verification_codes():
    data_dir = ensure_data_dir()
    codes_file = VERIFICATION_CODES_FILE
    with VERIFICATION_CODES_LOCK:
        if os.path.exists(codes_file):
            try:
                with open(codes_file, 'rb') as f:
                    encrypted_data = f.read()
                    if encrypted_data:
                        return decrypt_data(encrypted_data)
                    return {}
            except Exception as e:
                logger.error(f"加载验证码数据失败: {e}")
                return {}
        return {}

def save_verification_codes(codes_data):
    data_dir = ensure_data_dir()
    codes_file = VERIFICATION_CODES_FILE
    with VERIFICATION_CODES_LOCK:
        try:
            encrypted_data = encrypt_data(codes_data)
            with open(codes_file, 'wb') as f:
                f.write(encrypted_data)
            logger.info(f"验证码数据已保存: {codes_file}")
            return True
        except Exception as e:
            logger.error(f"保存验证码数据失败: {e}")
            return False

def load_email_limits():
    data_dir = ensure_data_dir()
    limits_file = EMAIL_LIMITS_FILE
    with EMAIL_LIMITS_LOCK:
        if os.path.exists(limits_file):
            try:
                with open(limits_file, 'rb') as f:
                    encrypted_data = f.read()
                    if encrypted_data:
                        return decrypt_data(encrypted_data)
                    return {}
            except Exception as e:
                logger.error(f"加载邮箱限制数据失败: {e}")
                return {}
        return {}

def save_email_limits(limits_data):
    data_dir = ensure_data_dir()
    limits_file = EMAIL_LIMITS_FILE
    with EMAIL_LIMITS_LOCK:
        try:
            encrypted_data = encrypt_data(limits_data)
            with open(limits_file, 'wb') as f:
                f.write(encrypted_data)
            logger.info(f"邮箱限制数据已保存: {limits_file}")
            return True
        except Exception as e:
            logger.error(f"保存邮箱限制数据失败: {e}")
            return False

def init_email_limits():
    data_dir = ensure_data_dir()
    limits_file = EMAIL_LIMITS_FILE
    with EMAIL_LIMITS_LOCK:
        if not os.path.exists(limits_file):
            try:
                encrypted_data = encrypt_data({})
                with open(limits_file, 'wb') as f:
                    f.write(encrypted_data)
                logger.info(f"邮箱限制文件已初始化创建: {limits_file}")
                return True
            except Exception as e:
                logger.error(f"初始化邮箱限制文件失败: {e}")
                return False
        return True

def init_verification_codes():
    data_dir = ensure_data_dir()
    codes_file = VERIFICATION_CODES_FILE
    with VERIFICATION_CODES_LOCK:
        if not os.path.exists(codes_file):
            try:
                encrypted_data = encrypt_data({})
                with open(codes_file, 'wb') as f:
                    f.write(encrypted_data)
                logger.info(f"验证码文件已初始化创建: {codes_file}")
                return True
            except Exception as e:
                logger.error(f"初始化验证码文件失败: {e}")
                return False
        return True

def initialize_storage():
    init_email_limits()
    init_verification_codes()

initialize_storage()

def generate_verification_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

def send_email(to_email, subject, body, html_body=None):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        logger.error("SMTP配置不完整，请检查 FEEDBACK_EMAIL 和 FEEDBACK_EMAIL_PASSWORD")
        return False, "邮件服务配置不完整"

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        part_text = MIMEText(body, 'plain', 'utf-8')
        msg.attach(part_text)

        if html_body:
            part_html = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(part_html)

        context = ssl.create_default_context()

        if USE_SSL:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls(context=context)
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
                server.send_message(msg)

        logger.info(f"邮件发送成功: {to_email} - {subject}")
        return True, "邮件发送成功"

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP认证失败: {e}")
        return False, "邮件服务器认证失败，请检查邮箱账号和密码"
    except smtplib.SMTPException as e:
        logger.error(f"SMTP发送失败: {e}")
        return False, f"邮件发送失败: {str(e)}"
    except Exception as e:
        logger.error(f"发送邮件异常: {e}")
        return False, f"邮件发送异常: {str(e)}"

def build_verification_email_html(username, code, expire_minutes, purpose="验证"):
    purpose_map = {
        "验证": "邮箱验证",
        "换绑": "邮箱换绑",
        "注册": "邮箱注册",
        "重置密码": "重置密码",
        "注销": "账号注销"
    }
    purpose_label = purpose_map.get(purpose, purpose)
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{purpose_label}验证码</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #f0f2f5;
            padding: 40px 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 580px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.08), 0 8px 20px rgba(0,0,0,0.02);
            overflow: hidden;
            border: 1px solid #e8ecf1;
        }}
        .header {{
            background: linear-gradient(135deg, #5865F2 0%, #4752C4 100%);
            padding: 36px 40px 30px;
            text-align: center;
            position: relative;
        }}
        .header::after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #5865F2, #57F287, #FEE75C, #EB459E);
            background-size: 300% 100%;
            animation: gradientMove 3s ease infinite;
        }}
        @keyframes gradientMove {{
            0%, 100% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
        }}
        .header .logo {{
            font-size: 48px;
            margin-bottom: 8px;
            display: block;
        }}
        .header h1 {{
            color: #ffffff;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 1px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header p {{
            color: rgba(255,255,255,0.85);
            font-size: 14px;
            margin-top: 4px;
            font-weight: 300;
        }}
        .content {{
            padding: 40px 40px 32px;
        }}
        .greeting {{
            font-size: 16px;
            color: #1a1a2e;
            margin-bottom: 20px;
        }}
        .greeting strong {{
            color: #5865F2;
        }}
        .message {{
            color: #4a4a5a;
            font-size: 15px;
            margin-bottom: 24px;
        }}
        .message .purpose {{
            color: #5865F2;
            font-weight: 600;
        }}
        .code-box {{
            background: linear-gradient(135deg, #f8f9fe 0%, #eef1ff 100%);
            border-radius: 16px;
            padding: 28px 20px;
            text-align: center;
            margin: 24px 0;
            border: 2px dashed #c8d0f0;
            position: relative;
        }}
        .code-box .code-label {{
            font-size: 12px;
            color: #8a8aaa;
            text-transform: uppercase;
            letter-spacing: 3px;
            font-weight: 600;
            margin-bottom: 8px;
            display: block;
        }}
        .code-box .code {{
            font-size: 48px;
            font-weight: 800;
            color: #5865F2;
            letter-spacing: 12px;
            font-family: 'Courier New', monospace;
            background: white;
            padding: 12px 24px;
            border-radius: 12px;
            display: inline-block;
            box-shadow: 0 2px 8px rgba(88,101,242,0.12);
            border: 1px solid #e0e6ff;
        }}
        .info-row {{
            display: flex;
            align-items: center;
            gap: 12px;
            background: #f8f9fc;
            border-radius: 12px;
            padding: 14px 20px;
            margin: 16px 0 8px;
        }}
        .info-row .icon {{
            font-size: 20px;
            flex-shrink: 0;
        }}
        .info-row .text {{
            font-size: 14px;
            color: #4a4a5a;
        }}
        .info-row .text strong {{
            color: #5865F2;
        }}
        .warning-box {{
            background: #fff8f0;
            border-left: 4px solid #f5a623;
            border-radius: 8px;
            padding: 14px 18px;
            margin: 20px 0 8px;
        }}
        .warning-box .text {{
            font-size: 13px;
            color: #8a7a5a;
        }}
        .divider {{
            height: 1px;
            background: linear-gradient(90deg, transparent, #e0e4ea, transparent);
            margin: 28px 0 20px;
        }}
        .footer-text {{
            font-size: 13px;
            color: #8a8aaa;
            line-height: 1.8;
        }}
        .footer-text .team {{
            font-weight: 600;
            color: #5865F2;
        }}
        .footer {{
            background: #f8f9fc;
            padding: 20px 40px 24px;
            text-align: center;
            border-top: 1px solid #e8ecf1;
        }}
        .footer .footer-links {{
            display: flex;
            justify-content: center;
            gap: 24px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }}
        .footer .footer-links a {{
            color: #8a8aaa;
            text-decoration: none;
            font-size: 12px;
            transition: color 0.2s;
        }}
        .footer .footer-links a:hover {{
            color: #5865F2;
        }}
        .footer .copyright {{
            font-size: 12px;
            color: #b0b0c8;
        }}
        .footer .copyright .heart {{
            color: #EB459E;
        }}
        @media (max-width: 480px) {{
            body {{ padding: 20px 12px; }}
            .header {{ padding: 28px 20px 24px; }}
            .header .logo {{ font-size: 36px; }}
            .header h1 {{ font-size: 20px; }}
            .content {{ padding: 28px 20px 24px; }}
            .code-box .code {{ font-size: 36px; letter-spacing: 8px; padding: 10px 16px; }}
            .info-row {{ padding: 12px 16px; flex-wrap: wrap; }}
            .footer {{ padding: 16px 20px 20px; }}
            .footer .footer-links {{ gap: 16px; }}
        }}
        @media (max-width: 380px) {{
            .code-box .code {{ font-size: 28px; letter-spacing: 6px; padding: 8px 12px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="logo"><svg width="48" height="48" viewBox="0 0 127.14 96.36" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M107.7 8.07C105.84 4.22 101.72 1.78 97.24 1.78H29.9C25.42 1.78 21.3 4.22 19.44 8.07L0.5 49.72C-0.16 51.1 -0.16 52.72 0.5 54.1L19.44 95.75C21.3 99.6 25.42 102.04 29.9 102.04H97.24C101.72 102.04 105.84 99.6 107.7 95.75L126.64 54.1C127.3 52.72 127.3 51.1 126.64 49.72L107.7 8.07Z" fill="#5865F2"/><path d="M85.24 25.94L63.58 47.6L41.92 25.94L33.58 34.28L55.24 55.94L33.58 77.6L41.92 85.94L63.58 64.28L85.24 85.94L93.58 77.6L71.92 55.94L93.58 34.28L85.24 25.94Z" fill="white"/></svg></span>
            <h1>虚拟手机号生成器</h1>
            <p>安全 · 便捷 · 智能</p>
        </div>

        <div class="content">
            <div class="greeting">
                您好{f'，<strong>{username}</strong>' if username else ''}！👋
            </div>

            <div class="message">
                您正在进行 <span class="purpose">{purpose_label}</span> 操作，请使用以下验证码完成验证：
            </div>

            <div class="code-box">
                <span class="code-label">✦ 验证码 ✦</span>
                <div class="code">{code}</div>
            </div>

            <div class="info-row">
                <span class="icon">⏱️</span>
                <span class="text">验证码有效期为 <strong>{expire_minutes} 分钟</strong>，请尽快使用</span>
            </div>

            <div class="info-row">
                <span class="icon">🔒</span>
                <span class="text">此验证码 <strong>一次性有效</strong>，验证后自动失效</span>
            </div>

            <div class="warning-box">
                <div class="text">⚠️ 如果您没有进行此操作，请忽略本邮件，并确保您的邮箱安全</div>
            </div>

            <div class="divider"></div>

            <div class="footer-text">
                此邮件由系统自动发送，请勿直接回复。<br>
                如有任何问题，请联系 <span class="team">虚拟手机号生成器团队</span>
            </div>
        </div>

        <div class="footer">
            <div class="footer-links">
                <a href="#">📖 帮助中心</a>
                <a href="#">📧 联系我们</a>
                <a href="#">🔐 隐私政策</a>
            </div>
            <div class="copyright">
                © 2026 虚拟手机号生成器 · Made with <span class="heart">❤️</span>
            </div>
        </div>
    </div>
</body>
</html>"""

def send_verification_code(email, username=None, purpose="验证"):
    if not email:
        return False, None, "邮箱地址不能为空"

    code = generate_verification_code(CODE_LENGTH)
    expire_minutes = CODE_EXPIRE_SECONDS // 60

    purpose_map = {
        "验证": "邮箱验证",
        "换绑": "邮箱换绑",
        "注册": "邮箱注册",
        "重置密码": "重置密码",
        "注销": "账号注销"
    }
    purpose_label = purpose_map.get(purpose, purpose)

    subject = f"【虚拟手机号生成器】{purpose_label}验证码"

    body = f"""
您好{f'，{username}' if username else ''}！

您的{purpose_label}验证码是：{code}

验证码有效期为 {expire_minutes} 分钟，请尽快使用。

如果您没有进行此操作，请忽略本邮件。

此致
虚拟手机号生成器团队
"""

    html_body = build_verification_email_html(username, code, expire_minutes, purpose)

    success, message = send_email(email, subject, body, html_body)

    if success:
        codes = load_verification_codes()
        codes[email] = {
            'code': code,
            'created_at': int(time.time()),
            'expires_at': int(time.time()) + CODE_EXPIRE_SECONDS,
            'username': username,
            'verified': False,
            'purpose': purpose
        }
        save_verification_codes(codes)
        logger.info(f"验证码已发送并存储: {email}, 用途: {purpose}")
        return True, code, message
    else:
        logger.error(f"验证码发送失败: {email}, 用途: {purpose}, 原因: {message}")
        return False, None, message

def send_verification_code_with_limit(email, username=None, purpose="验证"):
    if not email:
        return False, None, "邮箱地址不能为空"

    init_email_limits()

    limits = load_email_limits()
    today = time.strftime('%Y-%m-%d')

    if email not in limits:
        limits[email] = {'date': today, 'count': 0}

    if limits[email]['date'] != today:
        limits[email] = {'date': today, 'count': 0}

    if limits[email]['count'] >= DAILY_LIMIT:
        return False, None, f"今日验证码发送次数已达上限（{DAILY_LIMIT}次），请明日再试"

    success, code, message = send_verification_code(email, username, purpose)

    if success:
        limits[email]['count'] += 1
        save_email_limits(limits)
        logger.info(f"邮箱 {email} 今日验证码发送次数: {limits[email]['count']}/{DAILY_LIMIT}, 用途: {purpose}")
    else:
        logger.warning(f"验证码发送失败，不更新发送次数限制: {email}, 用途: {purpose}")

    return success, code, message

def verify_code(email, code):
    if not email or not code:
        return False, "邮箱和验证码不能为空"

    init_verification_codes()
    codes = load_verification_codes()

    if email not in codes:
        return False, "验证码不存在或已过期，请重新获取"

    record = codes[email]
    current_time = int(time.time())

    if record.get('expires_at', 0) < current_time:
        del codes[email]
        save_verification_codes(codes)
        return False, "验证码已过期，请重新获取"

    if record.get('verified', False):
        return False, "验证码已被使用，请重新获取"

    if record['code'] != code:
        del codes[email]
        save_verification_codes(codes)
        return False, "验证码错误，请重新获取"

    record['verified'] = True
    record['verified_at'] = current_time
    save_verification_codes(codes)

    return True, "验证成功"

def cleanup_expired_codes():
    init_verification_codes()
    codes = load_verification_codes()
    current_time = int(time.time())
    expired = []

    for email, record in codes.items():
        if record.get('expires_at', 0) < current_time:
            expired.append(email)

    for email in expired:
        del codes[email]

    if expired:
        save_verification_codes(codes)
        logger.info(f"清理了 {len(expired)} 个过期验证码")

    return len(expired)

def get_verification_status(email):
    init_verification_codes()
    codes = load_verification_codes()
    
    if email not in codes:
        return {
            'exists': False,
            'verified': False,
            'expired': True,
            'message': '验证码不存在'
        }

    record = codes[email]
    current_time = int(time.time())
    is_expired = record.get('expires_at', 0) < current_time

    return {
        'exists': True,
        'verified': record.get('verified', False),
        'expired': is_expired,
        'created_at': record.get('created_at', 0),
        'expires_at': record.get('expires_at', 0),
        'purpose': record.get('purpose', '验证'),
        'message': '验证码有效' if not is_expired and not record.get('verified') else '验证码已过期或已使用'
    }

def resend_verification_code(email, username=None, purpose="验证"):
    init_verification_codes()
    codes = load_verification_codes()
    if email in codes:
        del codes[email]
        save_verification_codes(codes)
    return send_verification_code(email, username, purpose)

def cleanup_verification_codes_loop():
    while True:
        time.sleep(60)
        try:
            cleanup_expired_codes()
        except Exception as e:
            logger.error(f"清理验证码异常: {e}")