import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

import config
import database as db
import admin as adm
from state import user_state
from keyboards import (
    main_menu, back_button, catalog_categories, category_products,
    product_detail, cart_menu, payment_menu, admin_menu,
)
from profile_card import generate_profile_card, format_tanggal_id
from notif_order import post_notif_order

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def is_admin(uid):
    return uid in config.ADMIN_IDS or db.is_admin_db(uid)


def format_rupiah(n):
    return f"Rp{int(n):,}".replace(",", ".")


def escape_md(text):
    if not text:
        return ""
    for ch in ["_", "*", "[", "]", "`"]:
        text = text.replace(ch, f"\\{ch}")
    return text


def kb_back(target="main_menu", label="🔙 Kembali"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=target)]
    ])


async def safe_edit(query, context, text, reply_markup=None):
    """Edit pesan dengan aman."""
    msg = query.message
    has_text = msg.text is not None or msg.caption is not None

    if has_text and msg.photo is None:
        try:
            await query.edit_message_text(text, reply_markup=reply_markup)
            return
        except Exception as e:
            logger.warning(f"edit_message_text gagal: {e}")

    try:
        await msg.delete()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=text,
        reply_markup=reply_markup
    )


# ================== COMMAND HANDLERS ==================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if db.is_banned(user.id):
        await update.message.reply_text("🚫 Akun Anda telah diblokir. Hubungi admin.")
        return

    db.get_user(user.id, first_name=user.first_name, username=user.username)
    is_adm = is_admin(user.id)
    settings = db.get_settings()

    safe_name = escape_md(user.first_name or "User")

    if is_adm:
        header = "👑 SELAMAT DATANG, ADMIN! 👑\n"
    else:
        header = f"✨ Selamat Datang di {settings['store_name']} ✨\n"

    caption = (
        f"{header}"
        f"{settings['tagline']}\n\n"
        f"Halo {safe_name}! 👋\n\n"
        f"{settings['description']}\n\n"
        f"Silakan pilih menu di bawah ini 🛒"
    )

    image = getattr(config, "WELCOME_IMAGE", "")

    if image:
        try:
            await update.message.reply_photo(
                photo=image,
                caption=caption,
                reply_markup=main_menu(is_admin=is_adm)
            )
            return
        except Exception as e:
            logger.error(f"Gagal kirim foto: {e}")

    await update.message.reply_text(
        caption,
        reply_markup=main_menu(is_admin=is_adm)
    )


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Anda bukan admin.")
        return
    await update.message.reply_text(
        "👑 ADMIN PANEL ARL INFINITY\n\nPilih menu:",
        reply_markup=adm.adm_main_kb()
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = db.get_settings()
    text = (
        "📖 Bantuan ARL INFINITY\n\n"
        "/start - Menu utama\n"
        "/help - Bantuan\n"
        "/admin - Panel admin (khusus admin)\n\n"
        f"Butuh bantuan? Hubungi admin @{settings['admin_username']}"
    )
    await update.message.reply_text(text, reply_markup=kb_back())


# ================== CALLBACK HANDLERS ==================
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    uid = query.from_user.id
    await query.answer()

    if db.is_banned(uid):
        try:
            await query.edit_message_text("🚫 Akun Anda telah diblokir.")
        except Exception:
            await context.bot.send_message(uid, "🚫 Akun Anda telah diblokir.")
        return

    # ===== ROUTING KE ADMIN =====
    if data.startswith(("adm_", "ordok_", "ordno_")):
        if adm.is_admin(uid):
            return await adm.handle_admin_callback(query, context, data, uid)
        else:
            await query.answer("⛔ Bukan admin!", show_alert=True)
            return

    products = db.get_products()
    user = db.get_user(uid)

    # ---------- MAIN MENU ----------
    if data == "main_menu":
        settings = db.get_settings()
        is_adm = is_admin(uid)

        safe_name = escape_md(query.from_user.first_name or "User")

        if is_adm:
            header = "👑 SELAMAT DATANG, ADMIN! 👑\n"
        else:
            header = f"✨ Selamat Datang di {settings['store_name']} ✨\n"

        caption = (
            f"{header}"
            f"{settings['tagline']}\n\n"
            f"Halo {safe_name}! 👋\n\n"
            f"{settings['description']}\n\n"
            f"Silakan pilih menu di bawah ini 🛒"
        )

        try:
            await query.message.delete()
        except Exception:
            pass

        image = getattr(config, "WELCOME_IMAGE", "")

        if image:
            try:
                await context.bot.send_photo(
                    chat_id=uid,
                    photo=image,
                    caption=caption,
                    reply_markup=main_menu(is_admin=is_adm)
                )
                return
            except Exception as e:
                logger.error(f"Gagal kirim foto: {e}")

        await context.bot.send_message(
            chat_id=uid,
            text=caption,
            reply_markup=main_menu(is_admin=is_adm)
        )
        return

    # ---------- ABOUT ----------
    if data == "about":
        settings = db.get_settings()
        text = (
            f"ℹ️ Tentang {settings['store_name']}\n\n"
            f"{settings['description']}\n\n"
            f"✅ Produk original\n"
            f"✅ Pelayanan cepat 24 jam\n"
            f"✅ Harga bersaing\n"
            f"✅ Garansi uang kembali\n\n"
            f"📢 Channel: @{settings['channel_username']}"
        )
        await safe_edit(query, context, text, kb_back())
        return

    # ---------- CATALOG (DENGAN FOTO) ----------
    if data == "catalog":
        if not products:
            await safe_edit(query, context, "❌ Belum ada produk tersedia.", kb_back())
            return

        caption = "🛍️ *Katalog Produk*\n\nPilih kategori di bawah ini:"
        image = "https://i.ibb.co/xtxmWcDp/katalog-produk.png"
        kb = catalog_categories(products)

        try:
            await query.message.delete()
        except Exception:
            pass

        try:
            await context.bot.send_photo(
                chat_id=uid,
                photo=image,
                caption=caption,
                reply_markup=kb,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Gagal kirim foto katalog: {e}")
            await context.bot.send_message(
                chat_id=uid,
                text=caption,
                reply_markup=kb,
                parse_mode="Markdown"
            )
        return

    if data.startswith("cat_"):
        cat = data[4:]
        await safe_edit(query, context, f"📂 Kategori: {cat}\n\nPilih produk:",
                        category_products(cat, products))
        return

    # ---------- PRODUCT DETAIL (DENGAN FOTO) ----------
    if data.startswith("product_"):
        pid = data.split("_")[1]
        p = db.get_product(pid)
        if not p:
            await safe_edit(query, context, "❌ Produk tidak ditemukan.", kb_back("catalog"))
            return

        caption = (
            f"📦 *{p['name']}*\n\n"
            f"💰 Harga: *{format_rupiah(p['price'])}*\n"
            f"📊 Stok: {p['stock']}\n"
            f"⭐ Rating: {p.get('rating', '-')} ({p.get('sold', 0)} terjual)\n"
            f"📂 Kategori: {p['category']}\n\n"
            f"📝 {p.get('description', '-')}"
        )

        image = (p.get("image") or "").strip()

        try:
            await query.message.delete()
        except Exception:
            pass

        if image:
            try:
                await context.bot.send_photo(
                    chat_id=uid,
                    photo=image,
                    caption=caption,
                    reply_markup=product_detail(pid),
                    parse_mode="Markdown"
                )
                return
            except Exception as e:
                logger.error(f"Gagal kirim foto produk {pid}: {e}")
                await context.bot.send_message(
                    chat_id=uid,
                    text=(
                        f"📦 {p['name']}\n\n"
                        f"💰 Harga: {format_rupiah(p['price'])}\n"
                        f"📊 Stok: {p['stock']}\n"
                        f"⭐ Rating: {p.get('rating', '-')} ({p.get('sold', 0)} terjual)\n"
                        f"📂 Kategori: {p['category']}\n\n"
                        f"📝 {p.get('description', '-')}"
                    ),
                    reply_markup=product_detail(pid)
                )
                return

        try:
            await context.bot.send_message(
                chat_id=uid,
                text=caption,
                reply_markup=product_detail(pid),
                parse_mode="Markdown"
            )
        except Exception:
            await context.bot.send_message(
                chat_id=uid,
                text=(
                    f"📦 {p['name']}\n\n"
                    f"💰 Harga: {format_rupiah(p['price'])}\n"
                    f"📊 Stok: {p['stock']}\n"
                    f"📂 Kategori: {p['category']}\n\n"
                    f"📝 {p.get('description', '-')}"
                ),
                reply_markup=product_detail(pid)
            )
        return

    # ---------- ADD TO CART ----------
    if data.startswith("addcart_"):
        pid = data.split("_")[1]
        p = db.get_product(pid)
        if not p or p["stock"] < 1:
            await query.answer("❌ Stok habis!", show_alert=True)
            return
        db.add_to_cart(uid, pid, 1)
        await query.answer("✅ Ditambahkan ke keranjang!", show_alert=True)
        return

    # ---------- BUY NOW ----------
    if data.startswith("buynow_"):
        pid = data.split("_")[1]
        p = db.get_product(pid)
        if not p or p["stock"] < 1:
            await query.answer("❌ Stok habis!", show_alert=True)
            return
        db.clear_cart(uid)
        db.add_to_cart(uid, pid, 1)
        await show_checkout(query, context, uid)
        return

    # ---------- REVIEW ----------
    if data.startswith("review_"):
        pid = data.split("_")[1]
        p = db.get_product(pid)
        text = (
            f"⭐ Testimoni - {p['name']}\n\n"
            f"Rating rata-rata: {p.get('rating', '-')}/5\n"
            f"Total terjual: {p.get('sold', 0)}\n\n"
            "Terima kasih untuk semua pembeli! 🙏"
        )
        await safe_edit(query, context, text, kb_back(f"product_{pid}"))
        return

    # ---------- CART ----------
    if data == "cart":
        user = db.get_user(uid)
        cart = user.get("cart", {})
        if not cart:
            await safe_edit(query, context, "🛒 Keranjang Anda kosong.", kb_back())
            return
        total = sum(products[pid]["price"] * qty for pid, qty in cart.items() if pid in products)
        text = f"🛒 Keranjang Anda\n\nTotal: {format_rupiah(total)}\n\nKlik ❌ untuk hapus item:"
        await safe_edit(query, context, text, cart_menu(cart, products))
        return

    if data.startswith("rmcart_"):
        pid = data.split("_")[1]
        db.remove_from_cart(uid, pid)
        await query.answer("✅ Item dihapus.")
        user = db.get_user(uid)
        cart = user.get("cart", {})
        if not cart:
            await safe_edit(query, context, "🛒 Keranjang kosong.", kb_back())
            return
        total = sum(products[pid]["price"] * qty for pid, qty in cart.items() if pid in products)
        text = f"🛒 Keranjang Anda\n\nTotal: {format_rupiah(total)}"
        await safe_edit(query, context, text, cart_menu(cart, products))
        return

    if data == "clearcart":
        db.clear_cart(uid)
        await safe_edit(query, context, "🗑️ Keranjang dikosongkan.", kb_back())
        return

    # ---------- CHECKOUT ----------
    if data == "checkout":
        await show_checkout(query, context, uid)
        return

    if data.startswith("pay_"):
        method = data[4:]
        await process_payment(query, context, uid, method)
        return

    # ---------- MY ORDERS ----------
    if data == "my_orders":
        orders = db.get_user_orders(uid)
        if not orders:
            await safe_edit(query, context, "📦 Belum ada pesanan.", kb_back())
            return
        text = "📦 Pesanan Anda\n\n"
        for o in orders[-10:]:
            emoji = {"pending": "⏳", "paid": "✅", "rejected": "❌", "done": "🎉"}.get(o["status"], "❔")
            text += f"{emoji} {o['id']} - {format_rupiah(o['total'])} ({o['status']})\n"
        await safe_edit(query, context, text, kb_back())
        return

    # ---------- BALANCE ----------
    if data == "balance":
        settings = db.get_settings()
        text = (
            f"💰 Saldo Anda\n\n"
            f"Saldo: {format_rupiah(user.get('balance', 0))}\n"
            f"Total belanja: {format_rupiah(user.get('total_spent', 0))}\n\n"
            f"Minimal top-up: {format_rupiah(settings['min_topup'])}"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Top-Up Saldo", callback_data="topup")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")],
        ])
        await safe_edit(query, context, text, kb)
        return

    if data == "topup":
        user_state[uid] = {"action": "topup"}
        settings = db.get_settings()
        await safe_edit(query, context,
            f"💰 Top-Up Saldo\n\nKirim nominal top-up (minimal {format_rupiah(settings['min_topup'])}).\n"
            f"Contoh: 50000\n\nKetik /cancel untuk batal.",
            kb_back()
        )
        return

    # ---------- PROFILE (KTP DIGITAL) ----------
    if data == "profile":
        u = query.from_user
        user = db.get_user(uid, first_name=u.first_name, username=u.username)

        photo_bytes = None
        try:
            photos = await context.bot.get_user_profile_photos(uid, limit=1)
            if photos.total_count > 0:
                file_id = photos.photos[0][-1].file_id
                tg_file = await context.bot.get_file(file_id)
                photo_bytes = bytes(await tg_file.download_as_bytearray())
        except Exception:
            pass

        settings = db.get_settings()
        try:
            card = generate_profile_card(
                user, u,
                store_name=settings["store_name"],
                photo_bytes=photo_bytes,
            )

            caption = (
                f"👤 DETAIL AKUN ANDA\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🆔 ID Telegram: {u.id}\n"
                f"📛 Nama Akun: {u.first_name or '-'}\n"
                f"🔗 Username: {'@' + u.username if u.username else 'Tidak ada'}\n"
                f"📅 Terdaftar Sejak: {format_tanggal_id(user.get('joined', ''))}\n\n"
                f"💰 Saldo: {format_rupiah(user.get('balance', 0))}\n"
                f"🛒 Total Belanja: {format_rupiah(user.get('total_spent', 0))}\n\n"
                f"Kartu di atas adalah identitas digital Anda di {settings['store_name']}."
            )

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh Kartu", callback_data="profile")],
                [InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")],
            ])

            try:
                await query.message.delete()
            except Exception:
                pass

            await context.bot.send_photo(
                chat_id=uid,
                photo=card,
                caption=caption,
                reply_markup=kb
            )
        except Exception as e:
            logger.error(f"Gagal generate kartu profil: {e}")
            text = (
                f"👤 DETAIL AKUN ANDA\n\n"
                f"🆔 ID: {u.id}\n"
                f"📛 Nama: {u.first_name or '-'}\n"
                f"🔗 Username: @{u.username or '-'}\n"
                f"📅 Bergabung: {format_tanggal_id(user.get('joined', ''))}\n\n"
                f"💰 Saldo: {format_rupiah(user.get('balance', 0))}\n"
                f"🛒 Total Belanja: {format_rupiah(user.get('total_spent', 0))}"
            )
            await safe_edit(query, context, text, kb_back())
        return

    # ---------- SEARCH ----------
    if data == "search":
        user_state[uid] = {"action": "search"}
        await safe_edit(query, context,
            "🔍 Cari Produk\n\nKetik nama produk yang ingin dicari.\nKetik /cancel untuk batal.",
            kb_back()
        )
        return

    # ---------- VOUCHER ----------
    if data == "voucher":
        user_state[uid] = {"action": "voucher"}
        await safe_edit(query, context,
            "🎟️ Pakai Voucher\n\nKetik kode voucher Anda.\nKetik /cancel untuk batal.",
            kb_back()
        )
        return

    # ---------- FALLBACK ----------
    await safe_edit(query, context, "❓ Menu tidak dikenal.", kb_back())
    return


