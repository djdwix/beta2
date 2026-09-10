[![CC BY-ND 4.0](https://licensebuttons.net/l/by-nd/4.0/88x31.png)](https://creativecommons.org/licenses/by-nd/4.0/deed.en) 

# 虚拟手机号生成器系统

一个功能完整的虚拟手机号生成与管理平台，包含积分系统、PL系统、游戏中心、智能客服等功能模块。

## 环境要求

- Python 3.9+
- pip
- OpenSSL（用于生成 SSL 证书）

## 快速开始

### 1. 安装依赖

pip install -r requirements.txt

### 2. 环境变量配置

在项目根目录创建 .env 文件，参考以下格式填写（所有 your-xxx-here 需替换为实际生成的值）：

SECRET_KEY=your-secret-key-here

ENCRYPTION_KEY=your-encryption-key-here

QR_SECRET=your-qr-secret-here

ADMIN_USERNAME=admin

ADMIN_PASSWORD_HASH=your-bcrypt-hash-here

CORS_ALLOWED_ORIGINS=https://your-domain.com,https://localhost:3000,https://127.0.0.1:3000

RATELIMIT_STORAGE_URI=memory://

RATELIMIT_STRATEGY=fixed-window

RATELIMIT_DEFAULT=200 per day;50 per hour

FILE_LOCK_TIMEOUT=10

FEEDBACK_EMAIL=your-email@example.com

FEEDBACK_EMAIL_PASSWORD=your-email-password


FEEDBACK_SMTP_SERVER=smtp.example.com

FEEDBACK_SMTP_PORT=465

VERIFICATION_CODE_EXPIRE_SECONDS=300

VERIFICATION_CODE_LENGTH=6

SMTP_USE_SSL=True

### 3. 密钥生成方法

生成 SECRET_KEY：
python -c "import secrets; print(secrets.token_hex(32))"

生成 ENCRYPTION_KEY：
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

生成 QR_SECRET：
python -c "import secrets; print(secrets.token_hex(32))"

生成管理员密码哈希（将 your_password 替换为实际密码）：
python -c "import bcrypt; print(bcrypt.generate_password_hash('your_password').decode('utf-8'))"

### 4. 生成 SSL 证书（可使用自己域名的证书）

mkdir -p ssl
openssl req -x509 -newkey rsa:4096 -nodes -out ssl/cert.pem -keyout ssl/key.pem -days 365

### 5. 启动服务器

python server.py

服务器将在 https://0.0.0.0:3000 启动。


### 6.快速认证说明

创建data/id_cards.csv文件

文件格式参照:
姓名,身份证号
宫雅,XXXXXXXXXXXXXX
[每行1个]



## 项目根目录结构

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

重要提示：
1. 以上所有 your-xxx-here 占位符均需替换为实际生成的值
2. 建议定期更换密钥，特别是 SECRET_KEY 和 ENCRYPTION_KEY
3. 生产环境请使用强密码并妥善保管
4. wiki双语指南:https://github.com/djdwix/beta2.wiki