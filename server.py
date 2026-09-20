from flask import Flask, session, request, jsonify, send_from_directory, make_response
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
from pypinyin import lazy_pinyin
import json
import os
import time
import random
import hashlib
import requests
import re
import base64
import ssl
import signal
import sys
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv
import logging
import threading
import secrets
import math
import hmac
import csv
import game
import qrcode
from io import BytesIO
from filelock import FileLock, Timeout
import email_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

class IgnoreBrokenPipe(logging.Filter):
    def filter(self, record):
        if record.levelno == logging.ERROR and 'werkzeug' in record.name:
            msg = record.getMessage()
            if 'BrokenPipeError' in msg or 'SSLError' in msg or 'UNEXPECTED_EOF' in msg:
                return False
        return True

for handler in logging.root.handlers:
    handler.addFilter(IgnoreBrokenPipe())

load_dotenv()
app = Flask(__name__, static_folder='public')

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["500 per day", "120 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)

RATE_LIMITS = {
    'login': '10 per minute',
    'register': '5 per minute',
    'generate_phone': '30 per minute',
    'exchange_cdk': '8 per minute',
    'attendance': '2 per minute',
    'transfer_pl': '5 per minute',
    'reset_password': '3 per minute',
    'verify_identity': '3 per minute',
    'order_create': '20 per minute',
    'captcha_generate': '10 per minute',
    'pay': '10 per minute',
    'refund': '5 per minute',
    'mail_claim': '10 per minute',
    'pool_claim': '2 per minute',
    'admin_login': '18 per minute'
}

LOCK_TIMEOUT = 30

QR_SECRET = os.getenv('QR_SECRET')
if not QR_SECRET:
    raise ValueError("QR_SECRET environment variable is required")
QR_SECRET = QR_SECRET.encode()

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")

app.secret_key = SECRET_KEY
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=3)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['SESSION_COOKIE_DOMAIN'] = None
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True

CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')
if not CORS_ALLOWED_ORIGINS or CORS_ALLOWED_ORIGINS == ['']:
    raise ValueError("CORS_ALLOWED_ORIGINS environment variable is required")

CORS(app, supports_credentials=True, origins=CORS_ALLOWED_ORIGINS)
bcrypt = Bcrypt(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY environment variable is required")

SALT_FILE = os.path.join(DATA_DIR, 'fernet_salt.bin')

def get_or_create_salt():
    if os.path.exists(SALT_FILE):
        with open(SALT_FILE, 'rb') as f:
            return f.read()
    else:
        salt = os.urandom(32)
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

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH')
if not ADMIN_PASSWORD_HASH:
    log.warning("ADMIN_PASSWORD_HASH not set, using default. Please set in production!")
    ADMIN_PASSWORD_HASH = bcrypt.generate_password_hash('changeme123').decode('utf-8')

admin_sessions = {}
ADMIN_SESSION_TIMEOUT = 3600

USERS_FILE = os.path.join(DATA_DIR, 'users.enc')
PHONE_RECORDS_FILE = os.path.join(DATA_DIR, 'phone_records.enc')
CAPTCHA_STORAGE_FILE = os.path.join(DATA_DIR, 'captcha_storage.enc')
AUTH_CODES_FILE = os.path.join(DATA_DIR, 'auth_codes.enc')
RESET_CODES_FILE = os.path.join(DATA_DIR, 'reset_codes.enc')
POINT_CODES_FILE = os.path.join(DATA_DIR, 'point_codes.enc')
PREMIUM_POINT_CODES_FILE = os.path.join(DATA_DIR, 'premium_point_codes.enc')
BOOST_CODES_FILE = os.path.join(DATA_DIR, 'boost_codes.enc')
SPECIAL_POINT_CODES_FILE = os.path.join(DATA_DIR, 'special_point_codes.enc')
MAKEUP_CODES_FILE = os.path.join(DATA_DIR, 'makeup_codes.enc')
GAMBLERS_CODES_FILE = os.path.join(DATA_DIR, 'gamblers_codes.enc')
BOX_CODES_FILE = os.path.join(DATA_DIR, 'box_codes.enc')
PLCARD_CODES_FILE = os.path.join(DATA_DIR, 'plcard_codes.enc')
PREMIUM_BOOST_CODES_FILE = os.path.join(DATA_DIR, 'premium_boost_codes.enc')
USER_BOOSTS_FILE = os.path.join(DATA_DIR, 'user_boosts.enc')
IDENTITY_VERIFICATIONS_FILE = os.path.join(DATA_DIR, 'identity_verifications.enc')
CANCELLATION_CODES_FILE = os.path.join(DATA_DIR, 'cancellation_codes.enc')
RESTRICTED_USERS_FILE = os.path.join(DATA_DIR, 'restricted_users.enc')
CDK_PACKAGES_FILE = os.path.join(DATA_DIR, 'cdk_packages.enc')
USER_CDK_RECORDS_FILE = os.path.join(DATA_DIR, 'user_cdk_records.enc')
ANNOUNCEMENTS_FILE = os.path.join(DATA_DIR, 'announcements.enc')
PL_EXCHANGE_FILE = os.path.join(DATA_DIR, 'pl_exchange.enc')
PL_RATE_FILE = os.path.join(DATA_DIR, 'pl_rate.enc')
USER_PL_FILE = os.path.join(DATA_DIR, 'user_pl.enc')
SYSTEM_POINTS_FILE = os.path.join(DATA_DIR, 'system_points.enc')
GATEWAY_CARDS_FILE = os.path.join(DATA_DIR, 'gateway_cards.enc')
ORDERS_FILE = os.path.join(DATA_DIR, 'orders.enc')
USER_PAY_PASSWORDS_FILE = os.path.join(DATA_DIR, 'user_pay_passwords.enc')
ID_CARDS_CSV = os.path.join(DATA_DIR, 'id_cards.csv')
ID_CARDS_USED_FILE = os.path.join(DATA_DIR, 'id_cards_used.json')
USER_CODE_LIMITS_FILE = os.path.join(DATA_DIR, 'user_code_limits.enc')
COUPONS_FILE = os.path.join(DATA_DIR, 'coupons.enc')
USER_COUPONS_FILE = os.path.join(DATA_DIR, 'user_coupons.enc')
COUPON_GRANTS_FILE = os.path.join(DATA_DIR, 'coupon_grants.enc')
PL_TRANSFERS_FILE = os.path.join(DATA_DIR, 'pl_transfers.enc')
MAIL_ATTACHMENTS_FILE = os.path.join(DATA_DIR, 'mail_attachments.enc')
MAIL_READ_RECEIPTS_FILE = os.path.join(DATA_DIR, 'mail_read_receipts.enc')
POOL_RECORDS_FILE = os.path.join(DATA_DIR, 'pool_records.enc')
USER_POOL_CLAIMS_FILE = os.path.join(DATA_DIR, 'user_pool_claims.enc')
NEWBIE_POOL_FILE = os.path.join(DATA_DIR, 'newbie_pool.enc')
NEWBIE_POOL_CLAIMS_FILE = os.path.join(DATA_DIR, 'newbie_pool_claims.enc')
FUND_DATA_FILE = os.path.join(DATA_DIR, 'fund_data.enc')
FUND_HISTORY_FILE = os.path.join(DATA_DIR, 'fund_history.enc')
NAV_DATA_FILE = os.path.join(DATA_DIR, 'nav_data.enc')
NAV_HOLDINGS_FILE = os.path.join(DATA_DIR, 'nav_holdings.enc')
NAV_HISTORY_FILE = os.path.join(DATA_DIR, 'nav_history.enc')
RESET_LIMITS_FILE = os.path.join(DATA_DIR, 'reset_limits.enc')
FUND_RATE_FILE = os.path.join(DATA_DIR, 'fund_rate.enc')
GATEWAY_STOCK_FILE = os.path.join(DATA_DIR, 'gateway_stock.enc')

COUPON_TYPE_MAP = {
    'full_reduction': '满减券',
    'unconditional': '无门槛券',
    'product_specific': '指定商品券',
    'pl_discount': 'PL立减金',
    'makeup_specific': '指定补签卡券',
    'gamblers_specific': '赌神卡券'
}

FILE_MODIFICATION_TIMES = {}

def get_file_lock(file_path):
    lock_path = file_path + '.lock'
    return FileLock(lock_path, timeout=LOCK_TIMEOUT)

def get_file_mtime(file_path):
    try:
        return os.path.getmtime(file_path)
    except:
        return 0

def encrypt_data(data):
    json_str = json.dumps(data, ensure_ascii=False, default=str)
    return cipher.encrypt(json_str.encode('utf-8'))

def decrypt_data(encrypted_data):
    decrypted = cipher.decrypt(encrypted_data)
    return json.loads(decrypted.decode('utf-8'))

def load_data(file_path, default_value=None):
    if default_value is None:
        default_value = {}
    if not os.path.exists(file_path):
        return default_value
    max_retries = 3
    for attempt in range(max_retries):
        try:
            lock = get_file_lock(file_path)
            with lock.acquire(timeout=LOCK_TIMEOUT):
                with open(file_path, 'rb') as f:
                    encrypted_data = f.read()
                    return decrypt_data(encrypted_data)
        except Timeout:
            log.warning(f"Lock timeout loading {file_path}, attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))
            else:
                log.error(f"Lock timeout loading {file_path} after {max_retries} attempts")
                return default_value
        except Exception as e:
            log.error(f"Error loading {file_path}: {e}")
            return default_value
    return default_value

def save_data(file_path, data):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            lock = get_file_lock(file_path)
            with lock.acquire(timeout=LOCK_TIMEOUT):
                encrypted_data = encrypt_data(data)
                with open(file_path, 'wb') as f:
                    f.write(encrypted_data)
                return True
        except Timeout:
            log.warning(f"Lock timeout saving {file_path}, attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))
            else:
                log.error(f"Lock timeout saving {file_path} after {max_retries} attempts")
                return False
        except Exception as e:
            log.error(f"Error saving {file_path}: {e}")
            return False
    return False

# ======================= DYNAMIC PRICING SYSTEM =======================

def get_user_effective_points(username):
    """
    Calculate the user's effective points balance (regular points + fund balance)
    """
    if username not in users:
        return 0
    
    user_data = users.get(username, {})
    regular_points = user_data.get('totalPoints', 0)
    fund_balance = get_user_fund_balance(username)
    
    return regular_points + fund_balance


def get_price_multiplier(username):
    """
    Get the price multiplier based on the user's effective points balance.
    Uses tiered pricing: higher balance = higher multiplier.
    """
    effective_points = get_user_effective_points(username)
    
    if effective_points >= 500000:
        return 1.90  # 90% increase
    elif effective_points >= 300000:
        return 1.70  # 70% increase
    elif effective_points >= 200000:
        return 1.48  # 48% increase
    elif effective_points >= 100000:
        return 1.35  # 35% increase
    elif effective_points >= 50000:
        return 1.20  # 20% increase
    else:
        return 1.00  # No multiplier for balances under 50,000


def get_final_price(original_price, username):
    """
    Calculate the final price after applying new user discount and tiered price multiplier.
    The multiplier is applied AFTER any new user discount.
    """
    # Step 1: Apply new user discount (if applicable)
    if is_new_user(username):
        discounted_price = round(original_price * 0.8, 2)
    else:
        discounted_price = original_price
    
    # Step 2: Apply tiered price multiplier based on effective points
    multiplier = get_price_multiplier(username)
    final_price = round(discounted_price * multiplier, 2)
    
    return final_price


def get_price_info(original_price, username):
    """
    Get detailed price information including discount and multiplier breakdown.
    Useful for displaying to the user.
    """
    is_new = is_new_user(username)
    effective_points = get_user_effective_points(username)
    multiplier = get_price_multiplier(username)
    
    if is_new:
        discounted_price = round(original_price * 0.8, 2)
        discount_amount = round(original_price - discounted_price, 2)
        discount_type = 'new_user'
    else:
        discounted_price = original_price
        discount_amount = 0
        discount_type = 'none'
    
    final_price = round(discounted_price * multiplier, 2)
    multiplier_amount = round(final_price - discounted_price, 2)
    
    return {
        'original_price': original_price,
        'discounted_price': discounted_price,
        'discount_amount': discount_amount,
        'discount_type': discount_type,
        'multiplier': multiplier,
        'multiplier_amount': multiplier_amount,
        'final_price': final_price,
        'effective_points': effective_points,
        'is_new_user': is_new
    }

# ======================= END DYNAMIC PRICING SYSTEM =======================

def load_id_cards_used():
    if os.path.exists(ID_CARDS_USED_FILE):
        try:
            with open(ID_CARDS_USED_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_id_cards_used(used_data):
    try:
        with open(ID_CARDS_USED_FILE, 'w', encoding='utf-8') as f:
            json.dump(used_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log.error(f"Error saving id cards used: {e}")
        return False

def load_captcha_storage():
    if os.path.exists(CAPTCHA_STORAGE_FILE):
        try:
            lock = get_file_lock(CAPTCHA_STORAGE_FILE)
            with lock.acquire(timeout=LOCK_TIMEOUT):
                with open(CAPTCHA_STORAGE_FILE, 'rb') as f:
                    encrypted_data = f.read()
                    return decrypt_data(encrypted_data)
        except:
            return {}
    return {}

def save_captcha_storage(data):
    try:
        lock = get_file_lock(CAPTCHA_STORAGE_FILE)
        with lock.acquire(timeout=LOCK_TIMEOUT):
            encrypted_data = encrypt_data(data)
            with open(CAPTCHA_STORAGE_FILE, 'wb') as f:
                f.write(encrypted_data)
    except Exception as e:
        log.error(f"Error saving captcha storage: {e}")

def load_system_total_points():
    if os.path.exists(SYSTEM_POINTS_FILE):
        try:
            lock = get_file_lock(SYSTEM_POINTS_FILE)
            with lock.acquire(timeout=LOCK_TIMEOUT):
                with open(SYSTEM_POINTS_FILE, 'rb') as f:
                    encrypted_data = f.read()
                    return decrypt_data(encrypted_data).get('total_points', 0)
        except:
            return 0
    return 0

def save_system_total_points(points):
    try:
        lock = get_file_lock(SYSTEM_POINTS_FILE)
        with lock.acquire(timeout=LOCK_TIMEOUT):
            encrypted_data = encrypt_data({'total_points': points})
            with open(SYSTEM_POINTS_FILE, 'wb') as f:
                f.write(encrypted_data)
    except Exception as e:
        log.error(f"Error saving system points: {e}")

system_total_points = load_system_total_points()


def burn_excess_system_points():
    global system_total_points
    if system_total_points >= SYSTEM_POINTS_BURN_THRESHOLD:
        burned = system_total_points - SYSTEM_POINTS_BURN_THRESHOLD
        system_total_points = SYSTEM_POINTS_BURN_THRESHOLD
        save_system_total_points(system_total_points)
        log.info(f"System points pool auto-burned: burned={burned}, remaining={system_total_points}")
        return burned
    return 0

def load_newbie_pool_data():
    if os.path.exists(NEWBIE_POOL_FILE):
        try:
            lock = get_file_lock(NEWBIE_POOL_FILE)
            with lock.acquire(timeout=LOCK_TIMEOUT):
                with open(NEWBIE_POOL_FILE, 'rb') as f:
                    encrypted_data = f.read()
                    return decrypt_data(encrypted_data)
        except:
            return {}
    return {}

def save_newbie_pool_data(data):
    try:
        lock = get_file_lock(NEWBIE_POOL_FILE)
        with lock.acquire(timeout=LOCK_TIMEOUT):
            encrypted_data = encrypt_data(data)
            with open(NEWBIE_POOL_FILE, 'wb') as f:
                f.write(encrypted_data)
    except Exception as e:
        log.error(f"Error saving newbie pool: {e}")

def load_reset_limits():
    if os.path.exists(RESET_LIMITS_FILE):
        try:
            lock = get_file_lock(RESET_LIMITS_FILE)
            with lock.acquire(timeout=LOCK_TIMEOUT):
                with open(RESET_LIMITS_FILE, 'rb') as f:
                    encrypted_data = f.read()
                    return decrypt_data(encrypted_data)
        except:
            return {}
    return {}

def save_reset_limits(data):
    try:
        lock = get_file_lock(RESET_LIMITS_FILE)
        with lock.acquire(timeout=LOCK_TIMEOUT):
            encrypted_data = encrypt_data(data)
            with open(RESET_LIMITS_FILE, 'wb') as f:
                f.write(encrypted_data)
            return True
    except Exception as e:
        log.error(f"Error saving reset limits: {e}")
        return False

def load_newbie_pool_claims():
    if os.path.exists(NEWBIE_POOL_CLAIMS_FILE):
        try:
            lock = get_file_lock(NEWBIE_POOL_CLAIMS_FILE)
            with lock.acquire(timeout=LOCK_TIMEOUT):
                with open(NEWBIE_POOL_CLAIMS_FILE, 'rb') as f:
                    encrypted_data = f.read()
                    return decrypt_data(encrypted_data)
        except:
            return {}
    return {}

def save_newbie_pool_claims(data):
    try:
        lock = get_file_lock(NEWBIE_POOL_CLAIMS_FILE)
        with lock.acquire(timeout=LOCK_TIMEOUT):
            encrypted_data = encrypt_data(data)
            with open(NEWBIE_POOL_CLAIMS_FILE, 'wb') as f:
                f.write(encrypted_data)
    except Exception as e:
        log.error(f"Error saving newbie claims: {e}")

newbie_pool_data = load_newbie_pool_data()
newbie_pool_claims = load_newbie_pool_claims()

def deduct_system_total_points(amount):
    global system_total_points
    system_total_points = max(0, system_total_points - amount)
    save_system_total_points(system_total_points)
    return system_total_points

def add_system_total_points(amount):
    global system_total_points
    system_total_points = system_total_points + amount
    if system_total_points >= SYSTEM_POINTS_BURN_THRESHOLD:
        burned = system_total_points - SYSTEM_POINTS_BURN_THRESHOLD
        system_total_points = SYSTEM_POINTS_BURN_THRESHOLD
        log.info(f"System points pool auto-burned: burned={burned}, remaining={system_total_points}")
    save_system_total_points(system_total_points)
    return system_total_points

mail_attachments = load_data(MAIL_ATTACHMENTS_FILE, {})
mail_read_receipts = load_data(MAIL_READ_RECEIPTS_FILE, {})

def save_mail_attachments():
    save_data(MAIL_ATTACHMENTS_FILE, mail_attachments)
    FILE_MODIFICATION_TIMES['mail_attachments'] = get_file_mtime(MAIL_ATTACHMENTS_FILE)

def save_mail_read_receipts():
    save_data(MAIL_READ_RECEIPTS_FILE, mail_read_receipts)
    FILE_MODIFICATION_TIMES['mail_read_receipts'] = get_file_mtime(MAIL_READ_RECEIPTS_FILE)

def save_pool_records():
    save_data(POOL_RECORDS_FILE, pool_records)
    FILE_MODIFICATION_TIMES['pool_records'] = get_file_mtime(POOL_RECORDS_FILE)

def save_user_pool_claims():
    save_data(USER_POOL_CLAIMS_FILE, user_pool_claims)
    FILE_MODIFICATION_TIMES['user_pool_claims'] = get_file_mtime(USER_POOL_CLAIMS_FILE)

def save_fund_data():
    save_data(FUND_DATA_FILE, fund_data)
    FILE_MODIFICATION_TIMES['fund_data'] = get_file_mtime(FUND_DATA_FILE)

def save_fund_history():
    save_data(FUND_HISTORY_FILE, fund_history)
    FILE_MODIFICATION_TIMES['fund_history'] = get_file_mtime(FUND_HISTORY_FILE)

def save_fund_rate():
    save_data(FUND_RATE_FILE, fund_rate)
    FILE_MODIFICATION_TIMES['fund_rate'] = get_file_mtime(FUND_RATE_FILE)

def reload_if_changed():
    global users, phone_records, auth_codes, reset_codes, point_codes, premium_point_codes, boost_codes, special_point_codes, makeup_codes, gamblers_codes, box_codes, plcard_codes, premium_boost_codes, user_boosts, identity_verifications, cancellation_codes, restricted_users, cdk_packages, user_cdk_records, announcements, pl_exchange_records, pl_rate_data, user_pl_balances, system_total_points, orders, user_pay_passwords, user_code_limits, coupons, user_coupons, coupon_grants, pl_transfers, gateway_cards, mail_attachments, mail_read_receipts, pool_records, user_pool_claims, fund_data, fund_history, fund_rate, nav_data, nav_holdings, nav_history, gateway_stock

    users_mtime = get_file_mtime(USERS_FILE)
    phone_mtime = get_file_mtime(PHONE_RECORDS_FILE)
    auth_mtime = get_file_mtime(AUTH_CODES_FILE)
    reset_mtime = get_file_mtime(RESET_CODES_FILE)
    point_mtime = get_file_mtime(POINT_CODES_FILE)
    premium_mtime = get_file_mtime(PREMIUM_POINT_CODES_FILE)
    boost_mtime = get_file_mtime(BOOST_CODES_FILE)
    special_mtime = get_file_mtime(SPECIAL_POINT_CODES_FILE)
    makeup_mtime = get_file_mtime(MAKEUP_CODES_FILE)
    gamblers_mtime = get_file_mtime(GAMBLERS_CODES_FILE)
    box_mtime = get_file_mtime(BOX_CODES_FILE)
    plcard_mtime = get_file_mtime(PLCARD_CODES_FILE)
    premium_boost_mtime = get_file_mtime(PREMIUM_BOOST_CODES_FILE)
    user_boost_mtime = get_file_mtime(USER_BOOSTS_FILE)
    identity_mtime = get_file_mtime(IDENTITY_VERIFICATIONS_FILE)
    cancellation_mtime = get_file_mtime(CANCELLATION_CODES_FILE)
    restricted_mtime = get_file_mtime(RESTRICTED_USERS_FILE)
    cdk_mtime = get_file_mtime(CDK_PACKAGES_FILE)
    user_cdk_mtime = get_file_mtime(USER_CDK_RECORDS_FILE)
    announcement_mtime = get_file_mtime(ANNOUNCEMENTS_FILE)
    pl_exchange_mtime = get_file_mtime(PL_EXCHANGE_FILE)
    pl_rate_mtime = get_file_mtime(PL_RATE_FILE)
    user_pl_mtime = get_file_mtime(USER_PL_FILE)
    system_points_mtime = get_file_mtime(SYSTEM_POINTS_FILE)
    orders_mtime = get_file_mtime(ORDERS_FILE)
    pay_password_mtime = get_file_mtime(USER_PAY_PASSWORDS_FILE)
    code_limits_mtime = get_file_mtime(USER_CODE_LIMITS_FILE)
    coupons_mtime = get_file_mtime(COUPONS_FILE)
    user_coupons_mtime = get_file_mtime(USER_COUPONS_FILE)
    coupon_grants_mtime = get_file_mtime(COUPON_GRANTS_FILE)
    pl_transfers_mtime = get_file_mtime(PL_TRANSFERS_FILE)
    gateway_cards_mtime = get_file_mtime(GATEWAY_CARDS_FILE)
    mail_attachments_mtime = get_file_mtime(MAIL_ATTACHMENTS_FILE)
    mail_read_receipts_mtime = get_file_mtime(MAIL_READ_RECEIPTS_FILE)
    pool_records_mtime = get_file_mtime(POOL_RECORDS_FILE)
    user_pool_claims_mtime = get_file_mtime(USER_POOL_CLAIMS_FILE)
    fund_data_mtime = get_file_mtime(FUND_DATA_FILE)
    fund_history_mtime = get_file_mtime(FUND_HISTORY_FILE)
    fund_rate_mtime = get_file_mtime(FUND_RATE_FILE)
    nav_data_mtime = get_file_mtime(NAV_DATA_FILE)
    nav_holdings_mtime = get_file_mtime(NAV_HOLDINGS_FILE)
    nav_history_mtime = get_file_mtime(NAV_HISTORY_FILE)
    gateway_stock_mtime = get_file_mtime(GATEWAY_STOCK_FILE)

    if users_mtime != FILE_MODIFICATION_TIMES.get('users', 0):
        users = load_data(USERS_FILE, {})
        FILE_MODIFICATION_TIMES['users'] = users_mtime

    if phone_mtime != FILE_MODIFICATION_TIMES.get('phone', 0):
        phone_records = load_data(PHONE_RECORDS_FILE, {})
        FILE_MODIFICATION_TIMES['phone'] = phone_mtime

    if auth_mtime != FILE_MODIFICATION_TIMES.get('auth', 0):
        auth_codes = load_data(AUTH_CODES_FILE, {})
        FILE_MODIFICATION_TIMES['auth'] = auth_mtime

    if reset_mtime != FILE_MODIFICATION_TIMES.get('reset', 0):
        reset_codes = load_data(RESET_CODES_FILE, {})
        FILE_MODIFICATION_TIMES['reset'] = reset_mtime

    if point_mtime != FILE_MODIFICATION_TIMES.get('point', 0):
        point_codes = load_data(POINT_CODES_FILE, {})
        FILE_MODIFICATION_TIMES['point'] = point_mtime

    if premium_mtime != FILE_MODIFICATION_TIMES.get('premium_point', 0):
        premium_point_codes = load_data(PREMIUM_POINT_CODES_FILE, {})
        FILE_MODIFICATION_TIMES['premium_point'] = premium_mtime

    if boost_mtime != FILE_MODIFICATION_TIMES.get('boost', 0):
        boost_codes = load_data(BOOST_CODES_FILE, {})
        FILE_MODIFICATION_TIMES['boost'] = boost_mtime

    if special_mtime != FILE_MODIFICATION_TIMES.get('special_point', 0):
        special_point_codes = load_data(SPECIAL_POINT_CODES_FILE, {})
        FILE_MODIFICATION_TIMES['special_point'] = special_mtime

    if makeup_mtime != FILE_MODIFICATION_TIMES.get('makeup', 0):
        makeup_codes = load_data(MAKEUP_CODES_FILE, {})
        FILE_MODIFICATION_TIMES['makeup'] = makeup_mtime

    if gamblers_mtime != FILE_MODIFICATION_TIMES.get('gamblers', 0):
        gamblers_codes = load_data(GAMBLERS_CODES_FILE, {})
        FILE_MODIFICATION_TIMES['gamblers'] = gamblers_mtime

    if box_mtime != FILE_MODIFICATION_TIMES.get('box', 0):
        box_codes = load_data(BOX_CODES_FILE, {})
        FILE_MODIFICATION_TIMES['box'] = box_mtime

    if plcard_mtime != FILE_MODIFICATION_TIMES.get('plcard', 0):
        plcard_codes = load_data(PLCARD_CODES_FILE, {})
        FILE_MODIFICATION_TIMES['plcard'] = plcard_mtime

    if premium_boost_mtime != FILE_MODIFICATION_TIMES.get('premium_boost', 0):
        premium_boost_codes = load_data(PREMIUM_BOOST_CODES_FILE, {})
        FILE_MODIFICATION_TIMES['premium_boost'] = premium_boost_mtime

    if user_boost_mtime != FILE_MODIFICATION_TIMES.get('user_boost', 0):
        user_boosts = load_data(USER_BOOSTS_FILE, {})
        FILE_MODIFICATION_TIMES['user_boost'] = user_boost_mtime

    if identity_mtime != FILE_MODIFICATION_TIMES.get('identity', 0):
        identity_verifications = load_data(IDENTITY_VERIFICATIONS_FILE, {})
        FILE_MODIFICATION_TIMES['identity'] = identity_mtime

    if cancellation_mtime != FILE_MODIFICATION_TIMES.get('cancellation', 0):
        cancellation_codes = load_data(CANCELLATION_CODES_FILE, {})
        FILE_MODIFICATION_TIMES['cancellation'] = cancellation_mtime

    if restricted_mtime != FILE_MODIFICATION_TIMES.get('restricted', 0):
        restricted_users = load_data(RESTRICTED_USERS_FILE, {})
        FILE_MODIFICATION_TIMES['restricted'] = restricted_mtime

    if cdk_mtime != FILE_MODIFICATION_TIMES.get('cdk', 0):
        cdk_packages = load_data(CDK_PACKAGES_FILE, {})
        FILE_MODIFICATION_TIMES['cdk'] = cdk_mtime

    if user_cdk_mtime != FILE_MODIFICATION_TIMES.get('user_cdk', 0):
        user_cdk_records = load_data(USER_CDK_RECORDS_FILE, {})
        FILE_MODIFICATION_TIMES['user_cdk'] = user_cdk_mtime

    if announcement_mtime != FILE_MODIFICATION_TIMES.get('announcements', 0):
        announcements = load_data(ANNOUNCEMENTS_FILE, {})
        FILE_MODIFICATION_TIMES['announcements'] = announcement_mtime

    if pl_exchange_mtime != FILE_MODIFICATION_TIMES.get('pl_exchange', 0):
        pl_exchange_records = load_data(PL_EXCHANGE_FILE, {})
        FILE_MODIFICATION_TIMES['pl_exchange'] = pl_exchange_mtime

    if pl_rate_mtime != FILE_MODIFICATION_TIMES.get('pl_rate', 0):
        pl_rate_data = load_data(PL_RATE_FILE, {})
        FILE_MODIFICATION_TIMES['pl_rate'] = pl_rate_mtime

    if user_pl_mtime != FILE_MODIFICATION_TIMES.get('user_pl', 0):
        user_pl_balances = load_data(USER_PL_FILE, {})
        FILE_MODIFICATION_TIMES['user_pl'] = user_pl_mtime

    if system_points_mtime != FILE_MODIFICATION_TIMES.get('system_points', 0):
        system_total_points = load_system_total_points()
        FILE_MODIFICATION_TIMES['system_points'] = system_points_mtime

    if orders_mtime != FILE_MODIFICATION_TIMES.get('orders', 0):
        orders = load_data(ORDERS_FILE, {})
        FILE_MODIFICATION_TIMES['orders'] = orders_mtime

    if pay_password_mtime != FILE_MODIFICATION_TIMES.get('pay_password', 0):
        user_pay_passwords = load_data(USER_PAY_PASSWORDS_FILE, {})
        FILE_MODIFICATION_TIMES['pay_password'] = pay_password_mtime

    if code_limits_mtime != FILE_MODIFICATION_TIMES.get('code_limits', 0):
        user_code_limits = load_data(USER_CODE_LIMITS_FILE, {})
        FILE_MODIFICATION_TIMES['code_limits'] = code_limits_mtime

    if coupons_mtime != FILE_MODIFICATION_TIMES.get('coupons', 0):
        coupons = load_data(COUPONS_FILE, {})
        FILE_MODIFICATION_TIMES['coupons'] = coupons_mtime

    if user_coupons_mtime != FILE_MODIFICATION_TIMES.get('user_coupons', 0):
        user_coupons = load_data(USER_COUPONS_FILE, {})
        FILE_MODIFICATION_TIMES['user_coupons'] = user_coupons_mtime

    if coupon_grants_mtime != FILE_MODIFICATION_TIMES.get('coupon_grants', 0):
        coupon_grants = load_data(COUPON_GRANTS_FILE, {})
        FILE_MODIFICATION_TIMES['coupon_grants'] = coupon_grants_mtime

    if pl_transfers_mtime != FILE_MODIFICATION_TIMES.get('pl_transfers', 0):
        pl_transfers = load_data(PL_TRANSFERS_FILE, {})
        FILE_MODIFICATION_TIMES['pl_transfers'] = pl_transfers_mtime

    if gateway_cards_mtime != FILE_MODIFICATION_TIMES.get('gateway_cards', 0):
        gateway_cards = load_data(GATEWAY_CARDS_FILE, {})
        FILE_MODIFICATION_TIMES['gateway_cards'] = gateway_cards_mtime

    if mail_attachments_mtime != FILE_MODIFICATION_TIMES.get('mail_attachments', 0):
        mail_attachments = load_data(MAIL_ATTACHMENTS_FILE, {})
        FILE_MODIFICATION_TIMES['mail_attachments'] = mail_attachments_mtime

    if mail_read_receipts_mtime != FILE_MODIFICATION_TIMES.get('mail_read_receipts', 0):
        mail_read_receipts = load_data(MAIL_READ_RECEIPTS_FILE, {})
        FILE_MODIFICATION_TIMES['mail_read_receipts'] = mail_read_receipts_mtime

    if pool_records_mtime != FILE_MODIFICATION_TIMES.get('pool_records', 0):
        pool_records = load_data(POOL_RECORDS_FILE, {})
        FILE_MODIFICATION_TIMES['pool_records'] = pool_records_mtime

    if user_pool_claims_mtime != FILE_MODIFICATION_TIMES.get('user_pool_claims', 0):
        user_pool_claims = load_data(USER_POOL_CLAIMS_FILE, {})
        FILE_MODIFICATION_TIMES['user_pool_claims'] = user_pool_claims_mtime

    if fund_data_mtime != FILE_MODIFICATION_TIMES.get('fund_data', 0):
        fund_data = load_data(FUND_DATA_FILE, {})
        FILE_MODIFICATION_TIMES['fund_data'] = fund_data_mtime

    if fund_history_mtime != FILE_MODIFICATION_TIMES.get('fund_history', 0):
        fund_history = load_data(FUND_HISTORY_FILE, {})
        FILE_MODIFICATION_TIMES['fund_history'] = fund_history_mtime

    if fund_rate_mtime != FILE_MODIFICATION_TIMES.get('fund_rate', 0):
        fund_rate = load_data(FUND_RATE_FILE, {})
        FILE_MODIFICATION_TIMES['fund_rate'] = fund_rate_mtime

    if nav_data_mtime != FILE_MODIFICATION_TIMES.get('nav_data', 0):
        nav_data = load_data(NAV_DATA_FILE, {})
        FILE_MODIFICATION_TIMES['nav_data'] = nav_data_mtime

    if nav_holdings_mtime != FILE_MODIFICATION_TIMES.get('nav_holdings', 0):
        nav_holdings = load_data(NAV_HOLDINGS_FILE, {})
        FILE_MODIFICATION_TIMES['nav_holdings'] = nav_holdings_mtime

    if nav_history_mtime != FILE_MODIFICATION_TIMES.get('nav_history', 0):
        nav_history = load_data(NAV_HISTORY_FILE, {})
        FILE_MODIFICATION_TIMES['nav_history'] = nav_history_mtime

    if gateway_stock_mtime != FILE_MODIFICATION_TIMES.get('gateway_stock', 0):
        gateway_stock = load_data(GATEWAY_STOCK_FILE, {})
        FILE_MODIFICATION_TIMES['gateway_stock'] = gateway_stock_mtime

users = load_data(USERS_FILE, {})
phone_records = load_data(PHONE_RECORDS_FILE, {})
auth_codes = load_data(AUTH_CODES_FILE, {})
reset_codes = load_data(RESET_CODES_FILE, {})
point_codes = load_data(POINT_CODES_FILE, {})
premium_point_codes = load_data(PREMIUM_POINT_CODES_FILE, {})
boost_codes = load_data(BOOST_CODES_FILE, {})
special_point_codes = load_data(SPECIAL_POINT_CODES_FILE, {})
makeup_codes = load_data(MAKEUP_CODES_FILE, {})
gamblers_codes = load_data(GAMBLERS_CODES_FILE, {})
box_codes = load_data(BOX_CODES_FILE, {})
plcard_codes = load_data(PLCARD_CODES_FILE, {})
premium_boost_codes = load_data(PREMIUM_BOOST_CODES_FILE, {})
user_boosts = load_data(USER_BOOSTS_FILE, {})
identity_verifications = load_data(IDENTITY_VERIFICATIONS_FILE, {})
cancellation_codes = load_data(CANCELLATION_CODES_FILE, {})
restricted_users = load_data(RESTRICTED_USERS_FILE, {})
cdk_packages = load_data(CDK_PACKAGES_FILE, {})
user_cdk_records = load_data(USER_CDK_RECORDS_FILE, {})
gateway_cards = load_data(GATEWAY_CARDS_FILE, {})
announcements = load_data(ANNOUNCEMENTS_FILE, {})
pl_exchange_records = load_data(PL_EXCHANGE_FILE, {})
pl_rate_data = load_data(PL_RATE_FILE, {})
user_pl_balances = load_data(USER_PL_FILE, {})
system_total_points = load_system_total_points()
orders = load_data(ORDERS_FILE, {})
user_pay_passwords = load_data(USER_PAY_PASSWORDS_FILE, {})
user_code_limits = load_data(USER_CODE_LIMITS_FILE, {})
coupons = load_data(COUPONS_FILE, {})
user_coupons = load_data(USER_COUPONS_FILE, {})
coupon_grants = load_data(COUPON_GRANTS_FILE, {})
pl_transfers = load_data(PL_TRANSFERS_FILE, {})
mail_attachments = load_data(MAIL_ATTACHMENTS_FILE, {})
mail_read_receipts = load_data(MAIL_READ_RECEIPTS_FILE, {})
pool_records = load_data(POOL_RECORDS_FILE, {})
user_pool_claims = load_data(USER_POOL_CLAIMS_FILE, {})
fund_data = load_data(FUND_DATA_FILE, {})
fund_history = load_data(FUND_HISTORY_FILE, {})
nav_data = load_data(NAV_DATA_FILE, {})
nav_holdings = load_data(NAV_HOLDINGS_FILE, {})
nav_history = load_data(NAV_HISTORY_FILE, {})
fund_rate = load_data(FUND_RATE_FILE, {})
gateway_stock = load_data(GATEWAY_STOCK_FILE, {})

FILE_MODIFICATION_TIMES['users'] = get_file_mtime(USERS_FILE)
FILE_MODIFICATION_TIMES['phone'] = get_file_mtime(PHONE_RECORDS_FILE)
FILE_MODIFICATION_TIMES['auth'] = get_file_mtime(AUTH_CODES_FILE)
FILE_MODIFICATION_TIMES['reset'] = get_file_mtime(RESET_CODES_FILE)
FILE_MODIFICATION_TIMES['point'] = get_file_mtime(POINT_CODES_FILE)
FILE_MODIFICATION_TIMES['premium_point'] = get_file_mtime(PREMIUM_POINT_CODES_FILE)
FILE_MODIFICATION_TIMES['boost'] = get_file_mtime(BOOST_CODES_FILE)
FILE_MODIFICATION_TIMES['special_point'] = get_file_mtime(SPECIAL_POINT_CODES_FILE)
FILE_MODIFICATION_TIMES['makeup'] = get_file_mtime(MAKEUP_CODES_FILE)
FILE_MODIFICATION_TIMES['gamblers'] = get_file_mtime(GAMBLERS_CODES_FILE)
FILE_MODIFICATION_TIMES['box'] = get_file_mtime(BOX_CODES_FILE)
FILE_MODIFICATION_TIMES['plcard'] = get_file_mtime(PLCARD_CODES_FILE)
FILE_MODIFICATION_TIMES['premium_boost'] = get_file_mtime(PREMIUM_BOOST_CODES_FILE)
FILE_MODIFICATION_TIMES['user_boost'] = get_file_mtime(USER_BOOSTS_FILE)
FILE_MODIFICATION_TIMES['identity'] = get_file_mtime(IDENTITY_VERIFICATIONS_FILE)
FILE_MODIFICATION_TIMES['cancellation'] = get_file_mtime(CANCELLATION_CODES_FILE)
FILE_MODIFICATION_TIMES['restricted'] = get_file_mtime(RESTRICTED_USERS_FILE)
FILE_MODIFICATION_TIMES['cdk'] = get_file_mtime(CDK_PACKAGES_FILE)
FILE_MODIFICATION_TIMES['user_cdk'] = get_file_mtime(USER_CDK_RECORDS_FILE)
FILE_MODIFICATION_TIMES['announcements'] = get_file_mtime(ANNOUNCEMENTS_FILE)
FILE_MODIFICATION_TIMES['pl_exchange'] = get_file_mtime(PL_EXCHANGE_FILE)
FILE_MODIFICATION_TIMES['pl_rate'] = get_file_mtime(PL_RATE_FILE)
FILE_MODIFICATION_TIMES['user_pl'] = get_file_mtime(USER_PL_FILE)
FILE_MODIFICATION_TIMES['system_points'] = get_file_mtime(SYSTEM_POINTS_FILE)
FILE_MODIFICATION_TIMES['orders'] = get_file_mtime(ORDERS_FILE)
FILE_MODIFICATION_TIMES['pay_password'] = get_file_mtime(USER_PAY_PASSWORDS_FILE)
FILE_MODIFICATION_TIMES['code_limits'] = get_file_mtime(USER_CODE_LIMITS_FILE)
FILE_MODIFICATION_TIMES['coupons'] = get_file_mtime(COUPONS_FILE)
FILE_MODIFICATION_TIMES['user_coupons'] = get_file_mtime(USER_COUPONS_FILE)
FILE_MODIFICATION_TIMES['coupon_grants'] = get_file_mtime(COUPON_GRANTS_FILE)
FILE_MODIFICATION_TIMES['pl_transfers'] = get_file_mtime(PL_TRANSFERS_FILE)
FILE_MODIFICATION_TIMES['gateway_cards'] = get_file_mtime(GATEWAY_CARDS_FILE)
FILE_MODIFICATION_TIMES['mail_attachments'] = get_file_mtime(MAIL_ATTACHMENTS_FILE)
FILE_MODIFICATION_TIMES['mail_read_receipts'] = get_file_mtime(MAIL_READ_RECEIPTS_FILE)
FILE_MODIFICATION_TIMES['pool_records'] = get_file_mtime(POOL_RECORDS_FILE)
FILE_MODIFICATION_TIMES['user_pool_claims'] = get_file_mtime(USER_POOL_CLAIMS_FILE)
FILE_MODIFICATION_TIMES['fund_data'] = get_file_mtime(FUND_DATA_FILE)
FILE_MODIFICATION_TIMES['fund_history'] = get_file_mtime(FUND_HISTORY_FILE)
FILE_MODIFICATION_TIMES['fund_rate'] = get_file_mtime(FUND_RATE_FILE)
FILE_MODIFICATION_TIMES['gateway_stock'] = get_file_mtime(GATEWAY_STOCK_FILE)

def save_users():
    save_data(USERS_FILE, users)
    FILE_MODIFICATION_TIMES['users'] = get_file_mtime(USERS_FILE)

def save_phone_records():
    save_data(PHONE_RECORDS_FILE, phone_records)
    FILE_MODIFICATION_TIMES['phone'] = get_file_mtime(PHONE_RECORDS_FILE)

def save_auth_codes():
    save_data(AUTH_CODES_FILE, auth_codes)
    FILE_MODIFICATION_TIMES['auth'] = get_file_mtime(AUTH_CODES_FILE)

def save_reset_codes():
    save_data(RESET_CODES_FILE, reset_codes)
    FILE_MODIFICATION_TIMES['reset'] = get_file_mtime(RESET_CODES_FILE)

def save_point_codes():
    save_data(POINT_CODES_FILE, point_codes)
    FILE_MODIFICATION_TIMES['point'] = get_file_mtime(POINT_CODES_FILE)

def save_premium_point_codes():
    save_data(PREMIUM_POINT_CODES_FILE, premium_point_codes)
    FILE_MODIFICATION_TIMES['premium_point'] = get_file_mtime(PREMIUM_POINT_CODES_FILE)

def save_boost_codes():
    save_data(BOOST_CODES_FILE, boost_codes)
    FILE_MODIFICATION_TIMES['boost'] = get_file_mtime(BOOST_CODES_FILE)

def save_special_point_codes():
    save_data(SPECIAL_POINT_CODES_FILE, special_point_codes)
    FILE_MODIFICATION_TIMES['special_point'] = get_file_mtime(SPECIAL_POINT_CODES_FILE)

def save_makeup_codes():
    save_data(MAKEUP_CODES_FILE, makeup_codes)
    FILE_MODIFICATION_TIMES['makeup'] = get_file_mtime(MAKEUP_CODES_FILE)

def save_gamblers_codes():
    save_data(GAMBLERS_CODES_FILE, gamblers_codes)
    FILE_MODIFICATION_TIMES['gamblers'] = get_file_mtime(GAMBLERS_CODES_FILE)

def save_box_codes():
    save_data(BOX_CODES_FILE, box_codes)
    FILE_MODIFICATION_TIMES['box'] = get_file_mtime(BOX_CODES_FILE)

def save_plcard_codes():
    save_data(PLCARD_CODES_FILE, plcard_codes)
    FILE_MODIFICATION_TIMES['plcard'] = get_file_mtime(PLCARD_CODES_FILE)

def save_premium_boost_codes():
    save_data(PREMIUM_BOOST_CODES_FILE, premium_boost_codes)
    FILE_MODIFICATION_TIMES['premium_boost'] = get_file_mtime(PREMIUM_BOOST_CODES_FILE)

def save_user_boosts():
    save_data(USER_BOOSTS_FILE, user_boosts)
    FILE_MODIFICATION_TIMES['user_boost'] = get_file_mtime(USER_BOOSTS_FILE)

def save_identity_verifications():
    save_data(IDENTITY_VERIFICATIONS_FILE, identity_verifications)
    FILE_MODIFICATION_TIMES['identity'] = get_file_mtime(IDENTITY_VERIFICATIONS_FILE)

def save_cancellation_codes():
    save_data(CANCELLATION_CODES_FILE, cancellation_codes)
    FILE_MODIFICATION_TIMES['cancellation'] = get_file_mtime(CANCELLATION_CODES_FILE)

def save_restricted_users():
    save_data(RESTRICTED_USERS_FILE, restricted_users)
    FILE_MODIFICATION_TIMES['restricted'] = get_file_mtime(RESTRICTED_USERS_FILE)

def save_cdk_packages():
    save_data(CDK_PACKAGES_FILE, cdk_packages)
    FILE_MODIFICATION_TIMES['cdk'] = get_file_mtime(CDK_PACKAGES_FILE)

def save_user_cdk_records():
    save_data(USER_CDK_RECORDS_FILE, user_cdk_records)
    FILE_MODIFICATION_TIMES['user_cdk'] = get_file_mtime(USER_CDK_RECORDS_FILE)

def save_announcements():
    save_data(ANNOUNCEMENTS_FILE, announcements)
    FILE_MODIFICATION_TIMES['announcements'] = get_file_mtime(ANNOUNCEMENTS_FILE)

def save_pl_exchange_records():
    save_data(PL_EXCHANGE_FILE, pl_exchange_records)
    FILE_MODIFICATION_TIMES['pl_exchange'] = get_file_mtime(PL_EXCHANGE_FILE)

def save_pl_rate_data():
    save_data(PL_RATE_FILE, pl_rate_data)
    FILE_MODIFICATION_TIMES['pl_rate'] = get_file_mtime(PL_RATE_FILE)

def save_user_pl_balances():
    save_data(USER_PL_FILE, user_pl_balances)
    FILE_MODIFICATION_TIMES['user_pl'] = get_file_mtime(USER_PL_FILE)

def save_system_points():
    save_system_total_points(system_total_points)
    FILE_MODIFICATION_TIMES['system_points'] = get_file_mtime(SYSTEM_POINTS_FILE)

def save_orders():
    save_data(ORDERS_FILE, orders)
    FILE_MODIFICATION_TIMES['orders'] = get_file_mtime(ORDERS_FILE)

def save_user_pay_passwords():
    save_data(USER_PAY_PASSWORDS_FILE, user_pay_passwords)
    FILE_MODIFICATION_TIMES['pay_password'] = get_file_mtime(USER_PAY_PASSWORDS_FILE)

def save_user_code_limits():
    save_data(USER_CODE_LIMITS_FILE, user_code_limits)
    FILE_MODIFICATION_TIMES['code_limits'] = get_file_mtime(USER_CODE_LIMITS_FILE)

def save_coupons():
    save_data(COUPONS_FILE, coupons)
    FILE_MODIFICATION_TIMES['coupons'] = get_file_mtime(COUPONS_FILE)

def save_gateway_cards():
    save_data(GATEWAY_CARDS_FILE, gateway_cards)
    FILE_MODIFICATION_TIMES['gateway_cards'] = get_file_mtime(GATEWAY_CARDS_FILE)

def save_user_coupons():
    save_data(USER_COUPONS_FILE, user_coupons)
    FILE_MODIFICATION_TIMES['user_coupons'] = get_file_mtime(USER_COUPONS_FILE)

def save_coupon_grants():
    save_data(COUPON_GRANTS_FILE, coupon_grants)
    FILE_MODIFICATION_TIMES['coupon_grants'] = get_file_mtime(COUPON_GRANTS_FILE)

def save_pl_transfers():
    save_data(PL_TRANSFERS_FILE, pl_transfers)
    FILE_MODIFICATION_TIMES['pl_transfers'] = get_file_mtime(PL_TRANSFERS_FILE)

def save_nav_data():
    save_data(NAV_DATA_FILE, nav_data)
    FILE_MODIFICATION_TIMES['nav_data'] = get_file_mtime(NAV_DATA_FILE)

def save_nav_holdings():
    save_data(NAV_HOLDINGS_FILE, nav_holdings)
    FILE_MODIFICATION_TIMES['nav_holdings'] = get_file_mtime(NAV_HOLDINGS_FILE)

def save_nav_history():
    save_data(NAV_HISTORY_FILE, nav_history)
    FILE_MODIFICATION_TIMES['nav_history'] = get_file_mtime(NAV_HISTORY_FILE)

def save_gateway_stock():
    save_data(GATEWAY_STOCK_FILE, gateway_stock)
    FILE_MODIFICATION_TIMES['gateway_stock'] = get_file_mtime(GATEWAY_STOCK_FILE)

def migrate_user_data():
    modified = False
    for username, user_data in users.items():
        if 'lastAttendanceTimestamp' not in user_data:
            user_data['lastAttendanceTimestamp'] = 0
            modified = True
        if 'attendanceClaimedTotalCycles' not in user_data:
            user_data['attendanceClaimedTotalCycles'] = {}
            modified = True
        if 'attendanceClaimedConsecutiveCycles' not in user_data:
            user_data['attendanceClaimedConsecutiveCycles'] = {}
            modified = True
        if 'specialPointCodePurchaseCount' not in user_data:
            user_data['specialPointCodePurchaseCount'] = 0
            user_data['lastSpecialPointCodePurchaseDate'] = ''
            modified = True
        if 'coupon_usage_count' not in user_data:
            user_data['coupon_usage_count'] = 0
            modified = True
        if 'makeup_code_used_count' not in user_data:
            user_data['makeup_code_used_count'] = 0
            modified = True
        if 'gamblers_code_purchase_count' not in user_data:
            user_data['gamblers_code_purchase_count'] = 0
            user_data['last_gamblers_purchase_date'] = ''
            modified = True
        if 'box_code_purchase_count' not in user_data:
            user_data['box_code_purchase_count'] = 0
            user_data['last_box_purchase_date'] = ''
            modified = True
        if 'plcard_code_purchase_count' not in user_data:
            user_data['plcard_code_purchase_count'] = 0
            user_data['last_plcard_purchase_date'] = ''
            modified = True
        if 'email_verified' not in user_data:
            user_data['email_verified'] = False
            modified = True
        if 'email_verified_at' not in user_data:
            user_data['email_verified_at'] = 0
            modified = True
        if 'email_changed' not in user_data:
            user_data['email_changed'] = False
            modified = True
        if 'email_changed_at' not in user_data:
            user_data['email_changed_at'] = 0
            modified = True
        if 'old_email' not in user_data:
            user_data['old_email'] = ''
            modified = True
        if 'membership' not in user_data:
            user_data['membership'] = {
                'is_member': False,
                'activated_at': 0,
                'expires_at': 0,
                'lifetime': True
            }
            modified = True
        else:
            membership = user_data['membership']
            if 'lifetime' not in membership:
                membership['lifetime'] = True
                modified = True
            if 'activated_at' not in membership:
                membership['activated_at'] = 0
                modified = True
            if 'expires_at' not in membership:
                membership['expires_at'] = 0
                modified = True
    if modified:
        save_users()

PL_MIN_RATE = 0.02
PL_MAX_RATE = 0.42
PL_FLUCTUATION_INTERVAL = 1800
PL_EXCHANGE_FEE = 0.05
RATE_REFRESH_COOLDOWN = 60
user_rate_refresh = {}

FUND_MIN_RATE = 0.0058
FUND_MAX_RATE = 0.8752

NAV_MIN = 0.0018
NAV_MAX = 0.5768

GATEWAY_STOCK_DAILY = {
    'hour': 600,
    'day': 250,
    'week': 25,
    'permanent': 8
}

POOL_BASE_MIN = 10000
POOL_BASE_MAX = 50000
POOL_GROWTH_FACTOR = 1.05
COOLDOWN_HOURS = 24
CHECKIN_BONUS_MIN = 300
CHECKIN_BONUS_MAX = 1800
NEW_USER_PROTECT_DAYS = 14
NEW_USER_BONUS_RATIO = 0.15
SYSTEM_POINTS_BURN_THRESHOLD = 85000

def get_gateway_stock_today():
    today = datetime.now().strftime('%Y-%m-%d')
    if today not in gateway_stock:
        gateway_stock[today] = {
            'hour': GATEWAY_STOCK_DAILY['hour'],
            'day': GATEWAY_STOCK_DAILY['day'],
            'week': GATEWAY_STOCK_DAILY['week'],
            'permanent': GATEWAY_STOCK_DAILY['permanent']
        }
        save_gateway_stock()
    return gateway_stock[today]

def check_gateway_stock(card_type):
    stock = get_gateway_stock_today()
    return stock.get(card_type, 0) > 0

def consume_gateway_stock(card_type):
    today = datetime.now().strftime('%Y-%m-%d')
    if today not in gateway_stock:
        gateway_stock[today] = {
            'hour': GATEWAY_STOCK_DAILY['hour'],
            'day': GATEWAY_STOCK_DAILY['day'],
            'week': GATEWAY_STOCK_DAILY['week'],
            'permanent': GATEWAY_STOCK_DAILY['permanent']
        }
    if gateway_stock[today].get(card_type, 0) <= 0:
        return False
    gateway_stock[today][card_type] -= 1
    save_gateway_stock()
    return True

def get_current_pl_rate():
    current_time = int(time.time())
    rate_data = pl_rate_data.get('rate_history', [])
    if rate_data:
        latest = rate_data[-1]
        if current_time - latest.get('timestamp', 0) < PL_FLUCTUATION_INTERVAL:
            return latest.get('rate', 0.07)
    return generate_new_pl_rate()

def generate_new_pl_rate():
    current_time = int(time.time())
    period = current_time // PL_FLUCTUATION_INTERVAL
    seed_bytes = str(period).encode() + b'pl_rate_salt_2024'
    seed_hash = hashlib.md5(seed_bytes).hexdigest()
    seed_int = int(seed_hash[:8], 16)
    random.seed(seed_int)
    raw_rate = random.uniform(PL_MIN_RATE, PL_MAX_RATE)
    random.seed()
    rate = round(raw_rate, 4)

    if 'rate_history' not in pl_rate_data:
        pl_rate_data['rate_history'] = []

    pl_rate_data['rate_history'].append({
        'timestamp': current_time,
        'rate': rate,
        'period': period
    })

    if len(pl_rate_data['rate_history']) > 1000:
        pl_rate_data['rate_history'] = pl_rate_data['rate_history'][-1000:]

    save_pl_rate_data()
    return rate

def get_current_fund_rate():
    current_time = int(time.time())
    today = datetime.now().strftime('%Y-%m-%d')
    rate_data = fund_rate.get(today)
    if rate_data:
        return rate_data.get('rate', 0.0058)
    return generate_new_fund_rate()

def generate_new_fund_rate():
    today = datetime.now().strftime('%Y-%m-%d')
    import hashlib
    seed_bytes = today.encode() + b'fund_rate_salt_2024'
    seed_hash = hashlib.md5(seed_bytes).hexdigest()
    seed_int = int(seed_hash[:8], 16)
    random.seed(seed_int)
    rate = round(random.uniform(FUND_MIN_RATE, FUND_MAX_RATE), 4)
    random.seed()
    fund_rate[today] = {
        'rate': rate,
        'date': today,
        'updated_at': int(time.time() * 1000)
    }
    save_fund_rate()
    return rate

def get_user_pl_balance(username):
    return user_pl_balances.get(username, {}).get('balance', 0)

def update_user_pl_balance(username, amount, operation_type, reference_id=''):
    if username not in user_pl_balances:
        user_pl_balances[username] = {
            'balance': 0,
            'total_earned': 0,
            'total_spent': 0,
            'last_updated': int(time.time())
        }
    user_pl_balances[username]['balance'] = round(user_pl_balances[username]['balance'] + amount, 4)
    user_pl_balances[username]['last_updated'] = int(time.time())
    if amount > 0:
        user_pl_balances[username]['total_earned'] = round(user_pl_balances[username].get('total_earned', 0) + amount, 4)
    else:
        user_pl_balances[username]['total_spent'] = round(user_pl_balances[username].get('total_spent', 0) + abs(amount), 4)
    record_id = f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
    pl_exchange_records[record_id] = {
        'username': username,
        'amount': round(amount, 4),
        'operation_type': operation_type,
        'reference_id': reference_id,
        'timestamp': int(time.time() * 1000),
        'rate': get_current_pl_rate()
    }
    save_user_pl_balances()
    save_pl_exchange_records()
    return True

def get_user_fund_balance(username):
    user_fund = fund_data.get(username, {})
    return user_fund.get('balance', 0)

def get_user_fund_total_interest(username):
    user_fund = fund_data.get(username, {})
    return user_fund.get('total_interest', 0)

def get_user_fund_today_interest(username):
    user_fund = fund_data.get(username, {})
    today = datetime.now().strftime('%Y-%m-%d')
    return user_fund.get('today_interest', {}).get(today, 0)

def get_user_fund_total_points(username):
    user_data = users.get(username, {})
    total_points = user_data.get('totalPoints', 0)
    fund_balance = get_user_fund_balance(username)
    return total_points + fund_balance

def fund_deposit(username, amount):
    if amount <= 0:
        return None, '存入金额必须大于0'
    user_data = users.get(username)
    if not user_data:
        return None, '用户不存在'
    if user_data.get('totalPoints', 0) < amount:
        return None, f'积分不足，需要{amount}积分，当前{user_data.get("totalPoints", 0):.2f}积分'
    user_data['totalPoints'] = round(user_data['totalPoints'] - amount, 2)
    save_users()
    if username not in fund_data:
        fund_data[username] = {
            'balance': 0,
            'total_interest': 0,
            'today_interest': {},
            'last_interest_date': ''
        }
    fund_data[username]['balance'] = round(fund_data[username]['balance'] + amount, 2)
    save_fund_data()
    record_id = f"fund_{int(time.time()*1000)}_{random.randint(1000,9999)}"
    fund_history[record_id] = {
        'id': record_id,
        'username': username,
        'type': 'deposit',
        'amount': round(amount, 2),
        'timestamp': int(time.time() * 1000)
    }
    save_fund_history()
    return {'balance': fund_data[username]['balance']}, None

def fund_withdraw(username, amount):
    if amount <= 0:
        return None, '提取金额必须大于0'
    user_fund = fund_data.get(username, {})
    if user_fund.get('balance', 0) < amount:
        return None, f'理财余额不足，需要{amount}积分，当前{user_fund.get("balance", 0):.2f}积分'
    user_data = users.get(username)
    if not user_data:
        return None, '用户不存在'
    user_data['totalPoints'] = round(user_data['totalPoints'] + amount, 2)
    save_users()
    fund_data[username]['balance'] = round(fund_data[username]['balance'] - amount, 2)
    save_fund_data()
    record_id = f"fund_{int(time.time()*1000)}_{random.randint(1000,9999)}"
    fund_history[record_id] = {
        'id': record_id,
        'username': username,
        'type': 'withdraw',
        'amount': round(amount, 2),
        'timestamp': int(time.time() * 1000)
    }
    save_fund_history()
    return {'balance': fund_data[username]['balance']}, None

def calculate_fund_interest(username):
    user_fund = fund_data.get(username, {})
    balance = user_fund.get('balance', 0)
    if balance <= 0:
        return 0
    today = datetime.now().strftime('%Y-%m-%d')
    last_date = user_fund.get('last_interest_date', '')
    if last_date == today:
        return user_fund.get('today_interest', {}).get(today, 0)
    rate = get_current_fund_rate()
    interest = (balance / 10000) * rate
    if interest < 0.01:
        interest = 0
    else:
        interest = round(interest, 4)
    if interest > 0:
        if 'today_interest' not in user_fund:
            user_fund['today_interest'] = {}
        user_fund['today_interest'][today] = interest
        user_fund['total_interest'] = round(user_fund.get('total_interest', 0) + interest, 2)
        fund_data[username]['balance'] = round(fund_data[username]['balance'] + interest, 2)
        record_id = f"fund_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        fund_history[record_id] = {
            'id': record_id,
            'username': username,
            'type': 'interest',
            'amount': round(interest, 2),
            'timestamp': int(time.time() * 1000)
        }
        save_fund_history()
    fund_data[username]['last_interest_date'] = today
    save_fund_data()
    return interest

def fund_interest_loop():
    while True:
        time.sleep(3600)
        try:
            for username in list(fund_data.keys()):
                calculate_fund_interest(username)
        except Exception as e:
            log.error(f"Fund interest loop error: {e}")

fund_interest_thread = threading.Thread(target=fund_interest_loop, daemon=True)
fund_interest_thread.start()

def exchange_points_to_pl(username, points_amount):
    if username not in users:
        return None, '用户不存在'
    user_data = users[username]
    if user_data.get('totalPoints', 0) < points_amount:
        return None, f'积分不足，需要{points_amount}积分'
    rate = get_current_pl_rate()
    pl_amount = round(points_amount * rate, 4)
    points_to_pl_fee_rate = 0.05
    fee = round(pl_amount * points_to_pl_fee_rate, 4)
    pl_received = round(pl_amount - fee, 4)
    if pl_received <= 0:
        return None, '兑换数量太少，请增加积分数量'
    deduct_user_points(username, points_amount)
    update_user_pl_balance(username, pl_received, 'points_to_pl', f'pts_{points_amount}')
    add_system_total_points(fee)
    return {
        'points_used': points_amount,
        'rate': rate,
        'pl_gross': pl_amount,
        'pl_fee': fee,
        'pl_received': pl_received,
        'new_pl_balance': get_user_pl_balance(username),
        'fee_rate': points_to_pl_fee_rate * 100
    }, None

def exchange_pl_to_points(username, pl_amount):
    if username not in users:
        return None, '用户不存在'
    current_balance = get_user_pl_balance(username)
    if current_balance < pl_amount:
        return None, f'PL余额不足，需要{pl_amount}PL'
    rate = get_current_pl_rate()
    points_gross = round(pl_amount / rate, 2)
    pl_to_points_fee_rate = 0.08
    fee = round(points_gross * pl_to_points_fee_rate, 2)
    points_received = round(points_gross - fee, 2)
    if points_received <= 0:
        return None, '兑换数量太少，请增加PL数量'
    update_user_pl_balance(username, -pl_amount, 'pl_to_points', f'pl_{pl_amount}')
    add_points_without_limit(username, points_received)
    add_system_total_points(fee)
    return {
        'pl_used': pl_amount,
        'rate': rate,
        'points_gross': points_gross,
        'points_fee': fee,
        'points_received': points_received,
        'new_pl_balance': get_user_pl_balance(username),
        'fee_rate': pl_to_points_fee_rate * 100
    }, None

def transfer_pl(username, target_username, amount, password):
    if username not in users:
        return None, '用户不存在'
    if target_username not in users:
        return None, '目标用户不存在'
    if username == target_username:
        return None, '不能转账给自己'
    if amount < 0.1:
        return None, '转账金额不能低于0.1PL'
    user_data = users[username]
    if not bcrypt.check_password_hash(user_data['password'], password):
        return None, '密码错误'
    current_balance = get_user_pl_balance(username)
    if current_balance < amount:
        return None, f'PL余额不足，需要{amount}PL'
    if not has_pay_password(username):
        return None, '请先设置支付密码'
    update_user_pl_balance(username, -amount, 'pl_transfer_out', f'to_{target_username}')
    update_user_pl_balance(target_username, amount, 'pl_transfer_in', f'from_{username}')
    transfer_id = f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
    pl_transfers[transfer_id] = {
        'transfer_id': transfer_id,
        'from_username': username,
        'to_username': target_username,
        'amount': round(amount, 4),
        'rate': get_current_pl_rate(),
        'timestamp': int(time.time() * 1000),
        'status': 'completed'
    }
    save_pl_transfers()
    return {
        'transfer_id': transfer_id,
        'amount': amount,
        'to_username': target_username,
        'new_balance': get_user_pl_balance(username)
    }, None

def pl_rate_updater():
    while True:
        time.sleep(PL_FLUCTUATION_INTERVAL)
        generate_new_pl_rate()

pl_thread = threading.Thread(target=pl_rate_updater, daemon=True)
pl_thread.start()

used_phone_numbers = set()

def load_used_phone_numbers():
    for user_records in phone_records.values():
        for record in user_records:
            if record.get('phoneNumber') and record.get('used', False):
                used_phone_numbers.add(record['phoneNumber'])

load_used_phone_numbers()

def validate_username(username):
    if not username or len(username) < 3 or len(username) > 20:
        return False
    if not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fa5]+$', username):
        return False
    return True

def validate_email(email):
    if not email or len(email) > 100:
        return False
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return False
    return True

def validate_password(password):
    if not password or len(password) < 8:
        return False
    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'[0-9]', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    type_count = sum([has_upper, has_lower, has_digit, has_special])
    return type_count >= 2

def validate_cdk_name(name):
    if not name or len(name) < 3 or len(name) > 32:
        return False
    if not re.match(r'^[a-z0-9]+$', name):
        return False
    return True

def hash_id_number(id_number):
    return hashlib.sha256(id_number.encode()).hexdigest()

def mask_id_number(id_number):
    if not id_number or len(id_number) != 18:
        return id_number
    return id_number[:3] + '*****' + id_number[14:]

def generate_reset_code():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    while True:
        parts = []
        for _ in range(4):
            part = ''.join(random.choice(chars) for _ in range(4))
            parts.append(part)
        code = '-'.join(parts)
        existing_codes = set(reset_codes.keys()) | set(point_codes.keys()) | set(premium_point_codes.keys()) | set(boost_codes.keys()) | set(cancellation_codes.keys()) | set(special_point_codes.keys()) | set(makeup_codes.keys()) | set(gamblers_codes.keys()) | set(box_codes.keys()) | set(plcard_codes.keys()) | set(premium_boost_codes.keys())
        if code not in existing_codes:
            return code

def generate_point_code():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    while True:
        parts = []
        for _ in range(4):
            part = ''.join(random.choice(chars) for _ in range(4))
            parts.append(part)
        code = '-'.join(parts)
        existing_codes = set(reset_codes.keys()) | set(point_codes.keys()) | set(premium_point_codes.keys()) | set(boost_codes.keys()) | set(cancellation_codes.keys()) | set(special_point_codes.keys()) | set(makeup_codes.keys()) | set(gamblers_codes.keys()) | set(box_codes.keys()) | set(plcard_codes.keys()) | set(premium_boost_codes.keys())
        if code not in existing_codes:
            return code

def generate_gateway_key():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    while True:
        parts = []
        for _ in range(4):
            part = ''.join(random.choice(chars) for _ in range(4))
            parts.append(part)
        key = '-'.join(parts)
        if key not in gateway_cards:
            return key

def generate_premium_point_code():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    while True:
        parts = []
        for _ in range(4):
            part = ''.join(random.choice(chars) for _ in range(4))
            parts.append(part)
        code = '-'.join(parts)
        existing_codes = set(reset_codes.keys()) | set(point_codes.keys()) | set(premium_point_codes.keys()) | set(boost_codes.keys()) | set(cancellation_codes.keys()) | set(special_point_codes.keys()) | set(makeup_codes.keys()) | set(gamblers_codes.keys()) | set(box_codes.keys()) | set(plcard_codes.keys()) | set(premium_boost_codes.keys())
        if code not in existing_codes:
            return code

def generate_boost_code():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    while True:
        parts = []
        for _ in range(4):
            part = ''.join(random.choice(chars) for _ in range(4))
            parts.append(part)
        code = '-'.join(parts)
        existing_codes = set(reset_codes.keys()) | set(point_codes.keys()) | set(premium_point_codes.keys()) | set(boost_codes.keys()) | set(cancellation_codes.keys()) | set(special_point_codes.keys()) | set(makeup_codes.keys()) | set(gamblers_codes.keys()) | set(box_codes.keys()) | set(plcard_codes.keys()) | set(premium_boost_codes.keys())
        if code not in existing_codes:
            return code

def generate_cancellation_code():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    while True:
        parts = []
        for _ in range(4):
            part = ''.join(random.choice(chars) for _ in range(4))
            parts.append(part)
        code = '-'.join(parts)
        existing_codes = set(reset_codes.keys()) | set(point_codes.keys()) | set(premium_point_codes.keys()) | set(boost_codes.keys()) | set(cancellation_codes.keys()) | set(special_point_codes.keys()) | set(makeup_codes.keys()) | set(gamblers_codes.keys()) | set(box_codes.keys()) | set(plcard_codes.keys()) | set(premium_boost_codes.keys())
        if code not in existing_codes:
            return code

def generate_special_point_code():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    while True:
        parts = []
        for _ in range(4):
            part = ''.join(random.choice(chars) for _ in range(4))
            parts.append(part)
        code = '-'.join(parts)
        existing_codes = set(reset_codes.keys()) | set(point_codes.keys()) | set(premium_point_codes.keys()) | set(boost_codes.keys()) | set(cancellation_codes.keys()) | set(special_point_codes.keys()) | set(makeup_codes.keys()) | set(gamblers_codes.keys()) | set(box_codes.keys()) | set(plcard_codes.keys()) | set(premium_boost_codes.keys())
        if code not in existing_codes:
            return code

def generate_makeup_code():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    while True:
        parts = []
        for _ in range(4):
            part = ''.join(random.choice(chars) for _ in range(4))
            parts.append(part)
        code = '-'.join(parts)
        existing_codes = set(reset_codes.keys()) | set(point_codes.keys()) | set(premium_point_codes.keys()) | set(boost_codes.keys()) | set(cancellation_codes.keys()) | set(special_point_codes.keys()) | set(makeup_codes.keys()) | set(gamblers_codes.keys()) | set(box_codes.keys()) | set(plcard_codes.keys()) | set(premium_boost_codes.keys())
        if code not in existing_codes:
            return code

def generate_gamblers_code():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    while True:
        parts = []
        for _ in range(4):
            part = ''.join(random.choice(chars) for _ in range(4))
            parts.append(part)
        code = '-'.join(parts)
        existing_codes = set(reset_codes.keys()) | set(point_codes.keys()) | set(premium_point_codes.keys()) | set(boost_codes.keys()) | set(cancellation_codes.keys()) | set(special_point_codes.keys()) | set(makeup_codes.keys()) | set(gamblers_codes.keys()) | set(box_codes.keys()) | set(plcard_codes.keys()) | set(premium_boost_codes.keys())
        if code not in existing_codes:
            return code

def generate_box_code():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    while True:
        parts = []
        for _ in range(4):
            part = ''.join(random.choice(chars) for _ in range(4))
            parts.append(part)
        code = '-'.join(parts)
        existing_codes = set(reset_codes.keys()) | set(point_codes.keys()) | set(premium_point_codes.keys()) | set(boost_codes.keys()) | set(cancellation_codes.keys()) | set(special_point_codes.keys()) | set(makeup_codes.keys()) | set(gamblers_codes.keys()) | set(box_codes.keys()) | set(plcard_codes.keys()) | set(premium_boost_codes.keys())
        if code not in existing_codes:
            return code

def generate_plcard_code():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    while True:
        parts = []
        for _ in range(4):
            part = ''.join(random.choice(chars) for _ in range(4))
            parts.append(part)
        code = '-'.join(parts)
        existing_codes = set(reset_codes.keys()) | set(point_codes.keys()) | set(premium_point_codes.keys()) | set(boost_codes.keys()) | set(cancellation_codes.keys()) | set(special_point_codes.keys()) | set(makeup_codes.keys()) | set(gamblers_codes.keys()) | set(box_codes.keys()) | set(plcard_codes.keys()) | set(premium_boost_codes.keys())
        if code not in existing_codes:
            return code

def generate_premium_boost_code():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    while True:
        parts = []
        for _ in range(4):
            part = ''.join(random.choice(chars) for _ in range(4))
            parts.append(part)
        code = '-'.join(parts)
        existing_codes = set(reset_codes.keys()) | set(point_codes.keys()) | set(premium_point_codes.keys()) | set(boost_codes.keys()) | set(cancellation_codes.keys()) | set(special_point_codes.keys()) | set(makeup_codes.keys()) | set(gamblers_codes.keys()) | set(box_codes.keys()) | set(plcard_codes.keys()) | set(premium_boost_codes.keys())
        if code not in existing_codes:
            return code

def generate_phone_number():
    prefixes = ['130', '131', '132', '133', '134', '135', '136', '137', '138', '139',
                '150', '151', '152', '153', '155', '156', '157', '158', '159',
                '180', '181', '182', '183', '184', '185', '186', '187', '188', '189']
    max_attempts = 100

    for _ in range(max_attempts):
        random_prefix = random.choice(prefixes)
        suffix = str(random.randint(0, 99999999)).zfill(8)
        phone_number = random_prefix + suffix

        if phone_number not in used_phone_numbers:
            used_phone_numbers.add(phone_number)
            return phone_number

    timestamp = str(int(time.time() * 1000))[-8:]
    random_suffix = str(random.randint(0, 9999)).zfill(4)
    fallback_phone = f'139{timestamp}{random_suffix}'
    if fallback_phone not in used_phone_numbers:
        used_phone_numbers.add(fallback_phone)
        return fallback_phone

    return f'155{str(int(time.time() * 1000))[-8:]}'

def generate_auth_code(phone_number):
    hash_input = f"{phone_number}{time.time()}{random.random()}"
    raw_code = hashlib.md5(hash_input.encode()).hexdigest()[:8].upper()
    return raw_code

def is_new_user(username):
    if username not in users:
        return False
    created_at = users[username].get('createdAt')
    if not created_at:
        return False
    try:
        created_time = datetime.fromisoformat(created_at)
        return (datetime.now() - created_time) < timedelta(hours=24)
    except:
        return False

def get_discounted_price(original_price, username):
    """
    Get the final price after applying new user discount and tiered multiplier.
    This uses the dynamic pricing system.
    """
    return get_final_price(original_price, username)

def is_bonus_period():
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute

    if current_hour == 13 and 0 <= current_minute <= 39:
        return True
    if current_hour == 0 and 0 <= current_minute <= 39:
        return True

    return False

def get_bonus_multiplier():
    if is_bonus_period():
        return 1.3
    return 1.0

def get_user_boost_multiplier(username):
    current_time = int(time.time())
    boost_data = user_boosts.get(username)
    if boost_data and boost_data.get('expiresAt', 0) > current_time:
        boost_type = boost_data.get('boost_type', 'normal')
        if boost_type == 'premium':
            return 1.9
        return 1.5
    if boost_data:
        del user_boosts[username]
        save_user_boosts()
    return 1.0

def get_total_multiplier(username):
    bonus_mult = get_bonus_multiplier()
    boost_mult = get_user_boost_multiplier(username)
    return round(bonus_mult * boost_mult, 2)

def check_and_award_daily_bonus(username):
    user_data = users.get(username)
    if not user_data:
        return
    daily_earned = user_data.get('dailyEarnedPoints', 0)
    if daily_earned >= 14:
        user_data['dailyEarnedPoints'] = 14
        if not user_data.get('dailyBonusAwarded', False):
            point_code = generate_point_code()
            mail_attachment_id = f"mail_{int(time.time()*1000)}_{random.randint(1000,9999)}"
            mail_attachments[mail_attachment_id] = {
                'id': mail_attachment_id,
                'username': username,
                'type': 'point_code',
                'code': point_code,
                'used': False,
                'created_at': int(time.time() * 1000),
                'expires_at': int(time.time() * 1000) + 28800000,
                'title': '每日奖励-普通积分卡密',
                'description': '恭喜您达到今日14积分上限，获得普通积分卡密1张',
                'claimed': False,
                'claimed_at': 0,
                'source': 'daily_bonus'
            }
            save_mail_attachments()
            user_data['dailyBonusAwarded'] = True
            user_data['dailyBonusCode'] = point_code
            save_users()

def reset_daily_points_if_needed(username):
    today = datetime.now().strftime('%Y-%m-%d')
    user_data = users.get(username)
    if not user_data:
        return False
    last_login_date = user_data.get('lastLoginDate', '')
    last_earned_date = user_data.get('lastEarnedDate', '')
    today = datetime.now().strftime('%Y-%m-%d')

    if last_login_date != today:
        if user_data.get('dailyEarnedPoints', 0) > 0:
            user_data['dailyEarnedPoints'] = 0
        if user_data.get('dailyBonusAwarded', False):
            user_data['dailyBonusAwarded'] = False
            user_data['dailyBonusCode'] = None
        user_data['lastLoginDate'] = today
        save_users()
        return True

    if last_earned_date != today:
        user_data['dailyEarnedPoints'] = 0
        user_data['lastEarnedDate'] = today
        if user_data.get('dailyBonusAwarded', False):
            user_data['dailyBonusAwarded'] = False
            user_data['dailyBonusCode'] = None
        save_users()
        return True

    return False

def update_earned_points(username, points_to_add, bypass_limit=False):
    today = datetime.now().strftime('%Y-%m-%d')
    if username not in users:
        return False
    user_data = users[username]
    if 'dailyEarnedPoints' not in user_data:
        user_data['dailyEarnedPoints'] = 0
    if 'lastEarnedDate' not in user_data:
        user_data['lastEarnedDate'] = today
    if user_data['lastEarnedDate'] != today:
        user_data['dailyEarnedPoints'] = 0
        user_data['lastEarnedDate'] = today
        if user_data.get('dailyBonusAwarded', False):
            user_data['dailyBonusAwarded'] = False
            user_data['dailyBonusCode'] = None
    bonus_mult = get_bonus_multiplier()
    boost_mult = get_user_boost_multiplier(username)
    if bonus_mult > 1.0 and boost_mult > 1.0:
        points_to_add = round(points_to_add * bonus_mult * boost_mult, 2)
    elif bonus_mult > 1.0:
        points_to_add = round(points_to_add * bonus_mult, 2)
    elif boost_mult > 1.0:
        points_to_add = round(points_to_add * boost_mult, 2)
    if not bypass_limit:
        current_daily = user_data['dailyEarnedPoints']
        new_daily = current_daily + points_to_add
        if new_daily > 14:
            overflow = new_daily - 14
            points_to_add = points_to_add - overflow
            new_daily = 14
            if points_to_add <= 0:
                return False
        user_data['dailyEarnedPoints'] = round(new_daily, 2)
    else:
        if 'unlimitedPoints' not in user_data:
            user_data['unlimitedPoints'] = 0
        user_data['unlimitedPoints'] = round(user_data.get('unlimitedPoints', 0) + points_to_add, 2)
    net_points, tax = calculate_high_balance_tax(username, points_to_add)
    if 'totalPoints' not in user_data:
        user_data['totalPoints'] = 0
    user_data['totalPoints'] = round(user_data['totalPoints'] + net_points, 2)
    if tax > 0:
        add_system_total_points(tax)
        log.info(f"High balance tax applied (earned) for {username}: earned={points_to_add}, tax={tax}, net={net_points}")
    save_users()
    if not bypass_limit:
        check_and_award_daily_bonus(username)
    return True

def add_points_without_limit(username, points_to_add):
    if username not in users:
        return False
    user_data = users[username]
    net_points, tax = calculate_high_balance_tax(username, points_to_add)
    if 'totalPoints' not in user_data:
        user_data['totalPoints'] = 0
    user_data['totalPoints'] = round(user_data['totalPoints'] + net_points, 2)
    if 'unlimitedPoints' not in user_data:
        user_data['unlimitedPoints'] = 0
    user_data['unlimitedPoints'] = round(user_data.get('unlimitedPoints', 0) + net_points, 2)
    if tax > 0:
        add_system_total_points(tax)
        log.info(f"High balance tax applied (unlimited) for {username}: earned={points_to_add}, tax={tax}, net={net_points}")
    save_users()
    return True

def deduct_user_points(username, points_to_deduct):
    if username not in users:
        return False
    user_data = users[username]
    current_total = user_data.get('totalPoints', 0)
    if current_total < points_to_deduct:
        return False
    user_data['totalPoints'] = round(current_total - points_to_deduct, 2)
    save_users()
    return True

def check_and_award_attendance_rewards(username):
    user_data = users.get(username)
    if not user_data:
        return None

    total_days = user_data.get('attendanceTotalDays', 0)
    consecutive_days = user_data.get('attendanceConsecutiveDays', 0)
    rewards = []
    claimed_total_cycles = user_data.get('attendanceClaimedTotalCycles', {})
    claimed_consecutive_cycles = user_data.get('attendanceClaimedConsecutiveCycles', {})
    
    pending_attachments = []

    if total_days >= 3 and total_days % 30 == 3:
        cycle = (total_days - 3) // 30 + 1
        cycle_key = f'total_3_cycle_{cycle}'
        if not claimed_total_cycles.get(cycle_key):
            add_points_without_limit(username, 1.0)
            rewards.append({'type': 'points', 'value': 1.0, 'message': f'累计签到{total_days}天，获得1.0积分'})
            claimed_total_cycles[cycle_key] = True

    if total_days >= 7 and total_days % 30 == 7:
        cycle = (total_days - 7) // 30 + 1
        cycle_key = f'total_7_cycle_{cycle}'
        if not claimed_total_cycles.get(cycle_key):
            add_points_without_limit(username, 1.8)
            rewards.append({'type': 'points', 'value': 1.8, 'message': f'累计签到{total_days}天，获得1.8积分'})
            claimed_total_cycles[cycle_key] = True

    if total_days >= 15 and total_days % 30 == 15:
        cycle = (total_days - 15) // 30 + 1
        cycle_key = f'total_15_cycle_{cycle}'
        if not claimed_total_cycles.get(cycle_key):
            add_points_without_limit(username, 3.0)
            rewards.append({'type': 'points', 'value': 3.0, 'message': f'累计签到{total_days}天，获得3.0积分'})
            claimed_total_cycles[cycle_key] = True

    if total_days >= 28 and total_days % 30 == 28:
        cycle = (total_days - 28) // 30 + 1
        cycle_key = f'total_28_cycle_{cycle}'
        if not claimed_total_cycles.get(cycle_key):
            add_points_without_limit(username, 8.8)
            rewards.append({'type': 'points', 'value': 8.8, 'message': f'累计签到{total_days}天，获得8.8积分'})
            boost_code = generate_boost_code()
            pending_attachments.append({
                'type': 'boost_code',
                'code': boost_code,
                'title': '签到奖励-积分加成卡密',
                'description': f'累计签到{total_days}天，获得积分加成卡密1张'
            })
            rewards.append({'type': 'boost_code', 'code': boost_code, 'message': f'累计签到{total_days}天，获得积分加成卡密1张(已发送至邮箱)'})
            claimed_total_cycles[cycle_key] = True

    if total_days >= 30 and total_days % 30 == 0:
        cycle = total_days // 30
        cycle_key = f'total_30_cycle_{cycle}'
        if not claimed_total_cycles.get(cycle_key):
            add_points_without_limit(username, 8.8)
            rewards.append({'type': 'points', 'value': 8.8, 'message': f'累计签到{total_days}天，获得8.8积分'})
            for _ in range(cycle):
                boost_code = generate_boost_code()
                pending_attachments.append({
                    'type': 'boost_code',
                    'code': boost_code,
                    'title': '签到奖励-积分加成卡密',
                    'description': f'累计签到{total_days}天，获得积分加成卡密1张'
                })
                rewards.append({'type': 'boost_code', 'code': boost_code, 'message': f'累计签到{total_days}天，获得积分加成卡密{cycle}张(已发送至邮箱)'})
            claimed_total_cycles[cycle_key] = True

    if total_days >= 59 and total_days % 30 == 29:
        cycle = (total_days - 29) // 30 + 1
        cycle_key = f'total_59_cycle_{cycle}'
        if not claimed_total_cycles.get(cycle_key):
            add_points_without_limit(username, 20.0)
            rewards.append({'type': 'points', 'value': 20.0, 'message': f'累计签到{total_days}天，获得20.0积分'})
            for _ in range(2):
                boost_code = generate_boost_code()
                pending_attachments.append({
                    'type': 'boost_code',
                    'code': boost_code,
                    'title': '签到奖励-积分加成卡密',
                    'description': f'累计签到{total_days}天，获得积分加成卡密1张'
                })
                rewards.append({'type': 'boost_code', 'code': boost_code, 'message': f'累计签到{total_days}天，获得积分加成卡密2张(已发送至邮箱)'})
            claimed_total_cycles[cycle_key] = True

    if total_days >= 99 and total_days % 30 == 9:
        cycle = (total_days - 9) // 30 + 1
        cycle_key = f'total_99_cycle_{cycle}'
        if not claimed_total_cycles.get(cycle_key):
            add_points_without_limit(username, 38.0)
            rewards.append({'type': 'points', 'value': 38.0, 'message': f'累计签到{total_days}天，获得38.0积分'})
            for _ in range(3):
                boost_code = generate_boost_code()
                pending_attachments.append({
                    'type': 'boost_code',
                    'code': boost_code,
                    'title': '签到奖励-积分加成卡密',
                    'description': f'累计签到{total_days}天，获得积分加成卡密1张'
                })
                rewards.append({'type': 'boost_code', 'code': boost_code, 'message': f'累计签到{total_days}天，获得积分加成卡密3张(已发送至邮箱)'})
            claimed_total_cycles[cycle_key] = True

    if consecutive_days >= 4 and consecutive_days % 30 == 4:
        cycle = (consecutive_days - 4) // 30 + 1
        cycle_key = f'consecutive_4_cycle_{cycle}'
        if not claimed_consecutive_cycles.get(cycle_key):
            premium_code = generate_premium_point_code()
            pending_attachments.append({
                'type': 'premium_point_code',
                'code': premium_code,
                'title': '签到奖励-高级积分卡密',
                'description': f'连续签到{consecutive_days}天，获得高级积分卡密1张'
            })
            rewards.append({'type': 'premium_code', 'code': premium_code, 'message': f'连续签到{consecutive_days}天，获得高级积分卡密1张(已发送至邮箱)'})
            claimed_consecutive_cycles[cycle_key] = True

    if consecutive_days >= 6 and consecutive_days % 30 == 6:
        cycle = (consecutive_days - 6) // 30 + 1
        cycle_key = f'consecutive_6_cycle_{cycle}'
        if not claimed_consecutive_cycles.get(cycle_key):
            for _ in range(2):
                premium_code = generate_premium_point_code()
                pending_attachments.append({
                    'type': 'premium_point_code',
                    'code': premium_code,
                    'title': '签到奖励-高级积分卡密',
                    'description': f'连续签到{consecutive_days}天，获得高级积分卡密1张'
                })
                rewards.append({'type': 'premium_code', 'code': premium_code, 'message': f'连续签到{consecutive_days}天，获得高级积分卡密2张(已发送至邮箱)'})
            claimed_consecutive_cycles[cycle_key] = True

    if consecutive_days >= 14 and consecutive_days % 30 == 14:
        cycle = (consecutive_days - 14) // 30 + 1
        cycle_key = f'consecutive_14_cycle_{cycle}'
        if not claimed_consecutive_cycles.get(cycle_key):
            for _ in range(3):
                premium_code = generate_premium_point_code()
                pending_attachments.append({
                    'type': 'premium_point_code',
                    'code': premium_code,
                    'title': '签到奖励-高级积分卡密',
                    'description': f'连续签到{consecutive_days}天，获得高级积分卡密1张'
                })
                rewards.append({'type': 'premium_code', 'code': premium_code, 'message': f'连续签到{consecutive_days}天，获得高级积分卡密3张(已发送至邮箱)'})
            claimed_consecutive_cycles[cycle_key] = True

    if consecutive_days >= 29 and consecutive_days % 30 == 29:
        cycle = (consecutive_days - 29) // 30 + 1
        cycle_key = f'consecutive_29_cycle_{cycle}'
        if not claimed_consecutive_cycles.get(cycle_key):
            for _ in range(3):
                premium_code = generate_premium_point_code()
                pending_attachments.append({
                    'type': 'premium_point_code',
                    'code': premium_code,
                    'title': '签到奖励-高级积分卡密',
                    'description': f'连续签到{consecutive_days}天，获得高级积分卡密1张'
                })
                rewards.append({'type': 'premium_code', 'code': premium_code, 'message': f'连续签到{consecutive_days}天，获得高级积分卡密3张(已发送至邮箱)'})
            for _ in range(2):
                boost_code = generate_boost_code()
                pending_attachments.append({
                    'type': 'boost_code',
                    'code': boost_code,
                    'title': '签到奖励-积分加成卡密',
                    'description': f'连续签到{consecutive_days}天，获得积分加成卡密1张'
                })
                rewards.append({'type': 'boost_code', 'code': boost_code, 'message': f'连续签到{consecutive_days}天，获得积分加成卡密2张(已发送至邮箱)'})
            reset_code = generate_reset_code()
            pending_attachments.append({
                'type': 'reset_code',
                'code': reset_code,
                'title': '签到奖励-重置密码卡密',
                'description': f'连续签到{consecutive_days}天，获得重置密码卡密1张'
            })
            rewards.append({'type': 'reset_code', 'code': reset_code, 'message': f'连续签到{consecutive_days}天，获得重置密码卡密1张(已发送至邮箱)'})
            claimed_consecutive_cycles[cycle_key] = True

    if consecutive_days >= 30 and consecutive_days % 30 == 0:
        cycle = consecutive_days // 30
        cycle_key = f'consecutive_30_cycle_{cycle}'
        if not claimed_consecutive_cycles.get(cycle_key):
            for _ in range(3):
                premium_code = generate_premium_point_code()
                pending_attachments.append({
                    'type': 'premium_point_code',
                    'code': premium_code,
                    'title': '签到奖励-高级积分卡密',
                    'description': f'连续签到{consecutive_days}天，获得高级积分卡密1张'
                })
                rewards.append({'type': 'premium_code', 'code': premium_code, 'message': f'连续签到{consecutive_days}天，获得高级积分卡密3张(已发送至邮箱)'})
            for _ in range(2):
                boost_code = generate_boost_code()
                pending_attachments.append({
                    'type': 'boost_code',
                    'code': boost_code,
                    'title': '签到奖励-积分加成卡密',
                    'description': f'连续签到{consecutive_days}天，获得积分加成卡密1张'
                })
                rewards.append({'type': 'boost_code', 'code': boost_code, 'message': f'连续签到{consecutive_days}天，获得积分加成卡密2张(已发送至邮箱)'})
            reset_code = generate_reset_code()
            pending_attachments.append({
                'type': 'reset_code',
                'code': reset_code,
                'title': '签到奖励-重置密码卡密',
                'description': f'连续签到{consecutive_days}天，获得重置密码卡密1张'
            })
            rewards.append({'type': 'reset_code', 'code': reset_code, 'message': f'连续签到{consecutive_days}天，获得重置密码卡密1张(已发送至邮箱)'})
            claimed_consecutive_cycles[cycle_key] = True

    if pending_attachments:
        if len(pending_attachments) == 1:
            att = pending_attachments[0]
            mail_attachment_id = f"mail_{int(time.time()*1000)}_{random.randint(1000,9999)}"
            mail_attachments[mail_attachment_id] = {
                'id': mail_attachment_id,
                'username': username,
                'type': att['type'],
                'code': att['code'],
                'codes': [att['code']],
                'used': False,
                'created_at': int(time.time() * 1000),
                'expires_at': int(time.time() * 1000) + 28800000,
                'title': att['title'],
                'description': att['description'],
                'claimed': False,
                'claimed_at': 0,
                'source': 'attendance_reward',
                'quantity': 1,
                'is_batch': False
            }
            save_mail_attachments()
        else:
            codes_by_type = {}
            for att in pending_attachments:
                att_type = att['type']
                if att_type not in codes_by_type:
                    codes_by_type[att_type] = []
                codes_by_type[att_type].append(att['code'])

            type_names = {
                'boost_code': '积分加成卡密',
                'premium_point_code': '高级积分卡密',
                'reset_code': '重置密码卡密',
                'point_code': '普通积分卡密',
                'special_point_code': '特殊积分卡密',
                'makeup_code': '补签卡',
                'gamblers_code': '赌神积分卡密',
                'cancellation_code': '注销卡密'
            }

            all_codes = []
            desc_lines = []
            for att_type, codes in codes_by_type.items():
                type_name = type_names.get(att_type, att_type)
                all_codes.extend(codes)
                desc_lines.append(f'{type_name} x{len(codes)}')
                for code in codes:
                    desc_lines.append(f'  {code}')

            first_att = pending_attachments[0]
            mail_attachment_id = f"mail_{int(time.time()*1000)}_{random.randint(1000,9999)}"
            mail_attachments[mail_attachment_id] = {
                'id': mail_attachment_id,
                'username': username,
                'type': 'combined_reward',
                'codes': all_codes,
                'code': all_codes[0] if all_codes else '',
                'used': False,
                'created_at': int(time.time() * 1000),
                'expires_at': int(time.time() * 1000) + 28800000,
                'title': f'签到奖励合集 ({len(pending_attachments)}项)',
                'description': f'签到获得以下奖励:\n\n' + '\n'.join(desc_lines),
                'claimed': False,
                'claimed_at': 0,
                'source': 'attendance_reward',
                'quantity': len(pending_attachments),
                'is_batch': True,
                'combined_types': list(codes_by_type.keys())
            }
            save_mail_attachments()

    if rewards:
        user_data['attendanceClaimedTotalCycles'] = claimed_total_cycles
        user_data['attendanceClaimedConsecutiveCycles'] = claimed_consecutive_cycles
        save_users()

    return rewards if rewards else None

def migrate_attendance_dates():
    modified = False
    for username, user_data in users.items():
        if 'attendance_dates' not in user_data:
            user_data['attendance_dates'] = []
            last_date = user_data.get('lastAttendanceDate', '')
            if last_date:
                user_data['attendance_dates'].append(last_date)
            modified = True
    if modified:
        save_users()

def migrate_game_membership_data():
    modified = False
    for username, user_data in users.items():
        if 'membership' not in user_data:
            user_data['membership'] = {
                'is_member': False,
                'activated_at': 0,
                'expires_at': 0,
                'lifetime': True
            }
            modified = True
        else:
            membership = user_data['membership']
            if 'lifetime' not in membership:
                membership['lifetime'] = True
                modified = True
            if 'activated_at' not in membership:
                membership['activated_at'] = 0
                modified = True
            if 'expires_at' not in membership:
                membership['expires_at'] = 0
                modified = True
    if modified:
        save_users()
        log.info("游戏会员数据迁移完成")
    return modified

def migrate_first_attendance_date():
    modified = False
    for username, user_data in users.items():
        if 'firstAttendanceDate' not in user_data:
            last_date = user_data.get('lastAttendanceDate', '')
            if last_date:
                user_data['firstAttendanceDate'] = last_date
                modified = True
            else:
                user_data['firstAttendanceDate'] = ''
                modified = True
        if 'attendance_dates' in user_data:
            del user_data['attendance_dates']
            modified = True
    if modified:
        save_users()

def check_identity_verified(username):
    verification = identity_verifications.get(username)
    if verification and verification.get('verified', False):
        return True
    return False

def get_user_restrictions(username):
    if username not in restricted_users:
        return {'login': False, 'mall': False, 'generate_phone': False}
    return restricted_users[username].get('restrictions', {'login': False, 'mall': False, 'generate_phone': False})

def is_login_restricted(username):
    restrictions = get_user_restrictions(username)
    return restrictions.get('login', False)

def is_mall_restricted(username):
    restrictions = get_user_restrictions(username)
    return restrictions.get('mall', False)

def is_generate_phone_restricted(username):
    restrictions = get_user_restrictions(username)
    return restrictions.get('generate_phone', False)

def identity_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': '请先登录'}), 401
        username = session['user']['username']
        if is_login_restricted(username):
            return jsonify({'error': '账号已被限制登录，请联系管理员'}), 403
        if not check_identity_verified(username):
            return jsonify({'error': '请先完成身份认证', 'redirect': '/identity_verification.html'}), 403
        return f(*args, **kwargs)
    return decorated_function

def login_restriction_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': '请先登录'}), 401
        username = session['user']['username']
        if is_login_restricted(username):
            return jsonify({'error': '账号已被限制登录，请联系管理员'}), 403
        return f(*args, **kwargs)
    return decorated_function

def mall_access_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': '请先登录'}), 401
        username = session['user']['username']
        if is_mall_restricted(username):
            return jsonify({'error': '账号已被限制使用商城功能，请联系管理员'}), 403
        if not check_identity_verified(username):
            return jsonify({'error': '请先完成身份认证', 'redirect': '/identity_verification.html'}), 403
        return f(*args, **kwargs)
    return decorated_function

def generate_phone_access_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': '请先登录'}), 401
        username = session['user']['username']
        if is_generate_phone_restricted(username):
            return jsonify({'error': '账号已被限制生成手机号功能，请联系管理员'}), 403
        if not check_identity_verified(username):
            return jsonify({'error': '请先完成身份认证', 'redirect': '/identity_verification.html'}), 403
        return f(*args, **kwargs)
    return decorated_function

def delete_user_completely(username):
    if username in phone_records:
        for record in phone_records[username]:
            if record.get('boundAuthCode') and record['boundAuthCode'] in auth_codes:
                del auth_codes[record['boundAuthCode']]
            if not record.get('used') and record.get('phoneNumber') in used_phone_numbers:
                used_phone_numbers.remove(record['phoneNumber'])
        del phone_records[username]
        save_phone_records()
        save_auth_codes()

    codes_to_remove = []
    for code, data in reset_codes.items():
        if data.get('username') == username:
            codes_to_remove.append(code)
    for code in codes_to_remove:
        del reset_codes[code]
    if codes_to_remove:
        save_reset_codes()

    codes_to_remove = []
    for code, data in point_codes.items():
        if data.get('username') == username:
            codes_to_remove.append(code)
    for code in codes_to_remove:
        del point_codes[code]
    if codes_to_remove:
        save_point_codes()

    codes_to_remove = []
    for code, data in premium_point_codes.items():
        if data.get('username') == username:
            codes_to_remove.append(code)
    for code in codes_to_remove:
        del premium_point_codes[code]
    if codes_to_remove:
        save_premium_point_codes()

    codes_to_remove = []
    for code, data in boost_codes.items():
        if data.get('username') == username:
            codes_to_remove.append(code)
    for code in codes_to_remove:
        del boost_codes[code]
    if codes_to_remove:
        save_boost_codes()

    codes_to_remove = []
    for code, data in special_point_codes.items():
        if data.get('username') == username:
            codes_to_remove.append(code)
    for code in codes_to_remove:
        del special_point_codes[code]
    if codes_to_remove:
        save_special_point_codes()

    codes_to_remove = []
    for code, data in makeup_codes.items():
        if data.get('username') == username:
            codes_to_remove.append(code)
    for code in codes_to_remove:
        del makeup_codes[code]
    if codes_to_remove:
        save_makeup_codes()

    codes_to_remove = []
    for code, data in gamblers_codes.items():
        if data.get('username') == username:
            codes_to_remove.append(code)
    for code in codes_to_remove:
        del gamblers_codes[code]
    if codes_to_remove:
        save_gamblers_codes()

    codes_to_remove = []
    for code, data in box_codes.items():
        if data.get('username') == username:
            codes_to_remove.append(code)
    for code in codes_to_remove:
        del box_codes[code]
    if codes_to_remove:
        save_box_codes()

    codes_to_remove = []
    for code, data in plcard_codes.items():
        if data.get('username') == username:
            codes_to_remove.append(code)
    for code in codes_to_remove:
        del plcard_codes[code]
    if codes_to_remove:
        save_plcard_codes()

    codes_to_remove = []
    for code, data in premium_boost_codes.items():
        if data.get('username') == username:
            codes_to_remove.append(code)
    for code in codes_to_remove:
        del premium_boost_codes[code]
    if codes_to_remove:
        save_premium_boost_codes()

    codes_to_remove = []
    for code, data in cancellation_codes.items():
        if data.get('username') == username:
            codes_to_remove.append(code)
    for code in codes_to_remove:
        del cancellation_codes[code]
    if codes_to_remove:
        save_cancellation_codes()

    if username in user_boosts:
        del user_boosts[username]
        save_user_boosts()

    if username in identity_verifications:
        verification = identity_verifications[username]
        id_card_key = verification.get('id_card_key')
        if id_card_key:
            used_data = load_id_cards_used()
            if id_card_key in used_data and used_data[id_card_key] == True:
                used_data[id_card_key] = False
                save_id_cards_used(used_data)
                log.info(f"Released ID card {id_card_key} for user {username} (manual or quick verify)")
        del identity_verifications[username]
        save_identity_verifications()

    if username in users:
        pl_balance = get_user_pl_balance(username)
        if pl_balance > 0:
            current_rate = get_current_pl_rate()
            points_from_pl = round(pl_balance / current_rate, 2)
            if points_from_pl > 0:
                add_system_total_points(points_from_pl)
        del users[username]
        save_users()

    if username in user_code_limits:
        del user_code_limits[username]
        save_user_code_limits()

    records_to_remove = []
    for code, record in user_cdk_records.items():
        if record.get('username') == username:
            records_to_remove.append(code)
    for code in records_to_remove:
        del user_cdk_records[code]
    if records_to_remove:
        save_user_cdk_records()

    coupons_to_remove = []
    for cid, coupon in user_coupons.items():
        if coupon.get('username') == username:
            coupons_to_remove.append(cid)
    for cid in coupons_to_remove:
        del user_coupons[cid]
    if coupons_to_remove:
        save_user_coupons()

    transfers_to_remove = []
    for tid, transfer in pl_transfers.items():
        if transfer.get('from_username') == username or transfer.get('to_username') == username:
            transfers_to_remove.append(tid)
    for tid in transfers_to_remove:
        del pl_transfers[tid]
    if transfers_to_remove:
        save_pl_transfers()

    if username in user_pl_balances:
        del user_pl_balances[username]
        save_user_pl_balances()

    if username in user_pay_passwords:
        del user_pay_passwords[username]
        save_user_pay_passwords()

    attachments_to_remove = []
    for aid, attachment in mail_attachments.items():
        if attachment.get('username') == username:
            attachments_to_remove.append(aid)
    for aid in attachments_to_remove:
        del mail_attachments[aid]
    if attachments_to_remove:
        save_mail_attachments()

    receipts_to_remove = []
    for rid, receipt in mail_read_receipts.items():
        if receipt.get('username') == username:
            receipts_to_remove.append(rid)
    for rid in receipts_to_remove:
        del mail_read_receipts[rid]
    if receipts_to_remove:
        save_mail_read_receipts()

    if username in user_pool_claims:
        del user_pool_claims[username]
        save_user_pool_claims()

    if username in fund_data:
        del fund_data[username]
        save_fund_data()

    history_to_remove = []
    for hid, history in fund_history.items():
        if history.get('username') == username:
            history_to_remove.append(hid)
    for hid in history_to_remove:
        del fund_history[hid]
    if history_to_remove:
        save_fund_history()

    if username in nav_holdings:
        del nav_holdings[username]
        save_nav_holdings()

    nav_history_to_remove = []
    for rid, record in nav_history.items():
        if record.get('username') == username:
            nav_history_to_remove.append(rid)
    for rid in nav_history_to_remove:
        del nav_history[rid]
    if nav_history_to_remove:
        save_nav_history()

def cleanup_unverified_users():
    current_time = datetime.now()
    users_to_delete = []
    for username, user_data in users.items():
        if not check_identity_verified(username):
            created_at_str = user_data.get('createdAt')
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str)
                    if (current_time - created_at) > timedelta(hours=24):
                        users_to_delete.append(username)
                except:
                    pass
    for username in users_to_delete:
        delete_user_completely(username)

def cleanup_expired_captcha_loop():
    while True:
        time.sleep(60)
        try:
            current_time = int(time.time())
            captcha_data = load_captcha_storage()
            captcha_ids_to_remove = []
            for captcha_id, data in captcha_data.items():
                created_at = data.get('created_at', 0)
                if current_time - created_at > 300:
                    captcha_ids_to_remove.append(captcha_id)
            for captcha_id in captcha_ids_to_remove:
                if captcha_id in captcha_data:
                    del captcha_data[captcha_id]
            if captcha_ids_to_remove:
                save_captcha_storage(captcha_data)
        except Exception as e:
            log.error(f"Cleanup expired captcha error: {e}")

captcha_cleanup_thread = threading.Thread(target=cleanup_expired_captcha_loop, daemon=True)
captcha_cleanup_thread.start()

def cleanup_inactive_users():
    current_time = datetime.now()
    users_to_delete = []
    for username, user_data in users.items():
        last_login = user_data.get('lastLoginDate', '')
        if last_login:
            try:
                last_login_dt = datetime.strptime(last_login, '%Y-%m-%d')
                days_inactive = (current_time - last_login_dt).days
                if days_inactive >= 14:
                    users_to_delete.append(username)
            except:
                pass
    for username in users_to_delete:
        delete_user_completely(username)

def cleanup_expired_mail_attachments():
    current_time = int(time.time() * 1000)
    attachments_to_remove = []
    for aid, attachment in mail_attachments.items():
        expires_at = attachment.get('expires_at', 0)
        if expires_at > 0 and current_time > expires_at:
            attachments_to_remove.append(aid)
        elif attachment.get('claimed', False):
            attachments_to_remove.append(aid)
    for aid in attachments_to_remove:
        if aid in mail_attachments:
            del mail_attachments[aid]
    if attachments_to_remove:
        save_mail_attachments()

def cleanup_expired_pool_claims():
    current_time = datetime.now()
    thirty_days_ago = (current_time - timedelta(days=30)).strftime('%Y-%m-%d')
    for username in list(user_pool_claims.keys()):
        claims = user_pool_claims[username]
        for date_str in list(claims.keys()):
            if date_str < thirty_days_ago:
                del claims[date_str]
        if not claims:
            del user_pool_claims[username]
    save_user_pool_claims()

def cleanup_pool_records():
    for date, data in pool_records.items():
        if 'payout_details' in data and data['payout_details']:
            total = sum(data['payout_details'].values())
            if data.get('total_payout', 0) != total:
                data['total_payout'] = total
                log.info(f"Fixed pool record for {date}: total_payout = {total}")
        elif 'payout_details' not in data:
            data['payout_details'] = {}
    save_pool_records()

def get_daily_pool_amount():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    yesterday_payout = 0
    for username, claims in user_pool_claims.items():
        if yesterday in claims:
            yesterday_payout += pool_records.get(yesterday, {}).get('total_payout', 0)
    
    eligible_users = 0
    for username, user_data in users.items():
        if check_identity_verified(username) and not is_login_restricted(username):
            if user_data.get('attendanceTotalDays', 0) >= 7:
                base = calculate_user_pool_base(username)
                if base > 0:
                    eligible_users += 1
    
    min_per_user = 50
    max_per_user = 200
    
    dynamic_min = max(10000, eligible_users * min_per_user)
    dynamic_max = max(50000, eligible_users * max_per_user)
    dynamic_max = min(dynamic_max, 500000)
    
    base = max(dynamic_min, yesterday_payout * POOL_GROWTH_FACTOR)
    return min(base, dynamic_max)

def add_random_system_points(username):
    user_data = users.get(username, {})
    consecutive = user_data.get('attendanceConsecutiveDays', 0)
    if consecutive >= 30:
        points_to_add = random.randint(1500, 1800)
    elif consecutive >= 14:
        points_to_add = random.randint(1000, 1500)
    elif consecutive >= 7:
        points_to_add = random.randint(500, 1000)
    else:
        points_to_add = random.randint(300, 600)
    global system_total_points
    system_total_points += points_to_add
    save_system_total_points(system_total_points)
    return points_to_add

def calculate_user_pool_base(username):
    user_data = users.get(username, {})
    total_points = get_user_fund_total_points(username)
    total_days = user_data.get('attendanceTotalDays', 0)
    if total_days < 7:
        return 0.0
    raw_base = 0.05 / (1 + math.log10(1 + total_points / 1000.0))
    raw_base = max(0.012, min(0.05, raw_base))
    created_at = user_data.get('createdAt', '')
    if created_at:
        try:
            created = datetime.fromisoformat(created_at)
            if (datetime.now() - created).days <= NEW_USER_PROTECT_DAYS:
                raw_base *= (1 + NEW_USER_BONUS_RATIO)
        except:
            pass
    return round(raw_base, 4)

def get_user_today_pool_base(username):
    user_data = users.get(username, {})
    consecutive = user_data.get('attendanceConsecutiveDays', 0)
    if consecutive >= 7:
        return calculate_user_pool_base(username)
    elif consecutive >= 4:
        return calculate_user_pool_base(username) * 0.7
    elif consecutive >= 1:
        return calculate_user_pool_base(username) * 0.4
    else:
        return 0.0

def build_user_bases():
    user_bases = {}
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    for username, user_data in users.items():
        if user_data.get('lastLoginDate', '') < seven_days_ago:
            continue
        if is_login_restricted(username) or not check_identity_verified(username):
            continue
        if user_data.get('attendanceTotalDays', 0) < 7:
            continue
        base = get_user_today_pool_base(username)
        if base > 0:
            user_bases[username] = {
                'base': base,
                'consecutive_days': user_data.get('attendanceConsecutiveDays', 0)
            }
    return user_bases

def normalize_user_bases_with_bonus(user_bases):
    pool_amount = get_daily_pool_amount()
    if len(user_bases) == 1:
        username = list(user_bases.keys())[0]
        single_cap = int(pool_amount * 0.3)
        return {username: single_cap}
    
    main_pool = pool_amount * 0.8
    bonus_pool = pool_amount * 0.2
    
    total_base = sum(d['base'] for d in user_bases.values())
    main_result = {}
    if total_base > 0:
        for username, data in user_bases.items():
            main_result[username] = main_pool * (data['base'] / total_base)
    
    bonus_result = {}
    bonus_users = [u for u, d in user_bases.items() if d.get('consecutive_days', 0) >= 7]
    if bonus_users:
        total_cons = sum(user_bases[u].get('consecutive_days', 0) for u in bonus_users)
        if total_cons > 0:
            for u in bonus_users:
                bonus_result[u] = bonus_pool * (user_bases[u].get('consecutive_days', 0) / total_cons)
    
    result = {}
    for username in user_bases:
        result[username] = round(main_result.get(username, 0) + bonus_result.get(username, 0), 4)
    
    return result

def get_user_today_pool_reward(username):
    user_bases = build_user_bases()
    normalized = normalize_user_bases_with_bonus(user_bases)
    return round(normalized.get(username, 0), 4)

def get_pool_status():
    today = get_today_pool_date()
    pool_amount = get_daily_pool_amount()
    user_bases = build_user_bases()
    normalized = normalize_user_bases_with_bonus(user_bases)
    total_base = sum(normalized.values())
    user_count = len([b for b in normalized.values() if b > 0])
    return {
        'today': today,
        'pool_amount': pool_amount,
        'total_base': round(total_base, 4),
        'user_count': user_count
    }

def calculate_user_pool_base_without_decay(username):
    user_data = users.get(username, {})
    total_points = get_user_fund_total_points(username)
    total_days = user_data.get('attendanceTotalDays', 0)
    if total_days < 7:
        return 0
    raw_base = 0.05 / (1 + math.log10(1 + total_points / 1000.0))
    raw_base = max(0.012, min(0.05, raw_base))
    created_at = user_data.get('createdAt', '')
    if created_at:
        try:
            created = datetime.fromisoformat(created_at)
            if (datetime.now() - created).days <= NEW_USER_PROTECT_DAYS:
                raw_base *= (1 + NEW_USER_BONUS_RATIO)
        except:
            pass
    return round(raw_base, 4)

def get_today_pool_date():
    return datetime.now().strftime('%Y-%m-%d')

def has_user_claimed_pool_today(username):
    today = get_today_pool_date()
    user_claims = user_pool_claims.get(username, {})
    return user_claims.get(today, False)

def mark_user_pool_claimed(username):
    today = get_today_pool_date()
    if username not in user_pool_claims:
        user_pool_claims[username] = {}
    user_pool_claims[username][today] = True
    save_user_pool_claims()

def has_cooldown_remaining(username):
    cooldown_data = user_pool_claims.get(username, {}).get('last_claim_cooldown', {})
    last_claim_time = cooldown_data.get('timestamp', 0)
    if last_claim_time == 0:
        return False
    cooldown_until = last_claim_time + (COOLDOWN_HOURS * 3600 * 1000)
    return int(time.time() * 1000) < cooldown_until

def mark_cooldown(username):
    if username not in user_pool_claims:
        user_pool_claims[username] = {}
    if 'last_claim_cooldown' not in user_pool_claims[username]:
        user_pool_claims[username]['last_claim_cooldown'] = {}
    user_pool_claims[username]['last_claim_cooldown']['timestamp'] = int(time.time() * 1000)
    save_user_pool_claims()

def process_pool_reward_for_user(username):
    try:
        if has_user_claimed_pool_today(username):
            return None, '今日已领取'
        
        if has_cooldown_remaining(username):
            return None, '领取冷却中，请稍后再试'
        
        user_data = users.get(username)
        if not user_data:
            return None, '用户不存在'
        
        total_days = user_data.get('attendanceTotalDays', 0)
        if total_days < 7:
            return None, f'需要累计签到7天才可瓜分，当前累计签到{total_days}天'
        
        if is_login_restricted(username):
            return None, '账号已被限制，无法瓜分'
        
        if not check_identity_verified(username):
            return None, '请先完成身份认证'
        
        reward = get_user_today_pool_reward(username)
        if reward <= 0:
            return None, '积分基数为0，无法瓜分'
        
        mail_attachment_id = f"mail_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        pool_amount = get_daily_pool_amount()
        user_bases = build_user_bases()
        normalized = normalize_user_bases_with_bonus(user_bases)
        base = normalized.get(username, 0)
        
        mail_attachments[mail_attachment_id] = {
            'id': mail_attachment_id,
            'username': username,
            'type': 'points',
            'points_amount': reward,
            'used': False,
            'created_at': int(time.time() * 1000),
            'expires_at': int(time.time() * 1000) + 28800000,
            'title': '积分瓜分奖励',
            'description': f'今日积分瓜分获得{reward}积分（池子总量{pool_amount}，基数{base*100:.2f}%）',
            'claimed': False,
            'claimed_at': 0,
            'source': 'pool_reward'
        }
        save_mail_attachments()
        mark_user_pool_claimed(username)
        mark_cooldown(username)
        
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in pool_records:
            pool_records[today] = {'total_payout': 0, 'payout_details': {}}
        
        if 'payout_details' not in pool_records[today]:
            pool_records[today]['payout_details'] = {}
        
        pool_records[today]['total_payout'] = pool_records[today].get('total_payout', 0) + reward
        pool_records[today]['payout_details'][username] = pool_records[today]['payout_details'].get(username, 0) + reward
        save_pool_records()
        
        return reward, None
        
    except Exception as e:
        log.error(f"Error in process_pool_reward_for_user: {e}")
        import traceback
        traceback.print_exc()
        return None, f'处理失败: {str(e)}'

def pool_reward_loop():
    while True:
        time.sleep(3600)
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            total_payout = 0
            for username, claims in user_pool_claims.items():
                if today in claims:
                    reward = get_user_today_pool_reward(username)
                    total_payout += reward
            if today not in pool_records:
                pool_records[today] = {'total_payout': 0}
            pool_records[today]['total_payout'] = total_payout
            save_pool_records()
        except Exception as e:
            log.error(f"Pool reward loop error: {e}")

def get_newbie_pool_status():
    today = datetime.now().strftime('%Y-%m-%d')
    system_total = load_system_total_points()
    
    pool_amount = newbie_pool_data.get(today, {}).get('pool_amount', 0)
    
    if pool_amount == 0:
        pool_amount = min(system_total * 0.05, 10000)
        if today not in newbie_pool_data:
            newbie_pool_data[today] = {}
        newbie_pool_data[today]['pool_amount'] = pool_amount
        newbie_pool_data[today]['updated_at'] = int(time.time() * 1000)
        save_newbie_pool_data(newbie_pool_data)
    
    eligible_users = []
    for username, user_data in users.items():
        created_at_str = user_data.get('createdAt', '')
        if not created_at_str:
            continue
        try:
            created_at = datetime.fromisoformat(created_at_str)
            days_old = (datetime.now() - created_at).days
            if days_old <= 7 and not is_login_restricted(username) and check_identity_verified(username):
                has_attended = user_data.get('lastAttendanceDate', '') == today
                is_active = user_data.get('lastLoginDate', '') == today
                eligible_users.append({
                    'username': username,
                    'days_old': days_old,
                    'has_attended': has_attended,
                    'is_active': is_active,
                    'verified': True
                })
        except:
            pass
    
    total_eligible = len(eligible_users)
    max_reward = min(pool_amount * 0.01, 100)
    
    return {
        'today': today,
        'pool_amount': round(pool_amount, 2),
        'eligible_count': total_eligible,
        'max_reward': round(max_reward, 2),
        'system_total': round(system_total, 2)
    }

def get_user_newbie_reward(username):
    user_data = users.get(username)
    if not user_data:
        return 0
    
    created_at_str = user_data.get('createdAt', '')
    if not created_at_str:
        return 0
    
    try:
        created_at = datetime.fromisoformat(created_at_str)
        days_old = (datetime.now() - created_at).days
        if days_old > 7:
            return 0
    except:
        return 0
    
    if is_login_restricted(username) or not check_identity_verified(username):
        return 0
    
    today = datetime.now().strftime('%Y-%m-%d')
    has_attended = user_data.get('lastAttendanceDate', '') == today
    is_active = user_data.get('lastLoginDate', '') == today
    
    base_multiplier = 1.0
    if has_attended:
        base_multiplier += 1.0
    if is_active:
        base_multiplier += 1.0
    
    days_factor = 1.0 - (days_old / 7) * 0.5
    base_multiplier = base_multiplier * max(0.5, days_factor)
    base_multiplier = min(base_multiplier, 3.0)
    
    status = get_newbie_pool_status()
    max_reward = status.get('max_reward', 10)
    base_reward = max_reward * 0.3
    reward = base_reward * base_multiplier
    reward = min(reward, max_reward)
    
    eligible_count = status.get('eligible_count', 1)
    if eligible_count > 0:
        per_user_limit = status.get('pool_amount', 1000) / eligible_count
        reward = min(reward, per_user_limit * 0.1)
    
    return round(reward, 2)

def has_user_claimed_newbie_today(username):
    today = datetime.now().strftime('%Y-%m-%d')
    user_claims = newbie_pool_claims.get(username, {})
    return user_claims.get(today, False)

def mark_user_newbie_claimed(username):
    today = datetime.now().strftime('%Y-%m-%d')
    if username not in newbie_pool_claims:
        newbie_pool_claims[username] = {}
    newbie_pool_claims[username][today] = True
    save_newbie_pool_claims(newbie_pool_claims)

def claim_newbie_reward(username):
    if not check_identity_verified(username):
        return None, '请先完成身份认证'
    
    if is_login_restricted(username):
        return None, '账号已被限制'
    
    user_data = users.get(username)
    if not user_data:
        return None, '用户不存在'
    
    created_at_str = user_data.get('createdAt', '')
    if not created_at_str:
        return None, '无法验证注册时间'
    
    try:
        created_at = datetime.fromisoformat(created_at_str)
        days_old = (datetime.now() - created_at).days
        if days_old > 7:
            return None, f'注册已超过7天（已{days_old}天），无法领取新人奖励'
    except:
        return None, '无法验证注册时间'
    
    if has_user_claimed_newbie_today(username):
        return None, '今日已领取新人奖励'
    
    reward = get_user_newbie_reward(username)
    if reward <= 0:
        return None, '当前奖励为0，无法领取'
    
    global system_total_points
    if system_total_points < reward:
        return None, f'系统积分池不足，当前池子{system_total_points:.2f}积分'
    
    add_points_without_limit(username, reward)
    deduct_system_total_points(reward)
    
    mark_user_newbie_claimed(username)
    
    today = datetime.now().strftime('%Y-%m-%d')
    if today in newbie_pool_data:
        newbie_pool_data[today]['pool_amount'] = max(0, newbie_pool_data[today].get('pool_amount', 0) - reward)
        save_newbie_pool_data(newbie_pool_data)
    
    mail_attachment_id = f"mail_{int(time.time()*1000)}_{random.randint(1000,9999)}"
    mail_attachments[mail_attachment_id] = {
        'id': mail_attachment_id,
        'username': username,
        'type': 'points',
        'points_amount': reward,
        'used': False,
        'created_at': int(time.time() * 1000),
        'expires_at': int(time.time() * 1000) + 28800000,
        'title': '新人奖池奖励',
        'description': f'新人奖池获得{reward}积分（注册{days_old}天）',
        'claimed': False,
        'claimed_at': 0,
        'source': 'newbie_pool'
    }
    save_mail_attachments()
    
    return reward, None

def get_nav_profit_tax_rate(profit, cost):
    if cost <= 0:
        return 0.08
    profit_ratio = profit / cost
    if profit_ratio <= 0.05:
        return 0.08
    elif profit_ratio <= 0.10:
        return 0.10
    elif profit_ratio <= 0.20:
        return 0.12
    elif profit_ratio <= 0.35:
        return 0.15
    elif profit_ratio <= 0.50:
        return 0.18
    else:
        return 0.20


def calculate_high_balance_tax(username, points_earned):
    if username not in users:
        return points_earned, 0
    user_data = users.get(username, {})
    main_points = user_data.get('totalPoints', 0)
    fund_balance = get_user_fund_balance(username)
    total_assets = main_points + fund_balance
    if total_assets > 100000:
        tax = round(points_earned * 0.14, 4)
        net_points = round(points_earned - tax, 4)
        return net_points, tax
    return points_earned, 0


def add_game_points(username, points):
    if username in users:
        if 'totalPoints' not in users[username]:
            users[username]['totalPoints'] = 0
        net_points, tax = calculate_high_balance_tax(username, points)
        users[username]['totalPoints'] = round(users[username]['totalPoints'] + net_points, 2)
        if tax > 0:
            add_system_total_points(tax)
            log.info(f"High balance tax applied for {username}: earned={points}, tax={tax}, net={net_points}")
        save_users()
        return True
    return False

def cleanup_all_expired_data():
    current_time = int(time.time() * 1000)

    auth_codes_to_remove = []
    for code, data in auth_codes.items():
        if data.get('used', False):
            auth_codes_to_remove.append(code)
        elif (current_time - data.get('createdAt', 0)) > 180000:
            auth_codes_to_remove.append(code)
    for code in auth_codes_to_remove:
        del auth_codes[code]
    if auth_codes_to_remove:
        save_auth_codes()

    reset_codes_to_remove = []
    for code, data in reset_codes.items():
        if data.get('used', False):
            reset_codes_to_remove.append(code)
        elif data.get('recycled', False):
            reset_codes_to_remove.append(code)
        elif (current_time - data.get('createdAt', 0)) > 86400000:
            reset_codes_to_remove.append(code)
    for code in reset_codes_to_remove:
        del reset_codes[code]
    if reset_codes_to_remove:
        save_reset_codes()

    point_codes_to_remove = []
    for code, data in point_codes.items():
        if data.get('used', False):
            point_codes_to_remove.append(code)
        elif data.get('recycled', False):
            point_codes_to_remove.append(code)
        elif (current_time - data.get('createdAt', 0)) > 172800000:
            point_codes_to_remove.append(code)
    for code in point_codes_to_remove:
        del point_codes[code]
    if point_codes_to_remove:
        save_point_codes()

    premium_codes_to_remove = []
    for code, data in premium_point_codes.items():
        if data.get('used', False):
            premium_codes_to_remove.append(code)
        elif data.get('recycled', False):
            premium_codes_to_remove.append(code)
        elif (current_time - data.get('createdAt', 0)) > 172800000:
            premium_codes_to_remove.append(code)
    for code in premium_codes_to_remove:
        del premium_point_codes[code]
    if premium_codes_to_remove:
        save_premium_point_codes()

    boost_codes_to_remove = []
    for code, data in boost_codes.items():
        if data.get('used', False):
            boost_codes_to_remove.append(code)
        elif data.get('recycled', False):
            boost_codes_to_remove.append(code)
        elif (current_time - data.get('createdAt', 0)) > 259200000:
            boost_codes_to_remove.append(code)
    for code in boost_codes_to_remove:
        del boost_codes[code]
    if boost_codes_to_remove:
        save_boost_codes()

    special_codes_to_remove = []
    for code, data in special_point_codes.items():
        if data.get('used', False):
            special_codes_to_remove.append(code)
        elif data.get('recycled', False):
            special_codes_to_remove.append(code)
        elif (current_time - data.get('createdAt', 0)) > 172800000:
            special_codes_to_remove.append(code)
    for code in special_codes_to_remove:
        del special_point_codes[code]
    if special_codes_to_remove:
        save_special_point_codes()

    makeup_codes_to_remove = []
    for code, data in makeup_codes.items():
        if data.get('used', False):
            makeup_codes_to_remove.append(code)
        elif data.get('recycled', False):
            makeup_codes_to_remove.append(code)
        elif (current_time - data.get('createdAt', 0)) > 3600000:
            makeup_codes_to_remove.append(code)
    for code in makeup_codes_to_remove:
        del makeup_codes[code]
    if makeup_codes_to_remove:
        save_makeup_codes()

    gamblers_codes_to_remove = []
    for code, data in gamblers_codes.items():
        if data.get('used', False):
            gamblers_codes_to_remove.append(code)
        elif data.get('recycled', False):
            gamblers_codes_to_remove.append(code)
        elif (current_time - data.get('createdAt', 0)) > 86400000:
            gamblers_codes_to_remove.append(code)
    for code in gamblers_codes_to_remove:
        del gamblers_codes[code]
    if gamblers_codes_to_remove:
        save_gamblers_codes()

    box_codes_to_remove = []
    for code, data in box_codes.items():
        if data.get('used', False):
            box_codes_to_remove.append(code)
        elif data.get('recycled', False):
            box_codes_to_remove.append(code)
        elif (current_time - data.get('createdAt', 0)) > 172800000:
            box_codes_to_remove.append(code)
    for code in box_codes_to_remove:
        del box_codes[code]
    if box_codes_to_remove:
        save_box_codes()

    plcard_codes_to_remove = []
    for code, data in plcard_codes.items():
        if data.get('used', False):
            plcard_codes_to_remove.append(code)
        elif data.get('recycled', False):
            plcard_codes_to_remove.append(code)
        elif (current_time - data.get('createdAt', 0)) > 86400000:
            plcard_codes_to_remove.append(code)
    for code in plcard_codes_to_remove:
        del plcard_codes[code]
    if plcard_codes_to_remove:
        save_plcard_codes()

    premium_boost_codes_to_remove = []
    for code, data in premium_boost_codes.items():
        if data.get('used', False):
            premium_boost_codes_to_remove.append(code)
        elif data.get('recycled', False):
            premium_boost_codes_to_remove.append(code)
        elif (current_time - data.get('createdAt', 0)) > 172800000:
            premium_boost_codes_to_remove.append(code)
    for code in premium_boost_codes_to_remove:
        del premium_boost_codes[code]
    if premium_boost_codes_to_remove:
        save_premium_boost_codes()

    cancellation_codes_to_remove = []
    for code, data in cancellation_codes.items():
        if data.get('used', False):
            cancellation_codes_to_remove.append(code)
        elif data.get('recycled', False):
            cancellation_codes_to_remove.append(code)
    for code in cancellation_codes_to_remove:
        del cancellation_codes[code]
    if cancellation_codes_to_remove:
        save_cancellation_codes()

    current_time_sec = int(time.time())
    boosts_to_remove = []
    for username, boost_data in user_boosts.items():
        if boost_data.get('expiresAt', 0) <= current_time_sec:
            boosts_to_remove.append(username)
    for username in boosts_to_remove:
        del user_boosts[username]
    if boosts_to_remove:
        save_user_boosts()

    cdk_packages_to_remove = []
    for code, package in cdk_packages.items():
        if package.get('used', False):
            cdk_packages_to_remove.append(code)
        elif package.get('is_universal', False):
            expiry_time_ms = package.get('expiry_time', 0)
            if expiry_time_ms > 0 and current_time > expiry_time_ms:
                cdk_packages_to_remove.append(code)
        else:
            expiry_time_ms = package.get('expiry_time', 0)
            if expiry_time_ms > 0 and current_time > expiry_time_ms:
                cdk_packages_to_remove.append(code)
    for code in cdk_packages_to_remove:
        del cdk_packages[code]
    if cdk_packages_to_remove:
        save_cdk_packages()

    announcements_to_disable = []
    for aid, ann in announcements.items():
        end_time_ms = ann.get('end_time', 0)
        if end_time_ms > 0 and current_time > end_time_ms and ann.get('is_active', False):
            announcements_to_disable.append(aid)
    for aid in announcements_to_disable:
        announcements[aid]['is_active'] = False
    if announcements_to_disable:
        save_announcements()

    cleanup_unverified_users()
    cleanup_inactive_users()

    orders_to_remove = []
    for order_id, order in orders.items():
        created_at = order.get('created_at', 0)
        if isinstance(created_at, str):
            try:
                created_at = int(created_at)
            except:
                created_at = 0

        status = order.get('status', 'pending')

        if status == 'pending':
            if current_time - created_at > 300000:
                orders_to_remove.append(order_id)
        else:
            if current_time - created_at > 43200000:
                orders_to_remove.append(order_id)

    for order_id in orders_to_remove:
        if order_id in orders:
            del orders[order_id]
    if orders_to_remove:
        save_orders()

    code_limits_to_clean = []
    for username, limits in user_code_limits.items():
        for code_type, data in limits.items():
            if data.get('expires_at', 0) < current_time:
                code_limits_to_clean.append((username, code_type))
    for username, code_type in code_limits_to_clean:
        if username in user_code_limits and code_type in user_code_limits[username]:
            del user_code_limits[username][code_type]
            if not user_code_limits[username]:
                del user_code_limits[username]
    if code_limits_to_clean:
        save_user_code_limits()

    coupons_to_remove = []
    for cid, coupon in user_coupons.items():
        if coupon.get('used', False):
            coupons_to_remove.append(cid)
        elif coupon.get('expire_at', 0) < current_time:
            coupons_to_remove.append(cid)
    for cid in coupons_to_remove:
        del user_coupons[cid]
    if coupons_to_remove:
        save_user_coupons()

    cleanup_expired_gateway_cards()
    cleanup_expired_mail_attachments()
    cleanup_expired_pool_claims()

    fund_data_to_clean = []
    for username in list(fund_data.keys()):
        if username not in users:
            fund_data_to_clean.append(username)
    for username in fund_data_to_clean:
        del fund_data[username]
    if fund_data_to_clean:
        save_fund_data()

    nav_holdings_to_clean = []
    for username in list(nav_holdings.keys()):
        if username not in users:
            nav_holdings_to_clean.append(username)
    for username in nav_holdings_to_clean:
        del nav_holdings[username]
    if nav_holdings_to_clean:
        save_nav_holdings()

    nav_history_to_remove = []
    for rid, record in nav_history.items():
        if record.get('username') not in users:
            nav_history_to_remove.append(rid)
    for rid in nav_history_to_remove:
        del nav_history[rid]
    if nav_history_to_remove:
        save_nav_history()

    today = datetime.now().strftime('%Y-%m-%d')
    if today in gateway_stock:
        stock = gateway_stock[today]
        if stock.get('hour', 0) == 0 and stock.get('day', 0) == 0 and stock.get('week', 0) == 0 and stock.get('permanent', 0) == 0:
            del gateway_stock[today]
            save_gateway_stock()

    try:
        email_service.cleanup_expired_codes()
    except:
        pass

def enforce_phone_record_limit():
    for username in list(phone_records.keys()):
        records = phone_records[username]
        if len(records) > 6:
            records_sorted = sorted(records, key=lambda x: x.get('timestamp', ''))
            records_to_remove = records_sorted[:-6]
            for old_record in records_to_remove:
                if old_record.get('boundAuthCode') and old_record['boundAuthCode'] in auth_codes:
                    del auth_codes[old_record['boundAuthCode']]
                if not old_record.get('used') and old_record.get('phoneNumber') in used_phone_numbers:
                    used_phone_numbers.remove(old_record['phoneNumber'])
            phone_records[username] = records_sorted[-6:]
            save_phone_records()
            save_auth_codes()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': '请先登录'}), 401
        username = session['user']['username']
        if is_login_restricted(username):
            return jsonify({'error': '账号已被限制登录，请联系管理员'}), 403
        return f(*args, **kwargs)
    return decorated_function

def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_token = request.headers.get('X-Admin-Token', '')
        if not admin_token or admin_token not in admin_sessions:
            return jsonify({'error': '请先登录管理员账户'}), 401
        if admin_sessions[admin_token] < time.time():
            del admin_sessions[admin_token]
            return jsonify({'error': '管理员会话已过期，请重新登录'}), 401
        admin_sessions[admin_token] = time.time() + ADMIN_SESSION_TIMEOUT
        return f(*args, **kwargs)
    return decorated_function

def get_available_id_card():
    used_data = load_id_cards_used()
    used_id_numbers = set()
    for id_num, used in used_data.items():
        if used:
            used_id_numbers.add(id_num)
    
    if not os.path.exists(ID_CARDS_CSV):
        return None
    
    try:
        with open(ID_CARDS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('姓名', '').strip()
                id_number = row.get('身份证号', '').strip()
                if not name or not id_number:
                    continue
                if len(id_number) != 18:
                    continue
                if id_number in used_id_numbers:
                    continue
                return {
                    'name': name,
                    'id_number': id_number,
                    'key': id_number
                }
        return None
    except Exception as e:
        log.error(f"Error reading id cards CSV: {e}")
        return None

def get_id_cards_stats():
    if not os.path.exists(ID_CARDS_CSV):
        return {'total': 0, 'used': 0, 'available': 0}
    
    used_data = load_id_cards_used()
    used_id_numbers = set()
    for id_num, used in used_data.items():
        if used:
            used_id_numbers.add(id_num)
    
    total = 0
    unique_id_numbers = set()
    try:
        with open(ID_CARDS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                id_number = row.get('身份证号', '').strip()
                if id_number and len(id_number) == 18:
                    unique_id_numbers.add(id_number)
                    total += 1
    except Exception as e:
        log.error(f"Error reading id cards CSV: {e}")
        return {'total': 0, 'used': 0, 'available': 0}
    
    unique_total = len(unique_id_numbers)
    used_count = len([x for x in used_id_numbers if x in unique_id_numbers])
    
    return {
        'total': total,
        'unique_total': unique_total,
        'used': used_count,
        'available': unique_total - used_count
    }

def fetch_weather_from_openmeteo(latitude, longitude):
    try:
        import requests
        from datetime import datetime
        
        url = (
            f'https://api.open-meteo.com/v1/forecast'
            f'?latitude={latitude}'
            f'&longitude={longitude}'
            f'&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m'
            f'&hourly=temperature_2m,precipitation_probability'
            f'&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,sunrise,sunset'
            f'&timezone=auto'
            f'&forecast_days=7'
        )
        
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        weather_codes = {
            0: '☀️ 晴天',
            1: '🌤️ 主要晴朗',
            2: '⛅ 部分多云',
            3: '☁️ 多云',
            45: '🌫️ 雾',
            48: '🌫️ 雾凇',
            51: '🌧️ 小雨',
            53: '🌧️ 中雨',
            55: '🌧️ 大雨',
            61: '🌧️ 小雨',
            63: '🌧️ 中雨',
            65: '🌧️ 大雨',
            71: '❄️ 小雪',
            73: '❄️ 中雪',
            75: '❄️ 大雪',
            80: '🌧️ 阵雨',
            81: '🌧️ 阵雨',
            82: '🌧️ 强阵雨',
            95: '⛈️ 雷暴',
            96: '⛈️ 雷暴',
            99: '⛈️ 强雷暴'
        }
        
        current = data.get('current', {})
        daily = data.get('daily', {})
        hourly = data.get('hourly', {})
        
        current_code = current.get('weather_code', 0)
        current_condition = weather_codes.get(current_code, '☁️ 多云')
        
        forecast = []
        if daily.get('time'):
            for i in range(min(7, len(daily['time']))):
                code = daily['weather_code'][i] if i < len(daily.get('weather_code', [])) else 0
                forecast.append({
                    'date': daily['time'][i],
                    'condition': weather_codes.get(code, '☁️'),
                    'high': str(round(daily['temperature_2m_max'][i])) if i < len(daily.get('temperature_2m_max', [])) else '--',
                    'low': str(round(daily['temperature_2m_min'][i])) if i < len(daily.get('temperature_2m_min', [])) else '--',
                    'precipitation': str(daily['precipitation_sum'][i]) if i < len(daily.get('precipitation_sum', [])) else '0'
                })
        
        hourly_data = []
        if hourly.get('time'):
            now = datetime.now()
            now_hour = now.hour
            target_index = -1
            
            for i, t in enumerate(hourly['time']):
                try:
                    dt = datetime.fromisoformat(t)
                    if dt.date() == now.date() and dt.hour == now_hour:
                        target_index = i
                        break
                except:
                    continue
            
            if target_index == -1:
                for i, t in enumerate(hourly['time']):
                    try:
                        dt = datetime.fromisoformat(t)
                        if dt.date() == now.date() and dt.hour >= now_hour:
                            target_index = i
                            break
                    except:
                        continue
            
            if target_index != -1:
                for i in range(min(8, len(hourly['time']) - target_index)):
                    idx = target_index + i
                    if idx >= len(hourly['time']):
                        break
                    try:
                        dt = datetime.fromisoformat(hourly['time'][idx])
                        temp = hourly['temperature_2m'][idx] if idx < len(hourly.get('temperature_2m', [])) else None
                        rain = hourly['precipitation_probability'][idx] if idx < len(hourly.get('precipitation_probability', [])) else None
                        if temp is not None:
                            hourly_data.append({
                                'time': f"{dt.hour:02d}:00",
                                'temp': str(round(temp)),
                                'rain': str(round(rain)) + '%' if rain is not None else ''
                            })
                    except:
                        continue
        
        return {
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude'),
            'timezone': data.get('timezone', 'Unknown'),
            'utc_offset_seconds': data.get('utc_offset_seconds', 0),
            'current': {
                'temperature': str(round(current.get('temperature_2m', 0))),
                'feels_like': str(round(current.get('apparent_temperature', 0))),
                'humidity': str(round(current.get('relative_humidity_2m', 0))) + '%',
                'precipitation': str(current.get('precipitation', 0)),
                'weather_code': current_code,
                'condition': current_condition,
                'cloud_cover': str(round(current.get('cloud_cover', 0))) + '%',
                'wind_speed': str(round(current.get('wind_speed_10m', 0))) + ' km/h',
                'wind_direction': str(round(current.get('wind_direction_10m', 0))) + '°',
                'time': current.get('time', '')
            },
            'hourly': hourly_data,
            'daily': forecast
        }
        
    except Exception as e:
        log.error(f"Open-Meteo weather fetch error: {e}")
        return None


def geocode_city_openmeteo(city_name):
    try:
        import requests
        
        def to_pinyin(text):
            try:
                from pypinyin import lazy_pinyin
                parts = lazy_pinyin(text)
                return ''.join(parts).capitalize()
            except Exception as e:
                log.error(f"Pinyin error: {e}")
                return text
        
        def query_geocode(name, count=5):
            url = f'https://geocoding-api.open-meteo.com/v1/search?name={requests.utils.quote(name)}&count={count}&language=zh'
            try:
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    return None
                data = response.json()
                if data.get('results') and len(data['results']) > 0:
                    return data['results']
                return None
            except Exception as e:
                log.error(f"Geocode query error for {name}: {e}")
                return None
        
        def is_match(user_input, result_name, result_admin1='', result_country=''):
            if not result_name:
                return False
            if result_country and result_country not in ['中国', 'China', '']:
                return False
            user_suffix = ''
            for s in ['省', '市', '区', '县', '镇', '乡']:
                if user_input.endswith(s):
                    user_suffix = s
                    break
            result_suffix = ''
            for s in ['省', '市', '区', '县', '镇', '乡']:
                if result_name.endswith(s):
                    result_suffix = s
                    break
            if user_suffix and result_suffix and user_suffix != result_suffix:
                return False
            core = user_input.rstrip('省市区县镇乡')
            if not core:
                return True
            if core in result_name:
                return True
            if result_name in core:
                return True
            return False
        
        def pick_best(results, user_input):
            if not results:
                return None
            valid = []
            for r in results:
                rname = r.get('name', '')
                radmin1 = r.get('admin1', '')
                rcountry = r.get('country', '')
                if is_match(user_input, rname, radmin1, rcountry):
                    valid.append(r)
            if not valid:
                return None
            def score(r):
                s = 0
                rname = r.get('name', '')
                radmin1 = r.get('admin1', '')
                core = user_input.rstrip('省市区县镇乡')
                if core and core == rname:
                    s += 100
                elif core and core in rname:
                    s += 50
                if radmin1 and radmin1 in user_input:
                    s += 30
                if user_input.endswith('县') and rname.endswith('县'):
                    s += 20
                if user_input.endswith('市') and rname.endswith('市'):
                    s += 20
                if user_input.endswith('区') and rname.endswith('区'):
                    s += 20
                return s
            valid.sort(key=score, reverse=True)
            return valid[0]
        
        def try_query(name):
            results = query_geocode(name)
            return pick_best(results, city_name)
        
        result = None
        matched_name = city_name
        
        result = try_query(city_name)
        if result:
            log.info(f"Found city by original name: {city_name} -> {result.get('name')}")
        
        if not result:
            pinyin_name = to_pinyin(city_name)
            log.info(f"Trying pinyin (keep suffix): {city_name} -> {pinyin_name}")
            result = try_query(pinyin_name)
            if result:
                matched_name = pinyin_name
        
        if not result and len(city_name) > 2:
            suffixes = ['县', '区', '镇', '乡']
            for suffix in suffixes:
                if city_name.endswith(suffix):
                    core = city_name[:-1]
                    if len(core) >= 2:
                        full_core = core + suffix
                        log.info(f"Trying core+keep: {full_core}")
                        result = try_query(full_core)
                        if result:
                            matched_name = full_core
                            break
                        pinyin_core = to_pinyin(full_core)
                        log.info(f"Trying pinyin core+suffix: {full_core} -> {pinyin_core}")
                        result = try_query(pinyin_core)
                        if result:
                            matched_name = pinyin_core
                            break
                        log.info(f"Trying core-only pinyin: {core} -> {to_pinyin(core)}")
                        result = try_query(to_pinyin(core))
                        if result:
                            matched_name = to_pinyin(core)
                            break
        
        if not result and len(city_name) > 2:
            suffixes = ['市', '省']
            for suffix in suffixes:
                if city_name.endswith(suffix):
                    core = city_name[:-1]
                    if len(core) >= 2:
                        log.info(f"Trying core-only: {core}")
                        result = try_query(core)
                        if result:
                            matched_name = core
                            break
                        pinyin_core = to_pinyin(core)
                        log.info(f"Trying pinyin core-only: {core} -> {pinyin_core}")
                        result = try_query(pinyin_core)
                        if result:
                            matched_name = pinyin_core
                            break
        
        if not result and len(city_name) > 3:
            for i in range(len(city_name) - 1, 2, -1):
                prefix = city_name[:i]
                if len(prefix) >= 3:
                    log.info(f"Trying prefix: {prefix}")
                    result = try_query(prefix)
                    if result:
                        matched_name = prefix
                        break
                    pinyin_prefix = to_pinyin(prefix)
                    log.info(f"Trying pinyin prefix: {prefix} -> {pinyin_prefix}")
                    result = try_query(pinyin_prefix)
                    if result:
                        matched_name = pinyin_prefix
                        break
        
        if not result:
            log.warning(f"All geocode attempts failed for {city_name}")
            return None
        
        display_name = result.get('name', city_name)
        country = result.get('country', '')
        admin1 = result.get('admin1', '')
        
        log.info(f"Geocode success: {city_name} -> {display_name} ({country}, {admin1}) [{matched_name}]")
        
        return {
            'name': display_name,
            'latitude': result['latitude'],
            'longitude': result['longitude'],
            'country': country,
            'admin1': admin1,
            'timezone': result.get('timezone', 'auto'),
            'matched_name': matched_name,
            'original_name': city_name
        }
        
    except Exception as e:
        log.error(f"Open-Meteo geocoding error: {e}")
        return None

def get_user_data_func(username):
    return users.get(username, {})

game_manager = game.init_game_manager(
    users,
    save_users,
    add_game_points,
    get_user_data_func
)

def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

def get_csrf_token():
    return generate_csrf_token()

def csrf_protect(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            session_token = session.get('_csrf_token')
            if not session_token:
                return jsonify({'error': '会话已过期，请刷新页面'}), 403
            
            token = request.headers.get('X-CSRF-Token')
            if not token or token != session_token:
                return jsonify({'error': 'CSRF验证失败，请刷新页面重试'}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/csrf-token', methods=['GET'])
def csrf_token_endpoint():
    return jsonify({'csrf_token': get_csrf_token()})

@app.route('/api/admin/login', methods=['POST'])
@limiter.limit(RATE_LIMITS['admin_login'])
@csrf_protect
def admin_login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': '请提供用户名和密码'}), 400
    
    if username != ADMIN_USERNAME:
        return jsonify({'error': '用户名或密码错误'}), 401
    
    if not bcrypt.check_password_hash(ADMIN_PASSWORD_HASH, password):
        return jsonify({'error': '用户名或密码错误'}), 401
    
    session_token = secrets.token_urlsafe(32)
    admin_sessions[session_token] = time.time() + ADMIN_SESSION_TIMEOUT
    
    return jsonify({
        'success': True,
        'token': session_token,
        'expires_in': ADMIN_SESSION_TIMEOUT
    })

@app.route('/api/admin/logout', methods=['POST'])
@csrf_protect
def admin_logout():
    admin_token = request.headers.get('X-Admin-Token', '')
    if admin_token in admin_sessions:
        del admin_sessions[admin_token]
    return jsonify({'success': True})

@app.route('/api/admin/check-session', methods=['GET'])
def check_admin_session():
    admin_token = request.headers.get('X-Admin-Token', '')
    if admin_token and admin_token in admin_sessions and admin_sessions[admin_token] > time.time():
        return jsonify({'valid': True})
    return jsonify({'valid': False}), 401

def get_user_owned_code_count(username):
    count = 0
    for code, data in point_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            count += 1
    for code, data in premium_point_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            count += 1
    for code, data in reset_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            count += 1
    for code, data in boost_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            count += 1
    for code, data in cancellation_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            count += 1
    for code, data in special_point_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            count += 1
    for code, data in makeup_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            count += 1
    for code, data in gamblers_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            count += 1
    for code, data in box_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            count += 1
    for code, data in plcard_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            count += 1
    for code, data in premium_boost_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            count += 1
    return count

def check_user_code_limit(username):
    count = get_user_owned_code_count(username)
    if count >= 16:
        return False, f'背包卡密已达上限(16/16)，请先使用或回收部分卡密'
    return True, None

def get_product_number(product_type):
    base = '2026'
    random_part = str(random.randint(1000000000000, 9999999999999))
    return base + random_part

def generate_order_id(product_type):
    prefix_map = {
        'reset': 'RST',
        'point': 'PNT',
        'premium_point': 'PMP',
        'boost': 'BST',
        'cancellation': 'CAN',
        'special_point': 'SPT',
        'makeup': 'MUP',
        'gamblers': 'GBS',
        'box': 'BOX',
        'plcard': 'PLC',
        'premium_boost': 'PBO',
        'gateway': 'GTW',
        'transfer': 'TRF'
    }
    prefix = prefix_map.get(product_type, 'ORD')
    timestamp = int(time.time() * 1000)
    random_part = ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(6))
    return f"{prefix}_{timestamp}_{random_part}"

def generate_coupon_id():
    return f"CPN_{int(time.time()*1000)}_{random.randint(1000,9999)}"

def get_user_coupon_count(username):
    count = 0
    for cid, coupon in user_coupons.items():
        if coupon.get('username') == username and not coupon.get('used', False):
            count += 1
    return count

def get_coupon_type_label(coupon_type):
    type_map = {
        'full_reduction': '满减券',
        'unconditional': '无门槛券',
        'product_specific': '指定商品券',
        'pl_discount': 'PL立减金',
        'makeup_specific': '指定补签卡券',
        'gamblers_specific': '赌神卡券'
    }
    return type_map.get(coupon_type, coupon_type)

def get_product_type_label(product_id):
    type_map = {
        'point_code': '普通积分卡密',
        'premium_point_code': '高级积分卡密',
        'reset_code': '重置密码卡密',
        'boost_code': '积分加成卡密',
        'special_point_code': '特殊积分卡密',
        'makeup_code': '补签卡',
        'gamblers_code': '赌神积分卡',
        'box_code': '盲盒卡',
        'plcard_code': '普通PL随机卡',
        'premium_boost_code': '高级加成卡'
    }
    return type_map.get(product_id, product_id)

def grant_coupon_to_user(username, coupon_type, discount, threshold=0, duration_hours=24, product_id='', description=''):
    if get_user_coupon_count(username) >= 9:
        return False, '用户优惠券已达上限(9张)'
    if duration_hours < 1:
        duration_hours = 1
    if duration_hours > 168:
        duration_hours = 168
    if coupon_type == 'pl_discount':
        if discount < 3 or discount > 12:
            return False, 'PL立减金金额必须在3-12之间'
        threshold = 0
        product_id = ''
        description = description or f'PL立减{discount}PL'
    elif coupon_type == 'full_reduction':
        if discount > 10:
            discount = 10
        if threshold < discount:
            threshold = discount * 2
        if threshold > 12:
            threshold = 12
        description = description or f'满{threshold}减{discount}'
    elif coupon_type == 'unconditional':
        if discount > 7:
            discount = 7
        description = description or f'无门槛减{discount}'
    elif coupon_type == 'product_specific':
        price_map = {'point_code': 1.2, 'premium_point_code': 3.5, 'reset_code': 8, 'boost_code': 8.8, 'special_point_code': 20, 'makeup_code': 200, 'gamblers_code': 100, 'box_code': 28.8, 'plcard_code': 35.8, 'premium_boost_code': 15.6}
        base_price = price_map.get(product_id, 0)
        if base_price <= 0:
            return False, '无效的商品ID'
        max_discount = base_price * 0.8
        if discount > max_discount:
            return False, f'指定商品券优惠金额不能超过原价{base_price}积分的80%，即{max_discount:.2f}积分'
        product_label = get_product_type_label(product_id) if product_id else ''
        description = description or f'指定{product_label}减{discount}'
    elif coupon_type == 'makeup_specific':
        return False, '补签卡券已移除'
    elif coupon_type == 'gamblers_specific':
        return False, '赌神卡券已移除'
    else:
        return False, '无效的优惠券类型'

    mail_attachment_id = f"mail_{int(time.time()*1000)}_{random.randint(1000,9999)}"
    coupon_id = generate_coupon_id()
    expire_at = int((time.time() + duration_hours * 3600) * 1000)

    mail_attachments[mail_attachment_id] = {
        'id': mail_attachment_id,
        'username': username,
        'type': 'coupon',
        'coupon_data': {
            'id': coupon_id,
            'username': username,
            'type': coupon_type,
            'discount': round(discount, 1),
            'threshold': round(threshold, 1),
            'product_id': product_id,
            'product_type': product_id.replace('_code', '') if product_id and '_code' in product_id else product_id,
            'used': False,
            'expire_at': expire_at,
            'created_at': int(time.time() * 1000),
            'description': description
        },
        'used': False,
        'created_at': int(time.time() * 1000),
        'expires_at': int(time.time() * 1000) + 28800000,
        'title': f'优惠券-{get_coupon_type_label(coupon_type)}',
        'description': description,
        'claimed': False,
        'claimed_at': 0,
        'source': 'admin_grant'
    }
    save_mail_attachments()

    if username not in coupon_grants:
        coupon_grants[username] = []
    coupon_grants[username].append({
        'coupon_id': coupon_id,
        'granted_at': int(time.time() * 1000),
        'type': coupon_type,
        'discount': round(discount, 1),
        'threshold': round(threshold, 1),
        'product_id': product_id,
        'via_mail': True,
        'mail_attachment_id': mail_attachment_id
    })
    save_coupon_grants()
    return True, coupon_id

def auto_grant_coupons():
    current_time = int(time.time() * 1000)
    for username, user_data in users.items():
        if is_login_restricted(username):
            continue
        if not check_identity_verified(username):
            continue
        last_grant_check = user_data.get('last_coupon_grant_check', 0)
        if current_time - last_grant_check < 600000:
            continue
        user_data['last_coupon_grant_check'] = current_time

        makeup_used_count = user_data.get('makeup_code_used_count', 0)
        makeup_remaining = 3 - makeup_used_count

        cancellation_purchased = user_data.get('cancellationCodePurchased', False)

        rand_val = random.random()
        if rand_val < 0.01:
            coupon_type = 'pl_discount'
            discount = round(random.uniform(3, 12), 1)
            desc = f'PL立减{discount}PL'
            grant_coupon_to_user(username, coupon_type, discount, 0, random.randint(24, 72), '', desc)
        elif rand_val < 0.04:
            coupon_type = 'unconditional'
            discount = round(random.uniform(0.3, 7), 1)
            if discount < 0.3:
                discount = 0.3
            desc = f'无门槛减{discount}'
            grant_coupon_to_user(username, coupon_type, discount, 0, random.randint(24, 72), '', desc)
        elif rand_val < 0.22:
            coupon_type = 'product_specific'
            product_ids = ['point_code', 'premium_point_code', 'reset_code', 'boost_code', 'special_point_code']
            if makeup_remaining > 0:
                product_ids.append('makeup_code')
            if not cancellation_purchased:
                product_ids.append('cancellation_code')
            product_id = random.choice(product_ids)
            price_map = {'point_code': 1.2, 'premium_point_code': 3.5, 'reset_code': 8, 'boost_code': 8.8, 'special_point_code': 20, 'cancellation_code': 9.9, 'gamblers_code': 100, 'box_code': 28.8, 'plcard_code': 35.8, 'premium_boost_code': 15.6}
            base_price = price_map.get(product_id, 0)
            max_discount = base_price * 0.8
            discount = round(random.uniform(0.3, max_discount), 1)
            if discount < 0.3:
                discount = 0.3
            if discount > max_discount:
                discount = max_discount
            product_label = get_product_type_label(product_id)
            desc = f'指定{product_label}减{discount}'
            grant_coupon_to_user(username, coupon_type, discount, 0, random.randint(24, 72), product_id, desc)
        elif rand_val < 0.52:
            coupon_type = 'full_reduction'
            discount = round(random.uniform(0.5, 10), 1)
            if discount < 0.5:
                discount = 0.5
            threshold = min(max(round(discount * random.uniform(2, 4), 1), discount + 0.5), 12)
            desc = f'满{threshold}减{discount}'
            grant_coupon_to_user(username, coupon_type, discount, threshold, random.randint(24, 72), '', desc)
        save_users()

def auto_grant_coupons_loop():
    while True:
        time.sleep(300)
        try:
            auto_grant_coupons()
        except Exception as e:
            log.error(f"Auto grant coupons error: {e}")

coupon_grant_thread = threading.Thread(target=auto_grant_coupons_loop, daemon=True)
coupon_grant_thread.start()

def get_current_period():
    return int(time.time()) // PL_FLUCTUATION_INTERVAL

def get_card_expire_time(card_type):
    now = datetime.now()
    if card_type == 'hour':
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        if now.minute == 0 and now.second == 0:
            next_hour = now + timedelta(hours=1)
            next_hour = next_hour.replace(minute=0, second=0, microsecond=0)
        return int(next_hour.timestamp() * 1000)
    elif card_type == 'day':
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return int(tomorrow.timestamp() * 1000)
    elif card_type == 'week':
        next_week = now + timedelta(days=7)
        return int(next_week.timestamp() * 1000)
    elif card_type == 'permanent':
        return 0
    return 0

def get_card_price(card_type, remain_hours=None):
    prices = {'hour': 6.6, 'week': 288.8, 'permanent': 1888.0}
    if card_type == 'day':
        if remain_hours is not None and remain_hours > 0:
            return round(remain_hours * 6.6, 2)
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        remain_ms = (tomorrow - now).total_seconds() * 1000
        remain_hours = max(0, math.ceil(remain_ms / (1000 * 60 * 60)))
        if remain_hours <= 0:
            return 0
        return round(remain_hours * 6.6, 2)
    return prices.get(card_type, 0)

def get_user_active_card(username):
    current_time = int(time.time() * 1000)
    if username not in gateway_cards:
        return None
    card_data = gateway_cards[username]
    if card_data.get('used', False):
        return None
    if card_data.get('expire_at', 0) > 0 and current_time > card_data.get('expire_at', 0):
        card_data['used'] = True
        save_gateway_cards()
        return None
    return card_data

def refund_gateway_card(username):
    if username in gateway_cards:
        card_data = gateway_cards[username]
        if not card_data.get('used', False):
            points_to_refund = card_data.get('price', 0)
            if points_to_refund > 0:
                user_data = users.get(username)
                if user_data:
                    user_data['totalPoints'] = round(user_data.get('totalPoints', 0) + points_to_refund, 2)
                    save_users()
            del gateway_cards[username]
            save_gateway_cards()
            return True
    return False

def cleanup_expired_gateway_cards():
    current_time = int(time.time() * 1000)
    users_to_remove = []
    for username, card_data in gateway_cards.items():
        if card_data.get('used', False):
            users_to_remove.append(username)
        elif card_data.get('expire_at', 0) > 0 and current_time > card_data.get('expire_at', 0):
            users_to_remove.append(username)
    for username in users_to_remove:
        if username in gateway_cards:
            del gateway_cards[username]
    if users_to_remove:
        save_gateway_cards()

def migrate_restricted_users():
    modified = False
    for username, data in restricted_users.items():
        if 'restrictions' not in data:
            data['restrictions'] = {'login': False, 'mall': False, 'generate_phone': False}
            modified = True
        for rtype in ['login', 'mall', 'generate_phone']:
            if rtype not in data['restrictions']:
                data['restrictions'][rtype] = False
                modified = True
    if modified:
        save_restricted_users()

def get_current_nav():
    today = datetime.now().strftime('%Y-%m-%d')
    nav_entry = nav_data.get(today)
    if nav_entry:
        return nav_entry.get('nav', 0.0018)
    return generate_new_nav()

def generate_new_nav():
    today = datetime.now().strftime('%Y-%m-%d')
    import hashlib
    seed_bytes = today.encode() + b'nav_salt_2024'
    seed_hash = hashlib.md5(seed_bytes).hexdigest()
    seed_int = int(seed_hash[:8], 16)
    random.seed(seed_int)
    nav = round(random.uniform(NAV_MIN, NAV_MAX), 4)
    random.seed()
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    yesterday_nav = nav_data.get(yesterday, {}).get('nav', None)
    
    if yesterday_nav is not None:
        change_percent = abs(nav - yesterday_nav) / yesterday_nav if yesterday_nav > 0 else 0
        if change_percent > 0.15:
            if nav > yesterday_nav:
                nav = round(yesterday_nav * 1.15, 4)
            else:
                nav = round(yesterday_nav * 0.85, 4)
    
    nav_data[today] = {
        'nav': nav,
        'date': today,
        'updated_at': int(time.time() * 1000)
    }
    save_nav_data()
    return nav

def get_user_nav_holdings(username):
    return nav_holdings.get(username, [])

def get_user_total_nav_shares(username):
    holdings = nav_holdings.get(username, [])
    return sum(h.get('shares', 0) for h in holdings)

def get_user_nav_market_value(username):
    holdings = nav_holdings.get(username, [])
    current_nav = get_current_nav()
    return sum(h.get('shares', 0) * current_nav for h in holdings)

def get_user_nav_profit(username):
    holdings = nav_holdings.get(username, [])
    current_nav = get_current_nav()
    total_profit = 0
    for h in holdings:
        cost = h.get('shares', 0) * h.get('buy_nav', 0)
        value = h.get('shares', 0) * current_nav
        total_profit += (value - cost)
    return round(total_profit, 4)

def get_user_nav_avg_cost(username):
    holdings = nav_holdings.get(username, [])
    total_cost = 0
    total_shares = 0
    for h in holdings:
        total_cost += h.get('shares', 0) * h.get('buy_nav', 0)
        total_shares += h.get('shares', 0)
    if total_shares > 0:
        return round(total_cost / total_shares, 4)
    return 0

def nav_buy(username, amount):
    if amount <= 0:
        return None, '申购金额必须大于0'
    user_data = users.get(username)
    if not user_data:
        return None, '用户不存在'
    if user_data.get('totalPoints', 0) < amount:
        return None, f'积分不足，需要{amount}积分，当前{user_data.get("totalPoints", 0):.2f}积分'
    
    current_nav = get_current_nav()
    shares = round(amount / current_nav, 2)
    if shares <= 0:
        return None, '申购金额太少，无法获得有效份额'
    
    user_data['totalPoints'] = round(user_data['totalPoints'] - amount, 2)
    save_users()
    
    if username not in nav_holdings:
        nav_holdings[username] = []
    
    nav_holdings[username].append({
        'shares': shares,
        'buy_nav': current_nav,
        'buy_amount': amount,
        'buy_time': int(time.time() * 1000)
    })
    save_nav_holdings()
    
    record_id = f"nav_{int(time.time()*1000)}_{random.randint(1000,9999)}"
    nav_history[record_id] = {
        'id': record_id,
        'username': username,
        'type': 'buy_nav',
        'shares': shares,
        'nav': current_nav,
        'amount': amount,
        'timestamp': int(time.time() * 1000)
    }
    save_nav_history()
    
    return {'shares': shares, 'nav': current_nav, 'amount': amount}, None

def nav_sell(username, shares_to_sell):
    if shares_to_sell <= 0:
        return None, '赎回份额必须大于0'
    holdings = nav_holdings.get(username, [])
    total_shares = sum(h.get('shares', 0) for h in holdings)
    if total_shares < shares_to_sell:
        return None, f'持有份额不足，需要{shares_to_sell}份，当前持有{total_shares:.2f}份'
    today_start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    today_end = int(datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999).timestamp() * 1000)
    today_buy_records = []
    for h in holdings:
        buy_time = h.get('buy_time', 0)
        if today_start <= buy_time <= today_end:
            today_buy_records.append(h)
    if today_buy_records:
        today_buy_count = len(today_buy_records)
        today_buy_shares = sum(h.get('shares', 0) for h in today_buy_records)
        return None, f'您今天有{today_buy_count}笔申购记录（共{today_buy_shares:.2f}份），申购当天不得进行赎回操作，请于次日00:00后再试'
    current_nav = get_current_nav()
    remaining_to_sell = shares_to_sell
    total_amount = 0
    total_cost = 0
    new_holdings = []
    for h in holdings:
        if remaining_to_sell <= 0:
            new_holdings.append(h)
            continue
        h_shares = h.get('shares', 0)
        if h_shares <= remaining_to_sell:
            remaining_to_sell -= h_shares
            total_amount += h_shares * current_nav
            total_cost += h_shares * h.get('buy_nav', 0)
        else:
            new_shares = h_shares - remaining_to_sell
            total_amount += remaining_to_sell * current_nav
            total_cost += remaining_to_sell * h.get('buy_nav', 0)
            h['shares'] = new_shares
            new_holdings.append(h)
            remaining_to_sell = 0
    nav_holdings[username] = new_holdings
    save_nav_holdings()
    profit = round(total_amount - total_cost, 4)
    user_data = users.get(username)
    if user_data:
        if profit > 0:
            tax_rate = get_nav_profit_tax_rate(profit, total_cost)
            profit_fee = round(profit * tax_rate, 4)
            user_receive = round(total_amount - profit_fee, 4)
            user_data['totalPoints'] = round(user_data['totalPoints'] + user_receive, 2)
            add_system_total_points(profit_fee)
        else:
            loss_amount = abs(profit)
            user_data['totalPoints'] = round(user_data['totalPoints'] + total_amount, 2)
            add_system_total_points(loss_amount)
        save_users()
    record_id = f"nav_{int(time.time()*1000)}_{random.randint(1000,9999)}"
    nav_history[record_id] = {
        'id': record_id,
        'username': username,
        'type': 'sell_nav',
        'shares': shares_to_sell,
        'nav': current_nav,
        'amount': total_amount,
        'profit': profit,
        'profit_fee': round(profit * get_nav_profit_tax_rate(profit, total_cost), 4) if profit > 0 else 0,
        'loss_amount': abs(profit) if profit < 0 else 0,
        'user_receive': round(total_amount - (profit * get_nav_profit_tax_rate(profit, total_cost)), 4) if profit > 0 else total_amount,
        'timestamp': int(time.time() * 1000)
    }
    save_nav_history()
    tax_rate = get_nav_profit_tax_rate(profit, total_cost) if profit > 0 else 0
    return {
        'amount': round(total_amount, 2),
        'shares': shares_to_sell,
        'nav': current_nav,
        'profit': profit,
        'profit_fee': round(profit * tax_rate, 4) if profit > 0 else 0,
        'loss_amount': abs(profit) if profit < 0 else 0,
        'user_receive': round(total_amount - (profit * tax_rate), 4) if profit > 0 else total_amount,
        'tax_rate': tax_rate
    }, None

def nav_sell_single(username, index, shares):
    if shares <= 0:
        return None, '赎回份额必须大于0'
    holdings = nav_holdings.get(username, [])
    if index < 0 or index >= len(holdings):
        return None, '持仓不存在'
    holding = holdings[index]
    if holding.get('shares', 0) < shares:
        return None, f'持有份额不足，需要{shares}份，当前持有{holding.get("shares", 0):.2f}份'
    today_start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    today_end = int(datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999).timestamp() * 1000)
    buy_time = holding.get('buy_time', 0)
    if today_start <= buy_time <= today_end:
        return None, '申购当天不得进行赎回操作，请于次日00:00后再试'
    current_nav = get_current_nav()
    total_amount = shares * current_nav
    total_cost = shares * holding.get('buy_nav', 0)
    profit = round(total_amount - total_cost, 4)
    if shares >= holding.get('shares', 0):
        del holdings[index]
    else:
        holding['shares'] = round(holding['shares'] - shares, 2)
    nav_holdings[username] = holdings
    save_nav_holdings()
    user_data = users.get(username)
    profit_fee = 0
    loss_amount = 0
    user_receive = total_amount
    if user_data:
        if profit > 0:
            tax_rate = get_nav_profit_tax_rate(profit, total_cost)
            profit_fee = round(profit * tax_rate, 4)
            user_receive = round(total_amount - profit_fee, 4)
            user_data['totalPoints'] = round(user_data['totalPoints'] + user_receive, 2)
            add_system_total_points(profit_fee)
        elif profit < 0:
            loss_amount = abs(profit)
            user_receive = total_amount
            user_data['totalPoints'] = round(user_data['totalPoints'] + total_amount, 2)
            add_system_total_points(loss_amount)
        else:
            user_receive = total_amount
            user_data['totalPoints'] = round(user_data['totalPoints'] + total_amount, 2)
        save_users()
    record_id = f"nav_{int(time.time()*1000)}_{random.randint(1000,9999)}"
    nav_history[record_id] = {
        'id': record_id,
        'username': username,
        'type': 'sell_nav',
        'shares': shares,
        'nav': current_nav,
        'amount': total_amount,
        'profit': profit,
        'profit_fee': profit_fee,
        'loss_amount': loss_amount,
        'user_receive': user_receive,
        'timestamp': int(time.time() * 1000)
    }
    save_nav_history()
    tax_rate = get_nav_profit_tax_rate(profit, total_cost) if profit > 0 else 0
    return {
        'amount': round(total_amount, 2),
        'shares': shares,
        'nav': current_nav,
        'profit': profit,
        'profit_fee': profit_fee,
        'loss_amount': loss_amount,
        'user_receive': user_receive,
        'tax_rate': tax_rate
    }, None

def migrate_auth_codes():
    modified = False
    for code, data in auth_codes.items():
        if 'verified' not in data:
            data['verified'] = False
            modified = True
        if 'reward_claimed' not in data:
            data['reward_claimed'] = False
            modified = True
    if modified:
        save_auth_codes()

def migrate_user_login_time():
    modified = False
    for username, user_data in users.items():
        if 'lastLoginTime' not in user_data:
            last_login_date = user_data.get('lastLoginDate', '')
            if last_login_date:
                try:
                    dt = datetime.strptime(last_login_date, '%Y-%m-%d')
                    user_data['lastLoginTime'] = dt.isoformat()
                except:
                    user_data['lastLoginTime'] = ''
            else:
                user_data['lastLoginTime'] = ''
            modified = True
    
    if modified:
        save_users()
        log.info("用户登录时间数据迁移完成 (ISO 8601)")

def migrate_game_stats_to_users():
    modified = False
    for username, user_data in users.items():
        if 'game_stats' not in user_data:
            user_data['game_stats'] = {
                'today_plays': 0,
                'today_date': '',
                'total_wins': 0,
                'total_plays': 0
            }
            modified = True
        else:
            if 'today_date' not in user_data['game_stats']:
                user_data['game_stats']['today_date'] = ''
                modified = True
            if 'today_plays' not in user_data['game_stats']:
                user_data['game_stats']['today_plays'] = 0
                modified = True
            if 'total_wins' not in user_data['game_stats']:
                user_data['game_stats']['total_wins'] = 0
                modified = True
            if 'total_plays' not in user_data['game_stats']:
                user_data['game_stats']['total_plays'] = 0
                modified = True
    if modified:
        save_users()
        log.info("游戏统计数据迁移完成")

def migrate_existing_game_limits_to_users():
    modified = False
    for username, limits in user_code_limits.items():
        if 'game' in limits and username in users:
            game_limits = limits['game']
            if 'game_stats' not in users[username]:
                users[username]['game_stats'] = {}
            users[username]['game_stats']['total_wins'] = game_limits.get('total_wins', 0)
            users[username]['game_stats']['total_plays'] = game_limits.get('total_plays', 0)
            modified = True
            log.info(f"已迁移用户 {username} 的游戏数据: 胜场 {game_limits.get('total_wins', 0)}, 总场 {game_limits.get('total_plays', 0)}")
    if modified:
        save_users()
        log.info("历史游戏数据迁移完成")

def force_recalculate_first_attendance_date():
    modified = False
    for username, user_data in users.items():
        total_days = user_data.get('attendanceTotalDays', 0)
        consecutive_days = user_data.get('attendanceConsecutiveDays', 0)
        last_date = user_data.get('lastAttendanceDate', '')
        
        if not last_date:
            continue
        
        if total_days == 0:
            continue
        
        try:
            last_dt = datetime.strptime(last_date, '%Y-%m-%d')
            first_dt = last_dt - timedelta(days=total_days - 1)
            first_date_str = first_dt.strftime('%Y-%m-%d')
            
            if user_data.get('firstAttendanceDate') != first_date_str:
                user_data['firstAttendanceDate'] = first_date_str
                modified = True
        except Exception as e:
            pass
    
    if modified:
        save_users()

force_recalculate_first_attendance_date()

def generate_qr_token(order_id, product_number):
    timestamp = int(time.time())
    data = f"{order_id}|{product_number}|{timestamp}"
    signature = hmac.new(QR_SECRET, data.encode(), hashlib.sha256).hexdigest()[:16]
    combined = f"{data}|{signature}"
    token = base64.urlsafe_b64encode(combined.encode()).decode().replace('=', '')
    return token, timestamp

def decode_qr_token(token):
    try:
        decoded = base64.urlsafe_b64decode(token + '=' * (4 - len(token) % 4)).decode()
        parts = decoded.split('|')
        if len(parts) != 4:
            return None, None, None, '格式错误'
        order_id = parts[0]
        product_number = parts[1]
        timestamp = int(parts[2])
        received_signature = parts[3]
        
        data = f"{order_id}|{product_number}|{timestamp}"
        expected_signature = hmac.new(QR_SECRET, data.encode(), hashlib.sha256).hexdigest()[:16]
        
        if not hmac.compare_digest(received_signature, expected_signature):
            return None, None, None, '签名验证失败'
        
        return order_id, product_number, timestamp, None
    except Exception as e:
        return None, None, None, str(e)

def get_card_usage_status(code, product_type):
    code_type_map = {
        'point': point_codes,
        'premium_point': premium_point_codes,
        'reset': reset_codes,
        'boost': boost_codes,
        'special_point': special_point_codes,
        'makeup': makeup_codes,
        'gamblers': gamblers_codes,
        'cancellation': cancellation_codes,
        'box': box_codes,
        'plcard': plcard_codes,
        'premium_boost': premium_boost_codes
    }
    if product_type not in code_type_map:
        return 'used'
    codes = code_type_map[product_type]
    if code in codes:
        if codes[code].get('used', False):
            return 'used'
        else:
            return 'unused'
    return 'used'

def perform_refund_risk_check(username, refund_points):
    if refund_points < 100:
        return True, None, 0, []

    user_data = users.get(username, {})
    if not user_data:
        return False, "用户不存在，无法进行风控审查", 100, [{'text': '用户不存在', 'score': 100}]

    risk_score = 0
    risk_details = []

    total_days = user_data.get('attendanceTotalDays', 0)
    consecutive_days = user_data.get('attendanceConsecutiveDays', 0)
    today = datetime.now().strftime('%Y-%m-%d')
    has_attended_today = user_data.get('lastAttendanceDate', '') == today

    if total_days < 7:
        risk_score += 15
        risk_details.append({'text': '注册天数不足7天', 'score': 15})
    elif total_days < 14:
        risk_score += 8
        risk_details.append({'text': '注册天数不足14天', 'score': 8})

    if consecutive_days < 3:
        risk_score += 10
        risk_details.append({'text': '连续签到天数不足3天', 'score': 10})
    elif consecutive_days < 7:
        risk_score += 5
        risk_details.append({'text': '连续签到天数不足7天', 'score': 5})

    if not has_attended_today:
        risk_score += 12
        risk_details.append({'text': '今日未签到', 'score': 12})

    restrictions = get_user_restrictions(username)
    if restrictions.get('login', False):
        risk_score += 30
        risk_details.append({'text': '账号已被限制登录', 'score': 30})
    if restrictions.get('mall', False):
        risk_score += 20
        risk_details.append({'text': '账号已被限制商城功能', 'score': 20})
    if restrictions.get('generate_phone', False):
        risk_score += 15
        risk_details.append({'text': '账号已被限制生成手机号', 'score': 15})

    if not check_identity_verified(username):
        risk_score += 25
        risk_details.append({'text': '未完成身份认证', 'score': 25})

    total_points = user_data.get('totalPoints', 0)
    fund_balance = get_user_fund_balance(username)
    total_assets = total_points + fund_balance

    if total_assets > 0 and refund_points > total_assets * 0.8:
        risk_score += 20
        risk_details.append({'text': '退款金额超过总资产的80%', 'score': 20})
    elif total_assets > 0 and refund_points > total_assets * 0.5:
        risk_score += 8
        risk_details.append({'text': '退款金额超过总资产的50%', 'score': 8})

    daily_earned = user_data.get('dailyEarnedPoints', 0)
    if daily_earned < 3 and total_points < 100:
        risk_score += 15
        risk_details.append({'text': '今日获取积分不足3分且总积分低于100', 'score': 15})

    created_at_str = user_data.get('createdAt', '')
    if created_at_str:
        try:
            created_at = datetime.fromisoformat(created_at_str)
            days_since_reg = (datetime.now() - created_at).days
            if days_since_reg < 1:
                risk_score += 20
                risk_details.append({'text': '注册不足24小时', 'score': 20})
        except:
            pass

    email = user_data.get('email', '')
    if not email:
        risk_score += 10
        risk_details.append({'text': '未绑定邮箱', 'score': 10})

    if not user_data.get('email_verified', False):
        risk_score += 8
        risk_details.append({'text': '邮箱未验证', 'score': 8})

    qq_number = user_data.get('qq_number', '')
    if not qq_number:
        risk_score += 5
        risk_details.append({'text': '未绑定QQ号', 'score': 5})

    pl_balance = get_user_pl_balance(username)
    if pl_balance < 1 and total_points < 50:
        risk_score += 10
        risk_details.append({'text': 'PL余额不足1且总积分低于50', 'score': 10})

    makeup_used_count = user_data.get('makeup_code_used_count', 0)
    if makeup_used_count >= 3:
        risk_score += 5
        risk_details.append({'text': '补签卡已使用完3次', 'score': 5})

    gamblers_purchase_count = user_data.get('gamblers_code_purchase_count', 0)
    if gamblers_purchase_count >= 3:
        risk_score += 3
        risk_details.append({'text': '当日赌神卡购买已达上限', 'score': 3})

    now = datetime.now()
    current_hour = now.hour
    if current_hour >= 0 and current_hour <= 5:
        risk_score += 8
        risk_details.append({'text': '凌晨时段操作 (0-5点)', 'score': 8})
    elif current_hour >= 23:
        risk_score += 5
        risk_details.append({'text': '深夜时段操作 (23-24点)', 'score': 5})

    user_orders = []
    for oid, order in orders.items():
        if order.get('username') == username and order.get('status') == 'paid' and not order.get('refunded', False):
            user_orders.append(order)
    if len(user_orders) < 3:
        risk_score += 8
        risk_details.append({'text': '历史订单数不足3笔', 'score': 8})

    refund_history_count = 0
    for oid, order in orders.items():
        if order.get('username') == username and order.get('refunded', False):
            refund_history_count += 1
    if refund_history_count > 3:
        risk_score += 20
        risk_details.append({'text': '历史退款次数超过3次', 'score': 20})
    elif refund_history_count > 1:
        risk_score += 5
        risk_details.append({'text': '历史有退款记录', 'score': 5})

    recent_refund_count = 0
    for oid, order in orders.items():
        if order.get('username') == username and order.get('refunded', False):
            refunded_at = order.get('refunded_at', 0)
            if refunded_at > 0 and int(time.time() * 1000) - refunded_at < 3600000:
                recent_refund_count += 1
    if recent_refund_count > 0:
        risk_score += 25
        risk_details.append({'text': '1小时内有过退款记录', 'score': 25})

    pl_exchange_count = 0
    for rid, record in pl_exchange_records.items():
        if record.get('username') == username and record.get('operation_type') == 'pl_to_points':
            pl_exchange_count += 1
    if pl_exchange_count > 0:
        risk_score += 5
        risk_details.append({'text': '近期有PL兑换积分记录', 'score': 5})

    today_pool_claimed = False
    pool_today = datetime.now().strftime('%Y-%m-%d')
    if username in user_pool_claims and pool_today in user_pool_claims[username]:
        today_pool_claimed = True
    if today_pool_claimed:
        risk_score += 5
        risk_details.append({'text': '今日已领取积分瓜分', 'score': 5})

    fund_deposit_count = 0
    for rid, record in fund_history.items():
        if record.get('username') == username and record.get('type') == 'deposit':
            fund_deposit_count += 1
    if fund_deposit_count == 0:
        risk_score += 5
        risk_details.append({'text': '从未使用过理财存入功能', 'score': 5})

    has_pay_pwd = has_pay_password(username)
    if not has_pay_pwd:
        risk_score += 10
        risk_details.append({'text': '未设置支付密码', 'score': 10})

    if not user_data.get('cancellationCodePurchased', False):
        risk_score += 3
        risk_details.append({'text': '未购买过注销卡密', 'score': 3})

    mail_count = sum(1 for a in mail_attachments.values() if a.get('username') == username and not a.get('claimed', False))
    if mail_count > 3:
        risk_score += 5
        risk_details.append({'text': '邮箱有大量未领取附件', 'score': 5})

    risk_score = min(risk_score, 100)

    log.info(f"Refund risk check for {username}: score={risk_score}, details={risk_details}")

    if risk_score < 15:
        return True, None, risk_score, risk_details
    elif risk_score < 35:
        return True, f"风控审查通过（风险评分 {risk_score}，{len(risk_details)} 项检查）", risk_score, risk_details
    elif risk_score < 55:
        return True, f"风控审查通过，但存在风险项（风险评分 {risk_score}）", risk_score, risk_details
    else:
        return False, f"风控审查未通过（风险评分 {risk_score}，共 {len(risk_details)} 项风险），退款申请已被拒绝", risk_score, risk_details

@app.errorhandler(500)
def internal_error(error):
    log.error(f"Internal server error: {error}")
    return jsonify({'error': '服务器内部错误'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '资源不存在'}), 404

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': '请求过于频繁，请稍后再试', 'retry_after': str(e.description)}), 429

@app.before_request
def before_request():
    reload_if_changed()
    cleanup_all_expired_data()

@app.route('/api/claim-backfill-reward', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def claim_backfill_reward():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    phone_number = data.get('phoneNumber', '').strip()
    auth_code = data.get('authCode', '').strip().upper()

    if not phone_number or not auth_code:
        return jsonify({'error': '请提供完整号码和授权码'}), 400

    if len(phone_number) != 11 or not phone_number.isdigit():
        return jsonify({'error': '无效的手机号码格式'}), 400

    if auth_code not in auth_codes:
        return jsonify({'error': '授权码无效或已过期'}), 400

    code_data = auth_codes[auth_code]

    if code_data.get('used'):
        return jsonify({'error': '授权码已被使用'}), 400

    if not code_data.get('verified', False):
        return jsonify({'error': '请先验证授权码'}), 400

    code_username = code_data.get('username')
    if code_username != username:
        return jsonify({'error': '授权码不属于当前用户'}), 400

    stored_phone = code_data.get('phoneNumber')
    if stored_phone != phone_number:
        return jsonify({'error': '完整号码与授权码不匹配'}), 400

    current_time = int(time.time() * 1000)
    if (current_time - code_data.get('createdAt', 0)) > 180000:
        del auth_codes[auth_code]
        save_auth_codes()
        return jsonify({'error': '授权码已过期（3分钟有效）'}), 400

    if code_data.get('reward_claimed', False):
        return jsonify({'error': '该授权码的积分奖励已被领取'}), 400

    points_earned = round(random.uniform(0.1, 0.5), 2)
    points_added = update_earned_points(username, points_earned, False)

    if not points_added:
        return jsonify({'error': '今日获取积分已达上限14分'}), 400

    code_data['used'] = True
    code_data['reward_claimed'] = True
    save_auth_codes()

    for record in phone_records.get(username, []):
        if record.get('authCode') == auth_code:
            record['used'] = True
            save_phone_records()
            break

    multiplier = get_total_multiplier(username)

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'pointsEarned': points_earned,
        'phoneNumber': phone_number,
        'responseTime': response_time,
        'bonusMultiplier': multiplier,
        'originalPoints': points_earned
    })

@app.route('/api/admin/users', methods=['GET'])
@admin_login_required
def admin_get_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').strip()

    user_list = []
    for username, user_data in users.items():
        if search and search.lower() not in username.lower() and search.lower() not in user_data.get('email', '').lower():
            continue

        is_verified = check_identity_verified(username)
        restrictions = get_user_restrictions(username)
        created_at = user_data.get('createdAt', '')
        days_since_reg = 0
        if created_at:
            try:
                created = datetime.fromisoformat(created_at)
                days_since_reg = (datetime.now() - created).days
            except:
                pass

        user_list.append({
            'username': username,
            'email': user_data.get('email', ''),
            'totalPoints': user_data.get('totalPoints', 0),
            'unlimitedPoints': user_data.get('unlimitedPoints', 0),
            'isVerified': is_verified,
            'loginRestricted': restrictions.get('login', False),
            'mallRestricted': restrictions.get('mall', False),
            'generatePhoneRestricted': restrictions.get('generate_phone', False),
            'createdAt': created_at,
            'daysSinceReg': days_since_reg,
            'attendanceTotalDays': user_data.get('attendanceTotalDays', 0),
            'attendanceConsecutiveDays': user_data.get('attendanceConsecutiveDays', 0),
            'hasCancellationCode': user_data.get('cancellationCodePurchased', False)
        })

    total = len(user_list)
    start = (page - 1) * per_page
    end = start + per_page
    user_list = user_list[start:end]

    return jsonify({
        'users': user_list,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })

@app.route('/api/admin/codes', methods=['GET'])
@admin_login_required
def admin_get_codes():
    code_type = request.args.get('type', '')
    username = request.args.get('username', '').strip()

    result_codes = []

    if not code_type or code_type == 'reset':
        for code, data in reset_codes.items():
            if username and data.get('username') != username:
                continue
            result_codes.append({
                'code': code,
                'username': data.get('username', ''),
                'type': 'reset',
                'used': data.get('used', False),
                'recycled': data.get('recycled', False),
                'createdAt': data.get('createdAt', 0),
                'adminGranted': data.get('adminGranted', False)
            })

    if not code_type or code_type == 'point':
        for code, data in point_codes.items():
            if username and data.get('username') != username:
                continue
            result_codes.append({
                'code': code,
                'username': data.get('username', ''),
                'type': 'point',
                'used': data.get('used', False),
                'recycled': data.get('recycled', False),
                'createdAt': data.get('createdAt', 0),
                'adminGranted': data.get('adminGranted', False)
            })

    if not code_type or code_type == 'premium_point':
        for code, data in premium_point_codes.items():
            if username and data.get('username') != username:
                continue
            result_codes.append({
                'code': code,
                'username': data.get('username', ''),
                'type': 'premium_point',
                'used': data.get('used', False),
                'recycled': data.get('recycled', False),
                'createdAt': data.get('createdAt', 0),
                'adminGranted': data.get('adminGranted', False)
            })

    if not code_type or code_type == 'boost':
        for code, data in boost_codes.items():
            if username and data.get('username') != username:
                continue
            result_codes.append({
                'code': code,
                'username': data.get('username', ''),
                'type': 'boost',
                'used': data.get('used', False),
                'recycled': data.get('recycled', False),
                'createdAt': data.get('createdAt', 0),
                'adminGranted': data.get('adminGranted', False)
            })

    if not code_type or code_type == 'cancellation':
        for code, data in cancellation_codes.items():
            if username and data.get('username') != username:
                continue
            result_codes.append({
                'code': code,
                'username': data.get('username', ''),
                'type': 'cancellation',
                'used': data.get('used', False),
                'recycled': data.get('recycled', False),
                'createdAt': data.get('createdAt', 0),
                'adminGranted': data.get('adminGranted', False)
            })

    if not code_type or code_type == 'special_point':
        for code, data in special_point_codes.items():
            if username and data.get('username') != username:
                continue
            result_codes.append({
                'code': code,
                'username': data.get('username', ''),
                'type': 'special_point',
                'used': data.get('used', False),
                'recycled': data.get('recycled', False),
                'createdAt': data.get('createdAt', 0),
                'adminGranted': data.get('adminGranted', False)
            })

    if not code_type or code_type == 'makeup':
        for code, data in makeup_codes.items():
            if username and data.get('username') != username:
                continue
            result_codes.append({
                'code': code,
                'username': data.get('username', ''),
                'type': 'makeup',
                'used': data.get('used', False),
                'recycled': data.get('recycled', False),
                'createdAt': data.get('createdAt', 0),
                'adminGranted': data.get('adminGranted', False)
            })

    if not code_type or code_type == 'gamblers':
        for code, data in gamblers_codes.items():
            if username and data.get('username') != username:
                continue
            result_codes.append({
                'code': code,
                'username': data.get('username', ''),
                'type': 'gamblers',
                'used': data.get('used', False),
                'recycled': data.get('recycled', False),
                'createdAt': data.get('createdAt', 0),
                'adminGranted': data.get('adminGranted', False)
            })

    if not code_type or code_type == 'box':
        for code, data in box_codes.items():
            if username and data.get('username') != username:
                continue
            result_codes.append({
                'code': code,
                'username': data.get('username', ''),
                'type': 'box',
                'used': data.get('used', False),
                'recycled': data.get('recycled', False),
                'createdAt': data.get('createdAt', 0),
                'adminGranted': data.get('adminGranted', False)
            })

    if not code_type or code_type == 'plcard':
        for code, data in plcard_codes.items():
            if username and data.get('username') != username:
                continue
            result_codes.append({
                'code': code,
                'username': data.get('username', ''),
                'type': 'plcard',
                'used': data.get('used', False),
                'recycled': data.get('recycled', False),
                'createdAt': data.get('createdAt', 0),
                'adminGranted': data.get('adminGranted', False)
            })

    if not code_type or code_type == 'premium_boost':
        for code, data in premium_boost_codes.items():
            if username and data.get('username') != username:
                continue
            result_codes.append({
                'code': code,
                'username': data.get('username', ''),
                'type': 'premium_boost',
                'used': data.get('used', False),
                'recycled': data.get('recycled', False),
                'createdAt': data.get('createdAt', 0),
                'adminGranted': data.get('adminGranted', False)
            })

    result_codes.sort(key=lambda x: x.get('createdAt', 0), reverse=True)

    return jsonify({'codes': result_codes})

@app.route('/api/admin/reissue-cancellation', methods=['POST'])
@csrf_protect
def admin_reissue_cancellation():
    data = request.get_json()
    username = data.get('username', '').strip()
    from_ai = data.get('from_ai', False)
    
    if from_ai:
        if 'user' not in session:
            return jsonify({'error': '请先登录'}), 401
        if session['user']['username'] != username:
            return jsonify({'error': '只能操作自己的账号'}), 403
    else:
        admin_token = request.headers.get('X-Admin-Token', '')
        if not admin_token or admin_token not in admin_sessions:
            return jsonify({'error': '请先登录管理员账户'}), 401
        if admin_sessions[admin_token] < time.time():
            del admin_sessions[admin_token]
            return jsonify({'error': '管理员会话已过期，请重新登录'}), 401
        admin_sessions[admin_token] = time.time() + ADMIN_SESSION_TIMEOUT

    if not username or username not in users:
        return jsonify({'error': '用户不存在'}), 400

    user_data = users[username]

    if not user_data.get('cancellationCodePurchased', False):
        if from_ai:
            return jsonify({
                'success': True,
                'status': 'not_purchased',
                'icon': '❌',
                'title': '未购买注销卡密',
                'message': '您尚未购买注销卡密',
                'detail': '购买条件：需连续签到 ≥ 4 天，价格 9.9 积分',
                'suggestion': '前往商城购买',
                'suggestion_url': '/mall.html'
            })
        return jsonify({'error': '该用户未购买过注销卡密，无法补发'}), 400

    for code, cdata in cancellation_codes.items():
        if cdata.get('username') == username and not cdata.get('used', False) and not cdata.get('recycled', False):
            if from_ai:
                return jsonify({
                    'success': True,
                    'status': 'has_card',
                    'icon': '✅',
                    'title': '已有有效注销卡密',
                    'message': '您已持有有效的注销卡密',
                    'detail': '卡密: ' + code,
                    'suggestion': '查看背包使用',
                    'suggestion_url': '/'
                })
            return jsonify({'error': '用户背包中已有有效的注销卡密，无需补发'}), 400

    cancellation_code = generate_cancellation_code()
    
    cancellation_codes[cancellation_code] = {
        'code': cancellation_code,
        'username': username,
        'used': False,
        'recycled': False,
        'createdAt': int(time.time() * 1000),
        'type': 'cancellation',
        'adminGranted': True,
        'source': 'ai_reissue' if from_ai else 'admin_reissue'
    }
    save_cancellation_codes()

    if from_ai:
        return jsonify({
            'success': True,
            'status': 'reissued',
            'icon': '🔄',
            'title': '注销卡密已补发',
            'message': '注销卡密已成功补发至您的背包',
            'detail': '卡密: ' + cancellation_code + '\n请前往背包查看使用',
            'card_code': cancellation_code,
            'suggestion': '查看背包',
            'suggestion_url': '/'
        })
    
    return jsonify({
        'success': True,
        'message': f'成功为用户{username}补发注销卡密'
    })

@app.route('/api/admin/cdk/list', methods=['GET'])
def admin_cdk_list():
    from_ai = request.args.get('from_ai', 'false').lower() == 'true'
    
    if from_ai:
        if 'user' not in session:
            return jsonify({'error': '请先登录'}), 401
    else:
        admin_token = request.headers.get('X-Admin-Token', '')
        if not admin_token or admin_token not in admin_sessions:
            return jsonify({'error': '请先登录管理员账户'}), 401
        if admin_sessions[admin_token] < time.time():
            del admin_sessions[admin_token]
            return jsonify({'error': '管理员会话已过期，请重新登录'}), 401
        admin_sessions[admin_token] = time.time() + ADMIN_SESSION_TIMEOUT
    
    try:
        available_cdks = []
        current_time = int(time.time() * 1000)
        
        for code, package in cdk_packages.items():
            if package.get('used', False):
                continue
            
            start_time_ms = package.get('start_time', 0)
            expiry_time_ms = package.get('expiry_time', 0)
            
            if start_time_ms > 0 and current_time < start_time_ms:
                continue
            
            if expiry_time_ms > 0 and current_time > expiry_time_ms:
                continue
            
            reward_type = package.get('reward_type', '')
            reward_type_map = {
                'points': '积分',
                'point_code': '普通积分卡密',
                'premium_point_code': '高级积分卡密',
                'reset_code': '重置密码卡密',
                'boost_code': '积分加成卡',
                'special_point_code': '特殊积分卡密',
                'makeup_code': '补签卡',
                'gamblers_code': '赌神积分卡',
                'box_code': '盲盒卡',
                'plcard_code': '普通PL随机卡'
            }
            reward_type_label = reward_type_map.get(reward_type, reward_type)
            
            available_cdks.append({
                'code': code,
                'name': package.get('name', ''),
                'reward_type': reward_type_label,
                'reward_value': package.get('reward_value', ''),
                'reward_quantity': package.get('reward_quantity', 1),
                'is_universal': package.get('is_universal', False),
                'min_total_days': package.get('min_total_days', 0),
                'min_consecutive_days': package.get('min_consecutive_days', 0),
                'start_time': start_time_ms,
                'expiry_time': expiry_time_ms,
                'created_at': package.get('created_at', 0)
            })
        
        available_cdks.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        
        if from_ai:
            if not available_cdks:
                return jsonify({
                    'success': True,
                    'status': 'empty',
                    'icon': '📭',
                    'title': '暂无可用CDK',
                    'message': '当前没有可用的CDK礼包码',
                    'cdks': []
                })
            
            return jsonify({
                'success': True,
                'status': 'available',
                'icon': '🎫',
                'title': '可用CDK列表',
                'message': f'当前有 {len(available_cdks)} 个可用的CDK礼包码',
                'cdks': available_cdks[:10]
            })
        
        return jsonify({'success': True, 'cdks': available_cdks})
    except Exception as e:
        print(f"list cdk error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/toggle-restrict', methods=['POST'])
@csrf_protect
@admin_login_required
def admin_toggle_restrict():
    data = request.get_json()
    username = data.get('username', '').strip()
    restrict_type = data.get('restrict_type', 'login')

    if not username or username not in users:
        return jsonify({'error': '用户不存在'}), 400

    if restrict_type not in ['login', 'mall', 'generate_phone']:
        return jsonify({'error': '无效的限制类型'}), 400

    if username not in restricted_users:
        restricted_users[username] = {
            'username': username,
            'restrictions': {'login': False, 'mall': False, 'generate_phone': False},
            'restricted_at': datetime.now().isoformat(),
            'restricted_by': 'admin'
        }
    else:
        if 'restrictions' not in restricted_users[username]:
            restricted_users[username]['restrictions'] = {'login': False, 'mall': False, 'generate_phone': False}

    current_value = restricted_users[username]['restrictions'].get(restrict_type, False)
    restricted_users[username]['restrictions'][restrict_type] = not current_value
    restricted_users[username]['restricted_at'] = datetime.now().isoformat()
    save_restricted_users()

    type_names = {
        'login': '登录',
        'mall': '积分商城',
        'generate_phone': '生成手机号'
    }

    status = '已限制' if not current_value else '已解除限制'

    return jsonify({
        'success': True,
        'message': f'用户{username}的{type_names[restrict_type]}功能{status}',
        'restrictions': restricted_users[username]['restrictions']
    })

@app.route('/api/admin/stats', methods=['GET'])
@admin_login_required
def admin_get_stats():
    total_users = len(users)
    verified_users = sum(1 for u in users if check_identity_verified(u))
    unverified_users = total_users - verified_users
    login_restricted = sum(1 for u in users if get_user_restrictions(u).get('login', False))
    mall_restricted = sum(1 for u in users if get_user_restrictions(u).get('mall', False))
    generate_phone_restricted = sum(1 for u in users if get_user_restrictions(u).get('generate_phone', False))

    total_points_all_users = sum(u.get('totalPoints', 0) for u in users.values())
    system_total = load_system_total_points()

    total_mail_attachments = len(mail_attachments)
    unclaimed_mail = sum(1 for a in mail_attachments.values() if not a.get('claimed', False))

    return jsonify({
        'users': {
            'total': total_users,
            'verified': verified_users,
            'unverified': unverified_users,
            'login_restricted': login_restricted,
            'mall_restricted': mall_restricted,
            'generate_phone_restricted': generate_phone_restricted
        },
        'total_points': round(system_total, 2),
        'user_total_points': round(total_points_all_users, 2),
        'mail': {
            'total': total_mail_attachments,
            'unclaimed': unclaimed_mail
        }
    })

@app.route('/api/admin/cdk/packages', methods=['GET'])
def admin_get_cdk_packages():
    packages_list = []
    for code, package in cdk_packages.items():
        packages_list.append({
            'code': code,
            'name': package.get('name', ''),
            'reward_type': package.get('reward_type', ''),
            'reward_value': package.get('reward_value', ''),
            'reward_quantity': package.get('reward_quantity', 1),
            'is_universal': package.get('is_universal', False),
            'used': package.get('used', False),
            'used_by': package.get('used_by', ''),
            'used_at': package.get('used_at', 0),
            'start_time': package.get('start_time', 0),
            'expiry_time': package.get('expiry_time', 0),
            'created_at': package.get('created_at', 0),
            'min_total_days': package.get('min_total_days', 0),
            'min_consecutive_days': package.get('min_consecutive_days', 0)
        })
    return jsonify({'packages': packages_list})

@app.route('/api/admin/cdk/create', methods=['POST'])
@csrf_protect
@admin_login_required
def admin_create_cdk_package():
    data = request.get_json()
    name = data.get('name', '').strip().lower()
    reward_type = data.get('reward_type', '')
    reward_value = data.get('reward_value', '')
    reward_quantity = data.get('reward_quantity', 1)
    is_universal = data.get('is_universal', False)
    start_time_str = data.get('start_time', '')
    expiry_time_str = data.get('expiry_time', '')
    min_total_days = int(data.get('min_total_days', 0))
    min_consecutive_days = int(data.get('min_consecutive_days', 0))

    if not name or not reward_type or not reward_value:
        return jsonify({'error': '请填写完整信息'}), 400

    if not validate_cdk_name(name):
        return jsonify({'error': 'CDK名称仅限小写字母和数字，长度3-32位'}), 400

    if name in cdk_packages:
        return jsonify({'error': 'CDK名称已存在'}), 400

    if reward_type not in ['points', 'point_code', 'premium_point_code', 'reset_code', 'boost_code', 'special_point_code', 'makeup_code', 'gamblers_code', 'box_code', 'plcard_code']:
        return jsonify({'error': '无效的奖励类型'}), 400

    if reward_type == 'points':
        try:
            reward_value_float = float(reward_value)
            if reward_value_float <= 0 or reward_value_float > 1000:
                return jsonify({'error': '积分数量必须在1-1000之间'}), 400
        except:
            return jsonify({'error': '积分数量必须是数字'}), 400

    try:
        reward_quantity_int = int(reward_quantity)
        if reward_quantity_int < 1 or reward_quantity_int > 100:
            return jsonify({'error': '数量必须在1-100之间'}), 400
    except:
        return jsonify({'error': '数量必须是数字'}), 400

    start_time_ms = 0
    expiry_time_ms = 0

    if start_time_str:
        try:
            start_dt = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            start_time_ms = int(start_dt.timestamp() * 1000)
        except:
            return jsonify({'error': '起始时间格式错误'}), 400

    if expiry_time_str:
        try:
            expiry_dt = datetime.strptime(expiry_time_str, '%Y-%m-%dT%H:%M')
            expiry_time_ms = int(expiry_dt.timestamp() * 1000)
        except:
            return jsonify({'error': '截止时间格式错误'}), 400

    if expiry_time_ms > 0 and start_time_ms > 0:
        max_12_years_ms = 12 * 365 * 24 * 3600 * 1000
        if expiry_time_ms - start_time_ms > max_12_years_ms:
            return jsonify({'error': '起止时间范围不能超过12年'}), 400

    if expiry_time_ms > 0 and start_time_ms > 0 and expiry_time_ms <= start_time_ms:
        return jsonify({'error': '截止时间必须大于起始时间'}), 400

    current_time = int(time.time() * 1000)
    cdk_code = name

    cdk_packages[cdk_code] = {
        'code': cdk_code,
        'name': name,
        'reward_type': reward_type,
        'reward_value': reward_value,
        'reward_quantity': reward_quantity_int,
        'is_universal': is_universal,
        'used': False,
        'used_by': '',
        'used_at': 0,
        'start_time': start_time_ms,
        'expiry_time': expiry_time_ms,
        'created_at': current_time,
        'min_total_days': min_total_days,
        'min_consecutive_days': min_consecutive_days
    }
    save_cdk_packages()

    return jsonify({
        'success': True,
        'message': f'CDK礼包码创建成功，数量: {reward_quantity_int}',
        'cdk_code': cdk_code
    })

@app.route('/api/admin/cdk/delete', methods=['POST'])
@csrf_protect
@admin_login_required
def admin_delete_cdk_package():
    data = request.get_json()
    code = data.get('code', '').strip().lower()

    if not code or code not in cdk_packages:
        return jsonify({'error': 'CDK礼包码不存在'}), 400

    del cdk_packages[code]
    save_cdk_packages()

    return jsonify({'success': True, 'message': 'CDK礼包码已删除'})

@app.route('/api/cdk/exchange', methods=['POST'])
@csrf_protect
@limiter.limit(RATE_LIMITS['exchange_cdk'])
@login_required
@identity_required
def exchange_cdk():
    start_time = time.time()
    data = request.get_json()
    username = session['user']['username']
    cdk_code = data.get('cdkCode', '').strip().lower()

    if not cdk_code:
        return jsonify({'error': '请输入CDK礼包码'}), 400

    cleanup_all_expired_data()

    package = cdk_packages.get(cdk_code)
    if not package:
        return jsonify({'error': 'CDK礼包码无效'}), 400

    if package.get('used', False):
        return jsonify({'error': 'CDK礼包码已被使用'}), 400

    current_time = int(time.time() * 1000)
    start_time_ms = package.get('start_time', 0)
    expiry_time_ms = package.get('expiry_time', 0)

    if start_time_ms > 0 and current_time < start_time_ms:
        start_dt = datetime.fromtimestamp(start_time_ms / 1000)
        return jsonify({'error': f'CDK礼包码尚未开始生效，生效时间: {start_dt.strftime("%Y-%m-%d %H:%M")}'}), 400

    if expiry_time_ms > 0 and current_time > expiry_time_ms:
        return jsonify({'error': 'CDK礼包码已过期'}), 400

    min_total_days = package.get('min_total_days', 0)
    min_consecutive_days = package.get('min_consecutive_days', 0)
    user_data = users.get(username, {})
    user_total_days = user_data.get('attendanceTotalDays', 0)
    user_consecutive_days = user_data.get('attendanceConsecutiveDays', 0)

    if min_total_days > 0 and user_total_days < min_total_days:
        return jsonify({'error': f'需要累计签到{min_total_days}天，当前累计签到{user_total_days}天'}), 400

    if min_consecutive_days > 0 and user_consecutive_days < min_consecutive_days:
        return jsonify({'error': f'需要连续签到{min_consecutive_days}天，当前连续签到{user_consecutive_days}天'}), 400

    if not package.get('is_universal', False):
        package['used'] = True
        package['used_by'] = username
        package['used_at'] = current_time
        save_cdk_packages()
    else:
        user_records = user_cdk_records.get(username, {})
        if cdk_code in user_records:
            return jsonify({'error': '您已经兑换过此CDK礼包码'}), 400

    reward_type = package.get('reward_type')
    reward_value = package.get('reward_value')
    reward_quantity = package.get('reward_quantity', 1)
    reward_description = ''

    # 只创建邮件，不直接存背包
    if reward_type == 'points':
        points_to_add = float(reward_value) * reward_quantity
        mail_attachment_id = f"mail_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        mail_attachments[mail_attachment_id] = {
            'id': mail_attachment_id,
            'username': username,
            'type': 'points',
            'points_amount': points_to_add,
            'used': False,
            'created_at': int(time.time() * 1000),
            'expires_at': int(time.time() * 1000) + 28800000,
            'title': 'CDK兑换-积分奖励',
            'description': f'CDK兑换获得{points_to_add}积分',
            'claimed': False,
            'claimed_at': 0,
            'source': 'cdk_exchange'
        }
        save_mail_attachments()
        reward_description = f'{points_to_add}积分'

    elif reward_type in ['point_code', 'premium_point_code', 'reset_code', 'boost_code', 'special_point_code', 'makeup_code', 'gamblers_code', 'cancellation_code', 'box_code', 'plcard_code', 'premium_boost_code']:
        # 生成卡密，只存入邮件，不直接存背包
        code_storage_map = {
            'point_code': (generate_point_code, '普通积分卡密'),
            'premium_point_code': (generate_premium_point_code, '高级积分卡密'),
            'reset_code': (generate_reset_code, '重置密码卡密'),
            'boost_code': (generate_boost_code, '积分加成卡密'),
            'special_point_code': (generate_special_point_code, '特殊积分卡密'),
            'makeup_code': (generate_makeup_code, '补签卡'),
            'gamblers_code': (generate_gamblers_code, '赌神积分卡密'),
            'cancellation_code': (generate_cancellation_code, '注销卡密'),
            'box_code': (generate_box_code, '盲盒卡'),
            'plcard_code': (generate_plcard_code, '普通PL随机卡'),
            'premium_boost_code': (generate_premium_boost_code, '高级加成卡')
        }

        if reward_type not in code_storage_map:
            return jsonify({'error': '无效的奖励类型'}), 400

        generate_func, type_label = code_storage_map[reward_type]
        generated_codes = []

        for _ in range(reward_quantity):
            code = generate_func()
            generated_codes.append(code)

        # 只存入邮件，不直接存背包
        if len(generated_codes) == 1:
            mail_attachment_id = f"mail_{int(time.time()*1000)}_{random.randint(1000,9999)}"
            mail_attachments[mail_attachment_id] = {
                'id': mail_attachment_id,
                'username': username,
                'type': reward_type,
                'code': generated_codes[0],
                'codes': generated_codes,
                'used': False,
                'created_at': int(time.time() * 1000),
                'expires_at': int(time.time() * 1000) + 28800000,
                'title': f'CDK兑换-{type_label}',
                'description': f'CDK兑换获得{type_label}1张',
                'claimed': False,
                'claimed_at': 0,
                'source': 'cdk_exchange',
                'quantity': 1,
                'is_batch': False
            }
            save_mail_attachments()
            reward_description = f'{type_label} x1'
        else:
            codes_str = '\n'.join(generated_codes)
            mail_attachment_id = f"mail_{int(time.time()*1000)}_{random.randint(1000,9999)}"
            mail_attachments[mail_attachment_id] = {
                'id': mail_attachment_id,
                'username': username,
                'type': reward_type,
                'codes': generated_codes,
                'code': generated_codes[0],
                'used': False,
                'created_at': int(time.time() * 1000),
                'expires_at': int(time.time() * 1000) + 28800000,
                'title': f'CDK兑换-{type_label} x{reward_quantity}',
                'description': f'CDK兑换获得{type_label} {reward_quantity}张\n\n卡密列表:\n{codes_str}',
                'claimed': False,
                'claimed_at': 0,
                'source': 'cdk_exchange',
                'quantity': reward_quantity,
                'is_batch': True
            }
            save_mail_attachments()
            reward_description = f'{type_label} x{reward_quantity}'

        # 注意：cancellation_code 的特殊处理也需要在邮件领取时做
        # 不要在兑换时直接修改用户状态

    else:
        return jsonify({'error': '无效的奖励类型'}), 400

    if package.get('is_universal', False):
        if username not in user_cdk_records:
            user_cdk_records[username] = {}
        user_cdk_records[username][cdk_code] = {
            'cdk_code': cdk_code,
            'cdk_name': package.get('name', ''),
            'exchanged_at': current_time,
            'reward_description': reward_description
        }
        save_user_cdk_records()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'message': f'兑换成功！奖励已发送至邮箱：{reward_description}',
        'reward': reward_description,
        'responseTime': response_time
    })

@app.route('/api/admin/announcements', methods=['GET'])
@admin_login_required
def admin_get_announcements():
    announcement_list = []
    for aid, ann in announcements.items():
        announcement_list.append({
            'id': aid,
            'title': ann.get('title', ''),
            'content': ann.get('content', ''),
            'type': ann.get('type', 'info'),
            'is_sticky': ann.get('is_sticky', False),
            'is_active': ann.get('is_active', True),
            'start_time': ann.get('start_time', 0),
            'end_time': ann.get('end_time', 0),
            'created_at': ann.get('created_at', 0)
        })
    announcement_list.sort(key=lambda x: -x.get('created_at', 0))
    return jsonify({'announcements': announcement_list})

@app.route('/api/admin/announcements/create', methods=['POST'])
@csrf_protect
@admin_login_required
def admin_create_announcement():
    data = request.get_json()
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    ann_type = data.get('type', 'info')
    is_sticky = data.get('is_sticky', False)
    start_time_str = data.get('start_time', '')
    end_time_str = data.get('end_time', '')

    if not title or not content:
        return jsonify({'error': '请填写标题和内容'}), 400

    if ann_type not in ['info', 'warning', 'success', 'danger']:
        ann_type = 'info'

    start_time_ms = 0
    end_time_ms = 0

    if start_time_str:
        try:
            start_dt = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            start_time_ms = int(start_dt.timestamp() * 1000)
        except:
            return jsonify({'error': '起始时间格式错误'}), 400

    if end_time_str:
        try:
            end_dt = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
            end_time_ms = int(end_dt.timestamp() * 1000)
        except:
            return jsonify({'error': '截止时间格式错误'}), 400

    if end_time_ms > 0 and start_time_ms > 0 and end_time_ms <= start_time_ms:
        return jsonify({'error': '截止时间必须大于起始时间'}), 400

    announcement_id = str(int(time.time() * 1000)) + '_' + str(random.randint(1000, 9999))

    announcements[announcement_id] = {
        'id': announcement_id,
        'title': title,
        'content': content,
        'type': ann_type,
        'is_sticky': is_sticky,
        'is_active': True,
        'start_time': start_time_ms,
        'end_time': end_time_ms,
        'created_at': int(time.time() * 1000),
        'created_by': session.get('user', {}).get('username', 'admin')
    }
    save_announcements()

    return jsonify({
        'success': True,
        'message': '公告创建成功',
        'announcement_id': announcement_id
    })

@app.route('/api/admin/announcements/update', methods=['POST'])
@csrf_protect
@admin_login_required
def admin_update_announcement():
    data = request.get_json()
    announcement_id = data.get('id', '')
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    ann_type = data.get('type', 'info')
    is_sticky = data.get('is_sticky', False)
    is_active = data.get('is_active', True)
    start_time_str = data.get('start_time', '')
    end_time_str = data.get('end_time', '')

    if not announcement_id or announcement_id not in announcements:
        return jsonify({'error': '公告不存在'}), 400

    if not title or not content:
        return jsonify({'error': '请填写标题和内容'}), 400

    if ann_type not in ['info', 'warning', 'success', 'danger']:
        ann_type = 'info'

    start_time_ms = 0
    end_time_ms = 0

    if start_time_str:
        try:
            start_dt = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            start_time_ms = int(start_dt.timestamp() * 1000)
        except:
            return jsonify({'error': '起始时间格式错误'}), 400

    if end_time_str:
        try:
            end_dt = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
            end_time_ms = int(end_dt.timestamp() * 1000)
        except:
            return jsonify({'error': '截止时间格式错误'}), 400

    if end_time_ms > 0 and start_time_ms > 0 and end_time_ms <= start_time_ms:
        return jsonify({'error': '截止时间必须大于起始时间'}), 400

    announcements[announcement_id]['title'] = title
    announcements[announcement_id]['content'] = content
    announcements[announcement_id]['type'] = ann_type
    announcements[announcement_id]['is_sticky'] = is_sticky
    announcements[announcement_id]['is_active'] = is_active
    announcements[announcement_id]['start_time'] = start_time_ms
    announcements[announcement_id]['end_time'] = end_time_ms
    announcements[announcement_id]['updated_at'] = int(time.time() * 1000)
    save_announcements()

    return jsonify({'success': True, 'message': '公告更新成功'})

@app.route('/api/admin/announcements/delete', methods=['POST'])
@csrf_protect
@admin_login_required
def admin_delete_announcement():
    data = request.get_json()
    announcement_id = data.get('id', '')

    if not announcement_id or announcement_id not in announcements:
        return jsonify({'error': '公告不存在'}), 400

    del announcements[announcement_id]
    save_announcements()

    return jsonify({'success': True, 'message': '公告删除成功'})

@app.route('/api/admin/knowledge', methods=['GET'])
@admin_login_required
def admin_get_knowledge():
    knowledge_base_path = os.path.join(os.path.dirname(__file__), 'knowledge_base.json')
    if not os.path.exists(knowledge_base_path):
        return jsonify({'topics': []})
    try:
        with open(knowledge_base_path, 'r', encoding='utf-8') as f:
            kb = json.load(f)
        return jsonify({'topics': kb.get('topics', [])})
    except Exception as e:
        log.error(f"Error loading knowledge base: {e}")
        return jsonify({'error': '加载知识库失败'}), 500


@app.route('/api/admin/knowledge/add', methods=['POST'])
@csrf_protect
@admin_login_required
def admin_add_knowledge():
    data = request.get_json()
    title = data.get('title', '').strip()
    keywords = data.get('keywords', [])
    content = data.get('content', '').strip()

    if not title:
        return jsonify({'error': '请输入标题'}), 400
    if not keywords or len(keywords) == 0:
        return jsonify({'error': '请至少输入一个关键词'}), 400
    if not content:
        return jsonify({'error': '请输入内容'}), 400

    keywords = [k.strip() for k in keywords if k.strip()]
    if not keywords:
        return jsonify({'error': '请至少输入一个有效关键词'}), 400

    knowledge_base_path = os.path.join(os.path.dirname(__file__), 'knowledge_base.json')
    if os.path.exists(knowledge_base_path):
        with open(knowledge_base_path, 'r', encoding='utf-8') as f:
            kb = json.load(f)
    else:
        kb = {'topics': []}

    new_id = f"kb_{int(time.time()*1000)}_{random.randint(1000,9999)}"
    kb['topics'].append({
        'id': new_id,
        'keywords': keywords,
        'title': title,
        'content': content
    })

    with open(knowledge_base_path, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    return jsonify({'success': True, 'message': '知识条目添加成功', 'id': new_id})


@app.route('/api/admin/knowledge/update', methods=['POST'])
@csrf_protect
@admin_login_required
def admin_update_knowledge():
    data = request.get_json()
    item_id = data.get('id', '').strip()
    title = data.get('title', '').strip()
    keywords = data.get('keywords', [])
    content = data.get('content', '').strip()

    if not item_id:
        return jsonify({'error': '请提供知识ID'}), 400
    if not title:
        return jsonify({'error': '请输入标题'}), 400
    if not keywords or len(keywords) == 0:
        return jsonify({'error': '请至少输入一个关键词'}), 400
    if not content:
        return jsonify({'error': '请输入内容'}), 400

    keywords = [k.strip() for k in keywords if k.strip()]
    if not keywords:
        return jsonify({'error': '请至少输入一个有效关键词'}), 400

    knowledge_base_path = os.path.join(os.path.dirname(__file__), 'knowledge_base.json')
    if not os.path.exists(knowledge_base_path):
        return jsonify({'error': '知识库不存在'}), 400

    with open(knowledge_base_path, 'r', encoding='utf-8') as f:
        kb = json.load(f)

    found = False
    for topic in kb.get('topics', []):
        if topic.get('id') == item_id:
            topic['title'] = title
            topic['keywords'] = keywords
            topic['content'] = content
            found = True
            break

    if not found:
        return jsonify({'error': '知识条目不存在'}), 400

    with open(knowledge_base_path, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    return jsonify({'success': True, 'message': '知识更新成功'})


@app.route('/api/admin/knowledge/delete', methods=['POST'])
@csrf_protect
@admin_login_required
def admin_delete_knowledge():
    data = request.get_json()
    item_id = data.get('id', '').strip()

    if not item_id:
        return jsonify({'error': '请提供知识ID'}), 400

    knowledge_base_path = os.path.join(os.path.dirname(__file__), 'knowledge_base.json')
    if not os.path.exists(knowledge_base_path):
        return jsonify({'error': '知识库不存在'}), 400

    with open(knowledge_base_path, 'r', encoding='utf-8') as f:
        kb = json.load(f)

    original_len = len(kb.get('topics', []))
    kb['topics'] = [t for t in kb.get('topics', []) if t.get('id') != item_id]

    if len(kb.get('topics', [])) == original_len:
        return jsonify({'error': '知识条目不存在'}), 400

    with open(knowledge_base_path, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    return jsonify({'success': True, 'message': '知识删除成功'})

@app.route('/api/order/create-batch', methods=['POST'])
@csrf_protect
@limiter.limit(RATE_LIMITS['order_create'])
@login_required
@identity_required
def create_batch_order():
    start_time = time.time()
    data = request.get_json()
    username = session['user']['username']
    product_id = data.get('product_id', '')
    product_type = data.get('product_type', '')
    quantity = int(data.get('quantity', 1))
    use_pl = data.get('use_pl', False)
    is_daifu = data.get('is_daifu', False)

    if quantity < 1 or quantity > 5:
        return jsonify({'error': '购买数量必须在1-5之间'}), 400

    product_map = {
        'reset': {'name': '重置密码卡密', 'price': 8, 'type': 'reset'},
        'point': {'name': '普通积分卡密', 'price': 1.2, 'type': 'point'},
        'premium_point': {'name': '高级积分卡密', 'price': 3.5, 'type': 'premium_point'},
        'boost': {'name': '积分加成卡', 'price': 8.8, 'type': 'boost'},
        'cancellation': {'name': '注销账号卡密', 'price': 9.9, 'type': 'cancellation'},
        'special_point': {'name': '特殊积分卡密', 'price': 20, 'type': 'special_point'},
        'makeup': {'name': '补签卡', 'price': 200, 'type': 'makeup'},
        'gamblers': {'name': '赌神积分卡', 'price': 100, 'type': 'gamblers'},
        'box': {'name': '盲盒卡', 'price': 28.8, 'type': 'box'},
        'plcard': {'name': '普通PL随机卡', 'price': 35.8, 'type': 'plcard'},
        'premium_boost': {'name': '高级加成卡', 'price': 15.6, 'type': 'premium_boost'}
    }

    if product_type not in product_map:
        return jsonify({'error': '无效的商品类型'}), 400

    if product_type == 'cancellation' and quantity > 1:
        return jsonify({'error': '注销卡密每个账号仅限购买一次'}), 400

    product_info = product_map[product_type]
    
    # Get detailed price information with tiered pricing
    price_info = get_price_info(product_info['price'], username)
    original_price = price_info['original_price']
    final_price = price_info['final_price']
    
    total_points_price = round(final_price * quantity, 2)
    total_original = round(original_price * quantity, 2)

    if use_pl and product_type == 'cancellation':
        return jsonify({'error': '注销卡密仅支持积分支付'}), 400

    if product_type == 'cancellation':
        user_data = users.get(username, {})
        if user_data.get('cancellationCodePurchased', False):
            return jsonify({'error': '每个账号仅限购买一次注销卡密'}), 400
        consecutive_days = user_data.get('attendanceConsecutiveDays', 0)
        if consecutive_days < 4:
            return jsonify({'error': f'需要连续签到4天才可购买注销卡密，当前连续签到{consecutive_days}天'}), 400

    if product_type == 'makeup':
        user_data = users.get(username, {})
        makeup_used_count = user_data.get('makeup_code_used_count', 0)
        if makeup_used_count >= 3:
            return jsonify({'error': '补签卡永久限购3次，您已使用完所有次数'}), 400
        if quantity > (3 - makeup_used_count):
            return jsonify({'error': f'补签卡剩余购买次数为{3 - makeup_used_count}次'}), 400

    if product_type == 'gamblers':
        user_data = users.get(username, {})
        today = datetime.now().strftime('%Y-%m-%d')
        last_purchase_date = user_data.get('last_gamblers_purchase_date', '')
        purchase_count = user_data.get('gamblers_code_purchase_count', 0)
        if last_purchase_date != today:
            purchase_count = 0
            user_data['gamblers_code_purchase_count'] = 0
            user_data['last_gamblers_purchase_date'] = today
            save_users()
        if purchase_count + quantity > 3:
            return jsonify({'error': f'赌神卡单日限购3次，今日已购买{purchase_count}次'}), 400

    if product_type == 'box':
        user_data = users.get(username, {})
        today = datetime.now().strftime('%Y-%m-%d')
        last_purchase_date = user_data.get('last_box_purchase_date', '')
        purchase_count = user_data.get('box_code_purchase_count', 0)
        if last_purchase_date != today:
            purchase_count = 0
            user_data['box_code_purchase_count'] = 0
            user_data['last_box_purchase_date'] = today
            save_users()
        if purchase_count + quantity > 5:
            return jsonify({'error': f'盲盒卡单日限购5次，今日已购买{purchase_count}次'}), 400

    if product_type == 'plcard':
        user_data = users.get(username, {})
        today = datetime.now().strftime('%Y-%m-%d')
        last_purchase_date = user_data.get('last_plcard_purchase_date', '')
        purchase_count = user_data.get('plcard_code_purchase_count', 0)
        if last_purchase_date != today:
            purchase_count = 0
            user_data['plcard_code_purchase_count'] = 0
            user_data['last_plcard_purchase_date'] = today
            save_users()
        if purchase_count + quantity > 10:
            return jsonify({'error': f'普通PL随机卡单日限购10次，今日已购买{purchase_count}次'}), 400

    can_add, msg = check_user_code_limit(username)
    if not can_add:
        return jsonify({'error': msg}), 400

    if get_user_owned_code_count(username) + quantity > 16 and not is_daifu:
        return jsonify({'error': f'购买{quantity}张卡密后背包将超出上限(16/16)，请先使用或回收部分卡密'}), 400

    payment_method = 'pl' if use_pl else 'points'

    if payment_method == 'pl':
        current_rate = get_current_pl_rate()
        pl_price = round(total_points_price / current_rate, 4)
        order_price = pl_price
    else:
        order_price = total_points_price

    order_id = create_order(
        username,
        f'{product_info["name"]} x{quantity}',
        order_price,
        payment_method,
        product_id,
        product_type,
        quantity,
        is_daifu
    )

    if is_daifu:
        product_number = get_product_number(product_type)
        token, _ = generate_qr_token(order_id, product_number)
        qr_url = f'/qr/{token}'
        base_url = request.host_url.rstrip('/')
        full_qr_url = base_url + qr_url
        return jsonify({
            'success': True,
            'order_id': order_id,
            'is_daifu': True,
            'qr_url': qr_url,
            'full_qr_url': full_qr_url,
            'message': '代付订单已创建，请让朋友扫码支付',
            'redirect_url': qr_url
        })

    return jsonify({
        'success': True,
        'order_id': order_id,
        'payment_method': payment_method,
        'redirect_url': f'/pay/{order_id}',
        'originalPrice': total_original,
        'finalPrice': total_points_price if not use_pl else round(total_points_price / get_current_pl_rate(), 4),
        'quantity': quantity,
        'savedPoints': total_original - total_points_price if is_new_user(username) else 0,
        'price_info': price_info,
        'responseTime': int((time.time() * 1000) % 1000)
    })

def create_order(username, product_name, product_price, payment_method, product_id=None, product_type=None, quantity=1, is_daifu=False):
    order_id = generate_order_id(product_type)
    anti_fake_code = generate_anti_fake_code()
    product_number = get_product_number(product_type)
    is_pl = payment_method == 'pl'
    current_rate = get_current_pl_rate()
    points_price = product_price if not is_pl else product_price * current_rate if current_rate > 0 else product_price
    
    price_info = get_price_info(product_price, username)
    effective_points = get_user_effective_points(username)
    multiplier = get_price_multiplier(username)

    if is_daifu:
        orders[order_id] = {
            'order_id': order_id,
            'username': username,
            'owner': username,
            'payer': None,
            'product_name': product_name,
            'product_price': product_price,
            'product_id': product_id,
            'product_type': product_type,
            'product_number': product_number,
            'payment_method': payment_method,
            'status': 'pending',
            'created_at': int(time.time() * 1000),
            'paid_at': 0,
            'anti_fake_code': anti_fake_code,
            'quantity': quantity,
            'original_price': price_info['original_price'],
            'applied_coupon_discount': 0,
            'used_coupon_ids': [],
            'points_price': points_price,
            'is_pl_order': is_pl,
            'expires_in': 300000,
            'order_type': 'mall',
            'is_daifu': True,
            'daifu_status': 'waiting_pay',
            'price_multiplier': multiplier,
            'effective_points': effective_points,
            'discount_amount': price_info['discount_amount'],
            'discount_type': price_info['discount_type']
        }
    else:
        orders[order_id] = {
            'order_id': order_id,
            'username': username,
            'owner': username,
            'payer': username,
            'product_name': product_name,
            'product_price': product_price,
            'product_id': product_id,
            'product_type': product_type,
            'product_number': product_number,
            'payment_method': payment_method,
            'status': 'pending',
            'created_at': int(time.time() * 1000),
            'paid_at': 0,
            'anti_fake_code': anti_fake_code,
            'quantity': quantity,
            'original_price': price_info['original_price'],
            'applied_coupon_discount': 0,
            'used_coupon_ids': [],
            'points_price': points_price,
            'is_pl_order': is_pl,
            'expires_in': 300000,
            'order_type': 'mall',
            'is_daifu': False,
            'daifu_status': None,
            'price_multiplier': multiplier,
            'effective_points': effective_points,
            'discount_amount': price_info['discount_amount'],
            'discount_type': price_info['discount_type']
        }

    save_orders()
    return order_id

def create_order_with_price(username, product_name, product_price, payment_method, product_id=None, product_type=None, points_price=None, original_price=None, is_pl=False):
    order_id = generate_order_id(product_type)
    anti_fake_code = generate_anti_fake_code()
    product_number = get_product_number(product_type)
    
    price_info = get_price_info(product_price, username)
    effective_points = get_user_effective_points(username)
    multiplier = get_price_multiplier(username)
    
    orders[order_id] = {
        'order_id': order_id,
        'username': username,
        'product_name': product_name,
        'product_price': product_price,
        'product_id': product_id,
        'product_type': product_type,
        'product_number': product_number,
        'payment_method': payment_method,
        'status': 'pending',
        'created_at': int(time.time() * 1000),
        'paid_at': 0,
        'anti_fake_code': anti_fake_code,
        'quantity': 1,
        'original_price': price_info['original_price'],
        'applied_coupon_discount': 0,
        'used_coupon_ids': [],
        'points_price': points_price or product_price,
        'is_pl_order': is_pl,
        'expires_in': 300000,
        'price_multiplier': multiplier,
        'effective_points': effective_points,
        'discount_amount': price_info['discount_amount'],
        'discount_type': price_info['discount_type']
    }
    save_orders()
    return order_id

def get_order(order_id):
    return orders.get(order_id)

def update_order_status(order_id, status, paid_at=0):
    if order_id in orders:
        orders[order_id]['status'] = status
        if paid_at:
            orders[order_id]['paid_at'] = paid_at
        save_orders()
        return True
    return False

def deliver_order(order_id):
    order = orders.get(order_id)
    if not order or order.get('status') != 'paid':
        return False

    product_type = order.get('product_type')
    username = order.get('username')
    quantity = order.get('quantity', 1)

    if not username or username not in users:
        return False

    if product_type == 'gateway':
        gateway_card_type = order.get('gateway_card_type')
        if not gateway_card_type:
            return False

        cleanup_expired_gateway_cards()

        active_card = get_user_active_card(username)
        if active_card:
            return False

        if not check_gateway_stock(gateway_card_type):
            return False

        if not consume_gateway_stock(gateway_card_type):
            return False

        card_key = generate_gateway_key()
        expire_at = get_card_expire_time(gateway_card_type)
        price = order.get('product_price', 0)

        gateway_cards[username] = {
            'username': username,
            'type': gateway_card_type,
            'key': card_key,
            'price': price,
            'created_at': int(time.time() * 1000),
            'expire_at': expire_at,
            'used': False
        }
        save_gateway_cards()

        order['delivered'] = True
        order['delivered_code'] = card_key
        order['delivered_codes'] = [card_key]
        order['delivered_quantity'] = 1
        save_orders()
        return True

    product_type_map = {
        'reset': {'type': 'reset_code', 'generate': generate_reset_code, 'title': '重置密码卡密'},
        'point': {'type': 'point_code', 'generate': generate_point_code, 'title': '普通积分卡密'},
        'premium_point': {'type': 'premium_point_code', 'generate': generate_premium_point_code, 'title': '高级积分卡密'},
        'boost': {'type': 'boost_code', 'generate': generate_boost_code, 'title': '积分加成卡密'},
        'cancellation': {'type': 'cancellation_code', 'generate': generate_cancellation_code, 'title': '注销卡密'},
        'special_point': {'type': 'special_point_code', 'generate': generate_special_point_code, 'title': '特殊积分卡密'},
        'makeup': {'type': 'makeup_code', 'generate': generate_makeup_code, 'title': '补签卡'},
        'gamblers': {'type': 'gamblers_code', 'generate': generate_gamblers_code, 'title': '赌神积分卡密'},
        'box': {'type': 'box_code', 'generate': generate_box_code, 'title': '盲盒卡'},
        'plcard': {'type': 'plcard_code', 'generate': generate_plcard_code, 'title': '普通PL随机卡'},
        'premium_boost': {'type': 'premium_boost_code', 'generate': generate_premium_boost_code, 'title': '高级加成卡'}
    }

    if product_type not in product_type_map:
        return False

    product_info = product_type_map[product_type]

    if product_type == 'cancellation':
        if quantity > 1:
            return False
        if users[username].get('cancellationCodePurchased', False):
            return False
        users[username]['cancellationCodePurchased'] = True
        save_users()

    if product_type == 'makeup':
        user_data = users.get(username, {})
        makeup_used_count = user_data.get('makeup_code_used_count', 0)
        if makeup_used_count + quantity > 3:
            return False

    if product_type == 'gamblers':
        user_data = users.get(username, {})
        today = datetime.now().strftime('%Y-%m-%d')
        last_purchase_date = user_data.get('last_gamblers_purchase_date', '')
        purchase_count = user_data.get('gamblers_code_purchase_count', 0)
        if last_purchase_date != today:
            purchase_count = 0
            user_data['gamblers_code_purchase_count'] = 0
            user_data['last_gamblers_purchase_date'] = today
            save_users()
        if purchase_count + quantity > 3:
            return False
        user_data['gamblers_code_purchase_count'] = purchase_count + quantity
        user_data['last_gamblers_purchase_date'] = today
        save_users()

    if product_type == 'box':
        user_data = users.get(username, {})
        today = datetime.now().strftime('%Y-%m-%d')
        last_purchase_date = user_data.get('last_box_purchase_date', '')
        purchase_count = user_data.get('box_code_purchase_count', 0)
        if last_purchase_date != today:
            purchase_count = 0
            user_data['box_code_purchase_count'] = 0
            user_data['last_box_purchase_date'] = today
            save_users()
        if purchase_count + quantity > 5:
            return False
        user_data['box_code_purchase_count'] = purchase_count + quantity
        user_data['last_box_purchase_date'] = today
        save_users()

    if product_type == 'plcard':
        user_data = users.get(username, {})
        today = datetime.now().strftime('%Y-%m-%d')
        last_purchase_date = user_data.get('last_plcard_purchase_date', '')
        purchase_count = user_data.get('plcard_code_purchase_count', 0)
        if last_purchase_date != today:
            purchase_count = 0
            user_data['plcard_code_purchase_count'] = 0
            user_data['last_plcard_purchase_date'] = today
            save_users()
        if purchase_count + quantity > 10:
            return False
        user_data['plcard_code_purchase_count'] = purchase_count + quantity
        user_data['last_plcard_purchase_date'] = today
        save_users()

    generated_codes = []
    for _ in range(quantity):
        code = product_info['generate']()
        generated_codes.append(code)

    if quantity == 1:
        mail_attachment_id = f"mail_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        mail_attachments[mail_attachment_id] = {
            'id': mail_attachment_id,
            'username': username,
            'type': product_info['type'],
            'code': generated_codes[0],
            'codes': generated_codes,
            'used': False,
            'created_at': int(time.time() * 1000),
            'expires_at': int(time.time() * 1000) + 28800000,
            'title': f'商城购买-{product_info["title"]}',
            'description': f'商城购买获得{product_info["title"]}1张',
            'claimed': False,
            'claimed_at': 0,
            'source': 'mall_purchase',
            'quantity': 1,
            'is_batch': False
        }
        save_mail_attachments()
    else:
        codes_str = '\n'.join(generated_codes)
        mail_attachment_id = f"mail_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        mail_attachments[mail_attachment_id] = {
            'id': mail_attachment_id,
            'username': username,
            'type': product_info['type'],
            'codes': generated_codes,
            'code': generated_codes[0],
            'used': False,
            'created_at': int(time.time() * 1000),
            'expires_at': int(time.time() * 1000) + 28800000,
            'title': f'商城购买-{product_info["title"]} x{quantity}',
            'description': f'商城批量购买获得{product_info["title"]} {quantity}张\n\n卡密列表:\n{codes_str}',
            'claimed': False,
            'claimed_at': 0,
            'source': 'mall_purchase',
            'quantity': quantity,
            'is_batch': True
        }
        save_mail_attachments()

    order['delivered'] = True
    order['delivered_code'] = generated_codes[0] if len(generated_codes) == 1 else generated_codes
    order['delivered_codes'] = generated_codes
    order['delivered_quantity'] = len(generated_codes)
    order['mail_attachment_id'] = mail_attachment_id
    save_orders()
    return True

def deliver_order_to_user(order_id, target_username):
    order = orders.get(order_id)
    if not order or order.get('status') != 'paid':
        return False

    product_type = order.get('product_type')
    quantity = order.get('quantity', 1)

    if not target_username or target_username not in users:
        return False

    product_type_map = {
        'reset': {'type': 'reset_code', 'generate': generate_reset_code, 'title': '重置密码卡密'},
        'point': {'type': 'point_code', 'generate': generate_point_code, 'title': '普通积分卡密'},
        'premium_point': {'type': 'premium_point_code', 'generate': generate_premium_point_code, 'title': '高级积分卡密'},
        'boost': {'type': 'boost_code', 'generate': generate_boost_code, 'title': '积分加成卡密'},
        'cancellation': {'type': 'cancellation_code', 'generate': generate_cancellation_code, 'title': '注销卡密'},
        'special_point': {'type': 'special_point_code', 'generate': generate_special_point_code, 'title': '特殊积分卡密'},
        'makeup': {'type': 'makeup_code', 'generate': generate_makeup_code, 'title': '补签卡'},
        'gamblers': {'type': 'gamblers_code', 'generate': generate_gamblers_code, 'title': '赌神积分卡密'},
        'box': {'type': 'box_code', 'generate': generate_box_code, 'title': '盲盒卡'},
        'plcard': {'type': 'plcard_code', 'generate': generate_plcard_code, 'title': '普通PL随机卡'},
        'premium_boost': {'type': 'premium_boost_code', 'generate': generate_premium_boost_code, 'title': '高级加成卡'}
    }

    if product_type not in product_type_map:
        return False

    product_info = product_type_map[product_type]
    generated_codes = []

    for _ in range(quantity):
        code = product_info['generate']()
        generated_codes.append(code)

    if quantity == 1:
        mail_attachment_id = f"mail_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        mail_attachments[mail_attachment_id] = {
            'id': mail_attachment_id,
            'username': target_username,
            'type': product_info['type'],
            'code': generated_codes[0],
            'codes': generated_codes,
            'used': False,
            'created_at': int(time.time() * 1000),
            'expires_at': int(time.time() * 1000) + 28800000,
            'title': f'代付购买-{product_info["title"]}',
            'description': f'朋友代付购买获得{product_info["title"]}1张',
            'claimed': False,
            'claimed_at': 0,
            'source': 'daifu_purchase',
            'quantity': 1,
            'is_batch': False,
            'daifu_payer': order.get('payer', '未知')
        }
        save_mail_attachments()
    else:
        codes_str = '\n'.join(generated_codes)
        mail_attachment_id = f"mail_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        mail_attachments[mail_attachment_id] = {
            'id': mail_attachment_id,
            'username': target_username,
            'type': product_info['type'],
            'codes': generated_codes,
            'code': generated_codes[0],
            'used': False,
            'created_at': int(time.time() * 1000),
            'expires_at': int(time.time() * 1000) + 28800000,
            'title': f'代付购买-{product_info["title"]} x{quantity}',
            'description': f'朋友代付购买获得{product_info["title"]} {quantity}张\n\n卡密列表:\n{codes_str}',
            'claimed': False,
            'claimed_at': 0,
            'source': 'daifu_purchase',
            'quantity': quantity,
            'is_batch': True,
            'daifu_payer': order.get('payer', '未知')
        }
        save_mail_attachments()

    order['delivered'] = True
    order['delivered_code'] = generated_codes[0] if len(generated_codes) == 1 else generated_codes
    order['delivered_codes'] = generated_codes
    order['delivered_quantity'] = len(generated_codes)
    order['delivered_to'] = target_username
    order['mail_attachment_id'] = mail_attachment_id
    save_orders()
    return True

def has_pay_password(username):
    return username in user_pay_passwords and user_pay_passwords[username].get('password') is not None

def verify_pay_password(username, password):
    if username not in user_pay_passwords:
        return False
    stored_hash = user_pay_passwords[username].get('password')
    if not stored_hash:
        return False
    return bcrypt.check_password_hash(stored_hash, password)

def set_pay_password(username, new_password):
    if len(new_password) != 6 or not new_password.isdigit():
        return False
    if username not in user_pay_passwords:
        user_pay_passwords[username] = {}
    user_pay_passwords[username]['password'] = bcrypt.generate_password_hash(new_password).decode('utf-8')
    user_pay_passwords[username]['set_at'] = int(time.time() * 1000)
    save_user_pay_passwords()
    return True

def generate_anti_fake_code():
    return str(random.randint(100000, 999999))

@app.route('/api/order/create', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def create_order_api():
    data = request.get_json()
    username = session['user']['username']
    product_name = data.get('product_name', '')
    product_price = data.get('product_price', 0)
    payment_method = data.get('payment_method', 'points')
    product_id = data.get('product_id', '')
    product_type = data.get('product_type', '')

    if not product_name or product_price <= 0:
        return jsonify({'error': '商品信息不完整'}), 400

    if payment_method not in ['points', 'pl']:
        return jsonify({'error': '不支持的支付方式'}), 400

    if not check_user_code_limit(username)[0]:
        return jsonify({'error': '背包卡密已达上限(8/8)，请先使用或回收部分卡密'}), 400

    # Apply tiered pricing to the order
    final_price = get_final_price(product_price, username)

    order_id = create_order_with_price(
        username, 
        product_name, 
        final_price, 
        payment_method, 
        product_id, 
        product_type,
        points_price=final_price,
        original_price=product_price
    )

    return jsonify({
        'success': True,
        'order_id': order_id,
        'payment_method': payment_method,
        'redirect_url': f'/pay/{order_id}'
    })

@app.route('/api/order/<order_id>', methods=['GET'])
@login_required
def get_order_api(order_id):
    username = session['user']['username']
    cleanup_all_expired_data()
    order = get_order(order_id)

    if not order:
        return jsonify({'error': '订单不存在'}), 400

    is_daifu = order.get('is_daifu', False)

    if is_daifu:
        if order.get('daifu_status') == 'paid':
            if order.get('username') != username and order.get('owner') != username:
                return jsonify({'error': '此代付订单已被支付，无权查看'}), 403
    else:
        if order.get('username') != username:
            return jsonify({'error': '无权查看此订单'}), 403

    current_rate = get_current_pl_rate()
    is_pl = order.get('payment_method') == 'pl' or order.get('order_type') == 'pl_transfer'
    is_gateway = order.get('order_type') == 'gateway'

    user_data = users.get(username, {})
    main_points = user_data.get('totalPoints', 0)
    fund_balance = get_user_fund_balance(username)
    total_available_points = main_points + fund_balance
    effective_points = get_user_effective_points(username)
    current_multiplier = get_price_multiplier(username)

    next_update = (int(time.time()) // PL_FLUCTUATION_INTERVAL + 1) * PL_FLUCTUATION_INTERVAL
    next_update_in = max(0, next_update - int(time.time()))

    if is_pl:
        points_price = order.get('points_price', order.get('product_price', 0) * current_rate if current_rate > 0 else order.get('product_price', 0))
        order['points_price'] = points_price
        order['product_price_pl'] = order.get('product_price', 0)
        if order.get('original_price') and order.get('original_price') != order.get('product_price'):
            order['original_price_pl'] = round(order['original_price'] / current_rate, 4) if current_rate > 0 else order['original_price']
    else:
        order['product_price_points'] = order.get('product_price', 0)
        order['points_price'] = order.get('product_price', 0)

    if order.get('delivered_codes'):
        order['delivered_codes'] = order.get('delivered_codes')
    elif order.get('delivered_code'):
        order['delivered_codes'] = [order.get('delivered_code')]

    if is_gateway:
        order['is_gateway'] = True
        order['gateway_card_type'] = order.get('gateway_card_type', '')

    used_coupon_types = set()
    if order.get('used_coupon_ids'):
        for cid in order.get('used_coupon_ids', []):
            if cid in user_coupons:
                coupon = user_coupons[cid]
                coupon_type = coupon.get('type')
                if coupon_type:
                    used_coupon_types.add(coupon_type)

    def is_product_match(coupon_product_id, order_product_id, order_product_type):
        if not coupon_product_id:
            return False
        coupon_product_type = coupon_product_id.replace('_code', '') if '_code' in coupon_product_id else coupon_product_id
        order_product_type_from_id = order_product_id.replace('_code', '') if '_code' in order_product_id else order_product_id
        return (
            order_product_id == coupon_product_id or
            order_product_type == coupon_product_id or
            order_product_id == coupon_product_type or
            order_product_type == coupon_product_type or
            order_product_type_from_id == coupon_product_id or
            coupon_product_type == order_product_type or
            coupon_product_type == order_product_id
        )

    available_coupons = []
    for cid, coupon in user_coupons.items():
        if coupon.get('username') == username and not coupon.get('used', False) and coupon.get('expire_at', 0) > int(time.time() * 1000):
            coupon_type = coupon.get('type')
            if coupon_type in used_coupon_types:
                continue
            points_price_val = order.get('points_price', order.get('product_price', 0))
            if coupon_type == 'full_reduction':
                if points_price_val >= coupon.get('threshold', 0):
                    available_coupons.append({
                        'id': cid,
                        'type': coupon_type,
                        'discount': coupon.get('discount', 0),
                        'threshold': coupon.get('threshold', 0),
                        'expire_at': coupon.get('expire_at', 0),
                        'description': coupon.get('description', '')
                    })
            elif coupon_type == 'unconditional':
                available_coupons.append({
                    'id': cid,
                    'type': coupon_type,
                    'discount': coupon.get('discount', 0),
                    'threshold': 0,
                    'expire_at': coupon.get('expire_at', 0),
                    'description': coupon.get('description', '')
                })
            elif coupon_type == 'product_specific':
                coupon_product_id = coupon.get('product_id', '')
                order_product_id = order.get('product_id', '')
                order_product_type = order.get('product_type', '')
                if is_product_match(coupon_product_id, order_product_id, order_product_type):
                    available_coupons.append({
                        'id': cid,
                        'type': coupon_type,
                        'discount': coupon.get('discount', 0),
                        'threshold': 0,
                        'expire_at': coupon.get('expire_at', 0),
                        'description': coupon.get('description', ''),
                        'product_id': coupon_product_id
                    })
            elif coupon_type == 'pl_discount':
                if is_pl and order.get('product_price', 0) > coupon.get('discount', 0):
                    available_coupons.append({
                        'id': cid,
                        'type': coupon_type,
                        'discount': coupon.get('discount', 0),
                        'threshold': 0,
                        'expire_at': coupon.get('expire_at', 0),
                        'description': coupon.get('description', '')
                    })

    created_at = order.get('created_at', 0)
    is_expired = False
    if order.get('status') == 'pending' and int(time.time() * 1000) - created_at > 300000:
        is_expired = True

    return jsonify({
        'order': order,
        'has_pay_password': has_pay_password(username),
        'current_rate': current_rate,
        'available_coupons': available_coupons,
        'next_update_in': next_update_in,
        'is_expired': is_expired,
        'expires_in': max(0, 300000 - (int(time.time() * 1000) - created_at)) if order.get('status') == 'pending' else 0,
        'main_points': main_points,
        'fund_balance': fund_balance,
        'total_available_points': total_available_points,
        'effective_points': effective_points,
        'price_multiplier': current_multiplier
    })

@app.route('/api/price-info', methods=['GET'])
@login_required
def get_price_info_api():
    """
    Get price multiplier information for the current user.
    """
    username = session['user']['username']
    base_price = request.args.get('base_price', 0, type=float)
    
    effective_points = get_user_effective_points(username)
    multiplier = get_price_multiplier(username)
    
    result = {
        'effective_points': effective_points,
        'multiplier': multiplier,
        'tiers': [
            {'threshold': 50000, 'multiplier': 1.20},
            {'threshold': 100000, 'multiplier': 1.35},
            {'threshold': 200000, 'multiplier': 1.48},
            {'threshold': 300000, 'multiplier': 1.70},
            {'threshold': 500000, 'multiplier': 1.90}
        ]
    }
    
    if base_price > 0:
        result['base_price'] = base_price
        result['final_price'] = get_final_price(base_price, username)
        result['price_info'] = get_price_info(base_price, username)
    
    return jsonify(result)

@app.route('/api/coupons/list', methods=['GET'])
@login_required
def get_user_coupons():
    username = session['user']['username']
    cleanup_all_expired_data()

    coupon_list = []
    for cid, coupon in user_coupons.items():
        if coupon.get('username') == username and not coupon.get('used', False):
            type_label = get_coupon_type_label(coupon.get('type', 'full_reduction'))
            display_desc = coupon.get('description', '')
            if coupon.get('type') == 'product_specific' and coupon.get('product_id'):
                product_label = get_product_type_label(coupon.get('product_id', ''))
                display_desc = f'指定{product_label}减{coupon.get("discount", 0)}'
            elif coupon.get('type') == 'makeup_specific':
                product_label = get_product_type_label(coupon.get('product_id', ''))
                display_desc = f'指定{product_label}减{coupon.get("discount", 0)}'
            elif coupon.get('type') == 'pl_discount':
                display_desc = f'PL立减{coupon.get("discount", 0)}PL'
            elif coupon.get('type') == 'gamblers_specific':
                product_label = get_product_type_label(coupon.get('product_id', ''))
                display_desc = f'指定{product_label}减{coupon.get("discount", 0)}'
            coupon_list.append({
                'id': cid,
                'type': coupon.get('type', 'full_reduction'),
                'type_label': type_label,
                'discount': coupon.get('discount', 0),
                'threshold': coupon.get('threshold', 0),
                'product_id': coupon.get('product_id', ''),
                'used': coupon.get('used', False),
                'expire_at': coupon.get('expire_at', 0),
                'created_at': coupon.get('created_at', 0),
                'description': display_desc or coupon.get('description', '')
            })

    coupon_list.sort(key=lambda x: (x.get('used', False), x.get('expire_at', 0)))
    return jsonify({'coupons': coupon_list})

@app.route('/api/captcha/generate', methods=['POST'])
@csrf_protect
@limiter.limit(RATE_LIMITS['captcha_generate'])
@login_required
def generate_captcha():
    import random
    import uuid
    import io
    import os

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return jsonify({'error': 'PIL not installed'}), 500

    captcha_id = str(uuid.uuid4())
    username = session['user']['username']
    data = request.get_json() or {}
    order_id = data.get('order_id', '')

    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    code = ''.join(random.choice(chars) for _ in range(6))

    captcha_data = load_captcha_storage()
    captcha_data[captcha_id] = {
        'code': code,
        'created_at': int(time.time()),
        'username': username,
        'order_id': order_id
    }
    save_captcha_storage(captcha_data)

    width, height = 400, 160
    image = Image.new('RGB', (width, height), (11, 14, 26))
    draw = ImageDraw.Draw(image)

    colors = [(102, 126, 234), (124, 140, 255), (167, 139, 250), (74, 222, 128), (247, 201, 72), (248, 113, 113)]

    font_size = 30
    font = None
    font_paths = [
        '/data/data/com.termux/files/home/.local/share/fonts/NotoSansCJK-Bold.otf',
        '/data/data/com.termux/files/home/.local/share/fonts/DejaVuSans-Bold.ttf',
        '/data/data/com.termux/files/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/data/data/com.termux/files/usr/share/fonts/truetype/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',
        '/System/Library/Fonts/Helvetica.ttc',
        '/System/Library/Fonts/HelveticaNeue.ttc',
        'C:/Windows/Fonts/Arial.ttf',
        'C:/Windows/Fonts/arial.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf'
    ]

    for path in font_paths:
        try:
            font = ImageFont.truetype(path, font_size)
            break
        except:
            continue

    if font is None:
        try:
            import subprocess
            result = subprocess.run(['fc-list', ':style=Bold', '--format=%{file}\\n'], capture_output=True, text=True)
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line and ('.ttf' in line or '.ttc' in line):
                        try:
                            font = ImageFont.truetype(line.strip(), font_size)
                            break
                        except:
                            continue
        except:
            pass

    if font is None:
        try:
            font = ImageFont.truetype('/system/fonts/Roboto-Bold.ttf', font_size)
        except:
            pass

    if font is None:
        try:
            font = ImageFont.truetype('arial.ttf', font_size)
        except:
            pass

    if font is None:
        try:
            font = ImageFont.load_default()
            font_size = 30
        except:
            font = ImageFont.load_default()
            font_size = 30

    for i, char in enumerate(code):
        x = 50 + i * 58 + random.randint(-6, 6)
        y = 80 + random.randint(-14, 14)
        color = colors[i % len(colors)]
        try:
            draw.text((x, y), char, fill=color, font=font, anchor='mm')
        except:
            draw.text((x, y), char, fill=color)

    for _ in range(15):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(124, 140, 255, 60), width=2)

    for _ in range(80):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(124, 140, 255, random.randint(30, 70)))

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    response = make_response(img_byte_arr)
    response.headers['Content-Type'] = 'image/png'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Captcha-Id'] = captcha_id

    return response

@app.route('/api/order/<order_id>/pay', methods=['POST'])
@csrf_protect
@limiter.limit(RATE_LIMITS['pay'])
@login_required
@identity_required
def pay_order_api(order_id):
    username = session['user']['username']
    data = request.get_json()
    pay_password = data.get('pay_password', '')
    coupon_ids = data.get('coupon_ids', [])
    captcha_id = data.get('captcha_id', '')
    captcha_code = data.get('captcha_code', '').strip().upper()

    if not pay_password:
        return jsonify({'error': '请输入支付密码'}), 400

    if not captcha_id or not captcha_code:
        return jsonify({'error': '请完成图形验证码验证'}), 400

    captcha_data = load_captcha_storage()

    if captcha_id not in captcha_data:
        return jsonify({'error': '验证码已过期，请刷新重试'}), 400

    stored = captcha_data[captcha_id]

    if stored.get('username') != username:
        cleanup_captcha_by_id(captcha_id)
        cleanup_captcha_for_order(order_id)
        return jsonify({'error': '验证码不属于当前用户'}), 400

    if stored.get('order_id') and stored.get('order_id') != order_id:
        cleanup_captcha_by_id(captcha_id)
        cleanup_captcha_for_order(order_id)
        return jsonify({'error': '验证码与订单不匹配，请重新获取'}), 400

    if int(time.time()) - stored.get('created_at', 0) > 300:
        cleanup_captcha_by_id(captcha_id)
        cleanup_captcha_for_order(order_id)
        return jsonify({'error': '验证码已过期（超过5分钟），请刷新重试'}), 400

    if captcha_code != stored.get('code', ''):
        cleanup_captcha_by_id(captcha_id)
        cleanup_captcha_for_order(order_id)
        return jsonify({'error': '验证码错误，请重新输入'}), 400

    cleanup_captcha_by_id(captcha_id)
    cleanup_captcha_for_order(order_id)

    cleanup_all_expired_data()
    order = get_order(order_id)
    if not order:
        return jsonify({'error': '订单不存在'}), 400

    is_daifu = order.get('is_daifu', False)
    owner = order.get('owner', order.get('username'))

    if is_daifu:
        if username == owner:
            return jsonify({'error': '这是代付订单，请让朋友扫码支付，您不能自己支付'}), 400
        if order.get('daifu_status') == 'paid':
            return jsonify({'error': '此代付订单已被支付'}), 400
        order['payer'] = username
        order['payer_username'] = username
    else:
        if order.get('username') != username:
            return jsonify({'error': '无权支付此订单'}), 403

    if order.get('status') != 'pending':
        return jsonify({'error': '订单状态异常'}), 400

    if (int(time.time() * 1000) - order.get('created_at', 0)) > 300000:
        if order_id in orders:
            del orders[order_id]
            save_orders()
        return jsonify({'error': '订单已过期（超过5分钟），请重新下单'}), 400

    if not verify_pay_password(username, pay_password):
        return jsonify({'error': '支付密码错误'}), 400

    payment_method = order.get('payment_method')
    order_type = order.get('order_type', 'mall')
    current_rate = get_current_pl_rate()
    is_pl = payment_method == 'pl' or order_type == 'pl_transfer'

    points_price = order.get('points_price', order.get('product_price', 0))
    if is_pl:
        pl_price = order.get('product_price', 0)
    else:
        pl_price = points_price / current_rate if current_rate > 0 else points_price

    used_coupon_ids = []
    applied_discount_points = 0
    applied_discount_pl = 0

    def is_product_match(coupon_product_id, order_product_id, order_product_type):
        if not coupon_product_id:
            return False
        coupon_product_type = coupon_product_id.replace('_code', '') if '_code' in coupon_product_id else coupon_product_id
        order_product_type_from_id = order_product_id.replace('_code', '') if '_code' in order_product_id else order_product_id
        return (
            order_product_id == coupon_product_id or
            order_product_type == coupon_product_id or
            order_product_id == coupon_product_type or
            order_product_type == coupon_product_type or
            order_product_type_from_id == coupon_product_id or
            coupon_product_type == order_product_type or
            coupon_product_type == order_product_id
        )

    if coupon_ids:
        used_coupons = []
        for cid in coupon_ids:
            if cid in user_coupons and user_coupons[cid].get('username') == username and not user_coupons[cid].get('used', False):
                coupon = user_coupons[cid]
                if coupon.get('expire_at', 0) > int(time.time() * 1000):
                    coupon_type = coupon.get('type')
                    discount = coupon.get('discount', 0)
                    order_product_id = order.get('product_id', '')
                    order_product_type = order.get('product_type', '')

                    if coupon_type == 'pl_discount':
                        if is_pl and discount < pl_price:
                            used_coupons.append((cid, discount, 'pl'))
                            applied_discount_pl += discount
                    elif coupon_type == 'full_reduction':
                        if points_price >= coupon.get('threshold', 0):
                            used_coupons.append((cid, discount, 'points'))
                            applied_discount_points += discount
                    elif coupon_type == 'unconditional':
                        used_coupons.append((cid, discount, 'points'))
                        applied_discount_points += discount
                    elif coupon_type == 'product_specific':
                        coupon_product_id = coupon.get('product_id', '')
                        if is_product_match(coupon_product_id, order_product_id, order_product_type):
                            used_coupons.append((cid, discount, 'points'))
                            applied_discount_points += discount

        if used_coupons:
            for cid, discount, discount_type in used_coupons:
                user_coupons[cid]['used'] = True
                used_coupon_ids.append(cid)
            save_user_coupons()

            if 'original_price' not in order:
                order['original_price'] = pl_price if is_pl else points_price

            order['applied_coupon_discount_points'] = applied_discount_points
            order['applied_coupon_discount_pl'] = applied_discount_pl
            order['used_coupon_ids'] = used_coupon_ids

            if is_pl:
                points_discount_pl = applied_discount_points / current_rate if current_rate > 0 else 0
                total_discount_pl = applied_discount_pl + points_discount_pl
                final_pl_price = max(0, pl_price - total_discount_pl)
                order['product_price'] = final_pl_price
                order['final_price'] = final_pl_price
            else:
                pl_discount_points = applied_discount_pl * current_rate if current_rate > 0 else 0
                total_discount_points = applied_discount_points + pl_discount_points
                final_points_price = max(0, points_price - total_discount_points)
                order['product_price'] = final_points_price
                order['final_price'] = final_points_price

            save_orders()

    final_price = order.get('product_price', 0)

    if order_type == 'pl_transfer':
        target_username = order.get('transfer_target')
        original_transfer_amount = order.get('transfer_amount', final_price)

        current_pl = get_user_pl_balance(username)
        if current_pl < final_price:
            return jsonify({'error': f'PL余额不足，需要{final_price:.4f}PL，当前余额{current_pl:.4f}PL'}), 400

        update_user_pl_balance(username, -final_price, 'pl_transfer_out', f'to_{target_username}')
        update_user_pl_balance(target_username, original_transfer_amount, 'pl_transfer_in', f'from_{username}')

        discount_amount = round(original_transfer_amount - final_price, 4)
        transfer_id = f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        pl_transfers[transfer_id] = {
            'transfer_id': transfer_id,
            'from_username': username,
            'to_username': target_username,
            'amount': round(original_transfer_amount, 4),
            'actual_paid': round(final_price, 4),
            'coupon_discount': discount_amount,
            'rate': current_rate,
            'timestamp': int(time.time() * 1000),
            'status': 'completed'
        }
        save_pl_transfers()
        update_order_status(order_id, 'paid', int(time.time() * 1000))
        order['delivered'] = True
        order['delivered_code'] = f'转账至{target_username}成功 ({original_transfer_amount:.4f} PL，实际支付 {final_price:.4f} PL，优惠 {discount_amount:.4f} PL)'
        order['delivered_codes'] = [f'转账至{target_username}成功 ({original_transfer_amount:.4f} PL，实际支付 {final_price:.4f} PL，优惠 {discount_amount:.4f} PL)']
        order['delivered_quantity'] = 1
        save_orders()
        cleanup_captcha_for_order(order_id)
        return jsonify({
            'success': True,
            'message': f'转账成功！已转出 {original_transfer_amount:.4f} PL 给 {target_username}（实际支付 {final_price:.4f} PL，优惠 {discount_amount:.4f} PL）',
            'delivered': True,
            'delivered_code': f'{original_transfer_amount:.4f} PL -> {target_username}',
            'delivered_codes': [f'{original_transfer_amount:.4f} PL -> {target_username}'],
            'delivered_quantity': 1,
            'coupon_discount_points': applied_discount_points,
            'coupon_discount_pl': applied_discount_pl,
            'used_coupon_ids': used_coupon_ids,
            'final_price': final_price,
            'original_amount': original_transfer_amount,
            'discount_amount': discount_amount
        })

    if order_type == 'gateway':
        gateway_card_type = order.get('gateway_card_type')
        if not gateway_card_type:
            return jsonify({'error': '网关卡密类型无效'}), 400

        cleanup_expired_gateway_cards()

        active_card = get_user_active_card(username)
        if active_card:
            return jsonify({'error': '您已拥有有效的通行卡密，无需重复购买'}), 400

        if not check_gateway_stock(gateway_card_type):
            return jsonify({'error': f'{gateway_card_type}卡库存已用完，请明日再试'}), 400

        if payment_method == 'points':
            if username not in users:
                return jsonify({'error': '用户不存在'}), 400
            user_data = users[username]
            total_points = user_data.get('totalPoints', 0)
            fund_balance = get_user_fund_balance(username)
            total_available = total_points + fund_balance
            if total_available < final_price:
                return jsonify({'error': f'积分不足（含理财账户），需要{final_price:.2f}积分，当前总可用{total_available:.2f}积分'}), 400

            remaining_to_deduct = final_price
            deducted_from_fund = 0
            deducted_from_main = 0

            if total_points >= remaining_to_deduct:
                user_data['totalPoints'] = round(total_points - remaining_to_deduct, 2)
                deducted_from_main = remaining_to_deduct
                remaining_to_deduct = 0
            else:
                deducted_from_main = total_points
                remaining_to_deduct = remaining_to_deduct - total_points
                user_data['totalPoints'] = 0
                if fund_balance >= remaining_to_deduct:
                    fund_data[username]['balance'] = round(fund_balance - remaining_to_deduct, 2)
                    deducted_from_fund = remaining_to_deduct
                    remaining_to_deduct = 0
                else:
                    fund_data[username]['balance'] = 0
                    deducted_from_fund = fund_balance
                    remaining_to_deduct = remaining_to_deduct - fund_balance

            save_users()
            save_fund_data()

            system_fee = round(final_price * 0.2, 2)
            add_system_total_points(system_fee)

        elif payment_method == 'pl':
            current_pl = get_user_pl_balance(username)
            if current_pl < final_price:
                return jsonify({'error': f'PL余额不足，需要{final_price:.4f}PL，当前{current_pl:.4f}PL'}), 400
            update_user_pl_balance(username, -final_price, 'gateway_purchase', order_id)
        else:
            return jsonify({'error': '不支持的支付方式'}), 400

        update_order_status(order_id, 'paid', int(time.time() * 1000))

        if not consume_gateway_stock(gateway_card_type):
            return jsonify({'error': '库存已被抢完，请稍后重试'}), 400

        card_key = generate_gateway_key()
        expire_at = get_card_expire_time(gateway_card_type)
        price = order.get('product_price', 0)

        gateway_cards[username] = {
            'username': username,
            'type': gateway_card_type,
            'key': card_key,
            'price': price,
            'created_at': int(time.time() * 1000),
            'expire_at': expire_at,
            'used': False
        }
        save_gateway_cards()

        order['delivered'] = True
        order['delivered_code'] = card_key
        order['delivered_codes'] = [card_key]
        order['delivered_quantity'] = 1
        save_orders()
        cleanup_captcha_for_order(order_id)

        return jsonify({
            'success': True,
            'message': f'通行卡密购买成功！卡密: {card_key}（20%即{system_fee:.2f}积分已归入系统池）',
            'delivered': True,
            'delivered_code': card_key,
            'delivered_codes': [card_key],
            'delivered_quantity': 1,
            'coupon_discount_points': applied_discount_points,
            'coupon_discount_pl': applied_discount_pl,
            'used_coupon_ids': used_coupon_ids,
            'final_price': final_price,
            'card_key': card_key,
            'card_type': gateway_card_type,
            'expire_at': expire_at,
            'system_fee': system_fee
        })

    if payment_method == 'points':
        if username not in users:
            return jsonify({'error': '用户不存在'}), 400

        user_data = users[username]
        total_points = user_data.get('totalPoints', 0)
        fund_balance = get_user_fund_balance(username)
        total_available = total_points + fund_balance

        if total_available < final_price:
            return jsonify({'error': f'积分不足（含理财账户），需要{final_price:.2f}积分，当前总可用{total_available:.2f}积分（原账户{total_points:.2f}，理财账户{fund_balance:.2f}）'}), 400

        remaining_to_deduct = final_price
        deducted_from_fund = 0
        deducted_from_main = 0

        if total_points >= remaining_to_deduct:
            user_data['totalPoints'] = round(total_points - remaining_to_deduct, 2)
            deducted_from_main = remaining_to_deduct
            remaining_to_deduct = 0
        else:
            deducted_from_main = total_points
            remaining_to_deduct = remaining_to_deduct - total_points
            user_data['totalPoints'] = 0

            if fund_balance >= remaining_to_deduct:
                fund_data[username]['balance'] = round(fund_balance - remaining_to_deduct, 2)
                deducted_from_fund = remaining_to_deduct
                remaining_to_deduct = 0
            else:
                fund_data[username]['balance'] = 0
                deducted_from_fund = fund_balance
                remaining_to_deduct = remaining_to_deduct - fund_balance

        save_users()
        save_fund_data()

        system_fee = round(final_price * 0.2, 2)
        add_system_total_points(system_fee)

        update_order_status(order_id, 'paid', int(time.time() * 1000))

        fund_record_id = f"fund_pay_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        if deducted_from_fund > 0:
            fund_history[fund_record_id] = {
                'id': fund_record_id,
                'username': username,
                'type': 'withdraw',
                'amount': round(deducted_from_fund, 2),
                'timestamp': int(time.time() * 1000)
            }
            save_fund_history()

        if is_daifu:
            if deliver_order_to_user(order_id, owner):
                order['daifu_status'] = 'paid'
                save_orders()
                cleanup_captcha_for_order(order_id)
                return jsonify({
                    'success': True,
                    'message': f'代付成功！商品已发放给 {owner}（扣除原账户{deducted_from_main:.2f}积分，理财账户{deducted_from_fund:.2f}积分，20%即{system_fee:.2f}积分已归入系统池）',
                    'delivered': True,
                    'delivered_code': order.get('delivered_code'),
                    'delivered_codes': order.get('delivered_codes', []),
                    'delivered_quantity': order.get('delivered_quantity', 0),
                    'is_daifu': True,
                    'owner': owner,
                    'payer': username,
                    'coupon_discount_points': applied_discount_points,
                    'coupon_discount_pl': applied_discount_pl,
                    'used_coupon_ids': used_coupon_ids,
                    'final_price': final_price,
                    'deducted_from_main': round(deducted_from_main, 2),
                    'deducted_from_fund': round(deducted_from_fund, 2),
                    'system_fee': system_fee
                })
            else:
                user_data['totalPoints'] = round(user_data['totalPoints'] + deducted_from_main, 2)
                if deducted_from_fund > 0:
                    fund_data[username]['balance'] = round(fund_data[username]['balance'] + deducted_from_fund, 2)
                save_users()
                save_fund_data()
                deduct_system_total_points(system_fee)
                return jsonify({'error': '代付发货失败，已退款'}), 500
        else:
            if deliver_order(order_id):
                order = get_order(order_id)
                save_orders()
                cleanup_captcha_for_order(order_id)
                return jsonify({
                    'success': True,
                    'message': f'支付成功，卡密已发送至邮箱（扣除原账户{deducted_from_main:.2f}积分，理财账户{deducted_from_fund:.2f}积分，20%即{system_fee:.2f}积分已归入系统池）',
                    'delivered': True,
                    'delivered_code': order.get('delivered_code'),
                    'delivered_codes': order.get('delivered_codes', []),
                    'delivered_quantity': order.get('delivered_quantity', 0),
                    'coupon_discount_points': applied_discount_points,
                    'coupon_discount_pl': applied_discount_pl,
                    'used_coupon_ids': used_coupon_ids,
                    'final_price': final_price,
                    'deducted_from_main': round(deducted_from_main, 2),
                    'deducted_from_fund': round(deducted_from_fund, 2),
                    'system_fee': system_fee
                })
            else:
                user_data['totalPoints'] = round(user_data['totalPoints'] + deducted_from_main, 2)
                if deducted_from_fund > 0:
                    fund_data[username]['balance'] = round(fund_data[username]['balance'] + deducted_from_fund, 2)
                save_users()
                save_fund_data()
                deduct_system_total_points(system_fee)
                return jsonify({'error': '发货失败，请稍后重试'}), 500

    elif payment_method == 'pl':
        current_pl = get_user_pl_balance(username)
        if current_pl < final_price:
            return jsonify({'error': f'PL余额不足，需要{final_price:.4f}PL，当前{current_pl:.4f}PL'}), 400
        update_user_pl_balance(username, -final_price, 'mall_purchase', order_id)
        update_order_status(order_id, 'paid', int(time.time() * 1000))

        if is_daifu:
            if deliver_order_to_user(order_id, owner):
                order['daifu_status'] = 'paid'
                save_orders()
                cleanup_captcha_for_order(order_id)
                return jsonify({
                    'success': True,
                    'message': f'代付成功！商品已发放给 {owner} (实付{final_price:.4f}PL)',
                    'delivered': True,
                    'delivered_code': order.get('delivered_code'),
                    'delivered_codes': order.get('delivered_codes', []),
                    'delivered_quantity': order.get('delivered_quantity', 0),
                    'is_daifu': True,
                    'owner': owner,
                    'payer': username,
                    'coupon_discount_points': applied_discount_points,
                    'coupon_discount_pl': applied_discount_pl,
                    'used_coupon_ids': used_coupon_ids,
                    'final_price': final_price,
                    'rate_used': current_rate
                })
            else:
                update_user_pl_balance(username, final_price, 'mall_purchase_refund', order_id)
                return jsonify({'error': '代付发货失败，已退款'}), 500
        else:
            if deliver_order(order_id):
                order = get_order(order_id)
                save_orders()
                cleanup_captcha_for_order(order_id)
                return jsonify({
                    'success': True,
                    'message': f'支付成功，卡密已发送至邮箱，请前往邮箱领取 (实付{final_price:.4f}PL)',
                    'delivered': True,
                    'delivered_code': order.get('delivered_code'),
                    'delivered_codes': order.get('delivered_codes', []),
                    'delivered_quantity': order.get('delivered_quantity', 0),
                    'coupon_discount_points': applied_discount_points,
                    'coupon_discount_pl': applied_discount_pl,
                    'used_coupon_ids': used_coupon_ids,
                    'final_price': final_price,
                    'rate_used': current_rate
                })
            else:
                update_user_pl_balance(username, final_price, 'mall_purchase_refund', order_id)
                return jsonify({'error': '发货失败，请稍后重试'}), 500

    return jsonify({'error': '不支持的支付方式'}), 400

@app.route('/api/order/<order_id>/status', methods=['GET'])
@login_required
def get_order_status_api(order_id):
    username = session['user']['username']
    order = get_order(order_id)

    if not order:
        return jsonify({'error': '订单不存在'}), 400

    if order.get('username') != username:
        return jsonify({'error': '无权查看此订单'}), 403

    current_time = int(time.time() * 1000)
    created_at = order.get('created_at', 0)
    is_expired = order.get('status') == 'pending' and (current_time - created_at) > 14400000

    return jsonify({
        'order_id': order_id,
        'status': order.get('status', 'pending'),
        'is_expired': is_expired,
        'expires_in': max(0, 14400000 - (current_time - created_at)) if order.get('status') == 'pending' else 0,
        'created_at': created_at
    })

@app.route('/api/captcha/delete', methods=['POST'])
@csrf_protect
@login_required
def delete_captcha():
    data = request.get_json()
    captcha_id = data.get('captcha_id', '')
    username = session['user']['username']

    if not captcha_id:
        return jsonify({'success': False, 'error': '缺少验证码ID'}), 400

    captcha_data = load_captcha_storage()

    if captcha_id in captcha_data:
        stored = captcha_data[captcha_id]
        if stored.get('username') == username:
            order_id = stored.get('order_id', '')
            del captcha_data[captcha_id]
            save_captcha_storage(captcha_data)
            if order_id:
                cleanup_captcha_for_order(order_id)

    return jsonify({'success': True})

@app.route('/api/order/<order_id>/cancel', methods=['POST'])
@csrf_protect
@login_required
def cancel_order_api(order_id):
    username = session['user']['username']
    order = get_order(order_id)

    if not order:
        return jsonify({'error': '订单不存在'}), 400

    if order.get('username') != username:
        return jsonify({'error': '无权操作此订单'}), 403

    if order.get('status') != 'pending':
        return jsonify({'error': '订单状态异常，无法取消'}), 400

    cleanup_captcha_for_order(order_id)

    if order_id in orders:
        del orders[order_id]
        save_orders()

    return jsonify({'success': True, 'message': '订单已取消'})

@app.route('/api/order/<order_id>/set-password', methods=['POST'])
@csrf_protect
@login_required
def set_pay_password_api(order_id):
    username = session['user']['username']
    data = request.get_json()
    new_password = data.get('pay_password', '')
    qq_number = data.get('qq_number', '').strip()

    if len(new_password) != 6 or not new_password.isdigit():
        return jsonify({'error': '支付密码必须为6位数字'}), 400

    if has_pay_password(username):
        return jsonify({'error': '您已设置过支付密码，请使用已有密码'}), 400

    user_data = users.get(username, {})
    bound_qq = user_data.get('qq_number', '')

    if not bound_qq:
        return jsonify({'error': '您尚未绑定QQ号，请先在玩家中心绑定QQ号后再设置支付密码'}), 400

    if qq_number != bound_qq:
        return jsonify({'error': 'QQ号验证失败，请输入绑定的QQ号'}), 400

    order = get_order(order_id)
    if not order or order.get('username') != username:
        return jsonify({'error': '订单无效'}), 400

    if set_pay_password(username, new_password):
        return jsonify({
            'success': True,
            'message': '支付密码设置成功'
        })
    return jsonify({'error': '设置失败，请重试'}), 500

@app.route('/api/check-pay-password', methods=['GET'])
@login_required
def check_pay_password_api():
    username = session['user']['username']
    return jsonify({
        'has_pay_password': has_pay_password(username)
    })

@app.route('/api/debug/clear-pay-password', methods=['POST'])
@csrf_protect
@login_required
def debug_clear_pay_password():
    username = session['user']['username']
    data = request.get_json()
    qq_number = data.get('qq_number', '').strip()
    password = data.get('password', '')

    user_data = users.get(username, {})
    bound_qq = user_data.get('qq_number', '')

    if not bound_qq:
        return jsonify({'success': False, 'message': '您尚未绑定QQ号'}), 400

    if qq_number != bound_qq:
        return jsonify({'success': False, 'message': 'QQ号验证失败，请输入绑定的QQ号'}), 400

    if not bcrypt.check_password_hash(user_data['password'], password):
        return jsonify({'success': False, 'message': '登录密码错误'}), 400

    current_points = user_data.get('totalPoints', 0)

    if current_points < 15:
        return jsonify({'success': False, 'message': '积分不足，清除支付密码需要15积分'}), 400

    if username not in user_pay_passwords:
        return jsonify({'success': False, 'message': '用户没有支付密码记录'}), 400

    del user_pay_passwords[username]
    save_user_pay_passwords()

    user_data['totalPoints'] = round(current_points - 15, 2)
    save_users()

    add_system_total_points(15)

    return jsonify({
        'success': True,
        'message': '已清除用户 ' + username + ' 的支付密码，消耗15积分（已归入系统总积分）'
    })

@app.route('/api/buy-reset-code', methods=['POST'])
@csrf_protect
@mall_access_required
@identity_required
def buy_reset_code():
    start_time = time.time()
    username = session['user']['username']
    user_data = users.get(username, {})

    original_price = 8
    final_price = get_discounted_price(original_price, username)

    use_pl = request.get_json().get('use_pl', False)
    payment_method = 'pl' if use_pl else 'points'

    can_add, msg = check_user_code_limit(username)
    if not can_add:
        return jsonify({'error': msg}), 400

    order_id = create_order(username, '重置密码卡密', final_price, payment_method, 'reset_code', 'reset')

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'order_id': order_id,
        'payment_method': payment_method,
        'redirect_url': f'/pay/{order_id}',
        'originalPrice': original_price,
        'finalPrice': final_price,
        'savedPoints': original_price - final_price if is_new_user(username) else 0,
        'responseTime': response_time
    })

@app.route('/api/buy-point-code', methods=['POST'])
@csrf_protect
@mall_access_required
@identity_required
def buy_point_code():
    start_time = time.time()
    username = session['user']['username']
    user_data = users.get(username, {})

    original_price = 1.2
    final_price = get_discounted_price(original_price, username)

    use_pl = request.get_json().get('use_pl', False)
    payment_method = 'pl' if use_pl else 'points'

    can_add, msg = check_user_code_limit(username)
    if not can_add:
        return jsonify({'error': msg}), 400

    order_id = create_order(username, '普通积分卡密', final_price, payment_method, 'point_code', 'point')

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'order_id': order_id,
        'payment_method': payment_method,
        'redirect_url': f'/pay/{order_id}',
        'originalPrice': original_price,
        'finalPrice': final_price,
        'savedPoints': original_price - final_price if is_new_user(username) else 0,
        'responseTime': response_time
    })

@app.route('/api/buy-premium-point-code', methods=['POST'])
@csrf_protect
@mall_access_required
@identity_required
def buy_premium_point_code():
    start_time = time.time()
    username = session['user']['username']
    user_data = users.get(username, {})

    original_price = 3.5
    final_price = get_discounted_price(original_price, username)

    use_pl = request.get_json().get('use_pl', False)
    payment_method = 'pl' if use_pl else 'points'

    can_add, msg = check_user_code_limit(username)
    if not can_add:
        return jsonify({'error': msg}), 400

    order_id = create_order(username, '高级积分卡密', final_price, payment_method, 'premium_point_code', 'premium_point')

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'order_id': order_id,
        'payment_method': payment_method,
        'redirect_url': f'/pay/{order_id}',
        'originalPrice': original_price,
        'finalPrice': final_price,
        'savedPoints': original_price - final_price if is_new_user(username) else 0,
        'responseTime': response_time
    })

@app.route('/api/buy-boost-code', methods=['POST'])
@csrf_protect
@mall_access_required
@identity_required
def buy_boost_code():
    start_time = time.time()
    username = session['user']['username']
    user_data = users.get(username, {})

    original_price = 8.8
    final_price = get_discounted_price(original_price, username)

    use_pl = request.get_json().get('use_pl', False)
    payment_method = 'pl' if use_pl else 'points'

    can_add, msg = check_user_code_limit(username)
    if not can_add:
        return jsonify({'error': msg}), 400

    order_id = create_order(username, '积分加成卡', final_price, payment_method, 'boost_code', 'boost')

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'order_id': order_id,
        'payment_method': payment_method,
        'redirect_url': f'/pay/{order_id}',
        'originalPrice': original_price,
        'finalPrice': final_price,
        'savedPoints': original_price - final_price if is_new_user(username) else 0,
        'responseTime': response_time
    })

@app.route('/api/buy-cancellation-code', methods=['POST'])
@csrf_protect
@mall_access_required
@identity_required
def buy_cancellation_code():
    start_time = time.time()
    username = session['user']['username']
    user_data = users.get(username, {})

    if user_data.get('cancellationCodePurchased', False):
        return jsonify({'error': '每个账号仅限购买一次注销卡密'}), 400

    consecutive_days = user_data.get('attendanceConsecutiveDays', 0)
    if consecutive_days < 4:
        return jsonify({'error': f'需要连续签到4天才可购买注销卡密，当前连续签到{consecutive_days}天'}), 400

    original_price = 9.9
    final_price = get_discounted_price(original_price, username)

    use_pl = request.get_json().get('use_pl', False)
    payment_method = 'pl' if use_pl else 'points'

    can_add, msg = check_user_code_limit(username)
    if not can_add:
        return jsonify({'error': msg}), 400

    order_id = create_order(username, '注销账号卡密', final_price, payment_method, 'cancellation_code', 'cancellation')

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'order_id': order_id,
        'payment_method': payment_method,
        'redirect_url': f'/pay/{order_id}',
        'originalPrice': original_price,
        'finalPrice': final_price,
        'savedPoints': original_price - final_price if is_new_user(username) else 0,
        'responseTime': response_time
    })

@app.route('/api/buy-special-point-code', methods=['POST'])
@csrf_protect
@mall_access_required
@identity_required
def buy_special_point_code():
    start_time = time.time()
    username = session['user']['username']
    user_data = users.get(username, {})

    original_price = 20
    final_price = get_discounted_price(original_price, username)

    use_pl = request.get_json().get('use_pl', False)
    payment_method = 'pl' if use_pl else 'points'

    can_add, msg = check_user_code_limit(username)
    if not can_add:
        return jsonify({'error': msg}), 400

    order_id = create_order(username, '特殊积分卡密', final_price, payment_method, 'special_point_code', 'special_point')

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'order_id': order_id,
        'payment_method': payment_method,
        'redirect_url': f'/pay/{order_id}',
        'originalPrice': original_price,
        'finalPrice': final_price,
        'savedPoints': original_price - final_price if is_new_user(username) else 0,
        'responseTime': response_time
    })

@app.route('/api/buy-makeup-code', methods=['POST'])
@csrf_protect
@mall_access_required
@identity_required
def buy_makeup_code():
    start_time = time.time()
    username = session['user']['username']
    user_data = users.get(username, {})

    makeup_used_count = user_data.get('makeup_code_used_count', 0)
    if makeup_used_count >= 3:
        return jsonify({'error': '补签卡永久限购3次，您已使用完所有次数'}), 400

    original_price = 200
    final_price = get_discounted_price(original_price, username)

    use_pl = request.get_json().get('use_pl', False)
    payment_method = 'pl' if use_pl else 'points'

    can_add, msg = check_user_code_limit(username)
    if not can_add:
        return jsonify({'error': msg}), 400

    order_id = create_order(username, '补签卡', final_price, payment_method, 'makeup_code', 'makeup')

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'order_id': order_id,
        'payment_method': payment_method,
        'redirect_url': f'/pay/{order_id}',
        'originalPrice': original_price,
        'finalPrice': final_price,
        'savedPoints': original_price - final_price if is_new_user(username) else 0,
        'responseTime': response_time
    })

@app.route('/api/buy-gamblers-code', methods=['POST'])
@csrf_protect
@mall_access_required
@identity_required
def buy_gamblers_code():
    start_time = time.time()
    username = session['user']['username']
    user_data = users.get(username, {})

    today = datetime.now().strftime('%Y-%m-%d')
    last_purchase_date = user_data.get('last_gamblers_purchase_date', '')
    purchase_count = user_data.get('gamblers_code_purchase_count', 0)

    if last_purchase_date != today:
        purchase_count = 0
        user_data['gamblers_code_purchase_count'] = 0
        user_data['last_gamblers_purchase_date'] = today
        save_users()

    if purchase_count >= 3:
        return jsonify({'error': f'赌神卡单日限购3次，今日已购买{purchase_count}次'}), 400

    original_price = 100
    final_price = get_discounted_price(original_price, username)

    use_pl = request.get_json().get('use_pl', False)
    payment_method = 'pl' if use_pl else 'points'

    can_add, msg = check_user_code_limit(username)
    if not can_add:
        return jsonify({'error': msg}), 400

    order_id = create_order(username, '赌神积分卡', final_price, payment_method, 'gamblers_code', 'gamblers')

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'order_id': order_id,
        'payment_method': payment_method,
        'redirect_url': f'/pay/{order_id}',
        'originalPrice': original_price,
        'finalPrice': final_price,
        'savedPoints': original_price - final_price if is_new_user(username) else 0,
        'responseTime': response_time
    })

@app.route('/api/buy-box-code', methods=['POST'])
@csrf_protect
@mall_access_required
@identity_required
def buy_box_code():
    start_time = time.time()
    username = session['user']['username']
    user_data = users.get(username, {})

    today = datetime.now().strftime('%Y-%m-%d')
    last_purchase_date = user_data.get('last_box_purchase_date', '')
    purchase_count = user_data.get('box_code_purchase_count', 0)

    if last_purchase_date != today:
        purchase_count = 0
        user_data['box_code_purchase_count'] = 0
        user_data['last_box_purchase_date'] = today
        save_users()

    if purchase_count >= 5:
        return jsonify({'error': f'盲盒卡单日限购5次，今日已购买{purchase_count}次'}), 400

    original_price = 28.8
    final_price = get_discounted_price(original_price, username)

    use_pl = request.get_json().get('use_pl', False)
    payment_method = 'pl' if use_pl else 'points'

    can_add, msg = check_user_code_limit(username)
    if not can_add:
        return jsonify({'error': msg}), 400

    order_id = create_order(username, '盲盒卡', final_price, payment_method, 'box_code', 'box')

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'order_id': order_id,
        'payment_method': payment_method,
        'redirect_url': f'/pay/{order_id}',
        'originalPrice': original_price,
        'finalPrice': final_price,
        'savedPoints': original_price - final_price if is_new_user(username) else 0,
        'responseTime': response_time
    })

@app.route('/api/buy-plcard-code', methods=['POST'])
@csrf_protect
@mall_access_required
@identity_required
def buy_plcard_code():
    start_time = time.time()
    username = session['user']['username']
    user_data = users.get(username, {})

    today = datetime.now().strftime('%Y-%m-%d')
    last_purchase_date = user_data.get('last_plcard_purchase_date', '')
    purchase_count = user_data.get('plcard_code_purchase_count', 0)

    if last_purchase_date != today:
        purchase_count = 0
        user_data['plcard_code_purchase_count'] = 0
        user_data['last_plcard_purchase_date'] = today
        save_users()

    if purchase_count >= 10:
        return jsonify({'error': f'普通PL随机卡单日限购10次，今日已购买{purchase_count}次'}), 400

    original_price = 35.8
    final_price = get_discounted_price(original_price, username)

    use_pl = request.get_json().get('use_pl', False)
    payment_method = 'pl' if use_pl else 'points'

    can_add, msg = check_user_code_limit(username)
    if not can_add:
        return jsonify({'error': msg}), 400

    order_id = create_order(username, '普通PL随机卡', final_price, payment_method, 'plcard_code', 'plcard')

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'order_id': order_id,
        'payment_method': payment_method,
        'redirect_url': f'/pay/{order_id}',
        'originalPrice': original_price,
        'finalPrice': final_price,
        'savedPoints': original_price - final_price if is_new_user(username) else 0,
        'responseTime': response_time
    })

@app.route('/api/buy-premium-boost-code', methods=['POST'])
@csrf_protect
@mall_access_required
@identity_required
def buy_premium_boost_code():
    start_time = time.time()
    username = session['user']['username']
    user_data = users.get(username, {})

    original_price = 15.6
    final_price = get_discounted_price(original_price, username)

    use_pl = request.get_json().get('use_pl', False)
    payment_method = 'pl' if use_pl else 'points'

    can_add, msg = check_user_code_limit(username)
    if not can_add:
        return jsonify({'error': msg}), 400

    order_id = create_order(username, '高级加成卡', final_price, payment_method, 'premium_boost_code', 'premium_boost')

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'order_id': order_id,
        'payment_method': payment_method,
        'redirect_url': f'/pay/{order_id}',
        'originalPrice': original_price,
        'finalPrice': final_price,
        'savedPoints': original_price - final_price if is_new_user(username) else 0,
        'responseTime': response_time
    })

@app.route('/api/use-gamblers-code', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def use_gamblers_code():
    start_time = time.time()
    username = session['user']['username']

    data = request.get_json()
    gamblers_code = data.get('gamblersCode', '').strip().upper()

    if not gamblers_code:
        return jsonify({'error': '请输入赌神积分卡密'}), 400

    cleanup_all_expired_data()

    code_data = gamblers_codes.get(gamblers_code)
    if not code_data:
        return jsonify({'error': '卡密无效'}), 400

    if code_data.get('used'):
        return jsonify({'error': '卡密已被使用'}), 400

    if code_data.get('recycled'):
        return jsonify({'error': '卡密已被回收'}), 400

    if code_data.get('username') != username:
        return jsonify({'error': '卡密不属于当前用户'}), 400

    current_time = int(time.time() * 1000)
    if (current_time - code_data.get('createdAt', 0)) > 86400000:
        del gamblers_codes[gamblers_code]
        save_gamblers_codes()
        return jsonify({'error': '卡密已过期（24小时有效）'}), 400

    points_earned = round(random.uniform(10, 102), 2)

    points_added = update_earned_points(username, points_earned, True)

    if not points_added:
        return jsonify({'error': '今日获取积分已达上限14分'}), 400

    del gamblers_codes[gamblers_code]
    save_gamblers_codes()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'pointsEarned': points_earned,
        'responseTime': response_time
    })

@app.route('/api/use-box-code', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def use_box_code():
    start_time = time.time()
    username = session['user']['username']

    data = request.get_json()
    box_code = data.get('boxCode', '').strip().upper()

    if not box_code:
        return jsonify({'error': '请输入盲盒卡密'}), 400

    cleanup_all_expired_data()

    code_data = box_codes.get(box_code)
    if not code_data:
        return jsonify({'error': '盲盒卡密无效'}), 400

    if code_data.get('used'):
        return jsonify({'error': '盲盒卡密已被使用'}), 400

    if code_data.get('recycled'):
        return jsonify({'error': '盲盒卡密已被回收'}), 400

    if code_data.get('username') != username:
        return jsonify({'error': '盲盒卡密不属于当前用户'}), 400

    current_time = int(time.time() * 1000)
    if (current_time - code_data.get('createdAt', 0)) > 172800000:
        del box_codes[box_code]
        save_box_codes()
        return jsonify({'error': '盲盒卡密已过期（48小时有效）'}), 400

    possible_types = ['point_code', 'premium_point_code', 'reset_code', 'boost_code', 'special_point_code', 'gamblers_code']
    chosen_type = random.choice(possible_types)
    type_map = {
        'point_code': ('point_code', generate_point_code, '普通积分卡密', point_codes, save_point_codes),
        'premium_point_code': ('premium_point_code', generate_premium_point_code, '高级积分卡密', premium_point_codes, save_premium_point_codes),
        'reset_code': ('reset_code', generate_reset_code, '重置密码卡密', reset_codes, save_reset_codes),
        'boost_code': ('boost_code', generate_boost_code, '积分加成卡密', boost_codes, save_boost_codes),
        'special_point_code': ('special_point_code', generate_special_point_code, '特殊积分卡密', special_point_codes, save_special_point_codes),
        'gamblers_code': ('gamblers_code', generate_gamblers_code, '赌神积分卡密', gamblers_codes, save_gamblers_codes)
    }

    type_info = type_map[chosen_type]
    generated_code = type_info[1]()
    title = type_info[2]

    mail_attachment_id = f"mail_{int(time.time()*1000)}_{random.randint(1000,9999)}"
    mail_attachments[mail_attachment_id] = {
        'id': mail_attachment_id,
        'username': username,
        'type': type_info[0],
        'code': generated_code,
        'codes': [generated_code],
        'used': False,
        'created_at': int(time.time() * 1000),
        'expires_at': int(time.time() * 1000) + 28800000,
        'title': f'盲盒开箱-{title}',
        'description': f'盲盒开箱获得{title}1张',
        'claimed': False,
        'claimed_at': 0,
        'source': 'box_reward',
        'quantity': 1,
        'is_batch': False
    }
    save_mail_attachments()

    del box_codes[box_code]
    save_box_codes()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'message': f'盲盒开启成功！获得{title}，已发送至邮箱',
        'reward_type': chosen_type,
        'responseTime': response_time
    })

@app.route('/api/use-plcard-code', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def use_plcard_code():
    start_time = time.time()
    username = session['user']['username']

    data = request.get_json()
    plcard_code = data.get('plcardCode', '').strip().upper()

    if not plcard_code:
        return jsonify({'error': '请输入普通PL随机卡密'}), 400

    cleanup_all_expired_data()

    code_data = plcard_codes.get(plcard_code)
    if not code_data:
        return jsonify({'error': '普通PL随机卡密无效'}), 400

    if code_data.get('used'):
        return jsonify({'error': '卡密已被使用'}), 400

    if code_data.get('recycled'):
        return jsonify({'error': '卡密已被回收'}), 400

    if code_data.get('username') != username:
        return jsonify({'error': '卡密不属于当前用户'}), 400

    current_time = int(time.time() * 1000)
    if (current_time - code_data.get('createdAt', 0)) > 86400000:
        del plcard_codes[plcard_code]
        save_plcard_codes()
        return jsonify({'error': '卡密已过期（24小时有效）'}), 400

    pl_amount = round(random.uniform(1, 10), 4)

    update_user_pl_balance(username, pl_amount, 'plcard_reward', plcard_code)

    del plcard_codes[plcard_code]
    save_plcard_codes()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'plEarned': pl_amount,
        'message': f'使用成功！获得{pl_amount}PL',
        'responseTime': response_time
    })

@app.route('/api/use-premium-boost-code', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def use_premium_boost_code():
    start_time = time.time()
    username = session['user']['username']

    data = request.get_json()
    premium_boost_code = data.get('premiumBoostCode', '').strip().upper()

    if not premium_boost_code:
        return jsonify({'error': '请输入高级加成卡密'}), 400

    cleanup_all_expired_data()

    code_data = premium_boost_codes.get(premium_boost_code)
    if not code_data:
        return jsonify({'error': '高级加成卡密无效'}), 400

    if code_data.get('used'):
        return jsonify({'error': '卡密已被使用'}), 400

    if code_data.get('recycled'):
        return jsonify({'error': '卡密已被回收'}), 400

    if code_data.get('username') != username:
        return jsonify({'error': '卡密不属于当前用户'}), 400

    current_time = int(time.time() * 1000)
    if (current_time - code_data.get('createdAt', 0)) > 172800000:
        del premium_boost_codes[premium_boost_code]
        save_premium_boost_codes()
        return jsonify({'error': '卡密已过期（48小时有效）'}), 400

    current_time_sec = int(time.time())
    existing_boost = user_boosts.get(username)
    if existing_boost and existing_boost.get('expiresAt', 0) > current_time_sec:
        return jsonify({'error': '已有激活的加成效果，请等待效果结束后再使用'}), 400

    expires_at = current_time_sec + 300
    user_boosts[username] = {
        'username': username,
        'activatedAt': current_time_sec,
        'expiresAt': expires_at,
        'boostCode': premium_boost_code,
        'boost_type': 'premium'
    }
    save_user_boosts()

    code_data['used'] = True
    save_premium_boost_codes()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'message': '高级加成卡激活成功，5分钟内享受90%积分加成',
        'expiresIn': 300,
        'responseTime': response_time
    })

@app.route('/api/account/cancel', methods=['POST'])
@csrf_protect
@limiter.limit('3 per minute')
@login_required
def cancel_account():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    
    email = data.get('email', '').strip().lower()
    verification_code = data.get('verification_code', '').strip()
    promise_agreed = data.get('promise_agreed', False)
    
    if not email or not verification_code:
        return jsonify({'error': '请填写邮箱和验证码'}), 400
    
    if not promise_agreed:
        return jsonify({'error': '请阅读并同意注销承诺书'}), 400
    
    user_data = users.get(username)
    if not user_data:
        return jsonify({'error': '用户不存在'}), 400
    
    if user_data.get('email') != email:
        return jsonify({'error': '邮箱与账号不匹配'}), 400
    
    success, message = email_service.verify_code(email, verification_code)
    if not success:
        return jsonify({'error': message}), 400
    
    delete_user_completely(username)
    
    session.clear()
    response = make_response(jsonify({'success': True, 'message': '账号已成功注销'}))
    response.set_cookie('session', '', expires=0, path='/')
    response.set_cookie('session_expiration', '', expires=0, path='/')
    
    response_time = int((time.time() - start_time) * 1000)
    response_data = jsonify({
        'success': True,
        'message': '账号已成功注销',
        'responseTime': response_time
    })
    return response_data

@app.route('/api/use-cancellation-code', methods=['POST'])
@csrf_protect
@login_required
def use_cancellation_code():
    start_time = time.time()
    data = request.get_json()
    username = session['user']['username']
    user_data = users.get(username, {})

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    cancellation_code = data.get('cancellationCode', '').strip().upper()
    promise_agreed = data.get('promiseAgreed', False)

    if not email or not password or not cancellation_code:
        return jsonify({'error': '请填写完整信息'}), 400

    if not promise_agreed:
        return jsonify({'error': '请阅读并同意注销承诺书'}), 400

    if user_data.get('email') != email:
        return jsonify({'error': '邮箱与账号不匹配'}), 400

    if not bcrypt.check_password_hash(user_data['password'], password):
        return jsonify({'error': '密码错误'}), 400

    if username != user_data.get('username'):
        return jsonify({'error': '当前登录用户与要注销的用户不一致'}), 400

    cleanup_all_expired_data()

    code_data = cancellation_codes.get(cancellation_code)
    if not code_data:
        return jsonify({'error': '注销卡密无效'}), 400

    if code_data.get('used'):
        return jsonify({'error': '注销卡密已被使用'}), 400

    if code_data.get('recycled'):
        return jsonify({'error': '注销卡密已被回收'}), 400

    if code_data.get('username') != username:
        return jsonify({'error': '注销卡密不属于当前用户'}), 400

    code_data['used'] = True
    save_cancellation_codes()

    delete_user_completely(username)

    session.clear()
    response = make_response(jsonify({'success': True, 'message': '账号已成功注销'}))
    response.set_cookie('session', '', expires=0, path='/')
    response.set_cookie('session_expiration', '', expires=0, path='/')

    response_time = int((time.time() - start_time) * 1000)
    response_data = jsonify({
        'success': True,
        'message': '账号已成功注销',
        'responseTime': response_time
    })
    return response_data

@app.route('/api/use-boost-code', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def use_boost_code():
    start_time = time.time()
    data = request.get_json()
    username = session['user']['username']
    boost_code = data.get('boostCode', '').strip().upper()

    if not boost_code:
        return jsonify({'error': '请输入加成卡密'}), 400

    cleanup_all_expired_data()

    code_data = boost_codes.get(boost_code)
    if not code_data:
        return jsonify({'error': '卡密无效'}), 400

    if code_data.get('used'):
        return jsonify({'error': '卡密已被使用'}), 400

    if code_data.get('recycled'):
        return jsonify({'error': '卡密已被回收'}), 400

    if code_data.get('username') != username:
        return jsonify({'error': '卡密不属于当前用户'}), 400

    current_time = int(time.time() * 1000)
    if (current_time - code_data.get('createdAt', 0)) > 259200000:
        del boost_codes[boost_code]
        save_boost_codes()
        return jsonify({'error': '卡密已过期（72小时有效）'}), 400

    current_time_sec = int(time.time())
    existing_boost = user_boosts.get(username)
    if existing_boost and existing_boost.get('expiresAt', 0) > current_time_sec:
        return jsonify({'error': '已有激活的加成效果，请等待效果结束后再使用'}), 400

    expires_at = current_time_sec + 300
    user_boosts[username] = {
        'username': username,
        'activatedAt': current_time_sec,
        'expiresAt': expires_at,
        'boostCode': boost_code,
        'boost_type': 'normal'
    }
    save_user_boosts()

    code_data['used'] = True
    save_boost_codes()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'message': '积分加成卡激活成功，5分钟内享受50%积分加成',
        'expiresIn': 300,
        'responseTime': response_time
    })

@app.route('/api/use-makeup-code', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def use_makeup_code():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    makeup_code = data.get('makeupCode', '').strip().upper()

    if not makeup_code:
        return jsonify({'error': '请输入补签卡密'}), 400

    cleanup_all_expired_data()

    code_data = makeup_codes.get(makeup_code)
    if not code_data:
        return jsonify({'error': '补签卡密无效'}), 400

    if code_data.get('used'):
        return jsonify({'error': '补签卡密已被使用'}), 400

    if code_data.get('recycled'):
        return jsonify({'error': '补签卡密已被回收'}), 400

    if code_data.get('username') != username:
        return jsonify({'error': '补签卡密不属于当前用户'}), 400

    current_time = int(time.time() * 1000)
    if (current_time - code_data.get('createdAt', 0)) > 3600000:
        del makeup_codes[makeup_code]
        save_makeup_codes()
        return jsonify({'error': '补签卡已过期（1小时有效）'}), 400

    user_data = users.get(username, {})
    makeup_used_count = user_data.get('makeup_code_used_count', 0)
    if makeup_used_count >= 3:
        return jsonify({'error': '补签卡永久限购3次，您已使用完所有次数'}), 400

    attendance_total_days = user_data.get('attendanceTotalDays', 0)
    attendance_consecutive_days = user_data.get('attendanceConsecutiveDays', 0)
    last_attendance_timestamp = user_data.get('lastAttendanceTimestamp', 0)

    if attendance_consecutive_days >= attendance_total_days:
        return jsonify({'error': '您的连续签到天数已等于或大于累计签到天数，无需补签'}), 400

    if attendance_total_days <= 0:
        return jsonify({'error': '您还没有任何签到记录，无法补签'}), 400

    if attendance_consecutive_days > 0:
        days_to_add = attendance_total_days - attendance_consecutive_days
    else:
        days_to_add = 0

    if days_to_add <= 0:
        return jsonify({'error': '您的连续签到天数已等于或大于累计签到天数，无需补签'}), 400

    days_to_add = min(days_to_add, 30)

    user_data['attendanceConsecutiveDays'] = attendance_consecutive_days + days_to_add
    if user_data['attendanceConsecutiveDays'] > attendance_total_days:
        user_data['attendanceConsecutiveDays'] = attendance_total_days

    user_data['makeup_code_used_count'] = makeup_used_count + 1
    code_data['used'] = True
    save_makeup_codes()
    save_users()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'message': f'补签成功！连续签到天数从{attendance_consecutive_days}天提升至{user_data["attendanceConsecutiveDays"]}天',
        'oldConsecutiveDays': attendance_consecutive_days,
        'newConsecutiveDays': user_data['attendanceConsecutiveDays'],
        'responseTime': response_time
    })

@app.route('/api/recycle-code', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def recycle_code():
    start_time = time.time()
    username = session['user']['username']

    data = request.get_json()
    code = data.get('code', '').strip().upper()
    code_type = data.get('type', '')

    if not code or code_type not in ['point', 'reset', 'premium_point', 'boost', 'special_point', 'plcard']:
        return jsonify({'error': '无效的请求参数'}), 400

    cleanup_all_expired_data()

    code_data = None
    if code_type == 'point':
        code_data = point_codes.get(code)
    elif code_type == 'premium_point':
        code_data = premium_point_codes.get(code)
    elif code_type == 'boost':
        code_data = boost_codes.get(code)
    elif code_type == 'special_point':
        code_data = special_point_codes.get(code)
    elif code_type == 'plcard':
        code_data = plcard_codes.get(code)
    else:
        code_data = reset_codes.get(code)

    if not code_data:
        return jsonify({'error': '卡密不存在'}), 400

    if code_data.get('username') != username:
        return jsonify({'error': '卡密不属于当前用户'}), 400

    if code_data.get('used'):
        return jsonify({'error': '卡密已被使用，无法回收'}), 400

    if code_data.get('recycled'):
        return jsonify({'error': '卡密已被回收'}), 400

    if code_data.get('adminGranted', False):
        return jsonify({'error': '管理员赠送的卡密不可回收'}), 400

    current_time = int(time.time() * 1000)
    if code_type == 'point' and (current_time - code_data.get('createdAt', 0)) > 172800000:
        return jsonify({'error': '卡密已过期，无法回收'}), 400
    if code_type == 'premium_point' and (current_time - code_data.get('createdAt', 0)) > 172800000:
        return jsonify({'error': '卡密已过期，无法回收'}), 400
    if code_type == 'special_point' and (current_time - code_data.get('createdAt', 0)) > 172800000:
        return jsonify({'error': '卡密已过期，无法回收'}), 400
    if code_type == 'boost' and (current_time - code_data.get('createdAt', 0)) > 259200000:
        return jsonify({'error': '卡密已过期，无法回收'}), 400
    if code_type == 'reset' and (current_time - code_data.get('createdAt', 0)) > 86400000:
        return jsonify({'error': '卡密已过期，无法回收'}), 400
    if code_type == 'plcard' and (current_time - code_data.get('createdAt', 0)) > 86400000:
        return jsonify({'error': '卡密已过期，无法回收'}), 400

    if code_type == 'boost':
        original_price = 8.8
    elif code_type == 'premium_point':
        original_price = 3.5
    elif code_type == 'point':
        original_price = 1.2
    elif code_type == 'special_point':
        original_price = 20
    elif code_type == 'plcard':
        original_price = 35.8
    else:
        original_price = 8

    recycle_price = round(original_price * 0.1, 2)

    user_data = users.get(username, {})
    if 'totalPoints' not in user_data:
        user_data['totalPoints'] = 0
    user_data['totalPoints'] = round(user_data['totalPoints'] + recycle_price, 2)
    save_users()

    code_data['recycled'] = True

    if code_type == 'point':
        save_point_codes()
    elif code_type == 'premium_point':
        save_premium_point_codes()
    elif code_type == 'boost':
        save_boost_codes()
    elif code_type == 'special_point':
        save_special_point_codes()
    elif code_type == 'plcard':
        save_plcard_codes()
    else:
        save_reset_codes()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'recyclePrice': recycle_price,
        'message': f'成功回收，获得{recycle_price}积分',
        'responseTime': response_time
    })

@app.route('/api/use-point-code', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def use_point_code():
    start_time = time.time()
    username = session['user']['username']

    data = request.get_json()
    point_code = data.get('pointCode', '').strip().upper()

    if not point_code:
        return jsonify({'error': '请输入积分卡密'}), 400

    cleanup_all_expired_data()

    code_data = point_codes.get(point_code)
    is_premium = False
    is_special = False

    if not code_data:
        code_data = premium_point_codes.get(point_code)
        if code_data:
            is_premium = True

    if not code_data:
        code_data = special_point_codes.get(point_code)
        if code_data:
            is_special = True

    if not code_data:
        return jsonify({'error': '卡密无效'}), 400

    if code_data.get('used'):
        return jsonify({'error': '卡密已被使用'}), 400

    if code_data.get('recycled'):
        return jsonify({'error': '卡密已被回收'}), 400

    if code_data.get('username') != username:
        return jsonify({'error': '卡密不属于当前用户'}), 400

    current_time = int(time.time() * 1000)
    if (current_time - code_data.get('createdAt', 0)) > 172800000:
        if is_premium:
            del premium_point_codes[point_code]
            save_premium_point_codes()
        elif is_special:
            del special_point_codes[point_code]
            save_special_point_codes()
        else:
            del point_codes[point_code]
            save_point_codes()
        return jsonify({'error': '卡密已过期（48小时有效）'}), 400

    if is_special:
        points_earned = round(random.uniform(18, 23), 2)
    elif is_premium:
        points_earned = round(random.uniform(2.5, 4.0), 2)
    else:
        points_earned = round(random.uniform(0.6, 2.0), 2)

    points_added = update_earned_points(username, points_earned, True)

    if not points_added:
        return jsonify({'error': '今日获取积分已达上限14分'}), 400

    if is_special:
        del special_point_codes[point_code]
        save_special_point_codes()
    elif is_premium:
        del premium_point_codes[point_code]
        save_premium_point_codes()
    else:
        del point_codes[point_code]
        save_point_codes()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'pointsEarned': points_earned,
        'isPremium': is_premium,
        'isSpecial': is_special,
        'responseTime': response_time
    })

@app.route('/api/get-inventory', methods=['GET'])
@csrf_protect
@login_required
@identity_required
def get_inventory():
    start_time = time.time()
    username = session['user']['username']

    cleanup_all_expired_data()

    user_point_codes = []
    user_premium_codes = []
    user_reset_codes = []
    user_boost_codes = []
    user_cancellation_codes = []
    user_special_codes = []
    user_makeup_codes = []
    user_gamblers_codes = []
    user_box_codes = []
    user_plcard_codes = []
    user_premium_boost_codes = []
    current_time = int(time.time() * 1000)

    for code, data in point_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            expires_in = 48 - (current_time - data.get('createdAt', 0)) / 3600000
            if expires_in > 0:
                user_point_codes.append({
                    'code': code,
                    'expiresIn': round(expires_in, 1),
                    'type': 'point',
                    'adminGranted': data.get('adminGranted', False),
                    'recyclable': not data.get('adminGranted', False)
                })

    for code, data in premium_point_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            expires_in = 48 - (current_time - data.get('createdAt', 0)) / 3600000
            if expires_in > 0:
                user_premium_codes.append({
                    'code': code,
                    'expiresIn': round(expires_in, 1),
                    'type': 'premium_point',
                    'adminGranted': data.get('adminGranted', False),
                    'recyclable': not data.get('adminGranted', False)
                })

    for code, data in reset_codes.items():
        if data.get('username') == username and data.get('type') == 'reset' and not data.get('used', False) and not data.get('recycled', False):
            expires_in = 24 - (current_time - data.get('createdAt', 0)) / 3600000
            if expires_in > 0:
                user_reset_codes.append({
                    'code': code,
                    'expiresIn': round(expires_in, 1),
                    'type': 'reset',
                    'adminGranted': data.get('adminGranted', False),
                    'recyclable': not data.get('adminGranted', False)
                })

    for code, data in boost_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            expires_in = 72 - (current_time - data.get('createdAt', 0)) / 3600000
            if expires_in > 0:
                user_boost_codes.append({
                    'code': code,
                    'expiresIn': round(expires_in, 1),
                    'type': 'boost',
                    'adminGranted': data.get('adminGranted', False),
                    'recyclable': not data.get('adminGranted', False)
                })

    for code, data in cancellation_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            user_cancellation_codes.append({
                'code': code,
                'type': 'cancellation',
                'adminGranted': data.get('adminGranted', False),
                'recyclable': False
            })

    for code, data in special_point_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            expires_in = 48 - (current_time - data.get('createdAt', 0)) / 3600000
            if expires_in > 0:
                user_special_codes.append({
                    'code': code,
                    'expiresIn': round(expires_in, 1),
                    'type': 'special_point',
                    'adminGranted': data.get('adminGranted', False),
                    'recyclable': not data.get('adminGranted', False)
                })

    for code, data in makeup_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            expires_in = 1 - (current_time - data.get('createdAt', 0)) / 3600000
            if expires_in > 0:
                user_makeup_codes.append({
                    'code': code,
                    'expiresIn': round(expires_in, 1),
                    'type': 'makeup',
                    'adminGranted': data.get('adminGranted', False),
                    'recyclable': False
                })

    for code, data in gamblers_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            expires_in = 24 - (current_time - data.get('createdAt', 0)) / 3600000
            if expires_in > 0:
                user_gamblers_codes.append({
                    'code': code,
                    'expiresIn': round(expires_in, 1),
                    'type': 'gamblers',
                    'adminGranted': data.get('adminGranted', False),
                    'recyclable': False
                })

    for code, data in box_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            expires_in = 48 - (current_time - data.get('createdAt', 0)) / 3600000
            if expires_in > 0:
                user_box_codes.append({
                    'code': code,
                    'expiresIn': round(expires_in, 1),
                    'type': 'box',
                    'adminGranted': data.get('adminGranted', False),
                    'recyclable': False
                })

    for code, data in plcard_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            expires_in = 24 - (current_time - data.get('createdAt', 0)) / 3600000
            if expires_in > 0:
                user_plcard_codes.append({
                    'code': code,
                    'expiresIn': round(expires_in, 1),
                    'type': 'plcard',
                    'adminGranted': data.get('adminGranted', False),
                    'recyclable': not data.get('adminGranted', False)
                })

    for code, data in premium_boost_codes.items():
        if data.get('username') == username and not data.get('used', False) and not data.get('recycled', False):
            expires_in = 48 - (current_time - data.get('createdAt', 0)) / 3600000
            if expires_in > 0:
                user_premium_boost_codes.append({
                    'code': code,
                    'expiresIn': round(expires_in, 1),
                    'type': 'premium_boost',
                    'adminGranted': data.get('adminGranted', False),
                    'recyclable': not data.get('adminGranted', False)
                })

    user_data = users.get(username, {})
    cancellation_purchased = user_data.get('cancellationCodePurchased', False)
    consecutive_days = user_data.get('attendanceConsecutiveDays', 0)
    cancellation_available = consecutive_days >= 4
    makeup_used_count = user_data.get('makeup_code_used_count', 0)

    created_at_str = user_data.get('createdAt', '')
    is_within_24h = False
    if created_at_str:
        try:
            created_at = datetime.fromisoformat(created_at_str)
            is_within_24h = (datetime.now() - created_at) <= timedelta(hours=24)
        except:
            pass
    can_force_cancel = check_identity_verified(username) and is_within_24h

    today = datetime.now().strftime('%Y-%m-%d')
    last_gamblers_purchase = user_data.get('last_gamblers_purchase_date', '')
    gamblers_purchase_count = user_data.get('gamblers_code_purchase_count', 0)
    if last_gamblers_purchase != today:
        gamblers_purchase_count = 0
        user_data['gamblers_code_purchase_count'] = 0
        user_data['last_gamblers_purchase_date'] = today
        save_users()

    last_box_purchase = user_data.get('last_box_purchase_date', '')
    box_purchase_count = user_data.get('box_code_purchase_count', 0)
    if last_box_purchase != today:
        box_purchase_count = 0
        user_data['box_code_purchase_count'] = 0
        user_data['last_box_purchase_date'] = today
        save_users()

    last_plcard_purchase = user_data.get('last_plcard_purchase_date', '')
    plcard_purchase_count = user_data.get('plcard_code_purchase_count', 0)
    if last_plcard_purchase != today:
        plcard_purchase_count = 0
        user_data['plcard_code_purchase_count'] = 0
        user_data['last_plcard_purchase_date'] = today
        save_users()

    mail_count = sum(1 for a in mail_attachments.values() if a.get('username') == username and not a.get('claimed', False))

    fund_balance = get_user_fund_balance(username)
    total_points_with_fund = user_data.get('totalPoints', 0) + fund_balance
    effective_points = get_user_effective_points(username)
    price_multiplier = get_price_multiplier(username)

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'pointCodes': user_point_codes,
        'premiumPointCodes': user_premium_codes,
        'resetCodes': user_reset_codes,
        'boostCodes': user_boost_codes,
        'cancellationCodes': user_cancellation_codes,
        'specialPointCodes': user_special_codes,
        'makeupCodes': user_makeup_codes,
        'gamblersCodes': user_gamblers_codes,
        'boxCodes': user_box_codes,
        'plcardCodes': user_plcard_codes,
        'premiumBoostCodes': user_premium_boost_codes,
        'isNewUser': is_new_user(username),
        'bonusPeriod': is_bonus_period(),
        'cancellationPurchased': cancellation_purchased,
        'cancellationAvailable': cancellation_available,
        'consecutiveDays': consecutive_days,
        'canForceCancel': can_force_cancel,
        'makeupUsedCount': makeup_used_count,
        'makeupMaxCount': 3,
        'gamblersPurchaseCount': gamblers_purchase_count,
        'gamblersMaxCount': 3,
        'boxPurchaseCount': box_purchase_count,
        'boxMaxCount': 5,
        'plcardPurchaseCount': plcard_purchase_count,
        'plcardMaxCount': 10,
        'mailCount': mail_count,
        'fundBalance': fund_balance,
        'totalPointsWithFund': total_points_with_fund,
        'effectivePoints': effective_points,
        'priceMultiplier': price_multiplier,
        'responseTime': response_time
    })

@app.route('/api/reset-password', methods=['POST'])
@csrf_protect
@limiter.limit(RATE_LIMITS['reset_password'])
def reset_password():
    start_time = time.time()
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    username = data.get('username', '').strip()
    new_password = data.get('newPassword', '')
    reset_code = data.get('resetCode', '').strip().upper()

    if not email or not username or not new_password or not reset_code:
        return jsonify({'error': '请填写完整信息'}), 400

    if username not in users:
        return jsonify({'error': '用户名不存在'}), 400

    user_data = users[username]
    if user_data.get('email') != email:
        return jsonify({'error': '邮箱与用户名不匹配'}), 400

    if not validate_password(new_password):
        return jsonify({'error': '密码至少8位，需包含至少两种类型（大小写字母/数字/特殊字符）'}), 400

    cleanup_all_expired_data()

    code_data = reset_codes.get(reset_code)
    if not code_data:
        return jsonify({'error': '卡密无效'}), 400

    if code_data.get('used'):
        return jsonify({'error': '卡密已被使用'}), 400

    if code_data.get('recycled'):
        return jsonify({'error': '卡密已被回收'}), 400

    if code_data.get('username') != username:
        return jsonify({'error': '卡密与用户名不匹配'}), 400

    if code_data.get('email') != email:
        return jsonify({'error': '卡密与邮箱不匹配'}), 400

    current_time = int(time.time() * 1000)
    if (current_time - code_data.get('createdAt', 0)) > 86400000:
        del reset_codes[reset_code]
        save_reset_codes()
        return jsonify({'error': '卡密已过期（24小时有效）'}), 400

    hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    users[username]['password'] = hashed_password
    save_users()

    del reset_codes[reset_code]
    save_reset_codes()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'message': '密码重置成功',
        'responseTime': response_time
    })

@app.route('/api/forgot-password/send-code', methods=['POST'])
@csrf_protect
@limiter.limit('3 per minute')
def forgot_password_send_code():
    start_time = time.time()
    data = request.get_json()
    
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    
    if not username or not email:
        return jsonify({'error': '请填写用户名和邮箱'}), 400
    
    if username not in users:
        return jsonify({'error': '用户名不存在'}), 400
    
    user_data = users[username]
    if user_data.get('email') != email:
        return jsonify({'error': '邮箱与用户名不匹配'}), 400
    
    if not validate_email(email):
        return jsonify({'error': '邮箱格式不正确'}), 400
    
    success, code, message = email_service.send_verification_code_with_limit(email, username, '重置密码')
    
    if success:
        response_time = int((time.time() - start_time) * 1000)
        return jsonify({
            'success': True,
            'message': '验证码已发送至您的邮箱，请查收',
            'expires_in': email_service.CODE_EXPIRE_SECONDS,
            'responseTime': response_time
        })
    else:
        return jsonify({'error': message}), 500


@app.route('/api/forgot-password', methods=['POST'])
@csrf_protect
@limiter.limit(RATE_LIMITS['reset_password'])
def forgot_password():
    start_time = time.time()
    data = request.get_json()
    
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    new_password = data.get('newPassword', '')
    verification_code = data.get('verificationCode', '').strip()
    
    if not username or not email or not new_password or not verification_code:
        return jsonify({'error': '请填写完整信息'}), 400
    
    if username not in users:
        return jsonify({'error': '用户名不存在'}), 400
    
    user_data = users[username]
    if user_data.get('email') != email:
        return jsonify({'error': '邮箱与用户名不匹配'}), 400
    
    if not validate_password(new_password):
        return jsonify({'error': '密码至少8位，需包含至少两种类型（大小写字母/数字/特殊字符）'}), 400
    
    reset_limits = load_reset_limits()
    today = time.strftime('%Y-%m-%d')
    if username not in reset_limits:
        reset_limits[username] = {'date': today, 'count': 0}
    if reset_limits[username]['date'] != today:
        reset_limits[username] = {'date': today, 'count': 0}
    if reset_limits[username]['count'] >= 2:
        return jsonify({'error': '今日重置密码次数已达上限（2次），请明日再试'}), 400
    
    success, message = email_service.verify_code(email, verification_code)
    if not success:
        return jsonify({'error': message}), 400
    
    total_points = user_data.get('totalPoints', 0)
    fund_balance = get_user_fund_balance(username)
    total_available = total_points + fund_balance
    
    if total_available < 8.8:
        return jsonify({'error': '重置密码需要8.8积分（含理财账户），当前可用积分不足'}), 400
    
    remaining_to_deduct = 8.8
    deducted_from_fund = 0
    deducted_from_main = 0
    
    if total_points >= remaining_to_deduct:
        user_data['totalPoints'] = round(total_points - remaining_to_deduct, 2)
        deducted_from_main = remaining_to_deduct
        remaining_to_deduct = 0
    else:
        deducted_from_main = total_points
        remaining_to_deduct = remaining_to_deduct - total_points
        user_data['totalPoints'] = 0
        if fund_balance >= remaining_to_deduct:
            fund_data[username]['balance'] = round(fund_balance - remaining_to_deduct, 2)
            deducted_from_fund = remaining_to_deduct
            remaining_to_deduct = 0
        else:
            fund_data[username]['balance'] = 0
            deducted_from_fund = fund_balance
            remaining_to_deduct = remaining_to_deduct - fund_balance
    
    save_users()
    save_fund_data()
    
    reset_limits[username]['count'] += 1
    save_reset_limits(reset_limits)
    
    hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    users[username]['password'] = hashed_password
    save_users()
    
    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'message': f'密码重置成功，已扣除8.8积分（原账户{deducted_from_main:.2f}，理财账户{deducted_from_fund:.2f}）',
        'responseTime': response_time
    })

@app.route('/api/get-boost-status', methods=['GET'])
@login_required
def get_boost_status():
    start_time = time.time()
    username = session['user']['username']
    current_time_sec = int(time.time())
    boost_data = user_boosts.get(username)
    boost_active = False
    boost_expires_in = 0
    boost_type = 'normal'
    if boost_data:
        expires_at = boost_data.get('expiresAt', 0)
        if expires_at > current_time_sec:
            boost_active = True
            boost_expires_in = expires_at - current_time_sec
            boost_type = boost_data.get('boost_type', 'normal')
        else:
            del user_boosts[username]
            save_user_boosts()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'boostActive': boost_active,
        'boostExpiresIn': boost_expires_in,
        'boostType': boost_type,
        'responseTime': response_time
    })

@app.route('/api/claim-daily-bonus', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def claim_daily_bonus():
    start_time = time.time()
    username = session['user']['username']
    user_data = users.get(username, {})

    daily_bonus_code = user_data.get('dailyBonusCode')
    if not daily_bonus_code:
        return jsonify({'error': '暂无待领取的每日奖励'}), 400

    for aid, attachment in mail_attachments.items():
        if attachment.get('username') == username and attachment.get('code') == daily_bonus_code and not attachment.get('claimed', False):
            if do_claim_mail_attachment(aid, username):
                user_data['dailyBonusAwarded'] = True
                user_data['dailyBonusCode'] = None
                save_users()
                response_time = int((time.time() - start_time) * 1000)
                return jsonify({
                    'success': True,
                    'bonusCode': daily_bonus_code,
                    'message': '每日奖励已领取到您的背包',
                    'responseTime': response_time
                })

    return jsonify({'error': '奖励卡密已失效'}), 400

@app.route('/api/pl/rate', methods=['GET'])
def get_pl_rate():
    rate = get_current_pl_rate()
    current_time = int(time.time())
    current_period = get_current_period()
    next_period_start = (current_period + 1) * PL_FLUCTUATION_INTERVAL
    next_update_in = max(0, next_period_start - current_time)

    last_update = pl_rate_data.get('last_update', 0)
    is_refreshing = False
    if current_time - last_update < 3:
        is_refreshing = True

    return jsonify({
        'rate': rate,
        'min_rate': PL_MIN_RATE,
        'max_rate': PL_MAX_RATE,
        'next_update': next_period_start,
        'next_update_in': next_update_in,
        'last_update': last_update,
        'is_refreshing': is_refreshing,
        'server_time': current_time
    })

@app.route('/api/pl/balance', methods=['GET'])
@login_required
def get_pl_balance():
    username = session['user']['username']
    balance = get_user_pl_balance(username)
    user_pl_data = user_pl_balances.get(username, {})
    return jsonify({
        'balance': balance,
        'total_earned': user_pl_data.get('total_earned', 0),
        'total_spent': user_pl_data.get('total_spent', 0)
    })

@app.route('/api/pl/exchange/points-to-pl', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def exchange_points_to_pl_api():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    points_amount = data.get('points', 0)
    if points_amount <= 0:
        return jsonify({'error': '请输入有效的积分数量'}), 400
    result, error = exchange_points_to_pl(username, points_amount)
    if error:
        return jsonify({'error': error}), 400
    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'data': result,
        'responseTime': response_time
    })

@app.route('/api/pl/exchange/pl-to-points', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def exchange_pl_to_points_api():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    pl_amount = data.get('pl', 0)
    if pl_amount <= 0:
        return jsonify({'error': '请输入有效的PL数量'}), 400
    result, error = exchange_pl_to_points(username, pl_amount)
    if error:
        return jsonify({'error': error}), 400
    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'data': result,
        'responseTime': response_time
    })

@app.route('/api/pl/transfer', methods=['POST'])
@csrf_protect
@limiter.limit(RATE_LIMITS['transfer_pl'])
@login_required
@identity_required
def transfer_pl_api():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    target_username = data.get('target_username', '').strip()
    amount = float(data.get('amount', 0))
    password = data.get('password', '')

    if not target_username:
        return jsonify({'error': '请输入对方用户名'}), 400

    if amount <= 0:
        return jsonify({'error': '请输入有效的转账金额'}), 400

    if amount < 0.1:
        return jsonify({'error': '转账金额不能低于0.1PL'}), 400

    if not password:
        return jsonify({'error': '请输入账号密码'}), 400

    if not has_pay_password(username):
        return jsonify({'error': '请先设置支付密码'}), 400

    result, error = transfer_pl(username, target_username, amount, password)
    if error:
        return jsonify({'error': error}), 400

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'data': result,
        'responseTime': response_time
    })

@app.route('/api/pl/transfer/confirm', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def confirm_transfer_pl_api():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    target_username = data.get('target_username', '').strip()
    amount = float(data.get('amount', 0))
    pay_password = data.get('pay_password', '')

    if not target_username or not amount or not pay_password:
        return jsonify({'error': '请填写完整信息'}), 400

    if not verify_pay_password(username, pay_password):
        return jsonify({'error': '支付密码错误'}), 400

    current_balance = get_user_pl_balance(username)
    if current_balance < amount:
        return jsonify({'error': f'PL余额不足，需要{amount}PL'}), 400

    result, error = transfer_pl(username, target_username, amount, users[username].get('password', ''))
    if error:
        return jsonify({'error': error}), 400

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'data': result,
        'responseTime': response_time
    })

@app.route('/api/pl/transfer/create-order', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def create_transfer_order():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    target_username = data.get('target_username', '').strip()
    amount = float(data.get('amount', 0))

    if not target_username:
        return jsonify({'error': '请输入对方用户名'}), 400

    if target_username not in users:
        return jsonify({'error': '对方用户不存在'}), 400

    if target_username == username:
        return jsonify({'error': '不能转账给自己'}), 400

    if amount <= 0:
        return jsonify({'error': '请输入有效的转账金额'}), 400

    if amount < 0.1:
        return jsonify({'error': '转账金额不能低于0.1PL'}), 400

    current_balance = get_user_pl_balance(username)
    if current_balance < amount:
        return jsonify({'error': f'PL余额不足，需要{amount}PL，当前余额{current_balance}PL'}), 400

    if not has_pay_password(username):
        return jsonify({'error': '请先设置支付密码'}), 400

    order_id = generate_order_id('transfer')
    product_number = get_product_number('transfer')
    orders[order_id] = {
        'order_id': order_id,
        'username': username,
        'product_name': f'PL转账至{target_username}',
        'product_price': amount,
        'product_id': 'pl_transfer',
        'product_type': 'pl_transfer',
        'product_number': product_number,
        'payment_method': 'pl',
        'status': 'pending',
        'created_at': int(time.time() * 1000),
        'paid_at': 0,
        'anti_fake_code': generate_anti_fake_code(),
        'quantity': 1,
        'original_price': amount,
        'order_type': 'pl_transfer',
        'transfer_target': target_username,
        'transfer_amount': amount
    }
    save_orders()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'order_id': order_id,
        'message': '转账订单已创建，请前往支付页面完成支付',
        'responseTime': response_time
    })

@app.route('/api/pl/transfers', methods=['GET'])
@login_required
def get_pl_transfers():
    username = session['user']['username']
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    transfer_type = request.args.get('type', 'all')

    records = []
    total_outgoing = 0
    total_incoming = 0
    total_coupon_saved = 0

    for tid, transfer in pl_transfers.items():
        is_from = transfer.get('from_username') == username
        is_to = transfer.get('to_username') == username
        if not is_from and not is_to:
            continue

        if transfer_type == 'outgoing' and not is_from:
            continue
        if transfer_type == 'incoming' and not is_to:
            continue

        amount = transfer.get('amount', 0)
        actual_paid = transfer.get('actual_paid', amount)
        coupon_discount = transfer.get('coupon_discount', 0)
        direction = 'outgoing' if is_from else 'incoming'

        if direction == 'outgoing':
            total_outgoing += amount
            total_coupon_saved += coupon_discount
        else:
            total_incoming += amount

        records.append({
            'id': tid,
            'from_username': transfer.get('from_username'),
            'to_username': transfer.get('to_username'),
            'direction': direction,
            'amount': round(amount, 4),
            'actual_paid': round(actual_paid, 4),
            'coupon_discount': round(coupon_discount, 4),
            'rate': transfer.get('rate', 0),
            'timestamp': transfer.get('timestamp', 0),
            'status': transfer.get('status', 'completed')
        })

    records.sort(key=lambda x: -x.get('timestamp', 0))
    total = len(records)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = records[start:end]

    return jsonify({
        'records': paginated,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page if total > 0 else 1,
        'summary': {
            'total_outgoing': round(total_outgoing, 4),
            'total_incoming': round(total_incoming, 4),
            'total_coupon_saved': round(total_coupon_saved, 4)
        }
    })

@app.route('/api/pl/history', methods=['GET'])
@login_required
def get_pl_history():
    username = session['user']['username']
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    records = []
    for rid, record in pl_exchange_records.items():
        if record.get('username') == username:
            records.append({
                'id': rid,
                'amount': record.get('amount', 0),
                'operation_type': record.get('operation_type', ''),
                'rate': record.get('rate', 0),
                'timestamp': record.get('timestamp', 0)
            })
    records.sort(key=lambda x: -x.get('timestamp', 0))
    total = len(records)
    start = (page - 1) * per_page
    end = start + per_page
    return jsonify({
        'records': records[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page if total > 0 else 1
    })

@app.route('/api/pl/history/clear', methods=['DELETE'])
@csrf_protect
@login_required
def clear_pl_history():
    start_time = time.time()
    username = session['user']['username']

    exchange_records_to_remove = []
    for rid, record in pl_exchange_records.items():
        if record.get('username') == username:
            exchange_records_to_remove.append(rid)
    for rid in exchange_records_to_remove:
        del pl_exchange_records[rid]
    save_pl_exchange_records()

    transfer_records_to_remove = []
    for tid, transfer in pl_transfers.items():
        if transfer.get('from_username') == username or transfer.get('to_username') == username:
            transfer_records_to_remove.append(tid)
    for tid in transfer_records_to_remove:
        del pl_transfers[tid]
    save_pl_transfers()

    total_deleted = len(exchange_records_to_remove) + len(transfer_records_to_remove)
    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'message': f'已清空 {total_deleted} 条操作记录',
        'deleted_count': total_deleted,
        'responseTime': response_time
    })

@app.route('/api/pl/rate-history', methods=['GET'])
@login_required
def get_pl_rate_history():
    limit = request.args.get('limit', 100, type=int)
    history = pl_rate_data.get('rate_history', [])
    history = sorted(history, key=lambda x: -x.get('timestamp', 0))
    return jsonify({
        'history': history[:limit],
        'current_rate': get_current_pl_rate()
    })

@app.route('/api/pool/status', methods=['GET'])
@login_required
def get_pool_status_api():
    username = session['user']['username']
    try:
        status = get_pool_status()
        today_reward = get_user_today_pool_reward(username)
        has_claimed = has_user_claimed_pool_today(username)
        
        cooldown_data = user_pool_claims.get(username, {}).get('last_claim_cooldown', {})
        last_claim_time = cooldown_data.get('timestamp', 0)
        cooldown_end_time = 0
        cooldown_remaining = False
        
        if last_claim_time > 0:
            cooldown_end_time = last_claim_time + (COOLDOWN_HOURS * 3600 * 1000)
            if int(time.time() * 1000) < cooldown_end_time:
                cooldown_remaining = True
        
        user_data = users.get(username, {})
        total_days = user_data.get('attendanceTotalDays', 0)
        consecutive_days = user_data.get('attendanceConsecutiveDays', 0)
        is_verified = check_identity_verified(username)
        is_restricted = is_login_restricted(username)
        
        total_points = get_user_fund_total_points(username)
        full_base = calculate_user_pool_base_without_decay(username)
        
        if consecutive_days >= 7:
            cons_bonus = 1.0
        elif consecutive_days >= 4:
            cons_bonus = 0.7
        elif consecutive_days >= 1:
            cons_bonus = 0.4
        else:
            cons_bonus = 0.0
        
        current_base = get_user_today_pool_base(username)
        
        now = datetime.now()
        next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        user_bases = build_user_bases()
        
        can_claim = (
            total_days >= 7 and 
            not has_claimed and 
            not cooldown_remaining and
            today_reward > 0 and 
            is_verified and 
            not is_restricted
        )
        
        return jsonify({
            'today': status['today'],
            'pool_amount': status['pool_amount'],
            'total_base': round(status['total_base'], 4),
            'user_count': status['user_count'],
            'user_base': round(current_base, 4),
            'full_base': round(full_base, 4),
            'consecutive_days': consecutive_days,
            'cons_bonus': cons_bonus,
            'total_points': total_points,
            'today_reward': today_reward,
            'has_claimed_today': has_claimed,
            'cooldown_remaining': cooldown_remaining,
            'cooldown_end_time': cooldown_end_time,
            'cooldown_hours': COOLDOWN_HOURS,
            'total_days': total_days,
            'min_days': 7,
            'is_verified': is_verified,
            'is_restricted': is_restricted,
            'can_claim': can_claim,
            'next_update': int(next_midnight.timestamp() * 1000),
            'single_user_cap': len(user_bases) == 1
        })
    except Exception as e:
        log.error(f"Error in get_pool_status_api: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/pool/claim', methods=['POST'])
@csrf_protect
@limiter.limit(RATE_LIMITS['pool_claim'])
@login_required
@identity_required
def claim_pool_reward():
    username = session['user']['username']
    try:
        if has_user_claimed_pool_today(username):
            return jsonify({'error': '今日已领取瓜分奖励'}), 400
        
        user_data = users.get(username)
        if not user_data:
            return jsonify({'error': '用户不存在'}), 400
        
        total_days = user_data.get('attendanceTotalDays', 0)
        if total_days < 7:
            return jsonify({'error': f'需要累计签到7天才可瓜分，当前累计签到{total_days}天'}), 400
        
        if is_login_restricted(username):
            return jsonify({'error': '账号已被限制，无法瓜分'}), 400
        
        reward, error = process_pool_reward_for_user(username)
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'success': True, 
            'reward': reward,
            'message': f'成功领取{reward}积分瓜分奖励'
        })
        
    except Exception as e:
        log.error(f"Claim exception: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/pool/tomorrow-preview', methods=['GET'])
@login_required
def get_tomorrow_pool_preview():
    username = session['user']['username']
    today_reward = get_user_today_pool_reward(username)
    status = get_pool_status()
    now = datetime.now()
    next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return jsonify({
        'today_reward': today_reward,
        'pool_amount': status['pool_amount'],
        'user_base': round(calculate_user_pool_base(username), 4),
        'total_base': round(status['total_base'], 4),
        'user_count': status['user_count'],
        'next_update': int(next_midnight.timestamp() * 1000)
    })

@app.route('/api/mail/list', methods=['GET'])
@login_required
def get_mail_list():
    username = session['user']['username']
    cleanup_expired_mail_attachments()

    attachments = []
    for aid, attachment in mail_attachments.items():
        if attachment.get('username') == username:
            is_claimed = attachment.get('claimed', False)
            if is_claimed:
                continue
            attachments.append({
                'id': aid,
                'title': attachment.get('title', ''),
                'description': attachment.get('description', ''),
                'type': attachment.get('type', ''),
                'created_at': attachment.get('created_at', 0),
                'expires_at': attachment.get('expires_at', 0),
                'claimed': is_claimed,
                'source': attachment.get('source', '')
            })

    attachments.sort(key=lambda x: -x.get('created_at', 0))

    return jsonify({
        'attachments': attachments,
        'total': len(attachments)
    })

@app.route('/api/pool/yesterday-details', methods=['GET'])
@login_required
def get_yesterday_pool_details():
    username = session['user']['username']
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    details = pool_records.get(yesterday, {})
    payout_details = details.get('payout_details', {})
    
    if not payout_details or not isinstance(payout_details, dict):
        return jsonify({
            'date': yesterday,
            'total_payout': 0,
            'user_count': 0,
            'user_reward': 0,
            'top_10': [],
            'has_record': False
        })
    
    user_reward = payout_details.get(username, 0)
    total_payout = details.get('total_payout', 0)
    
    if total_payout == 0:
        total_payout = sum(payout_details.values())
    
    user_count = len([u for u, r in payout_details.items() if r > 0])
    
    top_10 = sorted(payout_details.items(), key=lambda x: -x[1])[:10]
    top_10_list = [{'username': u, 'reward': round(r, 2)} for u, r in top_10 if r > 0]
    
    return jsonify({
        'date': yesterday,
        'total_payout': round(total_payout, 2),
        'user_count': user_count,
        'user_reward': round(user_reward, 2),
        'top_10': top_10_list,
        'has_record': user_count > 0 and total_payout > 0
    })

@app.route('/api/newbie-pool/status', methods=['GET'])
@login_required
def get_newbie_pool_status_api():
    username = session['user']['username']
    status = get_newbie_pool_status()
    
    user_data = users.get(username, {})
    created_at_str = user_data.get('createdAt', '')
    days_old = -1
    is_eligible = False
    if created_at_str:
        try:
            created_at = datetime.fromisoformat(created_at_str)
            days_old = (datetime.now() - created_at).days
            is_eligible = days_old <= 7 and check_identity_verified(username) and not is_login_restricted(username)
        except:
            pass
    
    today = datetime.now().strftime('%Y-%m-%d')
    has_attended = user_data.get('lastAttendanceDate', '') == today
    is_active = user_data.get('lastLoginDate', '') == today
    
    reward = get_user_newbie_reward(username) if is_eligible else 0
    has_claimed = has_user_claimed_newbie_today(username)
    
    return jsonify({
        'pool_amount': status['pool_amount'],
        'eligible_count': status['eligible_count'],
        'max_reward': status['max_reward'],
        'system_total': status['system_total'],
        'today': status['today'],
        'user_days_old': days_old,
        'is_eligible': is_eligible,
        'has_attended_today': has_attended,
        'is_active_today': is_active,
        'reward': reward,
        'has_claimed_today': has_claimed,
        'can_claim': is_eligible and not has_claimed and reward > 0 and status['pool_amount'] >= reward
    })

@app.route('/api/newbie-pool/claim', methods=['POST'])
@csrf_protect
@limiter.limit('2 per minute')
@login_required
def claim_newbie_reward_api():
    username = session['user']['username']
    reward, error = claim_newbie_reward(username)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({
        'success': True,
        'reward': reward,
        'message': f'成功领取{reward}积分新人奖励'
    })

@app.route('/api/mail/claim/<attachment_id>', methods=['POST'])
@csrf_protect
@limiter.limit(RATE_LIMITS['mail_claim'])
@login_required
def claim_mail_attachment(attachment_id):
    username = session['user']['username']

    if attachment_id not in mail_attachments:
        return jsonify({'error': '邮件附件不存在'}), 400

    attachment = mail_attachments[attachment_id]

    if attachment.get('username') != username:
        return jsonify({'error': '无权操作此邮件附件'}), 400

    if attachment.get('claimed', False):
        return jsonify({'error': '该附件已被领取'}), 400

    current_time = int(time.time() * 1000)
    expires_at = attachment.get('expires_at', 0)
    if expires_at > 0 and current_time > expires_at:
        del mail_attachments[attachment_id]
        save_mail_attachments()
        return jsonify({'error': '邮件附件已过期'}), 400

    success, message = do_claim_mail_attachment_with_message(attachment_id, username)

    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 400


def do_claim_mail_attachment(attachment_id, username):
    if attachment_id not in mail_attachments:
        return False

    attachment = mail_attachments[attachment_id]

    if attachment.get('username') != username:
        return False

    if attachment.get('claimed', False):
        return False

    is_batch = attachment.get('is_batch', False)
    attachment_type = attachment.get('type', '')
    codes = attachment.get('codes', [])

    code_storage_map = {
        'point_code': (point_codes, save_point_codes, 'point'),
        'premium_point_code': (premium_point_codes, save_premium_point_codes, 'premium_point'),
        'reset_code': (reset_codes, save_reset_codes, 'reset'),
        'boost_code': (boost_codes, save_boost_codes, 'boost'),
        'special_point_code': (special_point_codes, save_special_point_codes, 'special_point'),
        'makeup_code': (makeup_codes, save_makeup_codes, 'makeup'),
        'gamblers_code': (gamblers_codes, save_gamblers_codes, 'gamblers'),
        'cancellation_code': (cancellation_codes, save_cancellation_codes, 'cancellation'),
        'box_code': (box_codes, save_box_codes, 'box'),
        'plcard_code': (plcard_codes, save_plcard_codes, 'plcard'),
        'premium_boost_code': (premium_boost_codes, save_premium_boost_codes, 'premium_boost')
    }

    if attachment_type == 'combined_reward':
        if not codes:
            return False

        combined_types = attachment.get('combined_types', [])
        code_to_type = {}
        for att_type in combined_types:
            if att_type in code_storage_map:
                code_to_type[att_type] = code_storage_map[att_type]

        if not code_to_type:
            return False

        added_count = 0
        for code in codes:
            found_type = None
            found_storage = None
            found_save = None
            found_type_name = None

            for att_type, (storage, save_func, type_name) in code_to_type.items():
                if code not in storage:
                    found_type = att_type
                    found_storage = storage
                    found_save = save_func
                    found_type_name = type_name
                    break

            if found_type and found_storage is not None:
                found_storage[code] = {
                    'code': code,
                    'username': username,
                    'used': False,
                    'recycled': False,
                    'createdAt': attachment.get('created_at', int(time.time() * 1000)),
                    'type': found_type_name,
                    'adminGranted': attachment.get('source') == 'admin_grant' or attachment.get('source') == 'admin_reissue',
                    'source': attachment.get('source', 'mail')
                }
                found_save()
                added_count += 1

                if found_type == 'cancellation_code':
                    users[username]['cancellationCodePurchased'] = True
                    save_users()

        if added_count > 0:
            attachment['claimed'] = True
            attachment['claimed_at'] = int(time.time() * 1000)
            save_mail_attachments()
            return True
        return False

    elif attachment_type == 'points':
        points_amount = attachment.get('points_amount', 0)
        if points_amount > 0:
            add_points_without_limit(username, points_amount)
            attachment['claimed'] = True
            attachment['claimed_at'] = int(time.time() * 1000)
            save_mail_attachments()
            return True

    elif attachment_type in code_storage_map:
        code_storage, save_func, type_name = code_storage_map[attachment_type]

        if is_batch:
            codes = attachment.get('codes', [])
            if not codes:
                return False

            added_count = 0
            for code in codes:
                if code and code not in code_storage:
                    code_storage[code] = {
                        'code': code,
                        'username': username,
                        'used': False,
                        'recycled': False,
                        'createdAt': attachment.get('created_at', int(time.time() * 1000)),
                        'type': type_name,
                        'adminGranted': attachment.get('source') == 'admin_grant' or attachment.get('source') == 'admin_reissue',
                        'source': attachment.get('source', 'mail')
                    }
                    added_count += 1

            if added_count > 0:
                save_func()
                attachment['claimed'] = True
                attachment['claimed_at'] = int(time.time() * 1000)

                if attachment_type == 'cancellation_code':
                    users[username]['cancellationCodePurchased'] = True
                    save_users()

                save_mail_attachments()
                return True
            return False
        else:
            code = attachment.get('code', '')
            if code and code not in code_storage:
                code_storage[code] = {
                    'code': code,
                    'username': username,
                    'used': False,
                    'recycled': False,
                    'createdAt': attachment.get('created_at', int(time.time() * 1000)),
                    'type': type_name,
                    'adminGranted': attachment.get('source') == 'admin_grant' or attachment.get('source') == 'admin_reissue',
                    'source': attachment.get('source', 'mail')
                }
                save_func()

                if attachment_type == 'cancellation_code':
                    users[username]['cancellationCodePurchased'] = True
                    save_users()

                attachment['claimed'] = True
                attachment['claimed_at'] = int(time.time() * 1000)
                save_mail_attachments()
                return True
            return False

    elif attachment_type == 'coupon':
        coupon_data = attachment.get('coupon_data', {})
        if coupon_data:
            coupon_id = coupon_data.get('id')
            if coupon_id and coupon_id not in user_coupons:
                user_coupons[coupon_id] = coupon_data
                save_user_coupons()
                attachment['claimed'] = True
                attachment['claimed_at'] = int(time.time() * 1000)
                save_mail_attachments()
                return True
            else:
                return False
        else:
            return False

    return False


def do_claim_mail_attachment_with_message(attachment_id, username):
    if attachment_id not in mail_attachments:
        return False, '邮件附件不存在'

    attachment = mail_attachments[attachment_id]

    if attachment.get('username') != username:
        return False, '无权操作此邮件附件'

    if attachment.get('claimed', False):
        return False, '该附件已被领取'

    current_time = int(time.time() * 1000)
    expires_at = attachment.get('expires_at', 0)
    if expires_at > 0 and current_time > expires_at:
        del mail_attachments[attachment_id]
        save_mail_attachments()
        return False, '邮件附件已过期'

    attachment_type = attachment.get('type', '')
    type_names = {
        'points': '积分',
        'point_code': '普通积分卡密',
        'premium_point_code': '高级积分卡密',
        'reset_code': '重置密码卡密',
        'boost_code': '积分加成卡密',
        'special_point_code': '特殊积分卡密',
        'makeup_code': '补签卡',
        'gamblers_code': '赌神积分卡密',
        'cancellation_code': '注销卡密',
        'coupon': '优惠券',
        'box_code': '盲盒卡',
        'plcard_code': '普通PL随机卡',
        'premium_boost_code': '高级加成卡'
    }

    if do_claim_mail_attachment(attachment_id, username):
        type_name = type_names.get(attachment_type, attachment_type)
        quantity = attachment.get('quantity', 1)
        
        if quantity > 1:
            return True, f'成功领取{quantity}张{type_name}'
        return True, f'成功领取{type_name}'
    else:
        return False, '领取失败，请重试'

def cleanup_mail_attachments_loop():
    while True:
        time.sleep(300)
        try:
            cleanup_expired_mail_attachments()
        except Exception as e:
            log.error(f"Cleanup mail attachments error: {e}")

mail_cleanup_thread = threading.Thread(target=cleanup_mail_attachments_loop, daemon=True)
mail_cleanup_thread.start()

def cleanup_captcha_for_order(order_id):
    captcha_data = load_captcha_storage()
    captcha_ids_to_remove = []
    for captcha_id, data in captcha_data.items():
        if data.get('order_id') == order_id:
            captcha_ids_to_remove.append(captcha_id)
    for captcha_id in captcha_ids_to_remove:
        if captcha_id in captcha_data:
            del captcha_data[captcha_id]
    if captcha_ids_to_remove:
        save_captcha_storage(captcha_data)
    return len(captcha_ids_to_remove)

def cleanup_captcha_by_id(captcha_id):
    if not captcha_id:
        return False
    captcha_data = load_captcha_storage()
    if captcha_id in captcha_data:
        del captcha_data[captcha_id]
        save_captcha_storage(captcha_data)
        return True
    return False

def cleanup_boost_checker():
    while True:
        time.sleep(60)
        cleanup_all_expired_data()
        try:
            burn_excess_system_points()
        except Exception as e:
            log.error(f"Burn excess system points error: {e}")

boost_cleanup_thread = threading.Thread(target=cleanup_boost_checker, daemon=True)
boost_cleanup_thread.start()

pool_thread = threading.Thread(target=pool_reward_loop, daemon=True)
pool_thread.start()

@app.route('/api/login', methods=['POST'])
@csrf_protect
@limiter.limit(RATE_LIMITS['login'])
def login():
    start_time = time.time()
    data = request.get_json()
    username_or_email = data.get('username', '').strip()
    password = data.get('password', '')

    if not username_or_email or not password:
        return jsonify({'error': '请填写用户名/邮箱和密码'}), 400

    user_data = None
    username = None

    if username_or_email in users:
        username = username_or_email
        user_data = users[username]
    else:
        for u, data in users.items():
            if data.get('email') == username_or_email.lower():
                username = u
                user_data = data
                break

    if not user_data:
        return jsonify({'error': '用户名或密码错误'}), 400

    if not bcrypt.check_password_hash(user_data['password'], password):
        return jsonify({'error': '用户名或密码错误'}), 400

    session['user'] = {'username': username}
    user_data['lastLoginDate'] = datetime.now().strftime('%Y-%m-%d')
    save_users()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'username': username,
        'message': '登录成功',
        'responseTime': response_time
    })


@app.route('/api/register', methods=['POST'])
@csrf_protect
@limiter.limit(RATE_LIMITS['register'])
def register():
    start_time = time.time()
    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    qq_number = data.get('qq_number', '').strip()
    verification_code = data.get('verification_code', '').strip()

    if not username or not email or not password:
        return jsonify({'error': '请填写所有字段'}), 400

    if not validate_username(username):
        return jsonify({'error': '用户名必须为3-20位字符，仅支持字母、数字、下划线、中文'}), 400

    if username in users:
        return jsonify({'error': '用户名已被使用'}), 400

    if not validate_email(email):
        return jsonify({'error': '邮箱格式不正确'}), 400

    for existing_user in users.values():
        if existing_user.get('email') == email:
            return jsonify({'error': '邮箱已被注册'}), 400

    if not validate_password(password):
        return jsonify({'error': '密码至少8位，需包含至少两种类型（大小写字母/数字/特殊字符）'}), 400

    if qq_number and not re.match(r'^\d{5,15}$', qq_number):
        return jsonify({'error': 'QQ号格式不正确，请输入5-15位数字'}), 400

    if qq_number:
        for u, data in users.items():
            if data.get('qq_number') == qq_number:
                return jsonify({'error': '该QQ号已被其他用户绑定'}), 400

    if not verification_code:
        return jsonify({'error': '请输入邮箱验证码'}), 400

    success, message = email_service.verify_code(email, verification_code)
    if not success:
        return jsonify({'error': message}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    users[username] = {
        'username': username,
        'email': email,
        'password': hashed_password,
        'qq_number': qq_number,
        'totalPoints': 0,
        'unlimitedPoints': 0,
        'dailyEarnedPoints': 0,
        'lastEarnedDate': datetime.now().strftime('%Y-%m-%d'),
        'lastLoginDate': datetime.now().strftime('%Y-%m-%d'),
        'createdAt': datetime.now().isoformat(),
        'attendanceTotalDays': 0,
        'attendanceConsecutiveDays': 0,
        'lastAttendanceTimestamp': 0,
        'attendanceClaimedTotalCycles': {},
        'attendanceClaimedConsecutiveCycles': {},
        'cancellationCodePurchased': False,
        'coupon_usage_count': 0,
        'makeup_code_used_count': 0,
        'gamblers_code_purchase_count': 0,
        'last_gamblers_purchase_date': '',
        'box_code_purchase_count': 0,
        'last_box_purchase_date': '',
        'plcard_code_purchase_count': 0,
        'last_plcard_purchase_date': ''
    }
    save_users()

    session['user'] = {'username': username}

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'username': username,
        'message': '注册成功',
        'responseTime': response_time
    })

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    response = make_response(jsonify({'success': True, 'message': '已退出登录'}))
    response.set_cookie('session', '', expires=0, path='/')
    response.set_cookie('session_expiration', '', expires=0, path='/')
    response.set_cookie('session', '', expires=0, path='/', domain=None)
    response.set_cookie('session_expiration', '', expires=0, path='/', domain=None)
    return response

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if 'user' in session and session['user']:
        username = session['user']['username']
        if username in users:
            reset_daily_points_if_needed(username)
            user_data = users[username]
            is_verified = check_identity_verified(username)
            created_at_str = user_data.get('createdAt', '')
            is_within_24h = False
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str)
                    is_within_24h = (datetime.now() - created_at) <= timedelta(hours=24)
                except:
                    pass
            today = datetime.now().strftime('%Y-%m-%d')
            last_gamblers_purchase = user_data.get('last_gamblers_purchase_date', '')
            gamblers_purchase_count = user_data.get('gamblers_code_purchase_count', 0)
            if last_gamblers_purchase != today:
                gamblers_purchase_count = 0
                user_data['gamblers_code_purchase_count'] = 0
                user_data['last_gamblers_purchase_date'] = today
                save_users()

            last_box_purchase = user_data.get('last_box_purchase_date', '')
            box_purchase_count = user_data.get('box_code_purchase_count', 0)
            if last_box_purchase != today:
                box_purchase_count = 0
                user_data['box_code_purchase_count'] = 0
                user_data['last_box_purchase_date'] = today
                save_users()

            last_plcard_purchase = user_data.get('last_plcard_purchase_date', '')
            plcard_purchase_count = user_data.get('plcard_code_purchase_count', 0)
            if last_plcard_purchase != today:
                plcard_purchase_count = 0
                user_data['plcard_code_purchase_count'] = 0
                user_data['last_plcard_purchase_date'] = today
                save_users()

            mail_count = sum(1 for a in mail_attachments.values() if a.get('username') == username and not a.get('claimed', False))
            
            fund_balance = get_user_fund_balance(username)
            total_points_with_fund = user_data.get('totalPoints', 0) + fund_balance
            effective_points = get_user_effective_points(username)
            price_multiplier = get_price_multiplier(username)

            return jsonify({
                'authenticated': True,
                'username': username,
                'email': user_data.get('email', ''),
                'qq_number': user_data.get('qq_number', ''),
                'totalPoints': user_data.get('totalPoints', 0),
                'fundBalance': fund_balance,
                'totalPointsWithFund': total_points_with_fund,
                'dailyEarnedPoints': user_data.get('dailyEarnedPoints', 0),
                'isNewUser': is_new_user(username),
                'isVerified': is_verified,
                'hasCancellationCode': user_data.get('cancellationCodePurchased', False),
                'attendanceConsecutiveDays': user_data.get('attendanceConsecutiveDays', 0),
                'isWithin24Hours': is_within_24h,
                'dailyBonusCode': user_data.get('dailyBonusCode'),
                'createdAt': user_data.get('createdAt'),
                'lastLoginDate': user_data.get('lastLoginDate', ''),
                'lastLoginTime': user_data.get('lastLoginTime', ''),
                'makeupUsedCount': user_data.get('makeup_code_used_count', 0),
                'gamblersPurchaseCount': gamblers_purchase_count,
                'gamblersMaxCount': 3,
                'boxPurchaseCount': box_purchase_count,
                'boxMaxCount': 5,
                'plcardPurchaseCount': plcard_purchase_count,
                'plcardMaxCount': 10,
                'mailCount': mail_count,
                'effectivePoints': effective_points,
                'priceMultiplier': price_multiplier
            })
    return jsonify({'authenticated': False})

@app.route('/api/user/restrictions', methods=['GET'])
@login_required
def get_user_restrictions_api():
    username = session['user']['username']
    restrictions = get_user_restrictions(username)
    return jsonify({
        'loginRestricted': restrictions.get('login', False),
        'mallRestricted': restrictions.get('mall', False),
        'generatePhoneRestricted': restrictions.get('generate_phone', False)
    })

@app.route('/api/user/update-qq', methods=['POST'])
@csrf_protect
@login_required
def update_qq_number():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    qq_number = data.get('qq_number', '').strip()

    if not qq_number:
        return jsonify({'error': '请输入QQ号'}), 400

    if not re.match(r'^\d{5,15}$', qq_number):
        return jsonify({'error': 'QQ号格式不正确，请输入5-15位数字'}), 400

    user_data = users.get(username)
    if not user_data:
        return jsonify({'error': '用户不存在'}), 400

    if user_data.get('qq_number'):
        return jsonify({'error': 'QQ号已设置，不可修改'}), 400

    for u, data in users.items():
        if data.get('qq_number') == qq_number:
            return jsonify({'error': '该QQ号已被其他用户绑定'}), 400

    user_data['qq_number'] = qq_number
    save_users()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'message': 'QQ号绑定成功',
        'qq_number': qq_number,
        'responseTime': response_time
    })

@app.route('/api/get-points', methods=['GET'])
@login_required
def get_points():
    start_time = time.time()
    username = session['user']['username']
    if username in users:
        reset_daily_points_if_needed(username)
        user_data = users[username]
        fund_balance = get_user_fund_balance(username)
        total_points_with_fund = user_data.get('totalPoints', 0) + fund_balance
        effective_points = get_user_effective_points(username)
        price_multiplier = get_price_multiplier(username)
        return jsonify({
            'totalPoints': user_data.get('totalPoints', 0),
            'fundBalance': fund_balance,
            'totalPointsWithFund': total_points_with_fund,
            'dailyEarnedPoints': user_data.get('dailyEarnedPoints', 0),
            'isNewUser': is_new_user(username),
            'bonusPeriod': is_bonus_period(),
            'effectivePoints': effective_points,
            'priceMultiplier': price_multiplier,
            'responseTime': int((time.time() - start_time) * 1000)
        })
    return jsonify({'error': '用户不存在'}), 400

@app.route('/api/generate-phone', methods=['POST'])
@csrf_protect
@limiter.limit(RATE_LIMITS['generate_phone'])
@generate_phone_access_required
def generate_phone():
    start_time = time.time()
    username = session['user']['username']

    phone_number = generate_phone_number()
    auth_code = generate_auth_code(phone_number)
    hidden_phone = phone_number[:3] + '*****' + phone_number[-4:]

    if username not in phone_records:
        phone_records[username] = []

    auth_codes[auth_code] = {
        'code': auth_code,
        'phoneNumber': phone_number,
        'used': False,
        'createdAt': int(time.time() * 1000),
        'username': username
    }

    phone_records[username].append({
        'phoneNumber': phone_number,
        'hiddenPhone': hidden_phone,
        'authCode': auth_code,
        'boundAuthCode': auth_code,
        'used': False,
        'timestamp': datetime.now().isoformat(),
        'username': username
    })

    save_phone_records()
    save_auth_codes()
    enforce_phone_record_limit()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'hiddenPhone': hidden_phone,
        'authCode': auth_code,
        'responseTime': response_time
    })

@app.route('/api/get-records', methods=['GET'])
@login_required
def get_records():
    start_time = time.time()
    username = session['user']['username']
    records = []
    if username in phone_records:
        for record in phone_records[username]:
            records.append({
                'phoneNumber': record.get('phoneNumber', ''),
                'hiddenPhone': record.get('hiddenPhone', ''),
                'authCode': record.get('authCode', ''),
                'used': record.get('used', False),
                'timestamp': record.get('timestamp', '')
            })
    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'records': records,
        'responseTime': response_time
    })

@app.route('/api/verify-authcode', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def verify_authcode():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    auth_code = data.get('authCode', '').strip().upper()

    if not auth_code:
        return jsonify({'error': '请输入授权码'}), 400

    if auth_code not in auth_codes:
        return jsonify({'error': '授权码无效'}), 400

    code_data = auth_codes[auth_code]

    if code_data.get('used'):
        return jsonify({'error': '授权码已被使用'}), 400

    if code_data.get('verified', False):
        return jsonify({'error': '授权码已验证，请回填完整号码获取积分'}), 400

    code_username = code_data.get('username')
    if code_username != username:
        return jsonify({'error': '授权码不属于当前用户'}), 400

    current_time = int(time.time() * 1000)
    if (current_time - code_data.get('createdAt', 0)) > 180000:
        del auth_codes[auth_code]
        save_auth_codes()
        return jsonify({'error': '授权码已过期（3分钟有效）'}), 400

    code_data['verified'] = True
    save_auth_codes()

    phone_number = code_data['phoneNumber']

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'phoneNumber': phone_number,
        'responseTime': response_time
    })

@app.route('/api/attendance', methods=['POST'])
@csrf_protect
@limiter.limit(RATE_LIMITS['attendance'])
@login_required
@identity_required
def attendance():
    start_time = time.time()
    username = session['user']['username']
    user_data = users.get(username)
    if not user_data:
        return jsonify({'error': '用户不存在'}), 400
    today = datetime.now().strftime('%Y-%m-%d')
    last_attendance_date = user_data.get('lastAttendanceDate', '')
    if last_attendance_date == today:
        return jsonify({'error': '今日已签到'}), 400
    daily_earned = user_data.get('dailyEarnedPoints', 0)
    if daily_earned < 3:
        return jsonify({'error': f'今日获取积分需达到3积分才可签到，当前{daily_earned}/14'}), 400
    points_earned = 0.3
    user_data['dailyEarnedPoints'] = round(user_data.get('dailyEarnedPoints', 0), 2)
    if 'totalPoints' not in user_data:
        user_data['totalPoints'] = 0
    user_data['totalPoints'] = round(user_data['totalPoints'] + points_earned, 2)
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    if last_attendance_date == yesterday:
        user_data['attendanceConsecutiveDays'] = user_data.get('attendanceConsecutiveDays', 0) + 1
    else:
        user_data['attendanceConsecutiveDays'] = 1
    user_data['attendanceTotalDays'] = user_data.get('attendanceTotalDays', 0) + 1
    if 'firstAttendanceDate' not in user_data or not user_data['firstAttendanceDate']:
        user_data['firstAttendanceDate'] = today
    user_data['lastAttendanceDate'] = today
    user_data['lastAttendanceTimestamp'] = int(time.time())

    added_points = add_random_system_points(username)

    save_users()
    rewards = check_and_award_attendance_rewards(username)
    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'pointsEarned': points_earned,
        'totalDays': user_data['attendanceTotalDays'],
        'consecutiveDays': user_data['attendanceConsecutiveDays'],
        'systemPoolAdded': added_points,
        'rewards': rewards,
        'responseTime': response_time
    })

@app.route('/api/attendance/calendar', methods=['GET'])
@login_required
def get_attendance_calendar():
    username = session['user']['username']
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    if not year or not month:
        now = datetime.now()
        year = now.year
        month = now.month

    if month < 1 or month > 12:
        return jsonify({'error': '月份无效'}), 400

    user_data = users.get(username, {})
    consecutive_days = user_data.get('attendanceConsecutiveDays', 0)
    last_attendance_date = user_data.get('lastAttendanceDate', '')
    total_days = user_data.get('attendanceTotalDays', 0)
    first_attendance_date = user_data.get('firstAttendanceDate', '')

    if not first_attendance_date and last_attendance_date and total_days > 0:
        try:
            last_dt = datetime.strptime(last_attendance_date, '%Y-%m-%d')
            first_dt = last_dt - timedelta(days=total_days - 1)
            first_attendance_date = first_dt.strftime('%Y-%m-%d')
            user_data['firstAttendanceDate'] = first_attendance_date
            save_users()
        except:
            pass

    calendar_data = []
    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year, 12, 31)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    last_day_num = last_day.day

    py_weekday = first_day.weekday()
    first_weekday = (py_weekday + 1) % 7

    signed_days = set()

    if last_attendance_date and consecutive_days > 0:
        try:
            last_date = datetime.strptime(last_attendance_date, '%Y-%m-%d')
            for i in range(consecutive_days):
                check_date = last_date - timedelta(days=i)
                if check_date.year == year and check_date.month == month:
                    signed_days.add(check_date.day)
        except:
            pass

    for day in range(1, last_day_num + 1):
        date_obj = datetime(year, month, day)
        is_today = date_obj.date() == datetime.now().date()
        is_signed = day in signed_days
        py_wd = date_obj.weekday()
        weekday = (py_wd + 1) % 7
        is_weekend = weekday == 0 or weekday == 6

        day_index = -1
        if first_attendance_date:
            try:
                first_date = datetime.strptime(first_attendance_date, '%Y-%m-%d')
                day_index = (date_obj.date() - first_date.date()).days
                if day_index < 0:
                    day_index = -1
            except:
                pass

        calendar_data.append({
            'day': day,
            'is_today': is_today,
            'is_signed': is_signed,
            'is_weekend': is_weekend,
            'weekday': weekday,
            'date': date_obj.strftime('%Y-%m-%d'),
            'day_index': day_index
        })

    return jsonify({
        'year': year,
        'month': month,
        'month_name': first_day.strftime('%B'),
        'first_weekday': first_weekday,
        'days': calendar_data,
        'total_signed_days': len(signed_days),
        'total_days': len(calendar_data),
        'consecutive_days': consecutive_days,
        'total_attendance_days': total_days,
        'last_attendance_date': last_attendance_date,
        'first_attendance_date': first_attendance_date
    })

@app.route('/api/attendance-info', methods=['GET'])
@login_required
def attendance_info():
    start_time = time.time()
    username = session['user']['username']
    user_data = users.get(username)
    if not user_data:
        return jsonify({'error': '用户不存在'}), 400

    reset_daily_points_if_needed(username)
    user_data = users.get(username)

    today = datetime.now().strftime('%Y-%m-%d')
    has_attended_today = user_data.get('lastAttendanceDate', '') == today
    daily_earned = user_data.get('dailyEarnedPoints', 0)
    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'totalDays': user_data.get('attendanceTotalDays', 0),
        'consecutiveDays': user_data.get('attendanceConsecutiveDays', 0),
        'hasAttendedToday': has_attended_today,
        'lastAttendanceDate': user_data.get('lastAttendanceDate', ''),
        'dailyEarnedPoints': daily_earned,
        'firstAttendanceDate': user_data.get('firstAttendanceDate', ''),
        'responseTime': response_time
    })

@app.route('/api/verify_identity', methods=['POST'])
@csrf_protect
@limiter.limit(RATE_LIMITS['verify_identity'])
@login_required
def verify_identity():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    real_name = data.get('real_name', '').strip()
    id_number = data.get('id_number', '').strip()
    gender = data.get('gender', '')

    if not real_name or not id_number or not gender:
        return jsonify({'error': '请填写完整信息'}), 400

    if len(id_number) != 18 or not re.match(r'^\d{17}[\dXx]$', id_number):
        return jsonify({'error': '身份证号码格式不正确'}), 400

    id_number = id_number.upper()
    age = calculate_age(id_number)
    if age is None:
        return jsonify({'error': '身份证号码无效'}), 400
    if age < 10 or age > 80:
        return jsonify({'error': f'年龄需在10-80岁之间，当前{age}岁'}), 400

    actual_gender = get_gender_from_id_number(id_number)
    if actual_gender != gender:
        return jsonify({'error': f'性别与身份证号码不符，实际性别为{actual_gender}'}), 400

    if username in identity_verifications and identity_verifications[username].get('verified', False):
        return jsonify({'error': '已经完成身份认证，无需重复认证'}), 400

    id_hash = hash_id_number(id_number)
    id_masked = mask_id_number(id_number)

    identity_verifications[username] = {
        'username': username,
        'real_name': real_name,
        'id_number_hash': id_hash,
        'id_number_masked': id_masked,
        'gender': gender,
        'verified': True,
        'verified_at': datetime.now().isoformat(),
        'quick_verify': False,
        'id_card_key': id_number
    }
    save_identity_verifications()

    used_data = load_id_cards_used()
    if id_number not in used_data or used_data[id_number] == False:
        used_data[id_number] = True
        save_id_cards_used(used_data)
        log.info(f"Manual verification marked ID card {id_number} as used for user {username}")

    pl_amount = round(random.uniform(0.5, 3.0), 4)
    update_user_pl_balance(username, pl_amount, 'identity_verification_reward', 'id_verify')

    coupon_types = ['full_reduction', 'unconditional', 'product_specific']
    for _ in range(2):
        coupon_type = random.choice(coupon_types)
        if coupon_type == 'full_reduction':
            discount = round(random.uniform(0.5, 10), 1)
            if discount < 0.5:
                discount = 0.5
            threshold = min(max(round(discount * random.uniform(2, 4), 1), discount + 0.5), 12)
            desc = f'满{threshold}减{discount}'
            grant_coupon_to_user(username, coupon_type, discount, threshold, random.randint(24, 168), '', desc)
        elif coupon_type == 'unconditional':
            discount = round(random.uniform(0.3, 7), 1)
            if discount < 0.3:
                discount = 0.3
            desc = f'无门槛减{discount}'
            grant_coupon_to_user(username, coupon_type, discount, 0, random.randint(24, 168), '', desc)
        elif coupon_type == 'product_specific':
            product_ids = ['point_code', 'premium_point_code', 'reset_code', 'boost_code', 'special_point_code', 'makeup_code', 'gamblers_code']
            product_id = random.choice(product_ids)
            price_map = {'point_code': 1.2, 'premium_point_code': 3.5, 'reset_code': 8, 'boost_code': 8.8, 'special_point_code': 20, 'makeup_code': 200, 'gamblers_code': 100}
            base_price = price_map.get(product_id, 0)
            max_discount = base_price * 0.8
            discount = round(random.uniform(0.3, max_discount), 1)
            if discount < 0.3:
                discount = 0.3
            if discount > max_discount:
                discount = max_discount
            product_label = get_product_type_label(product_id)
            desc = f'指定{product_label}减{discount}'
            grant_coupon_to_user(username, coupon_type, discount, 0, random.randint(24, 168), product_id, desc)

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'message': f'身份认证成功！获得{pl_amount}PL和2张随机优惠券奖励（已发送至邮箱）',
        'pl_reward': pl_amount,
        'responseTime': response_time
    })

def calculate_age(id_number):
    if not id_number or len(id_number) != 18:
        return None
    try:
        birth_year = int(id_number[6:10])
        birth_month = int(id_number[10:12]) - 1
        birth_day = int(id_number[12:14])
        birth_date = datetime(birth_year, birth_month, birth_day)
        today = datetime.now()
        age = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        return age
    except:
        return None

def get_gender_from_id_number(id_number):
    if not id_number or len(id_number) != 18:
        return None
    try:
        gender_digit = int(id_number[16])
        return '男' if gender_digit % 2 == 1 else '女'
    except:
        return None

@app.route('/api/check_identity_status', methods=['GET'])
@csrf_protect
@login_required
def check_identity_status():
    username = session['user']['username']
    if username in identity_verifications:
        ver = identity_verifications[username]
        if ver.get('verified', False):
            return jsonify({
                'authenticated': True,
                'id_verified': True,
                'real_name': ver.get('real_name', ''),
                'id_number_masked': ver.get('id_number_masked', ''),
                'verified_at': ver.get('verified_at', '')
            })
    return jsonify({'authenticated': True, 'id_verified': False})

@app.route('/api/gateway/status', methods=['GET'])
@csrf_protect
@login_required
def gateway_status():
    start_time = time.time()
    username = session['user']['username']

    cleanup_expired_gateway_cards()

    user_data = users.get(username, {})
    active_card = get_user_active_card(username)

    result = {
        'username': username,
        'points': user_data.get('totalPoints', 0),
        'activeCard': None,
        'cardKey': None
    }

    if active_card:
        result['activeCard'] = {
            'type': active_card.get('type', ''),
            'expireAt': active_card.get('expire_at', 0),
            'price': active_card.get('price', 0)
        }
        result['cardKey'] = active_card.get('key', '')

    stock = get_gateway_stock_today()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        **result,
        'stock': stock,
        'responseTime': response_time
    })

@app.route('/api/gateway/create-order', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def gateway_create_order():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    card_type = data.get('cardType', '')
    day_price = data.get('dayPrice', None)
    remain_hours = data.get('remainHours', None)

    if card_type not in ['hour', 'day', 'week', 'permanent']:
        return jsonify({'error': '无效的卡密类型'}), 400

    cleanup_expired_gateway_cards()

    active_card = get_user_active_card(username)
    if active_card:
        return jsonify({'error': '您已拥有有效的通行卡密，无需重复购买'}), 400

    if not check_gateway_stock(card_type):
        return jsonify({'error': f'{card_type}卡库存已用完，请明日再试'}), 400

    base_price = get_card_price(card_type, remain_hours if card_type == 'day' else None)

    if base_price <= 0:
        return jsonify({'error': '当前时间无法购买天卡，请选择其他卡密'}), 400

    # Apply tiered pricing to gateway cards
    final_price = get_final_price(base_price, username)
    price_info = get_price_info(base_price, username)

    user_data = users.get(username, {})

    if user_data.get('totalPoints', 0) < final_price:
        return jsonify({'error': f'积分不足，需要 {final_price} 积分，当前 {user_data.get("totalPoints", 0):.2f} 积分'}), 400

    order_id = generate_order_id('gateway')
    product_number = get_product_number('gateway')
    orders[order_id] = {
        'order_id': order_id,
        'username': username,
        'product_name': f'通行卡密-{card_type}',
        'product_price': final_price,
        'product_id': 'gateway_card',
        'product_type': 'gateway',
        'product_number': product_number,
        'payment_method': 'points',
        'status': 'pending',
        'created_at': int(time.time() * 1000),
        'paid_at': 0,
        'anti_fake_code': generate_anti_fake_code(),
        'quantity': 1,
        'original_price': base_price,
        'applied_coupon_discount': 0,
        'used_coupon_ids': [],
        'points_price': final_price,
        'is_pl_order': False,
        'expires_in': 300000,
        'order_type': 'gateway',
        'gateway_card_type': card_type,
        'gateway_price': final_price,
        'price_multiplier': price_info['multiplier'],
        'effective_points': price_info['effective_points'],
        'discount_amount': price_info['discount_amount'],
        'discount_type': price_info['discount_type']
    }
    save_orders()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'order_id': order_id,
        'redirect_url': f'/pay/{order_id}',
        'message': '订单创建成功',
        'price_info': price_info,
        'responseTime': response_time
    })

@app.route('/api/gateway/check-access', methods=['GET'])
def gateway_check_access():
    start_time = time.time()
    card_key = request.args.get('key', '').strip().upper()

    if not card_key:
        return jsonify({'hasAccess': False, 'error': '请提供卡密'}), 400

    cleanup_expired_gateway_cards()

    for username, card_data in gateway_cards.items():
        if card_data.get('key') == card_key and not card_data.get('used', False):
            expire_at = card_data.get('expire_at', 0)
            current_time = int(time.time() * 1000)
            if expire_at == 0 or current_time <= expire_at:
                response_time = int((time.time() - start_time) * 1000)
                return jsonify({
                    'hasAccess': True,
                    'username': username,
                    'cardType': card_data.get('type', ''),
                    'expireAt': expire_at,
                    'responseTime': response_time
                })

    return jsonify({'hasAccess': False, 'error': '卡密无效或已过期'}), 400

@app.route('/api/gateway/stock', methods=['GET'])
def gateway_stock_api():
    stock = get_gateway_stock_today()
    return jsonify({
        'stock': stock,
        'daily_limits': GATEWAY_STOCK_DAILY
    })

@app.route('/api/order/history', methods=['GET'])
@login_required
def get_order_history():
    username = session['user']['username']
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    reload_if_changed()

    user_orders = []
    for order_id, order in orders.items():
        if order.get('username') == username:
            user_orders.append({
                'order_id': order_id,
                'product_name': order.get('product_name', ''),
                'product_price': order.get('product_price', 0),
                'quantity': order.get('quantity', 1),
                'payment_method': order.get('payment_method', 'points'),
                'status': order.get('status', 'pending'),
                'created_at': order.get('created_at', 0),
                'paid_at': order.get('paid_at', 0),
                'delivered': order.get('delivered', False)
            })

    user_orders.sort(key=lambda x: -x.get('created_at', 0))
    total = len(user_orders)
    start = (page - 1) * per_page
    end = start + per_page

    return jsonify({
        'orders': user_orders[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page if total > 0 else 1
    })

@app.route('/api/fund/status', methods=['GET'])
@login_required
def get_fund_status():
    start_time = time.time()
    username = session['user']['username']
    calculate_fund_interest(username)
    balance = get_user_fund_balance(username)
    total_interest = get_user_fund_total_interest(username)
    today_interest = get_user_fund_today_interest(username)
    user_data = users.get(username, {})
    available_points = user_data.get('totalPoints', 0)
    total_points = get_user_fund_total_points(username)
    effective_points = get_user_effective_points(username)
    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'balance': balance,
        'totalInterest': total_interest,
        'todayInterest': today_interest,
        'availablePoints': available_points,
        'totalPoints': total_points,
        'effectivePoints': effective_points,
        'responseTime': response_time
    })

@app.route('/api/fund/rate', methods=['GET'])
@login_required
def get_fund_rate():
    start_time = time.time()
    rate = get_current_fund_rate()
    today = datetime.now().strftime('%Y-%m-%d')
    next_update = datetime.strptime(today, '%Y-%m-%d') + timedelta(days=1)
    next_update = next_update.replace(hour=0, minute=0, second=0, microsecond=0)
    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'rate': rate,
        'minRate': FUND_MIN_RATE,
        'maxRate': FUND_MAX_RATE,
        'date': today,
        'nextUpdate': int(next_update.timestamp() * 1000),
        'responseTime': response_time
    })

@app.route('/api/fund/deposit', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def fund_deposit_api():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    amount = float(data.get('amount', 0))
    result, error = fund_deposit(username, amount)
    if error:
        return jsonify({'error': error}), 400
    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'balance': result['balance'],
        'responseTime': response_time
    })

@app.route('/api/fund/withdraw', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def fund_withdraw_api():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    amount = float(data.get('amount', 0))
    result, error = fund_withdraw(username, amount)
    if error:
        return jsonify({'error': error}), 400
    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'balance': result['balance'],
        'responseTime': response_time
    })

@app.route('/api/fund/history', methods=['GET'])
@login_required
def get_fund_history():
    start_time = time.time()
    username = session['user']['username']
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    records = []
    for rid, record in fund_history.items():
        if record.get('username') == username:
            records.append({
                'id': rid,
                'type': record.get('type', ''),
                'amount': record.get('amount', 0),
                'order_id': record.get('order_id', ''),
                'reason': record.get('reason', ''),
                'timestamp': record.get('timestamp', 0)
            })
    records.sort(key=lambda x: -x.get('timestamp', 0))
    total = len(records)
    start = (page - 1) * per_page
    end = start + per_page
    response_time = int((time.time() - start_time) * 1000)
    
    for record in records[start:end]:
        if record.get('type') == 'refund':
            record['display_sign'] = '+'
            record['display_type'] = '退款'
        elif record.get('type') == 'deposit':
            record['display_sign'] = '+'
            record['display_type'] = '存入'
        elif record.get('type') == 'interest':
            record['display_sign'] = '+'
            record['display_type'] = '收益'
        elif record.get('type') == 'withdraw':
            record['display_sign'] = '-'
            record['display_type'] = '提取'
        else:
            record['display_sign'] = '+' if record.get('amount', 0) >= 0 else '-'
            record['display_type'] = record.get('type', '')
    
    return jsonify({
        'records': records[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page if total > 0 else 1,
        'responseTime': response_time
    })

@app.route('/api/fund/history/clear', methods=['DELETE'])
@login_required
def clear_fund_history():
    start_time = time.time()
    username = session['user']['username']
    records_to_remove = []
    for rid, record in fund_history.items():
        if record.get('username') == username:
            records_to_remove.append(rid)
    for rid in records_to_remove:
        del fund_history[rid]
    save_fund_history()
    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'deleted': len(records_to_remove),
        'responseTime': response_time
    })

@app.route('/api/fund/nav/status', methods=['GET'])
@login_required
def get_nav_status():
    username = session['user']['username']
    current_nav = get_current_nav()
    today = datetime.now().strftime('%Y-%m-%d')
    
    holdings = nav_holdings.get(username, [])
    holdings_detail = []
    total_shares = 0
    total_profit = 0
    for h in holdings:
        shares = h.get('shares', 0)
        buy_nav = h.get('buy_nav', 0)
        buy_time = h.get('buy_time', 0)
        profit = round(shares * (current_nav - buy_nav), 4)
        total_shares += shares
        total_profit += profit
        holdings_detail.append({
            'shares': shares,
            'buy_nav': buy_nav,
            'buy_time': buy_time,
            'buy_amount': h.get('buy_amount', 0),
            'current_nav': current_nav,
            'profit': profit
        })
    
    market_value = total_shares * current_nav
    avg_cost = 0
    total_cost = 0
    for h in holdings:
        total_cost += h.get('shares', 0) * h.get('buy_nav', 0)
    if total_shares > 0:
        avg_cost = round(total_cost / total_shares, 4)
    
    next_update = datetime.strptime(today, '%Y-%m-%d') + timedelta(days=1)
    next_update = next_update.replace(hour=0, minute=0, second=0, microsecond=0)
    
    return jsonify({
        'current_nav': current_nav,
        'nav_date': int(datetime.strptime(today, '%Y-%m-%d').timestamp() * 1000),
        'total_shares': total_shares,
        'market_value': round(market_value, 2),
        'profit': round(total_profit, 4),
        'avg_cost': avg_cost,
        'holdings': holdings_detail,
        'next_update': int(next_update.timestamp() * 1000)
    })

@app.route('/api/fund/nav/sell-single', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def nav_sell_single_api():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    index = data.get('index', -1)
    shares = float(data.get('shares', 0))
    
    if index < 0:
        return jsonify({'error': '无效的持仓索引'}), 400
    
    holdings = nav_holdings.get(username, [])
    if index >= len(holdings):
        return jsonify({'error': '持仓不存在'}), 400
    
    holding = holdings[index]
    if holding.get('shares', 0) < shares:
        return jsonify({'error': '持有份额不足'}), 400
    
    today_start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    today_end = int(datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999).timestamp() * 1000)
    buy_time = holding.get('buy_time', 0)
    
    if today_start <= buy_time <= today_end:
        return jsonify({
            'error': '申购当天不得进行赎回操作，请于次日00:00后再试',
            'error_code': 'NAV_SELL_SAME_DAY'
        }), 400
    
    current_nav = get_current_nav()
    total_amount = shares * current_nav
    total_cost = shares * holding.get('buy_nav', 0)
    profit = round(total_amount - total_cost, 4)
    
    if shares >= holding.get('shares', 0):
        del holdings[index]
    else:
        holding['shares'] = round(holding['shares'] - shares, 2)
    
    nav_holdings[username] = holdings
    save_nav_holdings()
    
    user_data = users.get(username)
    
    profit_fee = 0
    loss_amount = 0
    user_receive = total_amount
    
    if user_data:
        if profit > 0:
            profit_fee = round(profit * 0.08, 4)
            user_receive = round(total_amount - profit_fee, 4)
            user_data['totalPoints'] = round(user_data['totalPoints'] + user_receive, 2)
            add_system_total_points(profit_fee)
        elif profit < 0:
            loss_amount = abs(profit)
            user_receive = total_amount
            user_data['totalPoints'] = round(user_data['totalPoints'] + total_amount, 2)
            add_system_total_points(loss_amount)
        else:
            user_receive = total_amount
            user_data['totalPoints'] = round(user_data['totalPoints'] + total_amount, 2)
        save_users()
    
    record_id = f"nav_{int(time.time()*1000)}_{random.randint(1000,9999)}"
    nav_history[record_id] = {
        'id': record_id,
        'username': username,
        'type': 'sell_nav',
        'shares': shares,
        'nav': current_nav,
        'amount': total_amount,
        'profit': profit,
        'profit_fee': profit_fee,
        'loss_amount': loss_amount,
        'user_receive': user_receive,
        'timestamp': int(time.time() * 1000)
    }
    save_nav_history()
    
    response_time = int((time.time() - start_time) * 1000)
    
    if profit > 0:
        msg = f'赎回成功！获得 {user_receive:.2f} 积分（收益 {profit:.2f}，其中8%即 {profit_fee:.2f} 积分已归入系统池）'
    elif profit < 0:
        msg = f'赎回成功！获得 {user_receive:.2f} 积分（亏损 {loss_amount:.2f}，已全额归入系统池）'
    else:
        msg = f'赎回成功！获得 {user_receive:.2f} 积分（持平）'
    
    return jsonify({
        'success': True,
        'amount': total_amount,
        'user_receive': user_receive,
        'shares': shares,
        'nav': current_nav,
        'profit': profit,
        'profit_fee': profit_fee,
        'loss_amount': loss_amount,
        'message': msg,
        'responseTime': response_time
    })

@app.route('/api/fund/nav/buy', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def nav_buy_api():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    amount = float(data.get('amount', 0))
    result, error = nav_buy(username, amount)
    if error:
        return jsonify({'error': error}), 400
    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'shares': result['shares'],
        'nav': result['nav'],
        'amount': result['amount'],
        'responseTime': response_time
    })

@app.route('/api/fund/nav/sell', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def nav_sell_api():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    shares = float(data.get('shares', 0))
    result, error = nav_sell(username, shares)
    if error:
        if '申购当天不得进行赎回操作' in error:
            return jsonify({
                'error': error,
                'error_code': 'NAV_SELL_SAME_DAY',
                'message': '您今天有申购记录，根据规则申购当天不得进行赎回操作，请于次日00:00后再试'
            }), 400
        return jsonify({'error': error}), 400
    response_time = int((time.time() - start_time) * 1000)
    
    message = f'赎回成功！获得 {result["user_receive"]:.2f} 积分'
    if result['profit'] > 0:
        message += f'（收益 {result["profit"]:.2f}，其中8%即 {result["profit_fee"]:.2f} 积分已归入系统池）'
    elif result['profit'] < 0:
        message += f'（亏损 {result["loss_amount"]:.2f}，已全额归入系统池）'
    
    return jsonify({
        'success': True,
        'amount': result['amount'],
        'shares': result['shares'],
        'nav': result['nav'],
        'profit': result['profit'],
        'profit_fee': result.get('profit_fee', 0),
        'loss_amount': result.get('loss_amount', 0),
        'user_receive': result['user_receive'],
        'message': message,
        'responseTime': response_time
    })

@app.route('/api/fund/nav/history', methods=['GET'])
@login_required
def get_nav_history():
    username = session['user']['username']
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    records = []
    for rid, record in nav_history.items():
        if record.get('username') == username:
            records.append({
                'id': rid,
                'type': record.get('type', ''),
                'shares': record.get('shares', 0),
                'nav': record.get('nav', 0),
                'amount': record.get('amount', 0),
                'profit': record.get('profit', 0),
                'timestamp': record.get('timestamp', 0)
            })
    records.sort(key=lambda x: -x.get('timestamp', 0))
    total = len(records)
    start = (page - 1) * per_page
    end = start + per_page
    return jsonify({
        'records': records[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page if total > 0 else 1
    })

@app.route('/api/order/qr/generate', methods=['POST'])
@csrf_protect
@login_required
def generate_qr_token_api():
    data = request.get_json()
    order_id = data.get('order_id', '')
    product_number = data.get('product_number', '')
    
    if not order_id:
        return jsonify({'error': '缺少订单号'}), 400
    
    order = orders.get(order_id)
    if not order:
        return jsonify({'error': '订单不存在'}), 404
    
    username = session['user']['username']
    if order.get('username') != username and order.get('owner') != username:
        return jsonify({'error': '无权操作此订单'}), 403
    
    token, timestamp = generate_qr_token(order_id, product_number or order.get('product_number', ''))
    
    return jsonify({
        'token': token,
        'timestamp': timestamp,
        'expires_in': 14400
    })

@app.route('/api/order/qr/<token>', methods=['GET'])
def qr_order_redirect(token):
    try:
        order_id, product_number, timestamp, error = decode_qr_token(token)
        if error:
            return jsonify({'valid': False, 'error': f'无效的二维码: {error}'}), 400

        current_time = int(time.time())
        if current_time - timestamp > 14400:
            return jsonify({'valid': False, 'error': '二维码已过期（超过4小时）'}), 400

        order = orders.get(order_id)
        if not order:
            return jsonify({'valid': False, 'error': '订单不存在'}), 404

        product_name = order.get('product_name', '未知商品')
        is_daifu = order.get('is_daifu', False)

        if is_daifu:
            owner = order.get('owner', order.get('username'))
            daifu_status = order.get('daifu_status', 'waiting_pay')
            return jsonify({
                'valid': True,
                'order_id': order_id,
                'product_number': product_number,
                'product_name': product_name,
                'status': order.get('status', 'pending'),
                'redirect_url': f'/pay/{order_id}',
                'is_daifu': True,
                'owner': owner,
                'daifu_status': daifu_status
            })

        if order.get('status') == 'paid':
            return jsonify({
                'valid': True,
                'order_id': order_id,
                'product_number': product_number,
                'product_name': product_name,
                'status': 'paid',
                'redirect_url': f'/pay/{order_id}'
            })

        if order.get('status') == 'pending':
            created_at = order.get('created_at', 0)
            current_time_ms = int(time.time() * 1000)
            if current_time_ms - created_at > 300000:
                return jsonify({
                    'valid': False,
                    'error': '订单已过期（超过5分钟未支付）',
                    'status': 'expired',
                    'order_id': order_id,
                    'product_name': product_name
                }), 400

        return jsonify({
            'valid': True,
            'order_id': order_id,
            'product_number': product_number,
            'product_name': product_name,
            'status': order.get('status', 'pending'),
            'redirect_url': f'/pay/{order_id}'
        })
    except Exception as e:
        log.error(f"QR order redirect error: {e}")
        return jsonify({'valid': False, 'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/order/<order_id>/refund-check', methods=['GET'])
@login_required
def refund_check(order_id):
    username = session['user']['username']
    
    if order_id not in orders:
        return jsonify({'error': '订单不存在'}), 400
    
    order = orders[order_id]
    
    if order.get('username') != username:
        return jsonify({'error': '无权操作此订单'}), 403
    
    if order.get('status') != 'paid':
        return jsonify({'can_refund': False, 'reason': '该订单状态不支持退款'}), 200
    
    if order.get('refunded', False):
        return jsonify({'can_refund': False, 'reason': '该订单已退款'}), 200
    
    product_type = order.get('product_type', '')
    
    if product_type == 'pl_transfer':
        return jsonify({'can_refund': False, 'reason': '转账订单禁止退款'}), 200
    
    if order.get('is_daifu', False):
        return jsonify({'can_refund': False, 'reason': '代付订单禁止退款'}), 200
    
    delivered_codes = order.get('delivered_codes', [])
    payment_method = order.get('payment_method', 'points')
    product_price = order.get('product_price', 0)
    final_price = order.get('final_price', product_price)
    
    is_pl_payment = payment_method == 'pl'
    current_rate = get_current_pl_rate()
    
    if is_pl_payment:
        points_price = round(final_price / current_rate, 2) if current_rate > 0 else final_price
    else:
        points_price = final_price
    
    mail_attachments_to_remove = []
    for aid, attachment in mail_attachments.items():
        if attachment.get('username') != username:
            continue
        if attachment.get('order_id') == order_id:
            mail_attachments_to_remove.append(aid)
        elif attachment.get('source') == 'mall_purchase' or attachment.get('source') == 'daifu_purchase':
            code = attachment.get('code', '')
            if code and code in delivered_codes:
                mail_attachments_to_remove.append(aid)
    
    if mail_attachments_to_remove:
        return jsonify({
            'can_refund': False,
            'reason': '该订单的卡密尚未从邮箱领取，请先领取卡密后再申请退款',
            'has_unclaimed': True,
            'unclaimed_count': len(mail_attachments_to_remove)
        }), 200
    
    refund_amount = 0
    refund_points = 0
    reason = ''
    detail = ''
    
    if product_type in ['point', 'premium_point', 'reset', 'boost', 'special_point', 'makeup', 'gamblers', 'cancellation', 'box', 'plcard', 'premium_boost']:
        if not delivered_codes:
            refund_amount = final_price
            refund_points = points_price
            if is_pl_payment:
                reason = f'未发货，全额退款 (PL支付，汇率 {current_rate:.4f}，折合 {refund_points:.2f} 积分)'
            else:
                reason = '未发货，全额退款'
        else:
            used_count = 0
            for code in delivered_codes:
                status = get_card_usage_status(code, product_type)
                if status == 'used':
                    used_count += 1
            
            total_codes = len(delivered_codes)
            
            if used_count == 0:
                refund_amount = final_price
                refund_points = points_price
                if is_pl_payment:
                    reason = f'所有卡密({total_codes}张)未使用，全额退款 (PL支付，汇率 {current_rate:.4f}，折合 {refund_points:.2f} 积分)'
                else:
                    reason = f'所有卡密({total_codes}张)未使用，全额退款'
            elif used_count == total_codes:
                refund_amount = round(final_price * 0.2, 2)
                refund_points = round(points_price * 0.2, 2)
                if is_pl_payment:
                    reason = f'所有卡密({total_codes}张)已使用，退款20% (PL支付，折合 {refund_points:.2f} 积分)'
                else:
                    reason = f'所有卡密({total_codes}张)已使用，退款20%'
            else:
                unused_count = total_codes - used_count
                per_code_price = final_price / total_codes
                per_code_points = points_price / total_codes
                unused_refund = per_code_price * unused_count
                used_refund = per_code_price * used_count * 0.2
                unused_points_refund = per_code_points * unused_count
                used_points_refund = per_code_points * used_count * 0.2
                refund_amount = round(unused_refund + used_refund, 2)
                refund_points = round(unused_points_refund + used_points_refund, 2)
                if is_pl_payment:
                    reason = f'卡密 {unused_count}张未使用全额退款，{used_count}张已使用退款20% (PL支付，折合 {refund_points:.2f} 积分)'
                    detail = f'未使用: {unused_count}张, 已使用: {used_count}张, 汇率: {current_rate:.4f}'
                else:
                    reason = f'卡密 {unused_count}张未使用全额退款，{used_count}张已使用退款20%'
                    detail = f'未使用: {unused_count}张, 已使用: {used_count}张'
    
    elif product_type == 'gateway':
        card = gateway_cards.get(username, {})
        card_type = card.get('type', '')
        card_expire = card.get('expire_at', 0)
        current_time = int(time.time() * 1000)
        
        if not card:
            return jsonify({'can_refund': False, 'reason': '通行卡密不存在'}), 200
        
        if card_expire > 0 and current_time > card_expire:
            return jsonify({'can_refund': False, 'reason': '通行卡密已过期，无法退款'}), 200
        
        if card_type == 'hour':
            refund_amount = final_price
            refund_points = points_price
            if is_pl_payment:
                reason = f'小时卡全额退款 (PL支付，折合 {refund_points:.2f} 积分)'
            else:
                reason = '小时卡全额退款'
        elif card_type == 'day':
            if card_expire > 0:
                total_ms = card_expire - card.get('created_at', 0)
                remain_ms = max(0, card_expire - current_time)
                if total_ms > 0:
                    refund_amount = round(final_price * remain_ms / total_ms, 2)
                    refund_points = round(points_price * remain_ms / total_ms, 2)
                else:
                    refund_amount = final_price
                    refund_points = points_price
                if is_pl_payment:
                    reason = f'天卡按剩余时间退款 {refund_amount:.4f} PL (折合 {refund_points:.2f} 积分)'
                    detail = f'剩余时间比例: {(remain_ms / total_ms * 100):.0f}%, 汇率: {current_rate:.4f}'
                else:
                    reason = f'天卡按剩余时间退款 {refund_amount:.2f}'
                    detail = f'剩余时间比例: {(remain_ms / total_ms * 100):.0f}%'
            else:
                refund_amount = final_price
                refund_points = points_price
                if is_pl_payment:
                    reason = f'天卡全额退款 (PL支付，折合 {refund_points:.2f} 积分)'
                else:
                    reason = '天卡全额退款'
        elif card_type == 'week':
            if card_expire > 0:
                total_ms = card_expire - card.get('created_at', 0)
                remain_ms = max(0, card_expire - current_time)
                if total_ms > 0:
                    refund_amount = round(final_price * remain_ms / total_ms, 2)
                    refund_points = round(points_price * remain_ms / total_ms, 2)
                else:
                    refund_amount = final_price
                    refund_points = points_price
                if is_pl_payment:
                    reason = f'周卡按剩余时间退款 {refund_amount:.4f} PL (折合 {refund_points:.2f} 积分)'
                    detail = f'剩余时间比例: {(remain_ms / total_ms * 100):.0f}%, 汇率: {current_rate:.4f}'
                else:
                    reason = f'周卡按剩余时间退款 {refund_amount:.2f}'
                    detail = f'剩余时间比例: {(remain_ms / total_ms * 100):.0f}%'
            else:
                refund_amount = final_price
                refund_points = points_price
                if is_pl_payment:
                    reason = f'周卡全额退款 (PL支付，折合 {refund_points:.2f} 积分)'
                else:
                    reason = '周卡全额退款'
        elif card_type == 'permanent':
            refund_amount = round(final_price * 0.6, 2)
            refund_points = round(points_price * 0.6, 2)
            if is_pl_payment:
                reason = f'永久卡退款60% (PL支付，折合 {refund_points:.2f} 积分)'
            else:
                reason = '永久卡退款60%'
        else:
            refund_amount = final_price
            refund_points = points_price
            if is_pl_payment:
                reason = f'未知类型，全额退款 (PL支付，折合 {refund_points:.2f} 积分)'
            else:
                reason = '未知类型，全额退款'
    
    else:
        refund_amount = final_price
        refund_points = points_price
        if is_pl_payment:
            reason = f'普通订单全额退款 (PL支付，折合 {refund_points:.2f} 积分)'
        else:
            reason = '普通订单全额退款'
    
    if refund_points <= 0:
        return jsonify({'can_refund': False, 'reason': '退款金额为0，无法退款'}), 200
    
    risk_passed, risk_message, risk_score, risk_details = perform_refund_risk_check(username, refund_points)
    if not risk_passed:
        return jsonify({
            'can_refund': False,
            'reason': risk_message,
            'refund_amount': round(refund_amount, 2),
            'refund_points': round(refund_points, 2),
            'order_status': order.get('status'),
            'product_type': product_type,
            'payment_method': payment_method,
            'is_pl_payment': is_pl_payment,
            'rate_used': current_rate if is_pl_payment else None,
            'product_name': order.get('product_name', ''),
            'product_price': order.get('product_price', 0),
            'created_at': order.get('created_at', 0),
            'paid_at': order.get('paid_at', 0),
            'anti_fake_code': order.get('anti_fake_code', ''),
            'is_refunded': order.get('refunded', False),
            'risk_check_failed': True,
            'risk_message': risk_message,
            'risk_score': risk_score,
            'risk_details': risk_details
        }), 200
    
    return jsonify({
        'can_refund': True,
        'refund_amount': round(refund_amount, 2),
        'refund_points': round(refund_points, 2),
        'reason': reason,
        'detail': detail,
        'order_status': order.get('status'),
        'product_type': product_type,
        'payment_method': payment_method,
        'is_pl_payment': is_pl_payment,
        'rate_used': current_rate if is_pl_payment else None,
        'product_name': order.get('product_name', ''),
        'product_price': order.get('product_price', 0),
        'created_at': order.get('created_at', 0),
        'paid_at': order.get('paid_at', 0),
        'anti_fake_code': order.get('anti_fake_code', ''),
        'is_refunded': order.get('refunded', False),
        'risk_check_passed': True,
        'risk_message': risk_message if risk_message else '风控审查通过',
        'risk_score': risk_score,
        'risk_details': risk_details
    })


@app.route('/api/order/<order_id>/refund-self', methods=['POST'])
@csrf_protect
@limiter.limit(RATE_LIMITS['refund'])
@login_required
@identity_required
def refund_self(order_id):
    username = session['user']['username']
    data = request.get_json() or {}
    is_gateway_refund = data.get('is_gateway_refund', False)
    card_key = data.get('card_key', '')
    
    if is_gateway_refund and order_id.startswith('GATEWAY_'):
        if not card_key:
            return jsonify({'error': '请提供通行卡密'}), 400
        
        found_username = None
        card_data = None
        for u, card in gateway_cards.items():
            if card.get('key') == card_key and not card.get('used', False):
                found_username = u
                card_data = card
                break
        
        if not card_data:
            return jsonify({'error': '通行卡密不存在或已失效'}), 400
        
        if found_username != username:
            return jsonify({'error': '该卡密不属于当前账号'}), 403
        
        card_type = card_data.get('type', '')
        card_price = card_data.get('price', 0)
        card_expire = card_data.get('expire_at', 0)
        created_at = card_data.get('created_at', 0)
        current_time = int(time.time() * 1000)
        
        if card_expire > 0 and current_time > card_expire:
            return jsonify({'error': '通行卡密已过期，无法退款'}), 400
        
        original_order_id = None
        original_order = None
        for oid, order in orders.items():
            if order.get('username') == username and order.get('product_type') == 'gateway':
                delivered_codes = order.get('delivered_codes', [])
                if delivered_codes and card_key in delivered_codes:
                    original_order_id = oid
                    original_order = order
                    break
        
        if original_order_id and original_order:
            if original_order.get('refunded', False):
                return jsonify({'error': '该卡密对应的订单已退款'}), 400
            
            if original_order.get('status') != 'paid':
                return jsonify({'error': '订单状态异常，无法退款'}), 400
            
            refund_amount = 0
            refund_points = 0
            reason = ''
            payment_method = original_order.get('payment_method', 'points')
            is_pl_payment = payment_method == 'pl'
            current_rate = get_current_pl_rate()
            
            if is_pl_payment:
                points_price = round(card_price / current_rate, 2) if current_rate > 0 else card_price
            else:
                points_price = card_price
            
            if card_type == 'hour':
                refund_amount = card_price
                refund_points = points_price
                if is_pl_payment:
                    reason = f'小时卡全额退款 (PL支付，汇率 {current_rate:.4f}，折合 {refund_points:.2f} 积分)'
                else:
                    reason = '小时卡全额退款'
            elif card_type == 'day':
                if card_expire > 0:
                    total_ms = card_expire - created_at
                    remain_ms = max(0, card_expire - current_time)
                    if total_ms > 0:
                        refund_amount = round(card_price * remain_ms / total_ms, 2)
                        refund_points = round(points_price * remain_ms / total_ms, 2)
                    else:
                        refund_amount = card_price
                        refund_points = points_price
                    if is_pl_payment:
                        reason = f'天卡按剩余时间退款 {refund_amount:.4f} PL (折合 {refund_points:.2f} 积分)'
                    else:
                        reason = f'天卡按剩余时间退款 {refund_amount:.2f}'
                else:
                    refund_amount = card_price
                    refund_points = points_price
                    if is_pl_payment:
                        reason = f'天卡全额退款 (PL支付，折合 {refund_points:.2f} 积分)'
                    else:
                        reason = '天卡全额退款'
            elif card_type == 'week':
                if card_expire > 0:
                    total_ms = card_expire - created_at
                    remain_ms = max(0, card_expire - current_time)
                    if total_ms > 0:
                        refund_amount = round(card_price * remain_ms / total_ms, 2)
                        refund_points = round(points_price * remain_ms / total_ms, 2)
                    else:
                        refund_amount = card_price
                        refund_points = points_price
                    if is_pl_payment:
                        reason = f'周卡按剩余时间退款 {refund_amount:.4f} PL (折合 {refund_points:.2f} 积分)'
                    else:
                        reason = f'周卡按剩余时间退款 {refund_amount:.2f}'
                else:
                    refund_amount = card_price
                    refund_points = points_price
                    if is_pl_payment:
                        reason = f'周卡全额退款 (PL支付，折合 {refund_points:.2f} 积分)'
                    else:
                        reason = '周卡全额退款'
            elif card_type == 'permanent':
                refund_amount = round(card_price * 0.6, 2)
                refund_points = round(points_price * 0.6, 2)
                if is_pl_payment:
                    reason = f'永久卡退款60% (PL支付，折合 {refund_points:.2f} 积分)'
                else:
                    reason = '永久卡退款60%'
            else:
                refund_amount = card_price
                refund_points = points_price
                if is_pl_payment:
                    reason = f'未知类型，全额退款 (PL支付，折合 {refund_points:.2f} 积分)'
                else:
                    reason = '未知类型，全额退款'
            
            if refund_points <= 0:
                return jsonify({'error': '退款金额为0，无法退款'}), 400

            risk_passed, risk_message, risk_score, risk_details = perform_refund_risk_check(username, refund_points)
            if not risk_passed:
                return jsonify({'error': risk_message}), 403
            
            del gateway_cards[username]
            save_gateway_cards()
            
            if username not in fund_data:
                fund_data[username] = {'balance': 0, 'total_interest': 0, 'today_interest': {}, 'last_interest_date': ''}
            
            old_balance = fund_data[username]['balance']
            fund_data[username]['balance'] = round(fund_data[username]['balance'] + refund_points, 2)
            save_fund_data()
            
            refund_timestamp = int(time.time() * 1000)
            fund_history_id = f"fund_refund_gateway_{refund_timestamp}_{random.randint(1000,9999)}"
            fund_history[fund_history_id] = {
                'id': fund_history_id,
                'username': username,
                'type': 'refund',
                'order_id': original_order_id,
                'amount': round(refund_points, 2),
                'reason': reason,
                'timestamp': refund_timestamp
            }
            save_fund_history()
            
            original_order['refunded'] = True
            original_order['refunded_at'] = refund_timestamp
            original_order['status'] = 'refunded'
            original_order['refund_amount'] = refund_amount
            original_order['refund_points'] = refund_points
            original_order['refund_reason'] = reason
            save_orders()
            
            return jsonify({
                'success': True,
                'message': f'退款成功！退还 {refund_points:.2f} 积分已存入理财账户',
                'refund_amount': refund_amount,
                'refund_points': refund_points,
                'reason': reason,
                'old_balance': old_balance,
                'new_balance': fund_data[username]['balance'],
                'order_refunded': True,
                'order_id': original_order_id,
                'is_pl_payment': is_pl_payment,
                'rate_used': current_rate if is_pl_payment else None,
                'risk_score': risk_score,
                'risk_details': risk_details,
                'risk_passed': risk_passed,
                'risk_message': risk_message
            })
        
        refund_amount = 0
        refund_points = 0
        reason = ''
        is_pl_payment = False
        current_rate = get_current_pl_rate()
        points_price = card_price
        
        if card_type == 'hour':
            refund_amount = card_price
            refund_points = points_price
            reason = '小时卡全额退款 (无对应订单)'
        elif card_type == 'day':
            if card_expire > 0:
                total_ms = card_expire - created_at
                remain_ms = max(0, card_expire - current_time)
                if total_ms > 0:
                    refund_amount = round(card_price * remain_ms / total_ms, 2)
                    refund_points = round(points_price * remain_ms / total_ms, 2)
                else:
                    refund_amount = card_price
                    refund_points = points_price
                reason = f'天卡按剩余时间退款 {refund_amount:.2f} (无对应订单)'
            else:
                refund_amount = card_price
                refund_points = points_price
                reason = '天卡全额退款 (无对应订单)'
        elif card_type == 'week':
            if card_expire > 0:
                total_ms = card_expire - created_at
                remain_ms = max(0, card_expire - current_time)
                if total_ms > 0:
                    refund_amount = round(card_price * remain_ms / total_ms, 2)
                    refund_points = round(points_price * remain_ms / total_ms, 2)
                else:
                    refund_amount = card_price
                    refund_points = points_price
                reason = f'周卡按剩余时间退款 {refund_amount:.2f} (无对应订单)'
            else:
                refund_amount = card_price
                refund_points = points_price
                reason = '周卡全额退款 (无对应订单)'
        elif card_type == 'permanent':
            refund_amount = round(card_price * 0.6, 2)
            refund_points = round(points_price * 0.6, 2)
            reason = '永久卡退款60% (无对应订单)'
        else:
            refund_amount = card_price
            refund_points = points_price
            reason = '未知类型，全额退款 (无对应订单)'
        
        if refund_points <= 0:
            return jsonify({'error': '退款金额为0，无法退款'}), 400
        
        risk_passed, risk_message, risk_score, risk_details = perform_refund_risk_check(username, refund_points)
        if not risk_passed:
            return jsonify({'error': risk_message}), 403
        
        del gateway_cards[username]
        save_gateway_cards()
        
        if username not in fund_data:
            fund_data[username] = {'balance': 0, 'total_interest': 0, 'today_interest': {}, 'last_interest_date': ''}
        
        old_balance = fund_data[username]['balance']
        fund_data[username]['balance'] = round(fund_data[username]['balance'] + refund_points, 2)
        save_fund_data()
        
        refund_timestamp = int(time.time() * 1000)
        fund_history_id = f"fund_refund_gateway_no_order_{refund_timestamp}_{random.randint(1000,9999)}"
        fund_history[fund_history_id] = {
            'id': fund_history_id,
            'username': username,
            'type': 'refund',
            'order_id': card_key,
            'amount': round(refund_points, 2),
            'reason': reason,
            'timestamp': refund_timestamp
        }
        save_fund_history()
        
        return jsonify({
            'success': True,
            'message': f'退款成功！退还 {refund_points:.2f} 积分已存入理财账户',
            'refund_amount': refund_amount,
            'refund_points': refund_points,
            'reason': reason,
            'old_balance': old_balance,
            'new_balance': fund_data[username]['balance'],
            'order_refunded': False,
            'order_id': None,
            'is_pl_payment': False,
            'rate_used': None,
            'risk_score': risk_score,
            'risk_details': risk_details,
            'risk_passed': risk_passed,
            'risk_message': risk_message
        })
    
    if order_id not in orders:
        return jsonify({'error': '订单不存在'}), 400
    
    order = orders[order_id]
    
    if order.get('username') != username:
        return jsonify({'error': '无权操作此订单'}), 403
    
    if order.get('status') != 'paid':
        return jsonify({'error': '该订单状态不支持退款'}), 400
    
    if order.get('refunded', False):
        return jsonify({'error': '该订单已退款'}), 400
    
    product_type = order.get('product_type', '')
    
    if product_type == 'pl_transfer':
        return jsonify({'error': '转账订单禁止退款'}), 400
    
    if order.get('is_daifu', False):
        return jsonify({'error': '代付订单禁止退款'}), 400
    
    delivered_codes = order.get('delivered_codes', [])
    payment_method = order.get('payment_method', 'points')
    product_price = order.get('product_price', 0)
    final_price = order.get('final_price', product_price)
    
    is_pl_payment = payment_method == 'pl'
    current_rate = get_current_pl_rate()
    
    if is_pl_payment:
        points_price = round(final_price / current_rate, 2) if current_rate > 0 else final_price
    else:
        points_price = final_price
    
    mail_attachments_to_remove = []
    for aid, attachment in mail_attachments.items():
        if attachment.get('username') != username:
            continue
        if attachment.get('order_id') == order_id:
            mail_attachments_to_remove.append(aid)
        elif attachment.get('source') == 'mall_purchase' or attachment.get('source') == 'daifu_purchase':
            code = attachment.get('code', '')
            if code and code in delivered_codes:
                mail_attachments_to_remove.append(aid)
    
    for aid in mail_attachments_to_remove:
        if aid in mail_attachments:
            del mail_attachments[aid]
    if mail_attachments_to_remove:
        save_mail_attachments()
    
    refund_amount = 0
    refund_points = 0
    reason = ''
    
    if product_type in ['point', 'premium_point', 'reset', 'boost', 'special_point', 'makeup', 'gamblers', 'cancellation', 'box', 'plcard', 'premium_boost']:
        if not delivered_codes:
            refund_amount = final_price
            refund_points = points_price
            if is_pl_payment:
                reason = f'未发货，全额退款 (PL支付，汇率 {current_rate:.4f}，折合 {refund_points:.2f} 积分)'
            else:
                reason = '未发货，全额退款'
        else:
            used_count = 0
            for code in delivered_codes:
                status = get_card_usage_status(code, product_type)
                if status == 'used':
                    used_count += 1
            
            total_codes = len(delivered_codes)
            
            if used_count == 0:
                refund_amount = final_price
                refund_points = points_price
                if is_pl_payment:
                    reason = f'所有卡密({total_codes}张)未使用，全额退款 (PL支付，汇率 {current_rate:.4f}，折合 {refund_points:.2f} 积分)'
                else:
                    reason = f'所有卡密({total_codes}张)未使用，全额退款'
            elif used_count == total_codes:
                refund_amount = round(final_price * 0.2, 2)
                refund_points = round(points_price * 0.2, 2)
                if is_pl_payment:
                    reason = f'所有卡密({total_codes}张)已使用，退款20% (PL支付，折合 {refund_points:.2f} 积分)'
                else:
                    reason = f'所有卡密({total_codes}张)已使用，退款20%'
            else:
                unused_count = total_codes - used_count
                per_code_price = final_price / total_codes
                per_code_points = points_price / total_codes
                unused_refund = per_code_price * unused_count
                used_refund = per_code_price * used_count * 0.2
                unused_points_refund = per_code_points * unused_count
                used_points_refund = per_code_points * used_count * 0.2
                refund_amount = round(unused_refund + used_refund, 2)
                refund_points = round(unused_points_refund + used_points_refund, 2)
                if is_pl_payment:
                    reason = f'卡密 {unused_count}张未使用全额退款，{used_count}张已使用退款20% (PL支付，折合 {refund_points:.2f} 积分)'
                else:
                    reason = f'卡密 {unused_count}张未使用全额退款，{used_count}张已使用退款20%'
    
    elif product_type == 'gateway':
        card = gateway_cards.get(username, {})
        card_type = card.get('type', '')
        card_expire = card.get('expire_at', 0)
        current_time = int(time.time() * 1000)
        
        if not card:
            return jsonify({'error': '通行卡密不存在'}), 400
        
        if card_expire > 0 and current_time > card_expire:
            return jsonify({'error': '通行卡密已过期，无法退款'}), 400
        
        if card_type == 'hour':
            refund_amount = final_price
            refund_points = points_price
            if is_pl_payment:
                reason = f'小时卡全额退款 (PL支付，折合 {refund_points:.2f} 积分)'
            else:
                reason = '小时卡全额退款'
        elif card_type == 'day':
            if card_expire > 0:
                total_ms = card_expire - card.get('created_at', 0)
                remain_ms = max(0, card_expire - current_time)
                if total_ms > 0:
                    refund_amount = round(final_price * remain_ms / total_ms, 2)
                    refund_points = round(points_price * remain_ms / total_ms, 2)
                else:
                    refund_amount = final_price
                    refund_points = points_price
                if is_pl_payment:
                    reason = f'天卡按剩余时间退款 {refund_amount:.4f} PL (折合 {refund_points:.2f} 积分)'
                else:
                    reason = f'天卡按剩余时间退款 {refund_amount:.2f}'
            else:
                refund_amount = final_price
                refund_points = points_price
                if is_pl_payment:
                    reason = f'天卡全额退款 (PL支付，折合 {refund_points:.2f} 积分)'
                else:
                    reason = '天卡全额退款'
        elif card_type == 'week':
            if card_expire > 0:
                total_ms = card_expire - card.get('created_at', 0)
                remain_ms = max(0, card_expire - current_time)
                if total_ms > 0:
                    refund_amount = round(final_price * remain_ms / total_ms, 2)
                    refund_points = round(points_price * remain_ms / total_ms, 2)
                else:
                    refund_amount = final_price
                    refund_points = points_price
                if is_pl_payment:
                    reason = f'周卡按剩余时间退款 {refund_amount:.4f} PL (折合 {refund_points:.2f} 积分)'
                else:
                    reason = f'周卡按剩余时间退款 {refund_amount:.2f}'
            else:
                refund_amount = final_price
                refund_points = points_price
                if is_pl_payment:
                    reason = f'周卡全额退款 (PL支付，折合 {refund_points:.2f} 积分)'
                else:
                    reason = '周卡全额退款'
        elif card_type == 'permanent':
            refund_amount = round(final_price * 0.6, 2)
            refund_points = round(points_price * 0.6, 2)
            if is_pl_payment:
                reason = f'永久卡退款60% (PL支付，折合 {refund_points:.2f} 积分)'
            else:
                reason = '永久卡退款60%'
        else:
            refund_amount = final_price
            refund_points = points_price
            if is_pl_payment:
                reason = f'未知类型，全额退款 (PL支付，折合 {refund_points:.2f} 积分)'
            else:
                reason = '未知类型，全额退款'
        
        if username in gateway_cards:
            del gateway_cards[username]
            save_gateway_cards()
    
    else:
        refund_amount = final_price
        refund_points = points_price
        if is_pl_payment:
            reason = f'普通订单全额退款 (PL支付，折合 {refund_points:.2f} 积分)'
        else:
            reason = '普通订单全额退款'
    
    if refund_points <= 0:
        return jsonify({'error': '退款金额为0，无法退款'}), 400

    risk_passed, risk_message, risk_score, risk_details = perform_refund_risk_check(username, refund_points)
    if not risk_passed:
        return jsonify({'error': risk_message}), 403
    
    if order.get('delivered', False):
        code_type_map = {
            'point': (point_codes, save_point_codes),
            'premium_point': (premium_point_codes, save_premium_point_codes),
            'reset': (reset_codes, save_reset_codes),
            'boost': (boost_codes, save_boost_codes),
            'special_point': (special_point_codes, save_special_point_codes),
            'makeup': (makeup_codes, save_makeup_codes),
            'gamblers': (gamblers_codes, save_gamblers_codes),
            'cancellation': (cancellation_codes, save_cancellation_codes),
            'box': (box_codes, save_box_codes),
            'plcard': (plcard_codes, save_plcard_codes),
            'premium_boost': (premium_boost_codes, save_premium_boost_codes)
        }
        if product_type in code_type_map:
            codes, save_func = code_type_map[product_type]
            for code in delivered_codes:
                if code in codes:
                    if not codes[code].get('used', False):
                        del codes[code]
            save_func()
    
    if username not in fund_data:
        fund_data[username] = {'balance': 0, 'total_interest': 0, 'today_interest': {}, 'last_interest_date': ''}
    
    old_balance = fund_data[username]['balance']
    fund_data[username]['balance'] = round(fund_data[username]['balance'] + refund_points, 2)
    save_fund_data()
    
    refund_timestamp = int(time.time() * 1000)
    fund_history_id = f"fund_refund_{refund_timestamp}_{random.randint(1000,9999)}"
    fund_history[fund_history_id] = {
        'id': fund_history_id,
        'username': username,
        'type': 'refund',
        'order_id': order_id,
        'amount': round(refund_points, 2),
        'reason': reason,
        'timestamp': refund_timestamp
    }
    save_fund_history()
    
    order['refunded'] = True
    order['refunded_at'] = refund_timestamp
    order['status'] = 'refunded'
    order['refund_amount'] = refund_amount
    order['refund_points'] = refund_points
    order['refund_reason'] = reason
    save_orders()
    
    return jsonify({
        'success': True,
        'message': f'退款成功！退还 {refund_points:.2f} 积分已存入理财账户',
        'refund_amount': refund_amount,
        'refund_points': refund_points,
        'reason': reason,
        'old_balance': old_balance,
        'new_balance': fund_data[username]['balance'],
        'is_pl_payment': is_pl_payment,
        'rate_used': current_rate if is_pl_payment else None,
        'risk_score': risk_score,
        'risk_details': risk_details,
        'risk_passed': risk_passed,
        'risk_message': risk_message
    })

@app.route('/api/order/search', methods=['GET'])
@login_required
def search_order():
    username = session['user']['username']
    keyword = request.args.get('keyword', '').strip()
    
    if not keyword:
        return jsonify({'error': '请输入查询关键词'}), 400
    
    if re.match(r'^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$', keyword):
        for u, card in gateway_cards.items():
            if card.get('key') == keyword and u == username and not card.get('used', False):
                card_type = card.get('type', '')
                card_price = card.get('price', 0)
                card_expire = card.get('expire_at', 0)
                created_at = card.get('created_at', 0)
                current_time = int(time.time() * 1000)
                
                if card_expire > 0 and current_time > card_expire:
                    return jsonify({
                        'type': 'gateway',
                        'exists': True,
                        'can_refund': False,
                        'reason': '通行卡密已过期，无法退款',
                        'card_key': keyword,
                        'card_type': card_type,
                        'card_price': card_price,
                        'created_at': created_at,
                        'expire_at': card_expire,
                        'status': '已过期',
                        'username': username
                    }), 200
                
                original_order_id = None
                original_order = None
                for oid, order in orders.items():
                    if order.get('username') == username and order.get('product_type') == 'gateway':
                        delivered_codes = order.get('delivered_codes', [])
                        if delivered_codes and keyword in delivered_codes:
                            original_order_id = oid
                            original_order = order
                            break
                
                if original_order_id and original_order:
                    if original_order.get('refunded', False):
                        return jsonify({
                            'type': 'gateway',
                            'exists': True,
                            'can_refund': False,
                            'reason': '该卡密对应的订单已退款，请勿重复操作',
                            'card_key': keyword,
                            'card_type': card_type,
                            'card_price': card_price,
                            'created_at': created_at,
                            'expire_at': card_expire,
                            'status': '已退款',
                            'username': username,
                            'order_id': original_order_id,
                            'is_refunded': True
                        }), 200
                
                if card_type == 'hour':
                    refund_amount = card_price
                    reason = '小时卡全额退款'
                elif card_type == 'day':
                    if card_expire > 0:
                        total_ms = card_expire - created_at
                        remain_ms = max(0, card_expire - current_time)
                        if total_ms > 0:
                            refund_amount = round(card_price * remain_ms / total_ms, 2)
                        else:
                            refund_amount = card_price
                        reason = f'天卡按剩余时间退款 {refund_amount:.2f}'
                    else:
                        refund_amount = card_price
                        reason = '天卡全额退款'
                elif card_type == 'week':
                    if card_expire > 0:
                        total_ms = card_expire - created_at
                        remain_ms = max(0, card_expire - current_time)
                        if total_ms > 0:
                            refund_amount = round(card_price * remain_ms / total_ms, 2)
                        else:
                            refund_amount = card_price
                        reason = f'周卡按剩余时间退款 {refund_amount:.2f}'
                    else:
                        refund_amount = card_price
                        reason = '周卡全额退款'
                elif card_type == 'permanent':
                    refund_amount = round(card_price * 0.6, 2)
                    reason = '永久卡退款60%'
                else:
                    refund_amount = card_price
                    reason = '未知类型，全额退款'
                
                virtual_order_id = f'GATEWAY_{keyword.replace("-", "")}'
                
                return jsonify({
                    'type': 'gateway',
                    'exists': True,
                    'can_refund': True,
                    'card_key': keyword,
                    'card_type': card_type,
                    'card_price': card_price,
                    'created_at': created_at,
                    'expire_at': card_expire,
                    'status': '有效',
                    'refund_amount': round(refund_amount, 2),
                    'refund_reason': reason,
                    'username': username,
                    'order_id': virtual_order_id,
                    'is_virtual_order': True,
                    'has_original_order': original_order_id is not None,
                    'original_order_id': original_order_id,
                    'is_refunded': False
                }), 200
        
        return jsonify({'type': 'gateway', 'exists': False, 'message': '通行卡密不存在或已被使用'}), 200
    
    found_orders = []
    for order_id, order in orders.items():
        if order.get('username') != username:
            continue
        
        order_number = order.get('product_number', '')
        anti_fake_code = order.get('anti_fake_code', '')
        
        if keyword == order_id or keyword == order_number or keyword == anti_fake_code:
            found_orders.append({
                'type': 'order',
                'order_id': order_id,
                'username': order.get('username', ''),
                'product_name': order.get('product_name', ''),
                'product_price': order.get('product_price', 0),
                'product_type': order.get('product_type', ''),
                'payment_method': order.get('payment_method', 'points'),
                'status': order.get('status', ''),
                'created_at': order.get('created_at', 0),
                'paid_at': order.get('paid_at', 0),
                'anti_fake_code': anti_fake_code,
                'delivered': order.get('delivered', False),
                'delivered_codes': order.get('delivered_codes', []),
                'refunded': order.get('refunded', False),
                'refund_amount': order.get('refund_amount', 0),
                'refund_reason': order.get('refund_reason', ''),
                'is_daifu': order.get('is_daifu', False),
                'quantity': order.get('quantity', 1),
                'final_price': order.get('final_price', order.get('product_price', 0)),
                'product_number': order_number,
                'owner': order.get('owner', order.get('username', ''))
            })
    
    if not found_orders:
        return jsonify({'type': 'order', 'orders': [], 'message': '未找到匹配订单'}), 200
    
    return jsonify({'type': 'order', 'orders': found_orders}), 200

@app.route('/api/debug/user-data', methods=['GET'])
@login_required
def debug_user_data():
    username = session['user']['username']
    user_data = users.get(username, {})
    return jsonify({
        'username': username,
        'firstAttendanceDate': user_data.get('firstAttendanceDate', ''),
        'lastAttendanceDate': user_data.get('lastAttendanceDate', ''),
        'attendanceTotalDays': user_data.get('attendanceTotalDays', 0),
        'attendanceConsecutiveDays': user_data.get('attendanceConsecutiveDays', 0)
    })

@app.route('/qr/<token>')
def qr_redirect_page(token):
    try:
        return send_from_directory('public', 'qr_redirect.html')
    except Exception as e:
        log.error(f"QR redirect page error: {e}")
        return f'<html><body><h1>二维码跳转</h1><p>正在跳转...</p><script>window.location.href="/gateway.html"</script></body></html>'

@app.route('/api/identity/quick-verify', methods=['POST'])
@csrf_protect
@limiter.limit('3 per minute')
@login_required
def quick_verify_identity():
    username = session['user']['username']
    
    if check_identity_verified(username):
        return jsonify({'error': '您已完成身份认证'}), 400
    
    available = get_available_id_card()
    if not available:
        stats = get_id_cards_stats()
        if stats['total'] == 0:
            return jsonify({'error': '快速认证暂不可用，请手动认证'}), 400
        return jsonify({'error': '所有身份证已使用完毕，请手动认证'}), 400
    
    real_name = available['name']
    id_number = available['id_number']
    key = available['key']
    
    gender_digit = int(id_number[16])
    gender = '男' if gender_digit % 2 == 1 else '女'
    
    age = calculate_age(id_number)
    if age is None or age < 10 or age > 80:
        return jsonify({'error': f'身份证年龄验证失败 (年龄: {age}岁，需10-80岁)'}), 400
    
    id_hash = hash_id_number(id_number)
    id_masked = mask_id_number(id_number)
    
    identity_verifications[username] = {
        'username': username,
        'real_name': real_name,
        'id_number_hash': id_hash,
        'id_number_masked': id_masked,
        'gender': gender,
        'verified': True,
        'verified_at': datetime.now().isoformat(),
        'quick_verify': True,
        'id_card_key': key
    }
    save_identity_verifications()
    
    used_data = load_id_cards_used()
    used_data[key] = True
    save_id_cards_used(used_data)
    
    pl_amount = round(random.uniform(0.5, 3.0), 4)
    update_user_pl_balance(username, pl_amount, 'identity_verification_reward', 'id_verify_quick')
    
    coupon_types = ['full_reduction', 'unconditional', 'product_specific']
    for _ in range(2):
        coupon_type = random.choice(coupon_types)
        if coupon_type == 'full_reduction':
            discount = round(random.uniform(0.5, 10), 1)
            if discount < 0.5:
                discount = 0.5
            threshold = min(max(round(discount * random.uniform(2, 4), 1), discount + 0.5), 12)
            desc = f'满{threshold}减{discount}'
            grant_coupon_to_user(username, coupon_type, discount, threshold, random.randint(24, 168), '', desc)
        elif coupon_type == 'unconditional':
            discount = round(random.uniform(0.3, 7), 1)
            if discount < 0.3:
                discount = 0.3
            desc = f'无门槛减{discount}'
            grant_coupon_to_user(username, coupon_type, discount, 0, random.randint(24, 168), '', desc)
        elif coupon_type == 'product_specific':
            product_ids = ['point_code', 'premium_point_code', 'reset_code', 'boost_code', 'special_point_code', 'makeup_code', 'gamblers_code']
            product_id = random.choice(product_ids)
            price_map = {'point_code': 1.2, 'premium_point_code': 3.5, 'reset_code': 8, 'boost_code': 8.8, 'special_point_code': 20, 'makeup_code': 200, 'gamblers_code': 100}
            base_price = price_map.get(product_id, 0)
            max_discount = base_price * 0.8
            discount = round(random.uniform(0.3, max_discount), 1)
            if discount < 0.3:
                discount = 0.3
            if discount > max_discount:
                discount = max_discount
            product_label = get_product_type_label(product_id)
            desc = f'指定{product_label}减{discount}'
            grant_coupon_to_user(username, coupon_type, discount, 0, random.randint(24, 168), product_id, desc)
    
    stats = get_id_cards_stats()
    
    return jsonify({
        'success': True,
        'message': f'快速认证成功！使用 {real_name} 完成认证，获得{pl_amount}PL和2张随机优惠券',
        'real_name': real_name,
        'id_number_masked': id_masked,
        'pl_reward': pl_amount,
        'stats': stats,
        'all_used': stats['available'] == 0
    })

@app.route('/api/identity/quick-status', methods=['GET'])
@csrf_protect
@login_required
def quick_verify_status():
    username = session['user']['username']
    
    if check_identity_verified(username):
        return jsonify({
            'available': False,
            'reason': 'already_verified',
            'message': '您已完成身份认证'
        })
    
    stats = get_id_cards_stats()
    available = get_available_id_card()
    
    if stats['total'] == 0:
        return jsonify({
            'available': False,
            'reason': 'no_data',
            'message': '暂无可用身份证数据，请手动认证',
            'stats': stats
        })
    
    if stats['available'] == 0:
        return jsonify({
            'available': False,
            'reason': 'all_used',
            'message': '所有身份证已使用完毕，请手动认证',
            'stats': stats
        })
    
    return jsonify({
        'available': True,
        'stats': stats,
        'message': f'还有 {stats["available"]} 张身份证可用'
    })

@app.route('/api/customer-service/search', methods=['POST'])
@login_required
def customer_service_search():
    start_time = time.time()
    data = request.get_json()
    query = data.get('query', '').strip()
    username = session['user']['username']
    
    if not query:
        return jsonify({'error': '请输入您的问题'}), 400
    
    knowledge_base_path = os.path.join(os.path.dirname(__file__), 'knowledge_base.json')
    
    if not os.path.exists(knowledge_base_path):
        return jsonify({'error': '知识库暂不可用'}), 500
    
    try:
        with open(knowledge_base_path, 'r', encoding='utf-8') as f:
            kb = json.load(f)
    except:
        return jsonify({'error': '知识库加载失败'}), 500
    
    topics = kb.get('topics', [])
    results = []
    query_lower = query.lower()
    
    for topic in topics:
        keywords = topic.get('keywords', [])
        title = topic.get('title', '')
        content = topic.get('content', '')
        match_score = 0
        matched_keywords = []
        
        for keyword in keywords:
            if keyword in query_lower:
                match_score += 1
                matched_keywords.append(keyword)
        
        title_lower = title.lower()
        content_lower = content.lower()
        title_words = title_lower.split()
        content_words = content_lower.split()
        query_words = query_lower.split()
        
        for qw in query_words:
            if len(qw) >= 2:
                for tw in title_words:
                    if tw in qw or qw in tw:
                        match_score += 0.5
                        if tw not in matched_keywords:
                            matched_keywords.append(tw)
                for cw in content_words:
                    if cw in qw or qw in cw:
                        if len(cw) >= 2 and cw not in matched_keywords:
                            matched_keywords.append(cw)
        
        if match_score > 0:
            results.append({
                'id': topic.get('id', ''),
                'title': title,
                'content': content,
                'score': round(match_score, 1),
                'matched_keywords': matched_keywords[:5]
            })
    
    results.sort(key=lambda x: x['score'], reverse=True)
    top_results = results[:3]
    
    user_data = users.get(username, {})
    today = datetime.now().strftime('%Y-%m-%d')
    response_data = {
        'found': True if top_results else False,
        'results': top_results,
        'user_data': {},
        'responseTime': int((time.time() - start_time) * 1000)
    }
    
    is_attendance_query = any(kw in query_lower for kw in ['签到', '打卡', '今日签到', '签到状态', '签到情况'])
    
    if is_attendance_query:
        has_attended_today = user_data.get('lastAttendanceDate', '') == today
        total_days = user_data.get('attendanceTotalDays', 0)
        consecutive_days = user_data.get('attendanceConsecutiveDays', 0)
        daily_earned = user_data.get('dailyEarnedPoints', 0)
        
        consecutive_rewards = get_consecutive_rewards(consecutive_days)
        total_rewards = get_total_rewards(total_days)
        
        response_data['user_data']['attendance'] = {
            'has_attended_today': has_attended_today,
            'total_days': total_days,
            'consecutive_days': consecutive_days,
            'daily_earned': daily_earned,
            'base_reward': 0.3,
            'consecutive_rewards': consecutive_rewards if consecutive_rewards else ['无'],
            'total_rewards': total_rewards if total_rewards else ['无'],
            'next_consecutive_milestone': get_next_milestone(consecutive_days, 'consecutive'),
            'next_total_milestone': get_next_milestone(total_days, 'total')
        }
    
    is_points_query = any(kw in query_lower for kw in ['积分', '剩余积分', '积分余额', '多少积分'])
    if is_points_query:
        total_points = user_data.get('totalPoints', 0)
        fund_balance = get_user_fund_balance(username)
        daily_earned = user_data.get('dailyEarnedPoints', 0)
        response_data['user_data']['points'] = {
            'total_points': total_points,
            'fund_balance': fund_balance,
            'combined_total': total_points + fund_balance,
            'daily_earned': daily_earned,
            'daily_limit': 14,
            'remaining_today': max(0, 14 - daily_earned)
        }
    
    is_pl_query = any(kw in query_lower for kw in ['pl', 'PL', 'pl余额', 'PL余额'])
    if is_pl_query:
        pl_balance = get_user_pl_balance(username)
        pl_rate = get_current_pl_rate()
        response_data['user_data']['pl'] = {
            'balance': pl_balance,
            'rate': pl_rate,
            'points_value': round(pl_balance / pl_rate, 2) if pl_rate > 0 else 0
        }
    
    return jsonify(response_data)

def get_consecutive_rewards(days):
    rewards = []
    base = days % 30
    if base == 0 and days > 0:
        cycle = days // 30
        rewards.append('高级积分卡密 ×3 + 积分加成卡 ×2 + 重置密码卡密 ×1（第' + str(cycle) + '周期）')
    elif base == 29:
        cycle = (days // 30) + 1
        rewards.append('高级积分卡密 ×3 + 积分加成卡 ×2 + 重置密码卡密 ×1（第' + str(cycle) + '周期）')
    elif base == 14:
        cycle = (days // 30) + 1
        rewards.append('高级积分卡密 ×3（第' + str(cycle) + '周期）')
    elif base == 6:
        cycle = (days // 30) + 1
        rewards.append('高级积分卡密 ×2（第' + str(cycle) + '周期）')
    elif base == 4:
        cycle = (days // 30) + 1
        rewards.append('高级积分卡密 ×1（第' + str(cycle) + '周期）')
    return rewards

def get_total_rewards(days):
    rewards = []
    base = days % 30
    if days >= 99 and base == 9:
        cycle = (days // 30) + 1
        rewards.append('38.0积分 + 积分加成卡 ×3（第' + str(cycle) + '周期）')
    elif days >= 59 and base == 29:
        cycle = (days // 30) + 1
        rewards.append('20.0积分 + 积分加成卡 ×2（第' + str(cycle) + '周期）')
    elif base == 0 and days > 0:
        cycle = days // 30
        rewards.append('8.8积分 + 积分加成卡 ×1（第' + str(cycle) + '周期）')
    elif base == 28:
        cycle = (days // 30) + 1
        rewards.append('8.8积分 + 积分加成卡 ×1（第' + str(cycle) + '周期）')
    elif base == 15:
        cycle = (days // 30) + 1
        rewards.append('3.0积分（第' + str(cycle) + '周期）')
    elif base == 7:
        cycle = (days // 30) + 1
        rewards.append('1.8积分（第' + str(cycle) + '周期）')
    elif base == 3:
        cycle = (days // 30) + 1
        rewards.append('1.0积分（第' + str(cycle) + '周期）')
    return rewards

def get_next_milestone(current, milestone_type):
    if milestone_type == 'consecutive':
        base = current % 30
        milestones = [4, 6, 14, 29, 30]
        for m in milestones:
            if base < m:
                return current + (m - base)
        cycle = current // 30
        next_target = (cycle + 1) * 30 + 4
        return next_target
    else:
        base = current % 30
        milestones = [3, 7, 15, 28, 30, 59, 99]
        for m in milestones:
            if base < m:
                return current + (m - base)
        cycle = current // 30
        next_target = (cycle + 1) * 30 + 3
        return next_target

@app.route('/api/customer-service/news', methods=['GET'])
@login_required
def get_news():
    start_time = time.time()
    try:
        response = requests.get('https://zj.v.api.aa1.cn/api/60s/', timeout=10)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'image' in content_type:
                import base64
                image_data = base64.b64encode(response.content).decode('utf-8')
                return jsonify({
                    'success': True,
                    'type': 'image',
                    'data': image_data,
                    'format': content_type.split('/')[-1] if '/' in content_type else 'png',
                    'responseTime': int((time.time() - start_time) * 1000)
                })
            else:
                return jsonify({
                    'success': True,
                    'type': 'text',
                    'data': response.text,
                    'responseTime': int((time.time() - start_time) * 1000)
                })
        else:
            return jsonify({
                'success': False,
                'error': '新闻服务暂时不可用',
                'responseTime': int((time.time() - start_time) * 1000)
            })
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': '新闻服务请求超时，请稍后重试',
            'responseTime': int((time.time() - start_time) * 1000)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'responseTime': int((time.time() - start_time) * 1000)
        })

@app.route('/api/customer-service/search-web', methods=['POST'])
@login_required
def search_web():
    start_time = time.time()
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': '请输入搜索内容'}), 400
    
    is_weather_query = any(kw in query for kw in ['天气', '气温', '温度', '降雨', '下雨', '晴天', '多云', '阴天', '风速'])
    
    if is_weather_query:
        import re
        
        lat_lng_pattern = r'(-?\d+\.?\d*)\s*[,，\s]\s*(-?\d+\.?\d*)'
        lat_lng_match = re.search(lat_lng_pattern, query)
        
        geo_result = None
        display_city = ''
        
        if lat_lng_match:
            try:
                latitude = float(lat_lng_match.group(1))
                longitude = float(lat_lng_match.group(2))
                
                if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                    log.info(f"Weather query by coordinates: lat={latitude}, lng={longitude}")
                    
                    weather_data = fetch_weather_from_openmeteo(latitude, longitude)
                    if weather_data:
                        display_city = f'坐标 ({latitude}, {longitude})'
                        
                        geo_result = {
                            'name': display_city,
                            'latitude': latitude,
                            'longitude': longitude,
                            'country': '',
                            'admin1': '',
                            'timezone': weather_data.get('timezone', 'auto'),
                            'matched_name': display_city
                        }
                        
                        return jsonify({
                            'success': True,
                            'query': query,
                            'engine': 'Open-Meteo',
                            'type': 'weather',
                            'weather_data': {
                                'city': display_city,
                                'search_city': query,
                                'matched_name': display_city,
                                'admin1': '',
                                'latitude': latitude,
                                'longitude': longitude,
                                'current_temp': weather_data['current']['temperature'],
                                'current_condition': weather_data['current']['condition'],
                                'feels_like': weather_data['current']['feels_like'],
                                'humidity': weather_data['current']['humidity'],
                                'wind': weather_data['current']['wind_speed'],
                                'precipitation': weather_data['current']['precipitation'],
                                'high_temp': weather_data['daily'][0]['high'] if weather_data['daily'] else '--',
                                'low_temp': weather_data['daily'][0]['low'] if weather_data['daily'] else '--',
                                'forecast': weather_data['daily'],
                                'hourly': weather_data['hourly'],
                                'update_time': weather_data['current']['time']
                            },
                            'responseTime': int((time.time() - start_time) * 1000)
                        })
                    else:
                        log.warning(f"Weather fetch failed for coordinates: {latitude}, {longitude}")
                else:
                    log.warning(f"Invalid coordinates: {latitude}, {longitude}")
            except Exception as e:
                log.error(f"Coordinate parse error: {e}")
        
        if not geo_result:
            cleaned = query
            for prefix in ['搜索', '搜', '查询', '查找', '查']:
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):].strip()
                    break
            cleaned = cleaned.replace('天气预报', '').replace('天气', '').replace('气温', '').replace('温度', '').replace('降雨', '').replace('下雨', '').replace('晴天', '').replace('多云', '').replace('阴天', '').replace('风速', '').strip()
            cleaned = cleaned.replace('的', '').replace('是', '').strip()
            cleaned = re.sub(r'[^\u4e00-\u9fa5]', '', cleaned)
            
            if not cleaned or len(cleaned) < 2:
                city = '北京'
            else:
                city = cleaned
            
            log.info(f"Weather query detected: original={query}, extracted_city={city}")
            
            geo_result = geocode_city_openmeteo(city)
            
            if geo_result:
                weather_data = fetch_weather_from_openmeteo(geo_result['latitude'], geo_result['longitude'])
                if weather_data:
                    city_display = geo_result['name']
                    if geo_result.get('admin1') and geo_result['admin1'] != geo_result['name']:
                        city_display += ' · ' + geo_result['admin1']
                    if geo_result.get('country'):
                        city_display += ', ' + geo_result['country']
                    
                    return jsonify({
                        'success': True,
                        'query': query,
                        'engine': 'Open-Meteo',
                        'type': 'weather',
                        'weather_data': {
                            'city': city_display,
                            'search_city': city,
                            'matched_name': geo_result.get('matched_name', city),
                            'admin1': geo_result.get('admin1', ''),
                            'latitude': geo_result['latitude'],
                            'longitude': geo_result['longitude'],
                            'current_temp': weather_data['current']['temperature'],
                            'current_condition': weather_data['current']['condition'],
                            'feels_like': weather_data['current']['feels_like'],
                            'humidity': weather_data['current']['humidity'],
                            'wind': weather_data['current']['wind_speed'],
                            'precipitation': weather_data['current']['precipitation'],
                            'high_temp': weather_data['daily'][0]['high'] if weather_data['daily'] else '--',
                            'low_temp': weather_data['daily'][0]['low'] if weather_data['daily'] else '--',
                            'forecast': weather_data['daily'],
                            'hourly': weather_data['hourly'],
                            'update_time': weather_data['current']['time']
                        },
                        'responseTime': int((time.time() - start_time) * 1000)
                    })
            else:
                log.warning(f"Geocode failed for city: {city}, falling back to search")
    
    is_time_query = any(kw in query for kw in ['时间', '几点', '现在几点', '当前时间', '时区', '几点了', '什么时间'])
    
    if is_time_query:
        time_result = fetch_time_info(query)
        if time_result:
            return jsonify({
                'success': True,
                'query': query,
                'engine': '时间服务',
                'type': 'time',
                'time_data': time_result,
                'responseTime': int((time.time() - start_time) * 1000)
            })
    
    search_engines = [
        {'name': 'Bing', 'url': f'https://www.bing.com/search?q={requests.utils.quote(query)}', 'parser': parse_bing},
        {'name': '搜狗', 'url': f'https://www.sogou.com/web?query={requests.utils.quote(query)}', 'parser': parse_sogou},
        {'name': '360搜索', 'url': f'https://www.so.com/s?q={requests.utils.quote(query)}', 'parser': parse_360},
        {'name': 'DuckDuckGo', 'url': f'https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}', 'parser': parse_duckduckgo},
        {'name': '百度', 'url': f'https://www.baidu.com/s?wd={requests.utils.quote(query)}', 'parser': parse_baidu}
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    for engine in search_engines:
        try:
            response = requests.get(engine['url'], headers=headers, timeout=8)
            if response.status_code == 200:
                results = engine['parser'](response.text)
                if results and len(results) > 0:
                    return jsonify({
                        'success': True,
                        'query': query,
                        'engine': engine['name'],
                        'type': 'search',
                        'results': results[:5],
                        'first_result': results[0] if results else None,
                        'responseTime': int((time.time() - start_time) * 1000)
                    })
        except:
            continue
    
    return jsonify({
        'success': False,
        'error': '未找到相关结果，请换个关键词试试',
        'responseTime': int((time.time() - start_time) * 1000)
    })


def fetch_time_info(query):
    import re
    from datetime import datetime
    
    timezone_map = {
        '中国': 'Asia/Shanghai', '北京': 'Asia/Shanghai', '上海': 'Asia/Shanghai',
        '香港': 'Asia/Hong_Kong', '澳门': 'Asia/Macau', '台湾': 'Asia/Taipei', '台北': 'Asia/Taipei',
        '日本': 'Asia/Tokyo', '东京': 'Asia/Tokyo',
        '韩国': 'Asia/Seoul', '首尔': 'Asia/Seoul',
        '美国': 'America/New_York', '纽约': 'America/New_York', '华盛顿': 'America/New_York',
        '洛杉矶': 'America/Los_Angeles', '旧金山': 'America/Los_Angeles', '芝加哥': 'America/Chicago',
        '英国': 'Europe/London', '伦敦': 'Europe/London',
        '法国': 'Europe/Paris', '巴黎': 'Europe/Paris',
        '德国': 'Europe/Berlin', '柏林': 'Europe/Berlin',
        '意大利': 'Europe/Rome', '罗马': 'Europe/Rome',
        '俄罗斯': 'Europe/Moscow', '莫斯科': 'Europe/Moscow',
        '澳大利亚': 'Australia/Sydney', '悉尼': 'Australia/Sydney', '墨尔本': 'Australia/Melbourne',
        '加拿大': 'America/Toronto', '多伦多': 'America/Toronto', '温哥华': 'America/Vancouver',
        '新加坡': 'Asia/Singapore', '马来西亚': 'Asia/Kuala_Lumpur', '吉隆坡': 'Asia/Kuala_Lumpur',
        '泰国': 'Asia/Bangkok', '曼谷': 'Asia/Bangkok',
        '越南': 'Asia/Ho_Chi_Minh', '胡志明': 'Asia/Ho_Chi_Minh',
        '印度': 'Asia/Kolkata', '新德里': 'Asia/Kolkata',
        '阿联酋': 'Asia/Dubai', '迪拜': 'Asia/Dubai',
        '南非': 'Africa/Johannesburg', '开普敦': 'Africa/Johannesburg',
        '巴西': 'America/Sao_Paulo', '圣保罗': 'America/Sao_Paulo',
        '阿根廷': 'America/Buenos_Aires', '布宜诺斯艾利斯': 'America/Buenos_Aires',
        '新西兰': 'Pacific/Auckland', '奥克兰': 'Pacific/Auckland',
        '印尼': 'Asia/Jakarta', '雅加达': 'Asia/Jakarta',
        '菲律宾': 'Asia/Manila', '马尼拉': 'Asia/Manila',
        '巴基斯坦': 'Asia/Karachi', '卡拉奇': 'Asia/Karachi',
        '土耳其': 'Europe/Istanbul', '伊斯坦布尔': 'Europe/Istanbul',
        '埃及': 'Africa/Cairo', '开罗': 'Africa/Cairo',
        '肯尼亚': 'Africa/Nairobi', '内罗毕': 'Africa/Nairobi',
        '墨西哥': 'America/Mexico_City', '墨西哥城': 'America/Mexico_City',
        '古巴': 'America/Havana', '哈瓦那': 'America/Havana',
        '智利': 'America/Santiago', '圣地亚哥': 'America/Santiago'
    }
    
    try:
        import pytz
        pytz_available = True
    except:
        pytz_available = False
    
    city_match = re.search(r'([\u4e00-\u9fa5]{2,10})(?:时间|几点|现在|当前|时区)?', query)
    
    location = '中国'
    timezone = 'Asia/Shanghai'
    
    if city_match:
        location = city_match.group(1)
        for key, tz in timezone_map.items():
            if key in location:
                timezone = tz
                break
    
    try:
        if pytz_available:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
        else:
            now = datetime.utcnow()
        
        time_str = now.strftime('%H:%M:%S')
        date_str = now.strftime('%Y年%m月%d日')
        weekday = now.strftime('%A')
        weekday_cn = {
            'Monday': '星期一', 'Tuesday': '星期二', 'Wednesday': '星期三',
            'Thursday': '星期四', 'Friday': '星期五', 'Saturday': '星期六',
            'Sunday': '星期日'
        }.get(weekday, weekday)
        
        offset = ''
        if pytz_available and now.utcoffset():
            offset_seconds = now.utcoffset().total_seconds()
            offset_hours = int(offset_seconds / 3600)
            offset_minutes = int((offset_seconds % 3600) / 60)
            if offset_hours >= 0:
                offset = f'UTC+{offset_hours:02d}:{offset_minutes:02d}'
            else:
                offset = f'UTC{offset_hours:02d}:{offset_minutes:02d}'
        else:
            offset = 'UTC'
        
        return {
            'location': location,
            'timezone': timezone,
            'time': time_str,
            'date': date_str,
            'weekday': weekday_cn,
            'offset': offset,
            'timestamp': int(now.timestamp())
        }
        
    except Exception as e:
        log.error(f"Time fetch error: {e}")
        return {
            'location': location,
            'timezone': timezone,
            'time': datetime.now().strftime('%H:%M:%S'),
            'date': datetime.now().strftime('%Y年%m月%d日'),
            'weekday': ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'][datetime.now().weekday()],
            'offset': 'UTC+08:00',
            'timestamp': int(datetime.now().timestamp())
        }


def parse_bing(html):
    import re
    results = []
    pattern = r'<li class="b_algo"[^>]*>.*?<h2[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<p[^>]*>(.*?)</p>'
    matches = re.findall(pattern, html, re.DOTALL)
    seen = set()
    for url, title, desc in matches:
        if url and url not in seen and not url.startswith('javascript:') and not url.startswith('#') and 'javascript' not in url:
            seen.add(url)
            title_clean = re.sub(r'<[^>]+>', '', title).strip()
            desc_clean = re.sub(r'<[^>]+>', '', desc).strip()
            if title_clean and len(title_clean) > 2:
                results.append({
                    'title': title_clean[:120],
                    'url': url,
                    'description': desc_clean[:350] if desc_clean else '暂无描述'
                })
        if len(results) >= 5:
            break
    return results[:5]


def parse_sogou(html):
    import re
    results = []
    pattern = r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<p[^>]*>(.*?)</p>'
    matches = re.findall(pattern, html, re.DOTALL)
    seen = set()
    for url, title, desc in matches[:30]:
        if url and url not in seen and not url.startswith('javascript:') and not url.startswith('#') and 'javascript' not in url:
            seen.add(url)
            title_clean = re.sub(r'<[^>]+>', '', title).strip()
            desc_clean = re.sub(r'<[^>]+>', '', desc).strip()
            if title_clean and len(title_clean) > 2:
                results.append({
                    'title': title_clean[:120],
                    'url': url,
                    'description': desc_clean[:350] if desc_clean else '暂无描述'
                })
        if len(results) >= 5:
            break
    return results[:5]


def parse_duckduckgo(html):
    import re
    results = []
    pattern = r'<a[^>]*rel="nofollow"[^>]*href="([^"]*)"[^>]*>.*?<span[^>]*>(.*?)</span>.*?<div[^>]*class="result__snippet"[^>]*>(.*?)</div>'
    matches = re.findall(pattern, html, re.DOTALL)
    seen = set()
    for url, title, desc in matches:
        if url and url not in seen and not url.startswith('javascript:') and not url.startswith('#') and 'javascript' not in url:
            seen.add(url)
            title_clean = re.sub(r'<[^>]+>', '', title).strip()
            desc_clean = re.sub(r'<[^>]+>', '', desc).strip()
            if title_clean and len(title_clean) > 2:
                results.append({
                    'title': title_clean[:120],
                    'url': url,
                    'description': desc_clean[:350] if desc_clean else '暂无描述'
                })
        if len(results) >= 5:
            break
    return results[:5]


def parse_360(html):
    import re
    results = []
    pattern = r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<p[^>]*class="[^"]*desc[^"]*"[^>]*>(.*?)</p>'
    matches = re.findall(pattern, html, re.DOTALL)
    seen = set()
    for url, title, desc in matches:
        if url and url not in seen and not url.startswith('javascript:') and not url.startswith('#') and 'javascript' not in url:
            seen.add(url)
            title_clean = re.sub(r'<[^>]+>', '', title).strip()
            desc_clean = re.sub(r'<[^>]+>', '', desc).strip()
            if title_clean and len(title_clean) > 2:
                results.append({
                    'title': title_clean[:120],
                    'url': url,
                    'description': desc_clean[:350] if desc_clean else '暂无描述'
                })
        if len(results) >= 5:
            break
    return results[:5]


def parse_baidu(html):
    import re
    results = []
    pattern = r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<div[^>]*class="[^"]*abstract[^"]*"[^>]*>(.*?)</div>'
    matches = re.findall(pattern, html, re.DOTALL)
    seen = set()
    for url, title, desc in matches:
        if url and url not in seen and not url.startswith('javascript:') and not url.startswith('#') and 'javascript' not in url:
            seen.add(url)
            title_clean = re.sub(r'<[^>]+>', '', title).strip()
            desc_clean = re.sub(r'<[^>]+>', '', desc).strip()
            if title_clean and len(title_clean) > 2:
                results.append({
                    'title': title_clean[:120],
                    'url': url,
                    'description': desc_clean[:350] if desc_clean else '暂无描述'
                })
        if len(results) >= 5:
            break
    return results[:5]

@app.route('/api/email/verify', methods=['POST'])
@csrf_protect
@login_required
def verify_email_code_api():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    code = data.get('code', '').strip()

    if not email or not code:
        return jsonify({'error': '请提供邮箱和验证码'}), 400

    if not validate_email(email):
        return jsonify({'error': '邮箱格式不正确'}), 400

    user_data = users.get(username)
    if not user_data:
        return jsonify({'error': '用户不存在'}), 400

    bound_email = user_data.get('email', '')
    if not bound_email:
        return jsonify({'error': '用户未绑定邮箱'}), 400

    if email != bound_email:
        return jsonify({'error': '输入的邮箱与绑定的邮箱不一致，请检查'}), 400

    success, message = email_service.verify_code(email, code)

    if success:
        user_data['email_verified'] = True
        user_data['email_verified_at'] = int(time.time() * 1000)
        save_users()
        response_time = int((time.time() - start_time) * 1000)
        return jsonify({
            'success': True,
            'message': '邮箱验证成功',
            'responseTime': response_time
        })
    else:
        return jsonify({'error': message}), 400


@app.route('/api/email/check-verification', methods=['GET'])
@login_required
def check_email_verification_api():
    username = session['user']['username']
    user_data = users.get(username, {})
    
    is_verified = user_data.get('email_verified', False)
    email = user_data.get('email', '')
    has_email = bool(email)
    
    return jsonify({
        'verified': is_verified,
        'has_email': has_email,
        'email': email
    })


@app.route('/api/email/change', methods=['POST'])
@csrf_protect
@login_required
def change_email_api():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    new_email = data.get('new_email', '').strip().lower()
    code = data.get('code', '').strip()

    if not new_email or not code:
        return jsonify({'error': '请填写新邮箱和验证码'}), 400

    if not validate_email(new_email):
        return jsonify({'error': '邮箱格式不正确'}), 400

    user_data = users.get(username)
    if not user_data:
        return jsonify({'error': '用户不存在'}), 400

    old_email = user_data.get('email', '')
    if not old_email:
        return jsonify({'error': '用户未绑定邮箱'}), 400

    if new_email == old_email:
        return jsonify({'error': '新邮箱与当前邮箱相同'}), 400

    if user_data.get('email_changed', False):
        return jsonify({'error': '每个账号仅允许换绑一次'}), 400

    for u, data in users.items():
        if data.get('email') == new_email and u != username:
            return jsonify({'error': '该邮箱已被其他用户绑定'}), 400

    success, message = email_service.verify_code(new_email, code)
    if not success:
        return jsonify({'error': message}), 400

    user_data['email'] = new_email
    user_data['email_changed'] = True
    user_data['email_changed_at'] = int(time.time() * 1000)
    user_data['old_email'] = old_email
    user_data['email_verified'] = True
    
    save_users()

    response_time = int((time.time() - start_time) * 1000)
    return jsonify({
        'success': True,
        'message': f'邮箱已成功从 {old_email} 更换为 {new_email}',
        'new_email': new_email,
        'responseTime': response_time
    })


@app.route('/api/email/send-change-code', methods=['POST'])
@csrf_protect
@login_required
@limiter.limit('3 per minute')
def send_change_email_code_api():
    start_time = time.time()
    username = session['user']['username']
    data = request.get_json()
    new_email = data.get('new_email', '').strip().lower()

    if not new_email:
        return jsonify({'error': '请输入新邮箱地址'}), 400

    if not validate_email(new_email):
        return jsonify({'error': '邮箱格式不正确'}), 400

    user_data = users.get(username)
    if not user_data:
        return jsonify({'error': '用户不存在'}), 400

    old_email = user_data.get('email', '')
    if not old_email:
        return jsonify({'error': '用户未绑定邮箱'}), 400

    if new_email == old_email:
        return jsonify({'error': '新邮箱与当前邮箱相同'}), 400

    if user_data.get('email_changed', False):
        return jsonify({'error': '每个账号仅允许换绑一次'}), 400

    for u, data in users.items():
        if data.get('email') == new_email and u != username:
            return jsonify({'error': '该邮箱已被其他用户绑定'}), 400

    status = email_service.get_verification_status(new_email)
    if status['exists'] and not status['expired'] and not status['verified']:
        remaining = status['expires_at'] - int(time.time())
        return jsonify({
            'error': f'验证码已发送，请等待 {remaining // 60} 分钟后重试',
            'remaining_seconds': remaining
        }), 429

    success, code, message = email_service.send_verification_code(new_email, username)

    if success:
        response_time = int((time.time() - start_time) * 1000)
        return jsonify({
            'success': True,
            'message': '验证码已发送至新邮箱，请查收',
            'expires_in': email_service.CODE_EXPIRE_SECONDS,
            'responseTime': response_time
        })
    else:
        return jsonify({'error': message}), 500

@app.route('/api/send-verification-code', methods=['POST'])
@csrf_protect
@limiter.limit('5 per minute')
def send_verification_code_api():
    start_time = time.time()
    data = request.get_json() or {}
    
    email = data.get('email', '').strip().lower()
    purpose = data.get('purpose', '验证')
    
    if not email:
        return jsonify({'error': '请输入邮箱地址'}), 400
    
    if not validate_email(email):
        return jsonify({'error': '邮箱格式不正确'}), 400
    
    if purpose == '注册':
        for u, user_data in users.items():
            if user_data.get('email') == email:
                return jsonify({'error': '该邮箱已被注册'}), 400
        success, code, message = email_service.send_verification_code_with_limit(email, None, '注册')
        if success:
            return jsonify({
                'success': True,
                'message': '验证码已发送至您的邮箱，请查收',
                'expires_in': email_service.CODE_EXPIRE_SECONDS,
                'responseTime': int((time.time() - start_time) * 1000)
            })
        else:
            return jsonify({'error': message}), 500
    
    if purpose == '验证':
        if 'user' not in session:
            return jsonify({'error': '请先登录'}), 401
        
        username = session['user']['username']
        user_data = users.get(username)
        if not user_data:
            return jsonify({'error': '用户不存在'}), 400
        
        bound_email = user_data.get('email', '')
        if not bound_email:
            return jsonify({'error': '用户未绑定邮箱'}), 400
        
        if email != bound_email:
            return jsonify({'error': '输入的邮箱与绑定的邮箱不一致'}), 400
        
        if user_data.get('email_verified', False):
            return jsonify({'error': '邮箱已验证，无需重复验证'}), 400
        
        success, code, message = email_service.send_verification_code_with_limit(email, username, '验证')
        if success:
            return jsonify({
                'success': True,
                'message': '验证码已发送至您的邮箱，请查收',
                'expires_in': email_service.CODE_EXPIRE_SECONDS,
                'responseTime': int((time.time() - start_time) * 1000)
            })
        else:
            return jsonify({'error': message}), 500
    
    if purpose == '换绑':
        if 'user' not in session:
            return jsonify({'error': '请先登录'}), 401
        
        username = session['user']['username']
        user_data = users.get(username)
        if not user_data:
            return jsonify({'error': '用户不存在'}), 400
        
        old_email = user_data.get('email', '')
        if not old_email:
            return jsonify({'error': '用户未绑定邮箱'}), 400
        
        if email == old_email:
            return jsonify({'error': '新邮箱与当前邮箱相同'}), 400
        
        if user_data.get('email_changed', False):
            return jsonify({'error': '每个账号仅允许换绑一次'}), 400
        
        for u, data in users.items():
            if data.get('email') == email and u != username:
                return jsonify({'error': '该邮箱已被其他用户绑定'}), 400
        
        success, code, message = email_service.send_verification_code_with_limit(email, username, '换绑')
        if success:
            return jsonify({
                'success': True,
                'message': '验证码已发送至新邮箱，请查收',
                'expires_in': email_service.CODE_EXPIRE_SECONDS,
                'responseTime': int((time.time() - start_time) * 1000)
            })
        else:
            return jsonify({'error': message}), 500
    
    if purpose == '重置密码':
        if 'user' not in session:
            username = None
        else:
            username = session['user']['username']
        
        found_user = None
        for u, user_data in users.items():
            if user_data.get('email') == email:
                found_user = u
                break
        
        if not found_user:
            return jsonify({'error': '该邮箱未注册'}), 400
        
        if username and found_user != username:
            return jsonify({'error': '该邮箱不属于当前登录用户'}), 400
        
        success, code, message = email_service.send_verification_code_with_limit(email, found_user, '重置密码')
        if success:
            return jsonify({
                'success': True,
                'message': '验证码已发送至您的邮箱，请查收',
                'expires_in': email_service.CODE_EXPIRE_SECONDS,
                'responseTime': int((time.time() - start_time) * 1000)
            })
        else:
            return jsonify({'error': message}), 500
    
    if purpose == '注销':
        if 'user' not in session:
            return jsonify({'error': '请先登录'}), 401
        
        username = session['user']['username']
        user_data = users.get(username)
        if not user_data:
            return jsonify({'error': '用户不存在'}), 400
        
        bound_email = user_data.get('email', '')
        if not bound_email:
            return jsonify({'error': '用户未绑定邮箱'}), 400
        
        if email != bound_email:
            return jsonify({'error': '输入的邮箱与绑定的邮箱不一致'}), 400
        
        success, code, message = email_service.send_verification_code_with_limit(email, username, '注销')
        if success:
            return jsonify({
                'success': True,
                'message': '验证码已发送至您的邮箱，请查收',
                'expires_in': email_service.CODE_EXPIRE_SECONDS,
                'responseTime': int((time.time() - start_time) * 1000)
            })
        else:
            return jsonify({'error': message}), 500
    
    return jsonify({'error': '无效的操作类型'}), 400

@app.route('/api/check-verification-status', methods=['POST'])
@csrf_protect
@limiter.limit('30 per minute')
def check_verification_status_api():
    """
    检查验证码状态
    """
    data = request.get_json()
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'error': '请输入邮箱地址'}), 400

    if not validate_email(email):
        return jsonify({'error': '邮箱格式不正确'}), 400

    status = email_service.get_verification_status(email)
    
    return jsonify({
        'exists': status['exists'],
        'verified': status['verified'],
        'expired': status['expired'],
        'message': status['message'],
        'expires_at': status.get('expires_at', 0)
    })

@app.route('/api/announcements', methods=['GET'])
def get_public_announcements():
    current_time = int(time.time() * 1000)
    announcement_list = []
    for aid, ann in announcements.items():
        if not ann.get('is_active', True):
            continue
        start_time = ann.get('start_time', 0)
        end_time = ann.get('end_time', 0)
        if start_time > 0 and current_time < start_time:
            continue
        if end_time > 0 and current_time > end_time:
            continue
        announcement_list.append({
            'id': aid,
            'title': ann.get('title', ''),
            'content': ann.get('content', ''),
            'type': ann.get('type', 'info'),
            'is_sticky': ann.get('is_sticky', False),
            'created_at': ann.get('created_at', 0)
        })
    announcement_list.sort(key=lambda x: (-x.get('is_sticky', False), -x.get('created_at', 0)))
    return jsonify({'announcements': announcement_list})

@app.route('/api/game/list', methods=['GET'])
@login_required
def get_game_list():
    username = session['user']['username']
    if is_login_restricted(username):
        return jsonify({'error': '账号已被限制'}), 403
    gm = game.get_game_manager()
    if not gm:
        return jsonify({'error': '游戏服务未初始化'}), 500
    return jsonify({
        'games': gm.get_game_list(),
        'stats': gm.get_stats(username)
    })


@app.route('/api/game/stats', methods=['GET'])
@login_required
def get_game_stats():
    username = session['user']['username']
    if is_login_restricted(username):
        return jsonify({'error': '账号已被限制'}), 403
    gm = game.get_game_manager()
    if not gm:
        return jsonify({'error': '游戏服务未初始化'}), 500
    return jsonify(gm.get_stats(username))

@app.route('/api/game/play/<game_id>', methods=['POST'])
@login_required
def play_game(game_id):
    start_time = time.time()
    username = session['user']['username']
    if is_login_restricted(username):
        return jsonify({'error': '账号已被限制'}), 403
    if not check_identity_verified(username):
        return jsonify({'error': '请先完成身份认证'}), 403
    gm = game.get_game_manager()
    if not gm:
        return jsonify({'error': '游戏服务未初始化'}), 500
    if game_id not in gm.games:
        return jsonify({'error': '游戏不存在'}), 400
    if not gm.can_play(username):
        return jsonify({'error': '今日游戏次数已达上限'}), 400
    try:
        data = request.get_json()
        if data is None:
            data = {}
    except Exception:
        data = {}
    try:
        if game_id == 'dice':
            bet_type = data.get('bet_type', 'high')
            bet_value = int(data.get('bet_value', 7))
            result = gm.play_dice(username, bet_type, bet_value)
        elif game_id == 'blackjack':
            result = gm.play_blackjack(username)
        elif game_id == 'guess_number':
            guess = data.get('guess')
            if guess is not None:
                try:
                    guess = int(guess)
                except:
                    return jsonify({'error': '请输入有效的数字'}), 400
            result = gm.play_guess_number(username, guess)
        elif game_id == 'rock_paper_scissors':
            player_move = data.get('move')
            result = gm.play_rps(username, player_move)
        elif game_id == 'roulette':
            bet_type = data.get('bet_type', 'number')
            bet_value = int(data.get('bet_value', 0))
            result = gm.play_roulette(username, bet_type, bet_value)
        else:
            return jsonify({'error': '游戏不存在'}), 400
        if result.get('success'):
            result['responseTime'] = int((time.time() - start_time) * 1000)
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error', '游戏失败')}), 400
    except ValueError as e:
        return jsonify({'error': '参数格式错误: ' + str(e)}), 400
    except Exception as e:
        log.error(f"Game error for {username} in {game_id}: {e}")
        return jsonify({'error': '游戏执行异常，请稍后重试'}), 500

@app.route('/api/game/guess/state', methods=['GET'])
@login_required
def get_guess_game_state():
    username = session['user']['username']
    gm = game.get_game_manager()
    if not gm:
        return jsonify({'error': '游戏服务未初始化'}), 500
    state = gm.get_guess_game_state(username)
    if not state:
        return jsonify({'active': False})
    return jsonify({
        'active': state.get('active', False),
        'attempts': state.get('attempts', 0),
        'max_attempts': state.get('max_attempts', 7),
        'hints': state.get('hints', [])
    })

@app.route('/api/game/rps/state', methods=['GET'])
@login_required
def get_rps_game_state():
    username = session['user']['username']
    gm = game.get_game_manager()
    if not gm:
        return jsonify({'error': '游戏服务未初始化'}), 500
    state = gm.rps_game_state.get(username)
    if not state:
        return jsonify({'active': False})
    return jsonify({
        'active': state.get('active', False),
        'player_wins': state.get('player_wins', 0),
        'ai_wins': state.get('ai_wins', 0),
        'rounds_played': state.get('rounds_played', 0),
        'best_of': state.get('best_of', 3),
        'round_history': state.get('round_history', [])
    })

@app.route('/api/membership/status', methods=['GET'])
@login_required
def get_membership_status():
    username = session['user']['username']
    gm = game.get_game_manager()
    membership = game.get_membership_data(users, username)
    stats = gm.get_stats(username) if gm else {}
    return jsonify({
        'is_member': game.is_game_member(users, username),
        'membership': membership,
        'today_plays': stats.get('today_plays', 0),
        'max_plays': game.get_member_max_plays(users, username),
        'bonus_rate': game.get_member_bonus_rate(users, username) * 100,
        'expires_at': membership.get('expires_at', 0) if membership else 0,
        'activated_at': membership.get('activated_at', 0) if membership else 0
    })

@app.route('/api/membership/buy', methods=['POST'])
@csrf_protect
@login_required
@identity_required
def buy_membership():
    start_time = time.time()
    username = session['user']['username']
    if is_login_restricted(username):
        return jsonify({'error': '账号已被限制'}), 403
    if game.is_game_member(users, username):
        return jsonify({'error': '您已是游戏会员'}), 400
    success, message = game.activate_game_membership(users, save_users, username)
    if success:
        if username in users and 'game_stats' in users[username]:
            stats = users[username]['game_stats']
            today = datetime.now().strftime('%Y-%m-%d')
            if stats.get('today_date') == today:
                pass
        reload_if_changed()
        response_time = int((time.time() - start_time) * 1000)
        return jsonify({
            'success': True,
            'message': message,
            'is_member': True,
            'max_plays': game.get_member_max_plays(users, username),
            'bonus_rate': game.get_member_bonus_rate(users, username) * 100,
            'responseTime': response_time
        })
    else:
        return jsonify({'error': message}), 400

@app.route('/api/weather/current', methods=['GET'])
@login_required
def get_weather_current():
    try:
        city = request.args.get('city', '').strip()
        latitude = request.args.get('latitude', type=float)
        longitude = request.args.get('longitude', type=float)
        
        if not city and (latitude is None or longitude is None):
            return jsonify({'error': '请提供城市名称或经纬度'}), 400
        
        if city and (latitude is None or longitude is None):
            geo_result = geocode_city_openmeteo(city)
            if not geo_result:
                return jsonify({'error': f'未找到城市: {city}'}), 404
            latitude = geo_result['latitude']
            longitude = geo_result['longitude']
            location_name = geo_result['name']
            country = geo_result.get('country', '')
        else:
            location_name = f'{latitude}, {longitude}'
            country = ''
        
        weather_data = fetch_weather_from_openmeteo(latitude, longitude)
        if not weather_data:
            return jsonify({'error': '天气数据获取失败'}), 500
        
        return jsonify({
            'success': True,
            'location': {
                'name': location_name,
                'country': country,
                'latitude': latitude,
                'longitude': longitude,
                'timezone': weather_data['timezone']
            },
            'current': weather_data['current'],
            'hourly': weather_data['hourly'],
            'daily': weather_data['daily'],
            'data_source': 'Open-Meteo',
            'attribution': 'Weather data by Open-Meteo.com (CC BY 4.0)'
        })
        
    except Exception as e:
        log.error(f"Weather API error: {e}")
        return jsonify({'error': '服务器错误: ' + str(e)}), 500


@app.route('/api/weather/forecast', methods=['GET'])
@login_required
def get_weather_forecast():
    try:
        city = request.args.get('city', '').strip()
        days = request.args.get('days', 7, type=int)
        
        if not city:
            return jsonify({'error': '请提供城市名称'}), 400
        
        if days < 1:
            days = 1
        if days > 16:
            days = 16
        
        geo_result = geocode_city_openmeteo(city)
        if not geo_result:
            return jsonify({'error': f'未找到城市: {city}'}), 404
        
        latitude = geo_result['latitude']
        longitude = geo_result['longitude']
        
        weather_data = fetch_weather_from_openmeteo(latitude, longitude)
        if not weather_data:
            return jsonify({'error': '天气数据获取失败'}), 500
        
        return jsonify({
            'success': True,
            'location': {
                'name': geo_result['name'],
                'country': geo_result.get('country', ''),
                'latitude': latitude,
                'longitude': longitude
            },
            'forecast': weather_data['daily'][:days],
            'data_source': 'Open-Meteo',
            'attribution': 'Weather data by Open-Meteo.com (CC BY 4.0)'
        })
        
    except Exception as e:
        log.error(f"Weather forecast API error: {e}")
        return jsonify({'error': '服务器错误: ' + str(e)}), 500

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/GAME/')
def game_index():
    return send_from_directory('GAME', 'index.html')

@app.route('/GAME/membership.html')
def game_membership_page():
    return send_from_directory('GAME', 'membership.html')

@app.route('/GAME/<path:path>')
def game_static(path):
    return send_from_directory('GAME', path)

@app.route('/login.html')
def login_page():
    return send_from_directory('public', 'login.html')

@app.route('/mall.html')
def mall_page():
    return send_from_directory('public', 'mall.html')

@app.route('/refund.html')
def refund_page():
    return send_from_directory('public', 'refund.html')

@app.route('/fund.html')
def fund_page():
    return send_from_directory('public', 'fund.html')

@app.route('/identity_verification.html')
def identity_verification_page():
    return send_from_directory('public', 'identity_verification.html')

@app.route('/player_center.html')
def player_center_page():
    return send_from_directory('public', 'player_center.html')

@app.route('/customer_service.html')
def customer_service_page():
    return send_from_directory('public', 'customer_service.html')

@app.route('/pay/<order_id>')
def pay_page(order_id):
    return send_from_directory('public', 'pay.html')

@app.route('/calendar.html')
def calendar_page():
    return send_from_directory('public', 'calendar.html')

@app.route('/admin')
def admin_page():
    return send_from_directory('public', 'admin.html')

@app.route('/mail.html')
def mail_page():
    return send_from_directory('public', 'mail.html')

@app.route('/pool.html')
def pool_page():
    return send_from_directory('public', 'pool.html')

@app.route('/public/mail.json')
def mail_json():
    return send_from_directory('public', 'mail.json')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('public', 'favicon.ico')

@app.route('/style.css')
def style_css():
    return send_from_directory('public', 'style.css')

@app.route('/script.js')
def script_js():
    return send_from_directory('public', 'script.js')

@app.route('/mail.css')
def mail_css():
    return send_from_directory('public', 'mail.css')

@app.route('/mail.js')
def mail_js():
    return send_from_directory('public', 'mail.js')

@app.route('/<path:path>')
def static_files(path):
    if path.startswith('api/') or path.startswith('admin/api/'):
        return jsonify({'error': 'API endpoint not found'}), 404

    try:
        return send_from_directory('public', path)
    except:
        return send_from_directory('public', 'index.html')

def signal_handler(signum, frame):
    print('\n正在优雅关闭服务器...')
    try:
        cleanup_all_expired_data()
        enforce_phone_record_limit()
        save_users()
        save_phone_records()
        save_auth_codes()
        save_reset_codes()
        save_point_codes()
        save_premium_point_codes()
        save_boost_codes()
        save_special_point_codes()
        save_makeup_codes()
        save_gamblers_codes()
        save_box_codes()
        save_plcard_codes()
        save_premium_boost_codes()
        save_user_boosts()
        save_identity_verifications()
        save_cancellation_codes()
        save_restricted_users()
        save_cdk_packages()
        save_user_cdk_records()
        save_announcements()
        save_pl_exchange_records()
        save_pl_rate_data()
        save_user_pl_balances()
        save_system_total_points(system_total_points)
        save_orders()
        save_user_pay_passwords()
        save_user_code_limits()
        save_coupons()
        save_user_coupons()
        save_coupon_grants()
        save_pl_transfers()
        save_mail_attachments()
        save_mail_read_receipts()
        save_pool_records()
        save_user_pool_claims()
        save_fund_data()
        save_fund_history()
        save_fund_rate()
        save_nav_data()
        save_nav_holdings()
        save_nav_history()
        save_gateway_stock()
        print('数据已保存并清理，服务器关闭完成')
    except Exception as e:
        print(f'保存数据时出错: {e}')
    sys.exit(0)

def start_verification_cleanup():
    """启动验证码清理线程"""
    import threading
    cleanup_thread = threading.Thread(target=email_service.cleanup_verification_codes_loop, daemon=True)
    cleanup_thread.start()
    log.info("验证码清理线程已启动")

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    cleanup_all_expired_data()
    enforce_phone_record_limit()
    cleanup_pool_records()
    
    migrate_user_login_time()
    migrate_restricted_users()
    migrate_auth_codes()
    migrate_first_attendance_date()
    migrate_attendance_dates()
    migrate_user_data()
    migrate_game_stats_to_users()
    migrate_existing_game_limits_to_users()
    migrate_game_membership_data()
    log.info("用户数据迁移完成")

    if not os.getenv('ADMIN_PASSWORD_HASH'):
        print("\n" + "="*60)
        print("⚠️  WARNING: ADMIN_PASSWORD_HASH not set in environment!")
        print("Using default admin credentials:")
        print("  Username: admin")
        print("  Password: changeme123")
        print("="*60 + "\n")
        print(f"\n{'='*60}")
        print(f"管理员登录端点: /api/admin/login")
        print(f"默认用户名: admin")
        print(f"默认密码: changeme123")
        print(f"请在 .env 文件中设置 ADMIN_PASSWORD_HASH 以使用自定义密码")
        print(f"生成哈希命令:")
        print(f"  python -c \"import bcrypt; print(bcrypt.generate_password_hash('your_password').decode('utf-8'))\"")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'='*60}")
        print(f"管理员登录端点: /api/admin/login")
        print(f"用户名: {ADMIN_USERNAME}")
        print(f"密码: 已从环境变量加载")
        print(f"{'='*60}\n")

    import socket
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"Server running on https://{local_ip}:3000")
        print(f"Also available on https://localhost:3000")
        print("按 Ctrl+C 优雅关闭服务器")
    except Exception as e:
        print(f"获取网络信息失败: {e}")

    ssl_dir = os.path.join(os.path.dirname(__file__), 'ssl')
    cert_file = os.path.join(ssl_dir, 'cert.pem')
    key_file = os.path.join(ssl_dir, 'key.pem')

    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print("SSL证书文件不存在，请先生成证书文件 ssl/cert.pem 和 ssl/key.pem")
        print("可以使用以下命令生成自签名证书:")
        print("mkdir -p ssl")
        print("openssl req -x509 -newkey rsa:4096 -nodes -out ssl/cert.pem -keyout ssl/key.pem -days 365")
        exit(1)

    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        app.run(host='0.0.0.0', port=3000, debug=False, ssl_context=context)
    except BrokenPipeError:
        print("连接中断，忽略错误")
    except Exception as e:
        print(f"服务器启动失败: {e}")