# ================== CHECKOUT & PAYMENT ==================
async def show_checkout(query, context, uid):
    user = db.get_user(uid)
    cart = user.get("cart", {})
    products = db.get_products()
    if not cart:
        await safe_edit(query, context, "🛒 Keranjang kosong.", kb_back())
        return
    total = sum(products[pid]["price"] * qty for pid, qty in cart.items() if pid in products)
    text = (
        f"🧾 Konfirmasi Checkout\n\n"
        f"Total item: {sum(cart.values())}\n"
        f"Total bayar: {format_rupiah(total)}\n\n"
        f"Pilih metode pembayaran:"
    )
    await safe_edit(query, context, text, payment_menu())


async def process_payment(query, context, uid, method):
    user = db.get_user(uid)
    cart = user.get("cart", {})
    products = db.get_products()
    settings = db.get_settings()
    if not cart:
        await safe_edit(query, context, "🛒 Keranjang kosong.", kb_back())
        return

    total = sum(products[pid]["price"] * qty for pid, qty in cart.items() if pid in products)

    if method == "balance":
        if user.get("balance", 0) < total:
            await query.answer("❌ Saldo tidak cukup!", show_alert=True)
            return
        db.update_balance(uid, -total)
        oid = db.create_order(uid, cart, total, "Saldo", None)
        db.update_order_status(oid, "paid")
        for pid, qty in cart.items():
            db.reduce_stock(pid, qty)
        db.clear_cart(uid)
        user = db.get_user(uid)
        user["total_spent"] = user.get("total_spent", 0) + total
        db.save_user(uid, user)

        text = (
            f"🎉 Pembayaran Berhasil!\n\n"
            f"Order ID: {oid}\n"
            f"Total: {format_rupiah(total)}\n\n"
            f"Produk akan segera dikirim oleh admin. Terima kasih! 🙏"
        )
        await safe_edit(query, context, text, kb_back())

        for aid in config.ADMIN_IDS:
            try:
                await context.bot.send_message(
                    aid,
                    f"🔔 Pesanan Baru (Saldo)\n\nOrder: {oid}\nUser: {uid}\nTotal: {format_rupiah(total)}"
                )
            except Exception:
                pass

        # ===== POST NOTIF KE CHANNEL TESTIMONI =====
        try:
            channel = getattr(config, "TESTIMONI_CHANNEL", "")
            order_data = db.get_order(oid)
            if channel and order_data:
                await post_notif_order(
                    context.bot,
                    channel,
                    order_data,
                    uid,
                    store_name=db.get_settings().get("store_name", "ARL INFINITY")
                )
        except Exception as e:
            logger.warning(f"Gagal kirim notif ke channel: {e}")
        return

    p = settings["payments"].get(method)
    if not p:
        await query.answer("❌ Metode tidak valid.", show_alert=True)
        return

    oid = db.create_order(uid, cart, total, p["name"], None)
    db.clear_cart(uid)

    user_state[uid] = {"action": "send_proof", "order_id": oid}

    text = (
        f"🧾 Instruksi Pembayaran\n\n"
        f"Order ID: {oid}\n"
        f"Total: {format_rupiah(total)}\n\n"
        f"💳 Metode: {p['name']}\n"
        f"No. Rekening: {p['number']}\n"
        f"Atas Nama: {p['holder']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📸 Setelah transfer, KIRIM FOTO BUKTI TRANSFER di chat ini.\n\n"
        f"Admin akan verifikasi & konfirmasi pesanan Anda.\n\n"
        f"Ketik /cancel untuk membatalkan."
    )
    await safe_edit(query, context, text, kb_back())

    for aid in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                aid,
                f"🔔 Pesanan Baru (Menunggu Bukti TF)\n\n"
                f"Order: {oid}\nUser: {uid}\nTotal: {format_rupiah(total)}\nMetode: {p['name']}"
            )
        except Exception:
            pass


