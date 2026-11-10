[![CC BY-ND 4.0](https://licensebuttons.net/l/by-nd/4.0/88x31.png)](https://creativecommons.org/licenses/by-nd/4.0/deed.en)

# 虚拟手机号生成器系统

一个基于 Python Flask 的综合管理平台，包含用户与权限管理、虚拟手机号记录、积分与 PL 系统、游戏中心、邮件验证、智能客服、网页搜索、天气与资讯等功能，并提供前端静态页面及音乐服务代理。

## 技术架构

### 核心技术栈

| 层级 | 使用技术 | 用途 |
| --- | --- | --- |
| 后端运行环境 | Python 3.9+ | 运行服务器及业务逻辑 |
| Web 框架 | Flask | 提供 HTTP/HTTPS 服务、路由及 JSON API |
| 跨域处理 | Flask-CORS | 配置允许访问的来源及凭据 |
| 密码哈希 | Flask-Bcrypt / bcrypt | 管理员密码哈希及密码校验 |
| 请求限流 | Flask-Limiter | 对全局及指定 API 设置访问频率限制 |
| HTTP 客户端 | Requests | 调用外部 AI、天气、资讯、搜索及音乐服务 |
| HTML 解析 | BeautifulSoup4、lxml | 解析网页内容及搜索结果 |
| 正文提取 | readability-lxml | 从网页中提取主要正文 |
| 数据格式 | JSON、CSV | 业务数据序列化及部分数据导入 |
| 本地数据存储 | 加密文件存储 | 将业务数据保存到项目 `data/` 目录，不依赖 SQL 数据库 |
| 数据加密 | Cryptography（Fernet、PBKDF2HMAC、SHA-256） | 加密本地数据文件及派生加密密钥 |
| 邮件服务 | Python smtplib、SMTP、SSL/TLS | 发送验证码、通知及反馈邮件 |
| 二维码 | qrcode | 生成二维码相关内容 |
| 并发处理 | threading、ThreadPoolExecutor | 后台任务、异步邮件及并发请求处理 |
| 前端 | HTML、CSS、JavaScript | 提供浏览器端页面和交互功能 |
| HTTPS | Python ssl、OpenSSL 证书 | 为 Flask 服务配置 TLS 加密连接 |

> **数据库说明：** 当前这三个 Python 文件体现的是基于本地文件的持久化方案。服务器通过自定义 `DataStore` 将 JSON 数据加密后写入 `data/` 目录，并使用内存缓存、线程锁和定时落盘机制；不是 MySQL、PostgreSQL 或 MongoDB 架构。

### 项目模块

| 文件 | 职责 |
| --- | --- |
| `server.py` | Flask 主服务、API 路由、用户会话、权限校验、限流、数据存储、外部服务调用及音乐 API 代理 |
| `game.py` | 游戏中心业务逻辑，包括游戏玩法、会员等级、任务、赛季、奖励及积分/G 币相关逻辑 |
| `email_service.py` | SMTP 邮件发送、验证码生成与校验、邮件发送限制，以及验证码和邮件限制数据的加密存储 |
| `knowledge_base.json` | 智能客服本地知识库数据（如项目中存在） |
| `public/` | 浏览器端静态页面、样式及 JavaScript |
| `data/` | 运行时生成的加密数据文件及相关数据 |
| `logs/` | 运行日志目录 |

## 外部服务与数据来源

下表列出 Python 代码中能够确认的外部服务。外部服务由各自运营方提供，服务可用性、免费额度、访问策略及返回内容均受第三方规则影响。

| 功能 | 服务 / 数据来源 | 代码中的调用地址或方式 | 用途 |
| --- | --- | --- | --- |
| AI 智能客服 | [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/) | `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/qwen/qwen3-30b-a3b-fp8` | 调用 `@cf/qwen/qwen3-30b-a3b-fp8` 模型，辅助知识库问答、内容整理及网页搜索结果总结 |
| 天气预报 | [Open-Meteo Forecast API](https://open-meteo.com/en/docs) | `https://api.open-meteo.com/v1/forecast` | 获取天气预报数据 |
| 城市地理编码 | [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api) | `https://geocoding-api.open-meteo.com/v1/search` | 将城市名称转换为地理位置，供天气查询使用 |
| 地震信息 | [USGS Earthquake Hazards Program](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php) | `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson` | 获取 USGS 提供的近期显著地震 GeoJSON 数据 |
| 每日资讯 | [AA1 API](https://zj.v.api.aa1.cn/api/60s/) | `https://zj.v.api.aa1.cn/api/60s/` | 获取每日资讯内容 |
| IP 签名档 | [SZFX API](https://api.szfx.top/) | `https://api.szfx.top/info-card/` | 获取 IP 信息卡片图片 |
| 网页搜索 | [Bing](https://www.bing.com/)、[搜狗](https://www.sogou.com/)、[360 搜索](https://www.so.com/)、[DuckDuckGo](https://duckduckgo.com/)、[百度](https://www.baidu.com/)、[Yandex](https://yandex.com/)、[Brave Search](https://search.brave.com/)、[Mojeek](https://www.mojeek.com/)、[Startpage](https://www.startpage.com/) | 服务器向各搜索引擎网页发起 HTTP 请求并解析结果 | 提供网页搜索及多来源结果汇总；实际返回情况取决于各搜索引擎 |
| 音乐服务 | [go-music-api](https://github.com/guohuiyuan/go-music-api) | 本地 `http://localhost:8080` | 通过本地音乐 API 获取歌曲搜索、播放地址、歌词及歌单数据 |

### 外部服务配置说明

- **Cloudflare Workers AI：** 需要在 `.env` 中配置 `CLOUDFLARE_ACCOUNT_ID` 和 `CLOUDFLARE_API_TOKEN`。未配置时，AI 调用函数会返回空结果，智能客服可按项目现有逻辑使用本地知识库或回退回答。
- **Open-Meteo、USGS、资讯、IP 签名档及网页搜索：** 代码中直接请求对应公开 URL；上述 Python 文件没有显示这些服务需要额外 API Key。
- **SMTP 邮件：** 通过环境变量配置邮件服务商、端口、邮箱账号和密码。代码默认 SMTP 主机为 `smtp.163.com`、端口为 `465`，但实际服务商可通过环境变量更改。
- **go-music-api：** 这是独立运行的本地服务，不是 Flask 自带模块。需要单独启动并监听 `8080` 端口；主服务器通过代理路由访问它。项目原有点歌台说明及上游发布页见 [go-music-api Releases](https://github.com/guohuiyuan/go-music-api/releases)。

## 环境要求

- Python 3.9+
- pip
- OpenSSL（用于生成或管理 HTTPS 证书）
- Go 1.25+（仅在需要从源码运行 go-music-api 时需要；使用对应平台的预编译程序可跳过）

## 快速开始

### 1. 安装 Python 依赖

在项目根目录执行：

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件。以下为主要配置项示例，所有占位符均需要替换为实际值：

```dotenv
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
SMTP_USE_SSL=True

VERIFICATION_CODE_EXPIRE_SECONDS=300
VERIFICATION_CODE_LENGTH=6

CLOUDFLARE_ACCOUNT_ID=your-account-id
CLOUDFLARE_API_TOKEN=your-api-token
```

其中 Cloudflare 配置为可选项；其余必需配置应以当前 `server.py` 的启动检查为准。不要将真实 `.env` 文件、邮箱密码、API Token 或加密密钥提交到公开仓库。

### 3. 生成密钥

生成 Flask `SECRET_KEY`：

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

生成数据加密密钥：

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

生成二维码相关密钥：

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

生成管理员密码哈希：

```bash
python -c 'import bcrypt; print(bcrypt.hashpw("your_password".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"))'
```

### 4. 配置 HTTPS 证书

项目启动代码会读取 `ssl/cert.pem` 和 `ssl/key.pem`，并通过 Python SSL 上下文启动 HTTPS 服务。

创建证书目录：

```bash
mkdir -p ssl
```

生成自签名证书（正式部署建议替换为可信 CA 签发的证书）：

```bash
openssl req -x509 -newkey rsa:4096 -nodes -out ssl/cert.pem -keyout ssl/key.pem -days 365
```

### 5. 启动主服务器

```bash
python server.py
```

当前 `server.py` 的启动配置为：

- 监听地址：`0.0.0.0`
- 端口：`3000`
- 协议：HTTPS
- 调试模式：关闭

访问地址通常为：

```text
https://服务器IP:3000
```

如果部署在云服务器上，还需要在云平台安全组及系统防火墙中放行相应端口。

## 智能客服配置

智能客服采用本地知识库与 Cloudflare Workers AI 组合：

1. 本地知识库由项目自身维护，相关内容保存在 `knowledge_base.json`。
2. 配置 Cloudflare Account ID 和 API Token 后，服务器会请求 Cloudflare Workers AI。
3. 当前代码调用的模型标识为 `@cf/qwen/qwen3-30b-a3b-fp8`。
4. AI 服务未配置或请求失败时，相关功能会按代码中的回退逻辑处理。

官方文档：

- [Cloudflare Workers AI 文档](https://developers.cloudflare.com/workers-ai/)
- [Workers AI REST API](https://developers.cloudflare.com/api/resources/ai/subresources/run/methods/run/)

## 邮件服务配置

`email_service.py` 使用 Python 标准库 `smtplib` 连接 SMTP 邮件服务器，支持 SSL 或 STARTTLS 连接方式。

主要配置项：

| 环境变量 | 说明 |
| --- | --- |
| `FEEDBACK_EMAIL` | 发件邮箱账号 |
| `FEEDBACK_EMAIL_PASSWORD` | SMTP 邮箱密码或授权码 |
| `FEEDBACK_SMTP_SERVER` | SMTP 服务器地址 |
| `FEEDBACK_SMTP_PORT` | SMTP 端口，代码默认 `465` |
| `SMTP_USE_SSL` | 是否使用 SMTP SSL，默认 `True` |
| `VERIFICATION_CODE_EXPIRE_SECONDS` | 验证码有效期，默认 `300` 秒 |
| `VERIFICATION_CODE_LENGTH` | 验证码长度，默认 `6` 位 |
| `ENCRYPTION_KEY` | 验证码及邮件限制数据加密所需密钥 |

验证码和邮件发送限制数据保存在 `data/` 目录的加密文件中。邮件发送任务支持线程池异步执行。

## 音乐点歌台配置

音乐功能依赖单独运行的 `go-music-api` 服务，默认监听本机 `8080` 端口。主服务器中的音乐代理会请求该本地服务。

### 获取与启动

1. 前往 [go-music-api Releases](https://github.com/guohuiyuan/go-music-api/releases) 下载适合当前系统的版本。
2. 解压文件；Linux/macOS 环境下如有需要，执行 `chmod +x` 为程序添加执行权限。
3. 启动程序，并确认本机 `http://localhost:8080` 可以访问。
4. 如需从源码运行，请安装 Go 1.25+，再按上游项目说明执行构建或启动命令。

音乐代理涉及的接口包括：

| 功能 | 本地接口 |
| --- | --- |
| 歌曲搜索 | `/api/v1/music/search` |
| 获取播放地址 | `/api/v1/music/url` |
| 推荐歌单 | `/api/v1/playlist/recommend` |
| 歌单详情 | `/api/v1/playlist/detail` |
| 获取歌词 | `/api/v1/music/lyric` |

代码中出现的音乐来源标识包括网易云、QQ 音乐、酷狗、酷我及百度等。具体可用音源、登录要求及播放能力以 go-music-api 上游项目和各音乐平台规则为准。

## 数据存储与安全机制

| 项目 | 当前实现 |
| --- | --- |
| 持久化位置 | 项目根目录下的 `data/` |
| 数据格式 | JSON 序列化后加密保存 |
| 加密方案 | Fernet 对称加密 |
| 密钥派生 | PBKDF2-HMAC-SHA256，迭代次数为 100,000 |
| 密码存储 | 使用 bcrypt 哈希 |
| 缓存与并发 | 内存缓存、线程锁及后台定时落盘 |
| 请求限制 | Flask-Limiter，当前配置使用内存型限流存储 |
| 会话 | Flask Session，配置了 HttpOnly 与 SameSite 属性 |

**部署注意事项：**

- `ENCRYPTION_KEY` 必须长期妥善保存；更换密钥前应先制定旧数据迁移方案，否则原有加密文件可能无法解密。
- `SECRET_KEY`、`QR_SECRET`、管理员密码及 SMTP 凭据不得公开。
- `data/` 是运行数据目录，应纳入安全备份范围，并限制文件系统访问权限。
- 当前限流存储配置为 `memory://`，适用于单进程内存场景；多进程或多实例部署时，不同进程之间不会自动共享限流状态。
- 当前主服务通过 Flask 自身的 `app.run()` 提供 HTTPS。正式对公网部署时，应根据实际负载评估 WSGI 服务器、反向代理、证书续期和进程管理方案。

## 项目目录结构

```text
项目根目录/
├── server.py
├── game.py
├── email_service.py
├── knowledge_base.json
├── requirements.txt
├── .env
├── ssl/
│   ├── cert.pem
│   └── key.pem
├── data/
├── logs/
├── public/
└── GAME/
```

## 许可证

本项目 README 当前标示为 [CC BY-ND 4.0](https://creativecommons.org/licenses/by-nd/4.0/deed.en)。代码文件及第三方依赖的许可证应分别以其原始许可证声明为准。
