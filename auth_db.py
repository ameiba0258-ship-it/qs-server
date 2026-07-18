"""Simple user auth & membership database using SQLite."""

import sqlite3
import hashlib
import uuid
import os
import time
import json
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "users.db")

# Membership limits
TIER_LIMITS = {
    "free": {"daily_searches": 50, "daily_exports": 3, "deep_search": False},
    "premium": {"daily_searches": 5000, "daily_exports": 100, "deep_search": True},
    "enterprise": {"daily_searches": 50000, "daily_exports": 1000, "deep_search": True},
    "admin": {"daily_searches": 999999, "daily_exports": 99999, "deep_search": True},
}


def _get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            email TEXT,
            tier TEXT DEFAULT 'free',
            token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            date TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            UNIQUE(user_id, action, date)
        );
    """)
    conn.commit()
    conn.close()


def _hash_password(password, salt=None):
    if salt is None:
        salt = uuid.uuid4().hex[:16]
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return h, salt


def register_user(username, password, email=""):
    conn = _get_db()
    try:
        pw_hash, salt = _hash_password(password)
        token = uuid.uuid4().hex
        conn.execute("INSERT INTO users (username, password_hash, salt, email, token) VALUES (?,?,?,?,?)",
                     (username, pw_hash, salt, email, token))
        conn.commit()
        return {"success": True, "token": token, "tier": "free"}
    except sqlite3.IntegrityError:
        return {"success": False, "error": "用户名已存在"}
    finally:
        conn.close()


def login_user(username, password):
    conn = _get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not row:
            return {"success": False, "error": "用户名或密码错误"}
        pw_hash, _ = _hash_password(password, row["salt"])
        if pw_hash != row["password_hash"]:
            return {"success": False, "error": "用户名或密码错误"}
        # Generate new token
        token = uuid.uuid4().hex
        conn.execute("UPDATE users SET token=? WHERE id=?", (token, row["id"]))
        conn.commit()
        return {"success": True, "token": token, "tier": row["tier"], "username": row["username"]}
    finally:
        conn.close()


def validate_token(token):
    conn = _get_db()
    try:
        # Check user token
        row = conn.execute("SELECT * FROM users WHERE token=?", (token,)).fetchone()
        if row:
            return {"id": row["id"], "username": row["username"], "tier": row["tier"]}
        
        # Check API token
        conn.execute("CREATE TABLE IF NOT EXISTS api_tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT UNIQUE NOT NULL, owner TEXT, tier TEXT DEFAULT 'free', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_used TIMESTAMP, is_active INTEGER DEFAULT 1)")
        api_row = conn.execute("SELECT * FROM api_tokens WHERE token=? AND is_active=1", (token,)).fetchone()
        if api_row:
            conn.execute("UPDATE api_tokens SET last_used=CURRENT_TIMESTAMP WHERE id=?", (api_row["id"],))
            conn.commit()
            return {"id": "api_"+str(api_row["id"]), "username": api_row["owner"]+" (API)", "tier": api_row["tier"]}
        
        return None
    finally:
        conn.close()


def check_usage(user_id, action="search"):
    conn = _get_db()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        row = conn.execute("SELECT count FROM usage_log WHERE user_id=? AND action=? AND date=?",
                          (user_id, action, today)).fetchone()
        return row["count"] if row else 0
    finally:
        conn.close()


def increment_usage(user_id, action="search", amount=1):
    conn = _get_db()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        conn.execute("""
            INSERT INTO usage_log (user_id, action, date, count) VALUES (?,?,?,?)
            ON CONFLICT(user_id, action, date) DO UPDATE SET count = count + ?
        """, (user_id, action, today, amount, amount))
        conn.commit()
    finally:
        conn.close()


def get_user_info(user_id):
    conn = _get_db()
    try:
        row = conn.execute("SELECT id, username, email, tier, created_at FROM users WHERE id=?", (user_id,)).fetchone()
        if row:
            today_count = check_usage(user_id)
            tier_info = TIER_LIMITS.get(row["tier"], TIER_LIMITS["free"])
            return {
                "id": row["id"],
                "username": row["username"],
                "email": row["email"] or "",
                "tier": row["tier"],
                "today_searches": today_count,
                "daily_limit": tier_info["daily_searches"],
                "deep_search": tier_info["deep_search"],
            }
        return None
    finally:
        conn.close()


# Initialize DB on import
init_db()


def set_user_tier(target_username, new_tier, admin_username="admin"):
    """Set a user's membership tier. Admin function."""
    if new_tier not in TIER_LIMITS and new_tier != "admin":
        return {"success": False, "error": "无效的会员等级"}
    conn = _get_db()
    try:
        row = conn.execute("SELECT id FROM users WHERE username=?", (target_username,)).fetchone()
        if not row:
            return {"success": False, "error": "用户不存在"}
        conn.execute("UPDATE users SET tier=? WHERE username=?", (new_tier, target_username))
        conn.commit()
        return {"success": True, "message": f"{target_username} 已升级为 {new_tier}"}
    finally:
        conn.close()


