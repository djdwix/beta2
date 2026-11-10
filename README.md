[![CC BY-ND 4.0](https://licensebuttons.net/l/by-nd/4.0/88x31.png)](https://creativecommons.org/licenses/by-nd/4.0/deed.en) 

# 虚拟手机号生成器系统

一个功能完整的虚拟手机号生成与管理平台，包含积分系统、PL系统、游戏中心、智能客服、音乐点歌台等功能模块。

## 环境要求

- Python 3.9+
- pip
- OpenSSL（用于生成 SSL 证书）
- Go 1.25+（仅点歌台功能需要，如不使用可跳过）

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

CORS_ALLOWED_ORIGINS=https://your-domain.com,https://localhost:POST,https://127.0.0.1:POST

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

# AI 智能客服（可选，不配置则智能客服仅使用本地知识库）

CLOUDFLARE_ACCOUNT_ID=your-account-id

CLOUDFLARE_API_TOKEN=your-api-token

### 3. 密钥生成方法

生成 SECRET_KEY：
python -c "import secrets; print(secrets.token_hex(32))"

生成 ENCRYPTION_KEY：
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

生成 QR_SECRET：
python -c "import secrets; print(secrets.token_hex(32))"

生成管理员密码哈希（将 your_password 替换为实际密码，请勿使用如 #、// 等注释类字符）：
python -c 'import bcrypt; print(bcrypt.hashpw("your_password".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"))'

### 4. 生成 SSL 证书（可使用自己域名的证书）

mkdir -p ssl
openssl req -x509 -newkey rsa:4096 -nodes -out ssl/cert.pem -keyout ssl/key.pem -days 365

### 5. 启动服务器

python server.py

服务器将在 https://{SERVER_IP}:POST 启动。


### 6. 快速认证说明

创建 data/id_cards.csv 文件

文件格式参照：
姓名,身份证号
宫雅,XXXXXXXXXXXXXX
[每行1个，自行在网络上寻找身份证批量生成器]


## AI 智能客服配置

智能客服的 AI 能力基于 Cloudflare Workers AI，免费额度足够日常使用。

**获取 Account ID 和 API Token：**

1. 注册并登录 Cloudflare 控制台（dash.cloudflare.com）
2. 在左侧菜单进入 **AI > Workers AI**
3. 点击 **Use REST API**
4. 点击 **Create a Workers AI API Token**，按提示创建后复制 **API Token**（该 Token 只显示一次，请妥善保存）[citation:9]
5. 在同一页面复制 **Account ID**[citation:4]

将这两个值填入 `.env` 文件的 `CLOUDFLARE_ACCOUNT_ID` 和 `CLOUDFLARE_API_TOKEN` 即可。未配置时，智能客服会退回到仅使用本地知识库回答，不影响其他功能。


## go-music 点歌台配置

系统内置了两套点歌体验，均依赖本地运行的 **go-music-api** 后端服务（默认端口 8080）。`server.py` 已内置对 `localhost:8080` 的代理，只需启动该服务即可。

**下载与配置 go-music-api：**

1. 前往项目 Release 页面下载对应系统的可执行文件：
   https://github.com/guohuiyuan/go-music-api/releases [citation:7]

2. 解压后直接运行二进制文件（Linux/macOS 先 `chmod +x`），默认监听 `http://localhost:8080`[citation:3]

3. 如需使用网易云、QQ 音乐等需要登录才能播放的音源，可通过扫码登录写入 Cookie：
   - 启动后访问 `http://localhost:8080/swagger/index.html` 查看 Swagger 文档
   - 调用扫码登录相关接口，成功后 Cookie 会自动保存到 `cookies.json`[citation:3][citation:6]

4. 如果不想用二进制，也可以从源码运行（需要 Go 1.25+）：
   go mod tidy
   go run main.go

**双端点歌台联动机制：**

- **智能客服点歌台**：在智能客服对话框输入「点歌 XXX」，系统会动态检测 go-music-api 服务是否可用。若可用，会弹窗引导您跳转至全新、功能更完善的 NEBULA 独立点歌台；若未启动，则会静默使用内置的 MetingJS 公共音源作为兜底，不影响基础听歌。
- **NEBULA 独立点歌台 (`/nebula.html`)**：专为本地 go-music-api 深度定制的沉浸式音乐空间。支持全平台音源切换、歌词解析、本地点歌历史、收藏管理及歌单直接载入，提供专业级的听歌体验。

如需指定其他端口，修改 `server.py` 中 `proxy_music_*` 函数里的 `localhost:8080` 即可。


## 项目根目录结构

项目根目录/
├── server.py              # 主服务器

├── game.py                # 游戏模块

├── email_service.py       # 邮件服务

├── knowledge_base.json    # 知识库数据（可编辑）

├── requirements.txt       # Python 依赖

├── .env                   # 环境配置（不提交，发行版2.1.6及以上的zip包里有模板）

├── data/                  # 数据存储（自动生成，不提交）

├── public/                # 前端静态文件（包含 nebula_music.html 等）

└── GAME/                  # 游戏中心前端

重要提示：
1. 以上所有 your-xxx-here 占位符均需替换为实际生成的值
2. POST 需要替换成你所使用的端口
3. 建议定期更换密钥，特别是 SECRET_KEY 和 ENCRYPTION_KEY
4. 生产环境请使用强密码并妥善保管