# ================== HANDLER FOTO BUKTI TF ==================
async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    state = user_state.get(uid)

    if not state or state.get("action") != "send_proof":
        return

    order_id = state.get("order_id")
    order = db.get_order(order_id)
    if not order:
        user_state.pop(uid, None)
        await update.message.reply_text(
            "❌ Pesanan tidak ditemukan. Silakan /start ulang.",
            reply_markup=kb_back()
        )
        return

    photo_file_id = update.message.photo[-1].file_id
    user_caption = update.message.caption or "-"

    orders = db._load("orders")
    if order_id in orders:
        orders[order_id]["proof_file_id"] = photo_file_id
        orders[order_id]["proof_caption"] = user_caption
        orders[order_id]["proof_sent_at"] = db.datetime.now().isoformat()
        db._save("orders", orders)

    sent = False
    for aid in config.ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id=aid,
                photo=photo_file_id,
                caption=(
                    f"📸 BUKTI TRANSFER BARU\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🧾 Order: {order_id}\n"
                    f"👤 User ID: {uid}\n"
                    f"💰 Total: {format_rupiah(order['total'])}\n"
                    f"💳 Metode: {order['payment']}\n\n"
                    f"📝 Catatan user: {user_caption}"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Konfirmasi", callback_data=f"ordok_{order_id}"),
                     InlineKeyboardButton("❌ Tolak", callback_data=f"ordno_{order_id}")]
                ])
            )
            sent = True
        except Exception as e:
            logger.error(f"Gagal forward bukti ke admin {aid}: {e}")

    user_state.pop(uid, None)

    if sent:
        await update.message.reply_text(
            f"✅ Bukti transfer diterima!\n\n"
            f"Order ID: {order_id}\n"
            f"Total: {format_rupiah(order['total'])}\n\n"
            f"⏳ Silakan tunggu konfirmasi dari admin.\n"
            f"Kami akan mengirim notifikasi jika pesanan sudah diproses.\n\n"
            f"Terima kasih! 🙏",
            reply_markup=kb_back()
        )
    else:
        await update.message.reply_text(
            "⚠️ Bukti Anda diterima, tapi gagal diteruskan ke admin.\n"
            f"Mohon kirim bukti langsung ke admin @{db.get_settings()['admin_username']}",
            reply_markup=kb_back()
        )


