import json
import os
from datetime import datetime

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "products": f"{DATA_DIR}/products.json",
    "users": f"{DATA_DIR}/users.json",
    "orders": f"{DATA_DIR}/orders.json",
    "vouchers": f"{DATA_DIR}/vouchers.json",
}

SETTINGS_FILE = f"{DATA_DIR}/settings.json"
LOGS_FILE = f"{DATA_DIR}/logs.json"
ADMINS_FILE = f"{DATA_DIR}/admins.json"

DEFAULT_DATA = {
    "products": {
        "1": {
            "name": "Akun Premium Netflix 1 Bulan",
            "price": 50000,
            "stock": 10,
            "category": "Streaming",
            "description": "Akun Netflix premium sharing 1 bulan, garansi 30 hari.",
            "content": "📧 Email: netflix1@arl.com\n🔑 Password: ArlNetflix2026\n👥 Profil: 1\n📅 Aktif: 30 hari",
            "rating": 4.8,
            "sold": 0,
        },
        "2": {
            "name": "Voucher Google Play Rp50.000",
            "price": 48000,
            "stock": 25,
            "category": "Voucher",
            "description": "Voucher Google Play Indonesia, dikirim via chat.",
            "content": "🎟️ Kode Voucher: GPLAY50K-XXXX-YYYY\n💰 Saldo: Rp50.000\n📱 Bisa untuk semua akun Google Play Indonesia",
            "rating": 5.0,
            "sold": 0,
        },
        "3": {
            "name": "Jasa Desain Logo Premium",
            "price": 150000,
            "stock": 5,
            "category": "Jasa",
            "description": "Desain logo profesional, revisi 3x, file mentah.",
            "content": "",
            "rating": 4.9,
            "sold": 0,
        },
    },
    "users": {},
    "orders": {},
    "vouchers": {
        "ARLNEW": {"type": "percent", "value": 10, "max_use": 100, "used": 0},
        "ARLHEMAT": {"type": "fixed", "value": 5000, "max_use": 50, "used": 0},
    },
}

DEFAULT_SETTINGS = {
    "store_name": "ARL INFINITY",
    "tagline": "Toko Digital Terpercaya",
    "description": "ARL INFINITY adalah toko online terpercaya yang menyediakan berbagai produk digital & fisik berkualitas.",
    "admin_username": "username_anda",
    "channel_username": "channel_anda",
    "payments": {
        "bca": {"name": "BCA", "number": "1234567890", "holder": "ARL INFINITY"},
        "dana": {"name": "DANA", "number": "081234567890", "holder": "ARL INFINITY"},
        "gopay": {"name": "GoPay", "number": "081234567890", "holder": "ARL INFINITY"},
        "qris": {"name": "QRIS", "number": "Scan QR di channel", "holder": "ARL INFINITY"},
    },
    "min_topup": 10000,
}


# ================== UTIL ==================
def _load(key):
    path = FILES[key]
    if not os.path.exists(path):
        _save(key, DEFAULT_DATA[key])
        return DEFAULT_DATA[key]
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(key, data):
    with open(FILES[key], "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def _load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4, ensure_ascii=False)
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ================== PRODUCTS ==================
def get_products():
    return _load("products")


def get_product(pid):
    return _load("products").get(str(pid))


def save_product(pid, data):
    products = _load("products")
    products[str(pid)] = data
    _save("products", products)


def delete_product(pid):
    products = _load("products")
    products.pop(str(pid), None)
    _save("products", products)


def reduce_stock(pid, qty=1):
    products = _load("products")
    pid = str(pid)
    if pid in products:
        products[pid]["stock"] = max(0, products[pid]["stock"] - qty)
        products[pid]["sold"] = products[pid].get("sold", 0) + qty
        _save("products", products)


def get_product_content(pid):
    """Ambil isi produk (konten otomatis). Return string atau '' jika kosong."""
    p = get_product(pid)
    if not p:
        return ""
    return p.get("content", "").strip()


# ================== USERS ==================
def get_user(uid, first_name=None, username=None):
    users = _load("users")
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "id": uid,
            "first_name": first_name,
            "username": username,
            "balance": 0,
            "total_spent": 0,
            "joined": datetime.now().isoformat(),
            "cart": {},
        }
        _save("users", users)
    else:
        updated = False
        if first_name and users[uid].get("first_name") != first_name:
            users[uid]["first_name"] = first_name
            updated = True
        if username != users[uid].get("username"):
            users[uid]["username"] = username
            updated = True
        if updated:
            _save("users", users)
    return users[uid]


