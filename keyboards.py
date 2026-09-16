from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu(is_admin=False):
    keyboard = [
        [InlineKeyboardButton("🛍️ Katalog Produk", callback_data="catalog")],
        [InlineKeyboardButton("🛒 Keranjang Saya", callback_data="cart"),
         InlineKeyboardButton("📦 Pesanan Saya", callback_data="my_orders")],
        [InlineKeyboardButton("💰 Saldo Saya", callback_data="balance"),
         InlineKeyboardButton("👤 Profil", callback_data="profile")],
        [InlineKeyboardButton("🔍 Cari Produk", callback_data="search"),
         InlineKeyboardButton("🎟️ Pakai Voucher", callback_data="voucher")],
        [InlineKeyboardButton("📞 Hubungi Admin", url="https://t.me/username_anda")],
        [InlineKeyboardButton("ℹ️ Tentang Kami", callback_data="about")],
    ]

    # Tombol khusus admin — muncul di paling atas
    if is_admin:
        keyboard.insert(0, [
            InlineKeyboardButton("Menu Admin", callback_data="adm_main")
        ])

    return InlineKeyboardMarkup(keyboard)


def back_button(target="main_menu", label="🔙 Kembali"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=target)]
    ])


def catalog_categories(products):
    categories = sorted({p["category"] for p in products.values()})
    keyboard = []
    for cat in categories:
        keyboard.append([InlineKeyboardButton(f"📂 {cat}", callback_data=f"cat_{cat}")])
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def category_products(cat, products):
    keyboard = []
    for pid, p in products.items():
        if p["category"] == cat:
            keyboard.append([
                InlineKeyboardButton(
                    f"{p['name']} - Rp{p['price']:,} (stok {p['stock']})",
                    callback_data=f"product_{pid}"
                )
            ])
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="catalog")])
    return InlineKeyboardMarkup(keyboard)


def product_detail(pid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Tambah ke Keranjang", callback_data=f"addcart_{pid}")],
        [InlineKeyboardButton("⚡ Beli Sekarang", callback_data=f"buynow_{pid}")],
        [InlineKeyboardButton("⭐ Testimoni", callback_data=f"review_{pid}")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="catalog")],
    ])


def cart_menu(cart, products):
    keyboard = []
    for pid, qty in cart.items():
        if pid in products:
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ {products[pid]['name']} x{qty}",
                    callback_data=f"rmcart_{pid}"
                )
            ])
    if cart:
        keyboard.append([InlineKeyboardButton("✅ Checkout", callback_data="checkout")])
        keyboard.append([InlineKeyboardButton("🗑️ Kosongkan", callback_data="clearcart")])
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def payment_menu():
    from config import PAYMENTS
    keyboard = []
    for key, p in PAYMENTS.items():
        keyboard.append([InlineKeyboardButton(f"💳 {p['name']}", callback_data=f"pay_{key}")])
    keyboard.append([InlineKeyboardButton("💰 Bayar dengan Saldo", callback_data="pay_balance")])
    keyboard.append([InlineKeyboardButton("🔙 Batal", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Kelola Produk", callback_data="adm_products")],
        [InlineKeyboardButton("🧾 Pesanan Masuk", callback_data="adm_orders")],
        [InlineKeyboardButton("👥 Data User", callback_data="adm_users")],
        [InlineKeyboardButton("🎟️ Kelola Voucher", callback_data="adm_vouchers")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")],
        [InlineKeyboardButton("📊 Statistik", callback_data="adm_stats")],
        [InlineKeyboardButton("🔙 Tutup", callback_data="main_menu")],
    ])