# ================== TEXT HANDLER ==================
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    state = user_state.get(uid)

    if db.is_banned(uid):
        await update.message.reply_text("🚫 Akun Anda telah diblokir.")
        return

    if state and state.get("action", "").startswith("adm_"):
        handled = await adm.handle_admin_text(update, context, state)
        if handled:
            return

    if not state:
        await update.message.reply_text(
            "Ketik /start untuk membuka menu.",
            reply_markup=kb_back()
        )
        return

    action = state.get("action")

    if text.lower() == "/cancel":
        user_state.pop(uid, None)
        await update.message.reply_text(
            "❌ Dibatalkan.",
            reply_markup=main_menu(is_admin=is_admin(uid))
        )
        return

    if action == "send_proof":
        await update.message.reply_text(
            "📸 Mohon kirim FOTO bukti transfer Anda (bukan teks).\n\n"
            "Kalau ingin membatalkan, ketik /cancel.",
            reply_markup=kb_back()
        )
        return

    # ---------- SEARCH ----------
    if action == "search":
        products = db.get_products()
        results = [p for p in products.items() if text.lower() in p[1]["name"].lower()]
        user_state.pop(uid, None)
        if not results:
            await update.message.reply_text(
                "🔍 Tidak ditemukan.",
                reply_markup=kb_back()
            )
            return
        kb = [[InlineKeyboardButton(f"{p['name']} - {format_rupiah(p['price'])}",
                                     callback_data=f"product_{pid}")]
              for pid, p in results[:10]]
        kb.append([InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")])
        await update.message.reply_text(
            f"🔍 Ditemukan {len(results)} produk:",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    # ---------- VOUCHER ----------
    if action == "voucher":
        v = db.get_voucher(text)
        user_state.pop(uid, None)
        if not v:
            await update.message.reply_text(
                "❌ Voucher tidak valid.",
                reply_markup=kb_back()
            )
            return
        if v.get("used", 0) >= v["max_use"]:
            await update.message.reply_text(
                "❌ Voucher sudah habis.",
                reply_markup=kb_back()
            )
            return
        await update.message.reply_text(
            f"🎟️ Voucher Valid!\n\nKode: {text.upper()}\n"
            f"Diskon: {'%' if v['type']=='percent' else 'Rp'}{v['value']}\n\n"
            f"Voucher akan otomatis diterapkan saat checkout.",
            reply_markup=kb_back()
        )
        return

    # ---------- TOPUP ----------
    if action == "topup":
        settings = db.get_settings()
        try:
            amount = int(text.replace(".", "").replace(",", ""))
            if amount < settings["min_topup"]:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                f"❌ Nominal tidak valid. Minimal {format_rupiah(settings['min_topup'])}.",
                reply_markup=kb_back()
            )
            return
        user_state.pop(uid, None)
        rekening = "\n".join([f"• {p['name']}: {p['number']} a/n {p['holder']}"
                              for p in settings["payments"].values()])
        text_out = (
            f"💰 Top-Up {format_rupiah(amount)}\n\n"
            f"Transfer ke salah satu rekening:\n\n{rekening}\n\n"
            f"Setelah transfer, kirim bukti ke @{settings['admin_username']}\n"
            f"Sertakan ID Anda: {uid}"
        )
        await update.message.reply_text(text_out, reply_markup=kb_back())
        return

    # ---------- FALLBACK ----------
    await update.message.reply_text(
        "❓ Perintah tidak dikenal. Ketik /start untuk membuka menu.",
        reply_markup=kb_back()
    )


# ================== MAIN ==================
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("cancel", on_text))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    print("🤖 ARL INFINITY Bot berjalan...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    print(">>> Memulai bot...")
    try:
        main()
    except Exception as e:
        print(f">>> ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("Tekan ENTER untuk keluar...")