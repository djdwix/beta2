# 虚拟手机号生成器系统

一个功能完整的虚拟手机号生成与管理平台，包含积分系统、PL系统、游戏中心、智能客服等功能模块。

## 环境要求

- Python 3.9+
- pip
- OpenSSL（用于生成 SSL 证书）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt


## 环境变量配置

在项目根目录创建 `.env` 文件，参考以下格式填写：

```env
# ============================================================
# 核心安全配置（必须修改）
# ============================================================

# Flask 会话密钥（使用 secrets.token_hex(32) 生成）
SECRET_KEY=your-secret-key-here

# 数据加密密钥（使用 Fernet.generate_key() 生成）
ENCRYPTION_KEY=your-encryption-key-here

# QR 码签名密钥（使用 secrets.token_hex(32) 生成）
QR_SECRET=your-qr-secret-here

# ============================================================
# 管理员认证配置（必须修改）
# ============================================================

# 管理员用户名
ADMIN_USERNAME=admin

# 管理员密码哈希（使用 bcrypt 生成）
# 生成命令: python -c "import bcrypt; print(bcrypt.generate_password_hash('your_password').decode('utf-8'))"
ADMIN_PASSWORD_HASH=your-bcrypt-hash-here

# ============================================================
# CORS 跨域配置（必须修改）
# ============================================================

CORS_ALLOWED_ORIGINS=https://your-domain.com,https://localhost:3000,https://127.0.0.1:3000

# ============================================================
# 可选配置
# ============================================================

# 数据存储目录（默认 ./data）
# DATA_DIR=./data

# 管理员会话超时时间（秒，默认 3600）
# ADMIN_SESSION_TIMEOUT=3600

# 速率限制配置（使用默认值即可）
RATELIMIT_STORAGE_URI=memory://
RATELIMIT_STRATEGY=fixed-window
RATELIMIT_DEFAULT=200 per day;50 per hour

# 文件锁超时（秒，默认 10）
FILE_LOCK_TIMEOUT=10

# ============================================================
# 反馈邮箱配置（可选）
# ============================================================

# 用于接收用户反馈的邮箱
FEEDBACK_EMAIL=your-email@example.com
FEEDBACK_EMAIL_PASSWORD=your-email-password
FEEDBACK_SMTP_SERVER=smtp.example.com
FEEDBACK_SMTP_PORT=465

# ============================================================
# 邮箱验证码配置（可选，使用默认值即可）
# ============================================================

VERIFICATION_CODE_EXPIRE_SECONDS=300
VERIFICATION_CODE_LENGTH=6
SMTP_USE_SSL=True


# 生成 SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# 生成 ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 生成 QR_SECRET
python -c "import secrets; print(secrets.token_hex(32))"

# 生成管理员密码哈希（将 your_password 替换为实际密码）
python -c "import bcrypt; print(bcrypt.generate_password_hash('your_password').decode('utf-8'))"

#证书生成[可使用自己域名的证书]
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 -nodes -out ssl/cert.pem -keyout ssl/key.pem -days 365

###项目根目录
项目根目录/
├── server.py              # 主服务器
├── game.py                # 游戏模块
├── email_service.py       # 邮件服务
├── knowledge_base.json    # 知识库数据（可编辑）
├── requirements.txt       # Python 依赖
├── .env                   # 环境配置（不提交，需自行创建）
├── data/                  # 数据存储（自动生成，不提交）
├── public/                # 前端静态文件
└── GAME/                  # 游戏中心前端