def get_all_users():
    conn = _get_db()
    try:
        rows = conn.execute("SELECT id, username, email, tier, created_at FROM users ORDER BY id").fetchall()
        users = []
        for row in rows:
            usage = check_usage(row["id"])
            users.append({
                "id": row["id"], "username": row["username"],
                "email": row["email"] or "", "tier": row["tier"],
                "today_searches": usage,
                "created_at": str(row["created_at"]) if row["created_at"] else "",
            })
        return users
    finally:
        conn.close()


# Create admin user if not exists
_ADMIN_EXISTS = False
conn = _get_db()
admin = conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()
if not admin:
    pw_hash, salt = _hash_password("admin123456")
    conn.execute("INSERT INTO users (username, password_hash, salt, tier, token) VALUES (?,?,?,?,?)",
                 ("admin", pw_hash, salt, "admin", ""))
    conn.commit()
_ADMIN_EXISTS = True
conn.close()




def register_by_email(email, password):
    """Register a new user using email as both username and email field."""
    conn = _get_db()
    try:
        # Check if email already in use
        existing = conn.execute("SELECT id FROM users WHERE email=? OR username=?", (email, email)).fetchone()
        if existing:
            return {"success": False, "error": "该邮箱已被注册"}
        pw_hash, salt = _hash_password(password)
        token = uuid.uuid4().hex
        conn.execute("INSERT INTO users (username, password_hash, salt, email, token) VALUES (?,?,?,?,?)",
                     (email, pw_hash, salt, email, token))
        conn.commit()
        return {"success": True, "token": token, "tier": "free", "username": email}
    except sqlite3.IntegrityError:
        return {"success": False, "error": "该邮箱已被注册"}
    finally:
        conn.close()


def login_by_email(email, password):
    """Login by email address (checks email column in users table)."""
    conn = _get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not row:
            # Also try username column for backward compatibility with old accounts
            row = conn.execute("SELECT * FROM users WHERE username=?", (email,)).fetchone()
        if not row:
            return {"success": False, "error": "邮箱或密码错误"}
        pw_hash, _ = _hash_password(password, row["salt"])
        if pw_hash != row["password_hash"]:
            return {"success": False, "error": "邮箱或密码错误"}
        # Generate new token
        token = uuid.uuid4().hex
        conn.execute("UPDATE users SET token=? WHERE id=?", (token, row["id"]))
        conn.commit()
        return {"success": True, "token": token, "tier": row["tier"], "username": row["username"]}
    finally:
        conn.close()


# --- Payment System ---
PAYMENT_DB = os.path.join(os.path.dirname(DB_PATH), "payments.json")