def save_user(uid, data):
    users = _load("users")
    users[str(uid)] = data
    _save("users", users)


def get_all_users():
    return _load("users")


def update_balance(uid, amount):
    user = get_user(uid)
    user["balance"] = user.get("balance", 0) + amount
    save_user(uid, user)
    return user["balance"]


def ban_user(uid, banned=True):
    user = get_user(uid)
    user["banned"] = banned
    save_user(uid, user)


def is_banned(uid):
    return get_user(uid).get("banned", False)


# ================== CART ==================
def add_to_cart(uid, pid, qty=1):
    user = get_user(uid)
    cart = user.get("cart", {})
    cart[str(pid)] = cart.get(str(pid), 0) + qty
    user["cart"] = cart
    save_user(uid, user)
    return cart


def remove_from_cart(uid, pid):
    user = get_user(uid)
    cart = user.get("cart", {})
    cart.pop(str(pid), None)
    user["cart"] = cart
    save_user(uid, user)


def clear_cart(uid):
    user = get_user(uid)
    user["cart"] = {}
    save_user(uid, user)


# ================== ORDERS ==================
def create_order(uid, items, total, payment, voucher=None):
    orders = _load("orders")
    oid = f"INV{datetime.now().strftime('%Y%m%d%H%M%S')}{uid}"
    orders[oid] = {
        "id": oid,
        "user_id": str(uid),
        "items": items,
        "total": total,
        "payment": payment,
        "voucher": voucher,
        "status": "pending",
        "created": datetime.now().isoformat(),
    }
    _save("orders", orders)
    return oid


def get_order(oid):
    return _load("orders").get(oid)


def get_order_by_invoice(inv):
    return _load("orders").get(inv)


def update_order_status(oid, status):
    orders = _load("orders")
    if oid in orders:
        orders[oid]["status"] = status
        _save("orders", orders)


def get_user_orders(uid):
    orders = _load("orders")
    return [o for o in orders.values() if o["user_id"] == str(uid)]


def get_all_orders():
    return _load("orders")


def get_orders_by_status(status):
    orders = _load("orders")
    return [o for o in orders.values() if o["status"] == status]


# ================== VOUCHERS ==================
def get_voucher(code):
    return _load("vouchers").get(code.upper())


def use_voucher(code):
    vouchers = _load("vouchers")
    code = code.upper()
    if code in vouchers:
        vouchers[code]["used"] = vouchers[code].get("used", 0) + 1
        _save("vouchers", vouchers)


def add_voucher(code, vtype, value, max_use=100):
    vouchers = _load("vouchers")
    vouchers[code.upper()] = {
        "type": vtype,
        "value": value,
        "max_use": max_use,
        "used": 0,
    }
    _save("vouchers", vouchers)


# ================== SETTINGS ==================
def get_settings():
    return _load_json(SETTINGS_FILE, DEFAULT_SETTINGS)


def save_settings(data):
    _save_json(SETTINGS_FILE, data)


def update_setting(key, value):
    s = get_settings()
    s[key] = value
    save_settings(s)


# ================== LOGS ==================
def add_log(admin_id, action, detail=""):
    logs = _load_json(LOGS_FILE, [])
    logs.append({
        "time": datetime.now().isoformat(),
        "admin": str(admin_id),
        "action": action,
        "detail": detail,
    })
    logs = logs[-500:]
    _save_json(LOGS_FILE, logs)


def get_logs(limit=30):
    logs = _load_json(LOGS_FILE, [])
    return logs[-limit:][::-1]


# ================== ADMINS ==================
def get_admins():
    return _load_json(ADMINS_FILE, {"admins": []})


def add_admin(uid):
    data = get_admins()
    if str(uid) not in data["admins"]:
        data["admins"].append(str(uid))
        _save_json(ADMINS_FILE, data)
        return True
    return False


def remove_admin(uid):
    data = get_admins()
    if str(uid) in data["admins"]:
        data["admins"].remove(str(uid))
        _save_json(ADMINS_FILE, data)
        return True
    return False


def is_admin_db(uid):
    return str(uid) in get_admins().get("admins", [])