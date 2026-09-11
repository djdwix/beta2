[![CC BY-ND 4.0](https://licensebuttons.net/l/by-nd/4.0/88x31.png)](https://creativecommons.org/licenses/by-nd/4.0/deed.en)

# Virtual mobile number generation system

A fully functional virtual mobile number generation and management platform, which includes functional modules such as points system, PL system, game center and intelligent customer service.

## Environmental requirements

- Python 3.9+
- pip
- OpenSSL（used to generate SSL certificates）

## Quick Start

### 1. Install dependencies

pip install -r requirements.txt

### 2. Environment variable configuration

Create a .env file in the project root directory and fill it out by referring to the following format (replace all your-xxx-here with the actually generated values):

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

### 3. Key generation method

Generate SECRET_KEY：
python -c "import secrets; print(secrets.token_hex(32))"

Generate ENCRYPTION_KEY：
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Generate QR_SECRET：
python -c "import secrets; print(secrets.token_hex(32))"

Generate administrator password hash (replace your_password with the actual password):
python -c "import bcrypt; print(bcrypt.generate_password_hash('your_password').decode('utf-8'))"

### 4. Generate SSL certificates (certificates that can use your own domain name)

mkdir -p ssl

openssl req -x509 -newkey rsa:4096 -nodes -out ssl/cert.pem -keyout ssl/key.pem -days 365

### 5. Start the server

python server.py

The server will start at https://0.0.0.0:3000

## Project root directory structure

project root directory/
├── server.py              # main server

├── game.py                # game module

├── email_service.py       # Email service

├── knowledge_base.json    #Knowledge base data (editable)

├── requirements.txt       # Python dependencies

├── .env                   # Environment configuration (needs to be created by yourself)

├── data/                  # Data Storage (Auto-generated)

├── public/                #Frontend static files
└── GAME/                  # Game Center Frontend

Important Notes:
1. Replace all your-xxx-here placeholders above with actual generated values
2. It is recommended to rotate your keys regularly, especially SECRET_KEY and ENCRYPTION_KEY
3. Use strong passwords and keep them properly in production environments
4. Wiki bilingual guide: https://github.com/djdwix/beta2.wiki