def save_payment_config(config: dict):
    """Save admin payment config (QR code, contact info)."""
    config_path = os.path.join(os.path.dirname(DB_PATH), "payment_config.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_payment_config() -> dict:
    """Get admin payment config."""
    config_path = os.path.join(os.path.dirname(DB_PATH), "payment_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "wechat_id": "请管理员设置微信号",
        "alipay_account": "请管理员设置支付宝",
        "qr_code_url": "",
        "price": "99",
        "contact": "",
    }


def add_payment_notification(username: str, amount: str = "99", contact: str = "") -> dict:
    """User submits payment notification."""
    os.makedirs(os.path.dirname(PAYMENT_DB), exist_ok=True)
    payments = []
    if os.path.exists(PAYMENT_DB):
        with open(PAYMENT_DB, "r", encoding="utf-8") as f:
            payments = json.load(f)
    notif = {
        "id": len(payments) + 1,
        "username": username,
        "amount": amount,
        "contact": contact,
        "status": "pending",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    payments.append(notif)
    with open(PAYMENT_DB, "w", encoding="utf-8") as f:
        json.dump(payments, f, ensure_ascii=False, indent=2)
    return notif


def get_pending_payments() -> list:
    """Get all pending payments."""
    if os.path.exists(PAYMENT_DB):
        with open(PAYMENT_DB, "r", encoding="utf-8") as f:
            payments = json.load(f)
        return [p for p in payments if p.get("status") == "pending"]
    return []


def confirm_payment(notification_id: int) -> bool:
    """Admin confirms payment."""
    if os.path.exists(PAYMENT_DB):
        with open(PAYMENT_DB, "r", encoding="utf-8") as f:
            payments = json.load(f)
        found = False
        for p in payments:
            if p["id"] == notification_id:
                p["status"] = "confirmed"
                found = True
                break
        if found:
            with open(PAYMENT_DB, "w", encoding="utf-8") as f:
                json.dump(payments, f, ensure_ascii=False, indent=2)
        return found
    return False


# --- API Token Management ---
def create_api_token(owner: str, tier: str = "free") -> str:
    """Create a new API token."""
    conn = _get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS api_tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT UNIQUE NOT NULL, owner TEXT, tier TEXT DEFAULT 'free', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_used TIMESTAMP, is_active INTEGER DEFAULT 1)")
    token = uuid.uuid4().hex + uuid.uuid4().hex[:16]
    conn.execute("INSERT INTO api_tokens (token, owner, tier) VALUES (?,?,?)", (token, owner, tier))
    conn.commit()
    conn.close()
    return token


def get_api_tokens() -> list:
    conn = _get_db()
    pass
    rows = conn.execute("SELECT * FROM api_tokens ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def revoke_api_token(token_id: int) -> bool:
    conn = _get_db()
    conn.execute("UPDATE api_tokens SET is_active=0 WHERE id=?", (token_id,))
    conn.commit()
    affected = conn.total_changes
    conn.close()
    return affected > 0

# Ensure table exists
_init_conn = _get_db()
_init_conn.execute("CREATE TABLE IF NOT EXISTS api_tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT UNIQUE NOT NULL, owner TEXT, tier TEXT DEFAULT 'free', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_used TIMESTAMP, is_active INTEGER DEFAULT 1)")
_init_conn.commit()


def change_password(user_id, old_password, new_password):
    """Change password for authenticated user. Returns dict."""
    conn = _get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            return {"success": False, "error": "用户不存在"}
        # Verify old password
        pw_hash, _ = _hash_password(old_password, row["salt"])
        if pw_hash != row["password_hash"]:
            return {"success": False, "error": "原密码错误"}
        # Set new password
        new_hash, new_salt = _hash_password(new_password)
        token = uuid.uuid4().hex
        conn.execute("UPDATE users SET password_hash=?, salt=?, token=? WHERE id=?",
                     (new_hash, new_salt, token, user_id))
        conn.commit()
        return {"success": True, "token": token, "message": "密码修改成功"}
    finally:
        conn.close()


def admin_reset_password(username_or_email, new_password):
    """Admin force-resets a user's password. Returns dict."""
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username=? OR email=?",
            (username_or_email, username_or_email)
        ).fetchone()
        if not row:
            return {"success": False, "error": "用户不存在"}
        new_hash, new_salt = _hash_password(new_password)
        token = uuid.uuid4().hex
        conn.execute("UPDATE users SET password_hash=?, salt=?, token=? WHERE id=?",
                     (new_hash, new_salt, token, row["id"]))
        conn.commit()
        return {"success": True, "message": f"密码已重置"}
    finally:
        conn.close()

_init_conn.close()
