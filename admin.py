import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import config
import database as db
from state import user_state

logger = logging.getLogger(__name__)


def is_admin(uid):
    return uid in config.ADMIN_IDS or db.is_admin_db(uid)


def fmt(n):
    return f"Rp{int(n):,}".replace(",", ".")


def adm_main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard", callback_data="adm_dashboard")],
        [InlineKeyboardButton("📦 Kelola Produk", callback_data="adm_products"),
         InlineKeyboardButton("🧾 Kelola Pesanan", callback_data="adm_orders")],
        [InlineKeyboardButton("👥 Kelola User", callback_data="adm_users"),
         InlineKeyboardButton("🎟️ Kelola Voucher", callback_data="adm_vouchers")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast"),
         InlineKeyboardButton("⚙️ Pengaturan Toko", callback_data="adm_settings")],
        [InlineKeyboardButton("📝 Log Aktivitas", callback_data="adm_logs"),
         InlineKeyboardButton("💾 Backup Data", callback_data="adm_backup")],
        [InlineKeyboardButton("👑 Kelola Admin", callback_data="adm_admins")],
        [InlineKeyboardButton("🔙 Kembali ke Menu Utama", callback_data="main_menu")],
    ])


def back_kb(target="adm_main", label="🔙 Kembali"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=target)]
    ])


async def admin_edit(query, context, text, reply_markup=None, parse_mode=None):
    """Safe edit pesan admin — works untuk pesan foto maupun teks."""
    msg = query.message
    try:
        if msg.photo is not None:
            await query.edit_message_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        return
    except Exception as e:
        logger.warning(f"admin_edit gagal: {e}")

    try:
        await msg.delete()
    except Exception:
        pass
    try:
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except Exception as e:
        logger.error(f"admin_edit fallback gagal: {e}")


# ================== MAIN HANDLER ==================
async def handle_admin_callback(query, context, data, uid):
    if not is_admin(uid):
        await query.answer("⛔ Anda bukan admin!", show_alert=True)
        return

    # ============ PANEL UTAMA ============
    if data == "adm_main":
        await admin_edit(
            query, context,
            "👑 *ADMIN PANEL ARL INFINITY*\n\n"
            "Selamat datang, Admin! Pilih menu di bawah ini:",
            adm_main_kb(),
            parse_mode="Markdown"
        )
        return

    # ============ DASHBOARD ============
    if data == "adm_dashboard":
        orders = db.get_all_orders()
        users = db.get_all_users()
        products = db.get_products()
        vouchers_raw = db._load("vouchers")

        total_income = sum(o["total"] for o in orders.values() if o["status"] == "paid")
        pending_count = sum(1 for o in orders.values() if o["status"] == "pending")
        paid_count = sum(1 for o in orders.values() if o["status"] == "paid")
        total_stock = sum(p.get("stock", 0) for p in products.values())
        low_stock = [p for p in products.values() if p.get("stock", 0) <= 3]

        text = (
            "📊 *DASHBOARD ARL INFINITY*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 Total User: *{len(users)}*\n"
            f"📦 Total Produk: *{len(products)}*\n"
            f"🎟️ Total Voucher: *{len(vouchers_raw)}*\n\n"
            f"🧾 Total Order: *{len(orders)}*\n"
            f"   ⏳ Pending: *{pending_count}*\n"
            f"   ✅ Sukses: *{paid_count}*\n\n"
            f"💰 Total Pendapatan: *{fmt(total_income)}*\n"
            f"📊 Total Stok: *{total_stock} unit*\n"
        )
        if low_stock:
            text += f"\n⚠️ *Stok menipis:* {len(low_stock)} produk\n"
            for p in low_stock[:5]:
                text += f"  • {p['name']} (stok {p['stock']})\n"

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="adm_dashboard")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="adm_main")],
        ])
        await admin_edit(query, context, text, kb, parse_mode="Markdown")
        return

    # ============ KELOLA PRODUK ============
    if data == "adm_products":
        products = db.get_products()
        text = "📦 *KELOLA PRODUK*\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        if products:
            for pid, p in products.items():
                stock_emoji = "🔴" if p["stock"] <= 3 else "🟢" if p["stock"] > 10 else "🟡"
                content_status = "✅ Auto" if (p.get("content") or "").strip() else "⏳ Manual"
                img_status = "🖼️ Ada" if (p.get("image") or "").strip() else "❌ Tidak ada"
                text += f"{stock_emoji} `{pid}` *{p['name']}*\n"
                text += f"   💰 {fmt(p['price'])} | 📊 stok {p['stock']} | 📂 {p['category']}\n"
                text += f"   📦 Delivery: {content_status} | Foto: {img_status}\n\n"
        else:
            text += "_Belum ada produk._\n"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Tambah Produk", callback_data="adm_prod_add")],
            [InlineKeyboardButton("✏️ Edit Produk", callback_data="adm_prod_edit"),
             InlineKeyboardButton("🗑️ Hapus Produk", callback_data="adm_prod_del")],
            [InlineKeyboardButton("📊 Restock Produk", callback_data="adm_prod_restock")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="adm_main")],
        ])
        await admin_edit(query, context, text, kb, parse_mode="Markdown")
        return

    if data == "adm_prod_add":
        user_state[uid] = {"action": "adm_addprod", "step": "name", "data": {}}
        await admin_edit(
            query, context,
            "➕ *TAMBAH PRODUK BARU*\n\nMasukkan **nama produk**:\n\n_Ketik /cancel untuk batal._",
            parse_mode="Markdown"
        )
        return

    if data == "adm_prod_edit":
        products = db.get_products()
        if not products:
            await query.answer("Belum ada produk.", show_alert=True)
            return
        kb = [[InlineKeyboardButton(f"{p['name']} (ID:{pid})", callback_data=f"adm_prodedit_{pid}")]
              for pid, p in products.items()]
        kb.append([InlineKeyboardButton("🔙 Kembali", callback_data="adm_products")])
        await admin_edit(
            query, context,
            "✏️ *Pilih produk yang ingin diedit:*",
            InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )
        return

    if data.startswith("adm_prodedit_"):
        pid = data.split("_")[2]
        p = db.get_product(pid)
        if not p:
            await query.answer("Produk tidak ditemukan.", show_alert=True)
            return
        content_preview = (p.get("content") or "-")[:150]
        image_preview = (p.get("image") or "-")[:150]
        text = (
            f"✏️ *EDIT PRODUK*\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📦 Nama: {p['name']}\n"
            f"💰 Harga: {fmt(p['price'])}\n"
            f"📊 Stok: {p['stock']}\n"
            f"📂 Kategori: {p['category']}\n"
            f"📝 Deskripsi: {p.get('description', '-')}\n\n"
            f"🖼️ Foto URL:\n`{image_preview}`\n\n"
            f"📦 Isi Produk:\n`{content_preview}`\n\n"
            f"Pilih field yang ingin diubah:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Nama", callback_data=f"adm_editf_{pid}_name"),
             InlineKeyboardButton("💰 Harga", callback_data=f"adm_editf_{pid}_price")],
            [InlineKeyboardButton("📊 Stok", callback_data=f"adm_editf_{pid}_stock"),
             InlineKeyboardButton("📂 Kategori", callback_data=f"adm_editf_{pid}_category")],
            [InlineKeyboardButton("📝 Deskripsi", callback_data=f"adm_editf_{pid}_description")],
            [InlineKeyboardButton("🖼️ Foto Produk (URL)", callback_data=f"adm_editf_{pid}_image")],
            [InlineKeyboardButton("📦 Isi Produk (Auto-Delivery)", callback_data=f"adm_editf_{pid}_content")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="adm_prod_edit")],
        ])
        await admin_edit(query, context, text, kb, parse_mode="Markdown")
        return

    if data.startswith("adm_editf_"):
        parts = data.split("_", 3)
        pid = parts[2]
        field = parts[3]
        user_state[uid] = {"action": "adm_editfield", "pid": pid, "field": field}
        label = {"name": "nama", "price": "harga (angka)",
                 "stock": "stok (angka)", "category": "kategori",
                 "description": "deskripsi", "content": "isi produk (auto-delivery)",
                 "image": "link/URL foto produk"}.get(field, field)

        if field == "content":
            await admin_edit(
                query, context,
                f"✏️ Masukkan **{label}** baru:\n\n"
                f"💡 Bisa multi-baris. Ketik `-` (strip) untuk mengosongkan.\n\n"
                f"_Ketik /cancel untuk batal._",
                parse_mode="Markdown"
            )
        elif field == "image":
            await admin_edit(
                query, context,
                f"✏️ Masukkan **{label}** baru:\n\n"
                f"📸 Contoh: `https://i.ibb.co/xxxxx/foto.jpg`\n\n"
                f"💡 Ketik `-` (strip) untuk menghapus foto.\n\n"
                f"_Ketik /cancel untuk batal._",
                parse_mode="Markdown"
            )
        else:
            await admin_edit(
                query, context,
                f"✏️ Masukkan **{label}** baru:\n\n_Ketik /cancel untuk batal._",
                parse_mode="Markdown"
            )
        return

    if data == "adm_prod_del":
        products = db.get_products()
        if not products:
            await query.answer("Belum ada produk.", show_alert=True)
            return
        kb = [[InlineKeyboardButton(f"🗑️ {p['name']} (ID:{pid})", callback_data=f"adm_proddel_{pid}")]
              for pid, p in products.items()]
        kb.append([InlineKeyboardButton("🔙 Kembali", callback_data="adm_products")])
        await admin_edit(
            query, context,
            "🗑️ *Pilih produk yang ingin dihapus:*\n\n_⚠️ Tindakan ini tidak bisa dibatalkan!_",
            InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )
        return

    if data.startswith("adm_proddel_"):
        pid = data.split("_")[2]
        p = db.get_product(pid)
        if not p:
            await query.answer("Produk tidak ditemukan.", show_alert=True)
            return
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ya, Hapus", callback_data=f"adm_proddelok_{pid}")],
            [InlineKeyboardButton("❌ Batal", callback_data="adm_products")],
        ])
        await admin_edit(
            query, context,
            f"⚠️ Yakin ingin menghapus *{p['name']}*?",
            kb,
            parse_mode="Markdown"
        )
        return

    if data.startswith("adm_proddelok_"):
        pid = data.split("_")[2]
        p = db.get_product(pid)
        db.delete_product(pid)
        db.add_log(uid, "hapus_produk", f"ID:{pid} - {p.get('name', '?') if p else '?'}")
        await admin_edit(query, context, "✅ Produk berhasil dihapus.", back_kb("adm_products"))
        return

    if data == "adm_prod_restock":
        products = db.get_products()
        if not products:
            await query.answer("Belum ada produk.", show_alert=True)
            return
        kb = [[InlineKeyboardButton(f"{p['name']} (stok {p['stock']})", callback_data=f"adm_restock_{pid}")]
              for pid, p in products.items()]
        kb.append([InlineKeyboardButton("🔙 Kembali", callback_data="adm_products")])
        await admin_edit(
            query, context,
            "📊 *Pilih produk untuk restock:*",
            InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )
        return

    if data.startswith("adm_restock_"):
        pid = data.split("_")[2]
        user_state[uid] = {"action": "adm_restock", "pid": pid}
        await admin_edit(
            query, context,
            "📊 Masukkan jumlah stok yang ingin **ditambahkan** (bisa negatif untuk kurangi):\n\n"
            "_Contoh: 10 atau -5_\n\n_Ketik /cancel untuk batal._",
            parse_mode="Markdown"
        )
        return

    # ============ KELOLA PESANAN ============
    if data == "adm_orders":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏳ Pending", callback_data="adm_ord_pending"),
             InlineKeyboardButton("✅ Sukses", callback_data="adm_ord_paid")],
            [InlineKeyboardButton("❌ Ditolak", callback_data="adm_ord_rejected"),
             InlineKeyboardButton("📋 Semua", callback_data="adm_ord_all")],
            [InlineKeyboardButton("🔍 Cari Invoice", callback_data="adm_ord_search")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="adm_main")],
        ])
        await admin_edit(
            query, context,
            "🧾 *KELOLA PESANAN*\n\nPilih filter:",
            kb,
            parse_mode="Markdown"
        )
        return

    if data.startswith("adm_ord_"):
        filter_type = data.split("_")[2]
        if filter_type == "search":
            user_state[uid] = {"action": "adm_search_order"}
            await admin_edit(
                query, context,
                "🔍 Masukkan Invoice ID atau User ID:\n\n_Ketik /cancel untuk batal._",
                parse_mode="Markdown"
            )
            return
        orders = db.get_all_orders()
        if filter_type == "all":
            filtered = list(orders.values())
        else:
            filtered = [o for o in orders.values() if o["status"] == filter_type]

        if not filtered:
            await admin_edit(
                query, context,
                f"📭 Tidak ada pesanan dengan status *{filter_type}*.",
                back_kb("adm_orders"),
                parse_mode="Markdown"
            )
            return

        filtered = sorted(filtered, key=lambda o: o["created"], reverse=True)[:5]
        for o in filtered:
            emoji = {"pending": "⏳", "paid": "✅", "rejected": "❌", "done": "🎉"}.get(o["status"], "❔")
            text = (
                f"{emoji} *INVOICE* `{o['id']}`\n"
                f"👤 User: `{o['user_id']}`\n"
                f"💰 Total: *{fmt(o['total'])}*\n"
                f"💳 Metode: {o['payment']}\n"
                f"📅 {o['created'][:19]}\n"
                f"📦 Items:\n"
            )
            products = db.get_products()
            for pid, qty in o["items"].items():
                pname = products.get(pid, {}).get("name", f"ID:{pid}")
                text += f"  • {pname} x{qty}\n"
            kb_rows = []
            if o["status"] == "pending":
                kb_rows.append([
                    InlineKeyboardButton("✅ Konfirmasi", callback_data=f"ordok_{o['id']}"),
                    InlineKeyboardButton("❌ Tolak", callback_data=f"ordno_{o['id']}"),
                ])
            elif o["status"] == "paid":
                kb_rows.append([
                    InlineKeyboardButton("✅ Sudah Dikirim ke Customer", callback_data="noop")
                ])
            elif o["status"] == "rejected":
                kb_rows.append([
                    InlineKeyboardButton("❌ Ditolak", callback_data="noop")
                ])
            kb_rows.append([
                InlineKeyboardButton("💬 Chat User", callback_data=f"adm_chatuser_{o['user_id']}")
            ])
            await query.message.reply_text(
                text, reply_markup=InlineKeyboardMarkup(kb_rows), parse_mode="Markdown"
            )
        await admin_edit(
            query, context,
            f"📋 Menampilkan {len(filtered)} pesanan.",
            back_kb("adm_orders")
        )
        return

    # ============ KONFIRMASI ORDER (AUTO-DELIVERY + NOTIF CHANNEL) ============
    if data.startswith("ordok_"):
        oid = data[6:]
        order = db.get_order(oid)
        if not order:
            await query.answer("Order tidak ditemukan.", show_alert=True)
            return
        if order["status"] == "paid":
            await query.answer("Pesanan ini sudah dikonfirmasi sebelumnya.", show_alert=True)
            return

        db.update_order_status(oid, "paid")
        products_data = db.get_products()
        for pid, qty in order["items"].items():
            db.reduce_stock(pid, qty)
        db.add_log(uid, "konfirmasi_order", oid)

        # Bangun pesan delivery
        delivery_lines = []
        for pid, qty in order["items"].items():
            p = products_data.get(pid, {})
            pname = p.get("name", f"Produk ID:{pid}")
            pcontent = (p.get("content") or "").strip()

            delivery_lines.append(f"📦 {pname}")
            delivery_lines.append(f"   Qty: {qty}")

            if pcontent:
                for i in range(qty):
                    if qty > 1:
                        delivery_lines.append(f"   ── Unit {i+1} ──")
                    delivery_lines.append(f"   {pcontent}")
            else:
                delivery_lines.append(f"   ⏳ Produk akan dikirim manual oleh admin")

            delivery_lines.append("")

        delivery_text = "\n".join(delivery_lines).strip()

        user_msg = (
            f"🎉 *PESANAN ANDA TELAH DIKIRIM!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🧾 Order ID: `{oid}`\n"
            f"💰 Total: {fmt(order['total'])}\n"
            f"📅 Tanggal: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📋 *Detail Produk:*\n\n"
            f"{delivery_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Simpan pesan ini sebagai bukti pembelian.\n"
            f"Jika ada kendala, hubungi admin @{config.ADMIN_USERNAME}\n\n"
            f"Terima kasih telah berbelanja! 🙏"
        )

        try:
            await context.bot.send_message(
                int(order["user_id"]),
                user_msg,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Gagal kirim delivery markdown: {e}")
            try:
                await context.bot.send_message(
                    int(order["user_id"]),
                    f"🎉 PESANAN ANDA TELAH DIKIRIM!\n\n"
                    f"Order ID: {oid}\n"
                    f"Total: {fmt(order['total'])}\n\n"
                    f"Detail Produk:\n{delivery_text}\n\n"
                    f"Terima kasih!"
                )
            except Exception as e2:
                logger.error(f"Gagal kirim delivery fallback: {e2}")

        # ===== POST NOTIF KE CHANNEL TESTIMONI =====
        try:
            from notif_order import post_notif_order
            channel = getattr(config, "TESTIMONI_CHANNEL", "")
            if channel:
                store_name = db.get_settings().get("store_name", "ARL INFINITY")
                await post_notif_order(
                    context.bot,
                    channel,
                    order,
                    order["user_id"],
                    store_name=store_name
                )
        except Exception as e:
            logger.warning(f"Gagal kirim notif ke channel: {e}")

        # Update pesan admin
        new_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Sudah Dikirim ke Customer", callback_data="noop")]
        ])

        if query.message.photo:
            old_caption = query.message.caption or ""
            new_caption = (
                f"{old_caption}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ STATUS: DIKONFIRMASI & DIKIRIM\n"
                f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
            await admin_edit(query, context, new_caption, new_kb)
        else:
            new_text = (
                f"✅ *PESANAN DIKONFIRMASI & DIKIRIM*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🧾 Order: `{oid}`\n"
                f"👤 User: `{order['user_id']}`\n"
                f"💰 Total: *{fmt(order['total'])}*\n\n"
                f"🕐 Dikonfirmasi: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
            await admin_edit(query, context, new_text, new_kb, parse_mode="Markdown")

        await query.answer("✅ Pesanan dikonfirmasi & produk otomatis dikirim!", show_alert=False)
        return

    # ============ TOLAK ORDER ============
    if data.startswith("ordno_"):
        oid = data[6:]
        order = db.get_order(oid)
        if not order:
            await query.answer("Order tidak ditemukan.", show_alert=True)
            return
        if order["status"] == "rejected":
            await query.answer("Pesanan ini sudah ditolak sebelumnya.", show_alert=True)
            return

        db.update_order_status(oid, "rejected")
        db.add_log(uid, "tolak_order", oid)

        try:
            await context.bot.send_message(
                int(order["user_id"]),
                f"❌ *Pesanan Ditolak*\n\n"
                f"Invoice: `{oid}`\n\n"
                f"Silakan hubungi admin @{config.ADMIN_USERNAME} untuk info lanjut.",
                parse_mode="Markdown"
            )
        except Exception:
            pass

        new_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Ditolak", callback_data="noop")]
        ])

        if query.message.photo:
            old_caption = query.message.caption or ""
            new_caption = (
                f"{old_caption}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"❌ STATUS: DITOLAK\n"
                f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
            await admin_edit(query, context, new_caption, new_kb)
        else:
            new_text = (
                f"❌ *PESANAN DITOLAK*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🧾 Order: `{oid}`\n"
                f"👤 User: `{order['user_id']}`\n"
                f"💰 Total: *{fmt(order['total'])}*\n\n"
                f"🕐 Ditolak: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
            await admin_edit(query, context, new_text, new_kb, parse_mode="Markdown")

        await query.answer("❌ Pesanan ditolak.", show_alert=False)
        return

    if data == "noop":
        await query.answer("Status sudah final.", show_alert=False)
        return

    # ============ KELOLA USER ============
    if data == "adm_users":
        users = db.get_all_users()
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 List User", callback_data="adm_user_list")],
            [InlineKeyboardButton("🔍 Cari User", callback_data="adm_user_search")],
            [InlineKeyboardButton("💰 Top-Up User", callback_data="adm_user_topup")],
            [InlineKeyboardButton("🚫 Ban/Unban User", callback_data="adm_user_ban")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="adm_main")],
        ])
        await admin_edit(
            query, context,
            f"👥 *KELOLA USER*\n\nTotal user: *{len(users)}*\n\nPilih menu:",
            kb,
            parse_mode="Markdown"
        )
        return

    if data == "adm_user_list":
        users = db.get_all_users()
        sorted_users = sorted(users.values(), key=lambda u: u.get("total_spent", 0), reverse=True)[:20]
        text = "👥 *TOP 20 USER (berdasarkan belanja)*\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, u in enumerate(sorted_users, 1):
            status = "🚫" if u.get("banned") else "✅"
            text += (f"{i}. {status} `{u['id']}`\n"
                     f"   💰 Saldo: {fmt(u.get('balance', 0))}\n"
                     f"   🛒 Belanja: {fmt(u.get('total_spent', 0))}\n\n")
        await admin_edit(query, context, text, back_kb("adm_users"), parse_mode="Markdown")
        return

    if data == "adm_user_search":
        user_state[uid] = {"action": "adm_search_user"}
        await admin_edit(
            query, context,
            "🔍 Masukkan User ID:\n\n_Ketik /cancel untuk batal._",
            parse_mode="Markdown"
        )
        return

    if data == "adm_user_topup":
        user_state[uid] = {"action": "adm_topup_user", "step": "uid"}
        await admin_edit(
            query, context,
            "💰 *TOP-UP SALDO USER*\n\nMasukkan User ID:\n\n_Ketik /cancel untuk batal._",
            parse_mode="Markdown"
        )
        return

    if data == "adm_user_ban":
        user_state[uid] = {"action": "adm_ban_user"}
        await admin_edit(
            query, context,
            "🚫 *BAN/UNBAN USER*\n\nMasukkan User ID:\n\n_Ketik /cancel untuk batal._",
            parse_mode="Markdown"
        )
        return

    # ============ VOUCHER ============
    if data == "adm_vouchers":
        vouchers = db._load("vouchers")
        text = "🎟️ *KELOLA VOUCHER*\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        if vouchers:
            for code, v in vouchers.items():
                tipe = "Percent" if v["type"] == "percent" else "Fixed"
                val = f"{v['value']}%" if v["type"] == "percent" else fmt(v["value"])
                text += (f"🎫 `{code}`\n"
                         f"   💰 {tipe}: {val}\n"
                         f"   📊 Used: {v.get('used', 0)}/{v['max_use']}\n\n")
        else:
            text += "_Belum ada voucher._\n"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Tambah", callback_data="adm_vcr_add")],
            [InlineKeyboardButton("🗑️ Hapus", callback_data="adm_vcr_del"),
             InlineKeyboardButton("🔄 Reset Usage", callback_data="adm_vcr_reset")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="adm_main")],
        ])
        await admin_edit(query, context, text, kb, parse_mode="Markdown")
        return

    if data == "adm_vcr_add":
        user_state[uid] = {"action": "adm_addvoucher", "step": "code", "data": {}}
        await admin_edit(
            query, context,
            "➕ *TAMBAH VOUCHER*\n\nMasukkan kode voucher (contoh: PROMO50):\n\n_Ketik /cancel untuk batal._",
            parse_mode="Markdown"
        )
        return

    if data == "adm_vcr_del":
        vouchers = db._load("vouchers")
        if not vouchers:
            await query.answer("Belum ada voucher.", show_alert=True)
            return
        kb = [[InlineKeyboardButton(f"🗑️ {code}", callback_data=f"adm_vcrdel_{code}")]
              for code in vouchers.keys()]
        kb.append([InlineKeyboardButton("🔙 Kembali", callback_data="adm_vouchers")])
        await admin_edit(
            query, context,
            "🗑️ *Pilih voucher untuk dihapus:*",
            InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )
        return

    if data.startswith("adm_vcrdel_"):
        code = data.split("_")[2]
        vouchers = db._load("vouchers")
        vouchers.pop(code, None)
        db._save("vouchers", vouchers)
        db.add_log(uid, "hapus_voucher", code)
        await admin_edit(
            query, context,
            f"✅ Voucher `{code}` dihapus.",
            back_kb("adm_vouchers"),
            parse_mode="Markdown"
        )
        return

    if data == "adm_vcr_reset":
        user_state[uid] = {"action": "adm_reset_voucher"}
        await admin_edit(
            query, context,
            "🔄 Masukkan kode voucher yang ingin di-reset penggunaannya:\n\n_Ketik /cancel untuk batal._",
            parse_mode="Markdown"
        )
        return

    # ============ BROADCAST ============
    if data == "adm_broadcast":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Ke Semua User", callback_data="adm_bc_all")],
            [InlineKeyboardButton("👤 Ke User Tertentu", callback_data="adm_bc_user")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="adm_main")],
        ])
        await admin_edit(
            query, context,
            "📢 *BROADCAST*\n\nPilih target:",
            kb,
            parse_mode="Markdown"
        )
        return

    if data == "adm_bc_all":
        user_state[uid] = {"action": "adm_broadcast_all"}
        await admin_edit(
            query, context,
            "📢 *BROADCAST KE SEMUA USER*\n\n"
            "Kirim pesan yang akan dikirim ke semua user.\n"
            "Mendukung format Markdown: *bold*, _italic_, `code`.\n\n"
            "_Ketik /cancel untuk batal._",
            parse_mode="Markdown"
        )
        return

    if data == "adm_bc_user":
        user_state[uid] = {"action": "adm_broadcast_user", "step": "uid"}
        await admin_edit(
            query, context,
            "👤 Masukkan User ID target:\n\n_Ketik /cancel untuk batal._",
            parse_mode="Markdown"
        )
        return

    # ============ PENGATURAN TOKO ============
    if data == "adm_settings":
        s = db.get_settings()
        text = (
            "⚙️ *PENGATURAN TOKO*\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏪 Nama Toko: *{s['store_name']}*\n"
            f"📝 Tagline: _{s['tagline']}_\n"
            f"📄 Deskripsi: {s['description'][:100]}...\n\n"
            f"📞 Admin: @{s['admin_username']}\n"
            f"📢 Channel: @{s['channel_username']}\n\n"
            f"💰 Min Top-Up: {fmt(s['min_topup'])}\n\n"
            f"💳 Rekening:\n"
        )
        for k, p in s["payments"].items():
            text += f"  • {p['name']}: `{p['number']}` ({p['holder']})\n"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏪 Nama Toko", callback_data="adm_set_store_name")],
            [InlineKeyboardButton("📝 Tagline", callback_data="adm_set_tagline")],
            [InlineKeyboardButton("📄 Deskripsi", callback_data="adm_set_description")],
            [InlineKeyboardButton("📞 Admin Username", callback_data="adm_set_admin_username")],
            [InlineKeyboardButton("📢 Channel Username", callback_data="adm_set_channel_username")],
            [InlineKeyboardButton("💰 Min Top-Up", callback_data="adm_set_min_topup")],
            [InlineKeyboardButton("💳 Rekening", callback_data="adm_set_payments")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="adm_main")],
        ])
        await admin_edit(query, context, text, kb, parse_mode="Markdown")
        return

    if data in ("adm_set_store_name", "adm_set_tagline", "adm_set_description",
                "adm_set_admin_username", "adm_set_channel_username", "adm_set_min_topup"):
        key_map = {
            "adm_set_store_name": "store_name",
            "adm_set_tagline": "tagline",
            "adm_set_description": "description",
            "adm_set_admin_username": "admin_username",
            "adm_set_channel_username": "channel_username",
            "adm_set_min_topup": "min_topup",
        }
        key = key_map[data]
        user_state[uid] = {"action": "adm_set_field", "key": key}
        label = key.replace("_", " ").title()
        await admin_edit(
            query, context,
            f"⚙️ Masukkan nilai baru untuk *{label}*:\n\n_Ketik /cancel untuk batal._",
            parse_mode="Markdown"
        )
        return

    if data == "adm_set_payments":
        s = db.get_settings()
        text = "💳 *PENGATURAN REKENING*\n\n"
        for k, p in s["payments"].items():
            text += f"• *{p['name']}* → `{p['number']}`\n  a/n {p['holder']}\n\n"
        kb = [[InlineKeyboardButton(f"✏️ {p['name']}", callback_data=f"adm_setpay_{k}")]
              for k, p in s["payments"].items()]
        kb.append([InlineKeyboardButton("🔙 Kembali", callback_data="adm_settings")])
        await admin_edit(
            query, context,
            text,
            InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )
        return

    if data.startswith("adm_setpay_"):
        key = data.split("_")[2]
        user_state[uid] = {"action": "adm_set_payment", "key": key, "step": "number"}
        s = db.get_settings()
        await admin_edit(
            query, context,
            f"💳 Edit *{s['payments'][key]['name']}*\n\nMasukkan nomor rekening baru:\n\n_Ketik /cancel untuk batal._",
            parse_mode="Markdown"
        )
        return

    # ============ LOG ============
    if data == "adm_logs":
        logs = db.get_logs(20)
        text = "📝 *LOG AKTIVITAS (20 terbaru)*\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        if logs:
            for l in logs:
                t = l["time"][:19].replace("T", " ")
                text += f"• `{t}`\n  👑 `{l['admin']}` → *{l['action']}*\n  {l['detail']}\n\n"
        else:
            text += "_Belum ada log._\n"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="adm_logs")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="adm_main")],
        ])
        await admin_edit(query, context, text, kb, parse_mode="Markdown")
        return

    # ============ BACKUP ============
    if data == "adm_backup":
        import os
        import json

        backup_dir = "data/backup"
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        backup_data = {
            "products": db.get_products(),
            "users": db.get_all_users(),
            "orders": db.get_all_orders(),
            "vouchers": db._load("vouchers"),
            "settings": db.get_settings(),
        }
        path = f"{backup_dir}/backup_{timestamp}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=4, ensure_ascii=False)

        with open(path, "rb") as f:
            await query.message.reply_document(
                document=f,
                filename=f"arl_backup_{timestamp}.json",
                caption=f"💾 *Backup ARL INFINITY*\n\nTanggal: {timestamp}\n"
                        f"Total: {len(backup_data['products'])} produk, "
                        f"{len(backup_data['users'])} user, "
                        f"{len(backup_data['orders'])} order",
                parse_mode="Markdown"
            )
        db.add_log(uid, "backup_data", f"file: {path}")
        await admin_edit(
            query, context,
            "✅ Backup berhasil dibuat & dikirim ke chat ini.",
            back_kb("adm_main")
        )
        return

    # ============ KELOLA ADMIN ============
    if data == "adm_admins":
        db_admins = db.get_admins().get("admins", [])
        text = "👑 *KELOLA ADMIN*\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        text += "*Super Admin (dari config):*\n"
        for a in config.ADMIN_IDS:
            text += f"  🔒 `{a}`\n"
        text += "\n*Admin Tambahan (dari DB):*\n"
        if db_admins:
            for a in db_admins:
                text += f"  ✅ `{a}`\n"
        else:
            text += "  _Belum ada._\n"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Tambah Admin", callback_data="adm_admin_add")],
            [InlineKeyboardButton("➖ Hapus Admin", callback_data="adm_admin_remove")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="adm_main")],
        ])
        await admin_edit(query, context, text, kb, parse_mode="Markdown")
        return

    if data == "adm_admin_add":
        user_state[uid] = {"action": "adm_admin_add"}
        await admin_edit(
            query, context,
            "👑 *TAMBAH ADMIN*\n\nMasukkan User ID yang ingin dijadikan admin:\n\n_Ketik /cancel untuk batal._",
            parse_mode="Markdown"
        )
        return

    if data == "adm_admin_remove":
        user_state[uid] = {"action": "adm_admin_remove"}
        await admin_edit(
            query, context,
            "➖ *HAPUS ADMIN*\n\nMasukkan User ID admin yang ingin dihapus:\n\n_Ketik /cancel untuk batal._",
            parse_mode="Markdown"
        )
        return

    # ============ CHAT USER ============
    if data.startswith("adm_chatuser_"):
        target_uid = data.split("_")[2]
        user_state[uid] = {"action": "adm_chat_user", "target": target_uid}
        await admin_edit(
            query, context,
            f"💬 *KIRIM PESAN KE USER* `{target_uid}`\n\n"
            "Ketik pesan yang ingin dikirim:\n\n_Ketik /cancel untuk batal._",
            parse_mode="Markdown"
        )
        return

    await query.answer("Menu tidak tersedia.", show_alert=True)


# ================== TEXT INPUT HANDLER ==================
async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE, state):
    uid = update.effective_user.id
    text = update.message.text.strip()
    action = state.get("action")

    # ============ TAMBAH PRODUK ============
    if action == "adm_addprod":
        step = state["step"]
        data = state["data"]
        if step == "name":
            data["name"] = text
            state["step"] = "price"
            await update.message.reply_text("💰 Masukkan **harga** (angka saja):", parse_mode="Markdown")
            return True
        if step == "price":
            try:
                data["price"] = int(text.replace(".", "").replace(",", ""))
            except ValueError:
                await update.message.reply_text("❌ Harus angka. Coba lagi:")
                return True
            state["step"] = "stock"
            await update.message.reply_text("📊 Masukkan **stok**:", parse_mode="Markdown")
            return True
        if step == "stock":
            try:
                data["stock"] = int(text)
            except ValueError:
                await update.message.reply_text("❌ Harus angka. Coba lagi:")
                return True
            state["step"] = "category"
            await update.message.reply_text("📂 Masukkan **kategori**:", parse_mode="Markdown")
            return True
        if step == "category":
            data["category"] = text
            state["step"] = "description"
            await update.message.reply_text("📝 Masukkan **deskripsi**:", parse_mode="Markdown")
            return True
        if step == "description":
            data["description"] = text
            state["step"] = "image"
            await update.message.reply_text(
                "🖼️ Masukkan **link/URL foto produk** (yang akan tampil di katalog).\n\n"
                "Contoh: `https://i.ibb.co/xxxxx/foto.jpg`\n\n"
                "💡 Ketik `-` (strip) kalau produk tidak ada foto.\n\n"
                "_Ketik /cancel untuk batal._",
                parse_mode="Markdown"
            )
            return True
        if step == "image":
            data["image"] = "" if text.strip() == "-" else text.strip()
            state["step"] = "content"
            await update.message.reply_text(
                "📦 Masukkan *ISI PRODUK* yang akan otomatis dikirim ke customer setelah pembayaran.\n\n"
                "Contoh:\n"
                "`Email: user@mail.com`\n"
                "`Password: abc123`\n"
                "`Garansi: 30 hari`\n\n"
                "💡 Bisa multi-baris. Ketik `-` (strip) kalau ingin dikirim manual (misal: jasa).\n\n"
                "_Ketik /cancel untuk batal._",
                parse_mode="Markdown"
            )
            return True
        if step == "content":
            data["content"] = "" if text.strip() == "-" else text
            data["rating"] = 5.0
            data["sold"] = 0
            products = db.get_products()
            new_id = str(max([int(k) for k in products.keys()] or [0]) + 1)
            db.save_product(new_id, data)
            db.add_log(uid, "tambah_produk", f"ID:{new_id} - {data['name']}")

            status_auto = "✅ Auto-delivery" if data["content"] else "⏳ Kirim manual"
            img_status = "🖼️ Ada" if data["image"] else "❌ Tidak ada"
            user_state.pop(uid, None)
            await update.message.reply_text(
                f"✅ Produk *{data['name']}* ditambahkan (ID: `{new_id}`).\n"
                f"📦 Delivery: {status_auto}\n"
                f"🖼️ Foto: {img_status}",
                reply_markup=back_kb("adm_products"), parse_mode="Markdown"
            )
            return True

    # ============ EDIT FIELD ============
    if action == "adm_editfield":
        pid = state["pid"]
        field = state["field"]
        p = db.get_product(pid)
        if not p:
            await update.message.reply_text("❌ Produk tidak ditemukan.")
            user_state.pop(uid, None)
            return True
        if field in ("price", "stock"):
            try:
                p[field] = int(text.replace(".", "").replace(",", ""))
            except ValueError:
                await update.message.reply_text("❌ Harus angka. Coba lagi:")
                return True
        elif field == "content":
            p["content"] = "" if text.strip() == "-" else text
        elif field == "image":
            p["image"] = "" if text.strip() == "-" else text.strip()
        else:
            p[field] = text
        db.save_product(pid, p)
        db.add_log(uid, "edit_produk", f"ID:{pid} field:{field}")
        user_state.pop(uid, None)

        status_auto = "✅ Auto-delivery" if (p.get("content") or "").strip() else "⏳ Manual"
        img_status = "🖼️ Ada" if (p.get("image") or "").strip() else "❌ Tidak ada"
        await update.message.reply_text(
            f"✅ Field *{field}* produk `{pid}` berhasil diubah.\n"
            f"📦 Delivery: {status_auto}\n"
            f"🖼️ Foto: {img_status}",
            reply_markup=back_kb("adm_products"), parse_mode="Markdown"
        )
        return True

    # ============ RESTOCK ============
    if action == "adm_restock":
        pid = state["pid"]
        try:
            amount = int(text)
        except ValueError:
            await update.message.reply_text("❌ Harus angka. Coba lagi:")
            return True
        p = db.get_product(pid)
        if not p:
            await update.message.reply_text("❌ Produk tidak ditemukan.")
            user_state.pop(uid, None)
            return True
        p["stock"] = max(0, p["stock"] + amount)
        db.save_product(pid, p)
        db.add_log(uid, "restock", f"ID:{pid} {amount:+d} → {p['stock']}")
        user_state.pop(uid, None)
        await update.message.reply_text(
            f"✅ Stok *{p['name']}* sekarang: *{p['stock']}*",
            reply_markup=back_kb("adm_products"), parse_mode="Markdown"
        )
        return True

    # ============ SEARCH ORDER ============
    if action == "adm_search_order":
        orders = db.get_all_orders()
        found = [o for o in orders.values() if text in o["id"] or text == o["user_id"]]
        user_state.pop(uid, None)
        if not found:
            await update.message.reply_text("❌ Tidak ditemukan.", reply_markup=back_kb("adm_orders"))
            return True
        for o in found[:5]:
            emoji = {"pending": "⏳", "paid": "✅", "rejected": "❌"}.get(o["status"], "❔")
            msg = (f"{emoji} `{o['id']}`\n"
                   f"👤 User: `{o['user_id']}`\n"
                   f"💰 Total: {fmt(o['total'])}\n"
                   f"📅 {o['created'][:19]}\n"
                   f"Status: *{o['status']}*")
            await update.message.reply_text(msg, parse_mode="Markdown")
        await update.message.reply_text("✅ Selesai.", reply_markup=back_kb("adm_orders"))
        return True

    # ============ SEARCH USER ============
    if action == "adm_search_user":
        user = db.get_user(text)
        user_state.pop(uid, None)
        orders = [o for o in db.get_all_orders().values() if o["user_id"] == text]
        text_out = (
            f"👤 *DETAIL USER* `{text}`\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Saldo: *{fmt(user.get('balance', 0))}*\n"
            f"🛒 Total Belanja: *{fmt(user.get('total_spent', 0))}*\n"
            f"📦 Total Order: *{len(orders)}*\n"
            f"🚫 Status: {'Banned' if user.get('banned') else 'Aktif'}\n"
            f"📅 Bergabung: {user.get('joined', '-')[:10]}"
        )
        await update.message.reply_text(text_out, reply_markup=back_kb("adm_users"), parse_mode="Markdown")
        return True

    # ============ TOPUP USER ============
    if action == "adm_topup_user":
        step = state.get("step")
        if step == "uid":
            state["target"] = text
            state["step"] = "amount"
            await update.message.reply_text("💰 Masukkan jumlah top-up (bisa negatif untuk kurangi):")
            return True
        if step == "amount":
            try:
                amount = int(text.replace(".", "").replace(",", ""))
            except ValueError:
                await update.message.reply_text("❌ Harus angka. Coba lagi:")
                return True
            target = state["target"]
            new_balance = db.update_balance(target, amount)
            db.add_log(uid, "topup_user", f"{target} {amount:+d} → {new_balance}")
            user_state.pop(uid, None)
            try:
                await context.bot.send_message(
                    int(target),
                    f"💰 *Saldo Anda telah diubah!*\n\n"
                    f"Perubahan: *{amount:+d}*\n"
                    f"Saldo sekarang: *{fmt(new_balance)}*",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
            await update.message.reply_text(
                f"✅ Saldo user `{target}` diperbarui.\nSaldo sekarang: *{fmt(new_balance)}*",
                reply_markup=back_kb("adm_users"), parse_mode="Markdown"
            )
            return True

    # ============ BAN/UNBAN ============
    if action == "adm_ban_user":
        user = db.get_user(text)
        current = user.get("banned", False)
        db.ban_user(text, not current)
        status = "di-unban" if current else "di-ban"
        db.add_log(uid, "ban_user", f"{text} → {status}")
        user_state.pop(uid, None)
        await update.message.reply_text(
            f"✅ User `{text}` {status}.",
            reply_markup=back_kb("adm_users"), parse_mode="Markdown"
        )
        return True

    # ============ VOUCHER ============
    if action == "adm_addvoucher":
        step = state["step"]
        data = state["data"]
        if step == "code":
            data["code"] = text.upper()
            state["step"] = "type"
            await update.message.reply_text("Tipe: `percent` atau `fixed`:", parse_mode="Markdown")
            return True
        if step == "type":
            if text.lower() not in ("percent", "fixed"):
                await update.message.reply_text("❌ Harus `percent` atau `fixed`:")
                return True
            data["type"] = text.lower()
            state["step"] = "value"
            await update.message.reply_text("Masukkan nilai voucher:")
            return True
        if step == "value":
            try:
                data["value"] = int(text)
            except ValueError:
                await update.message.reply_text("❌ Harus angka. Coba lagi:")
                return True
            state["step"] = "maxuse"
            await update.message.reply_text("Batas maksimal penggunaan (contoh: 100):")
            return True
        if step == "maxuse":
            try:
                max_use = int(text)
            except ValueError:
                await update.message.reply_text("❌ Harus angka:")
                return True
            db.add_voucher(data["code"], data["type"], data["value"], max_use)
            db.add_log(uid, "tambah_voucher", data["code"])
            user_state.pop(uid, None)
            await update.message.reply_text(
                f"✅ Voucher `{data['code']}` ditambahkan.",
                reply_markup=back_kb("adm_vouchers"), parse_mode="Markdown"
            )
            return True

    if action == "adm_reset_voucher":
        vouchers = db._load("vouchers")
        code = text.upper()
        if code not in vouchers:
            await update.message.reply_text("❌ Voucher tidak ditemukan.")
            user_state.pop(uid, None)
            return True
        vouchers[code]["used"] = 0
        db._save("vouchers", vouchers)
        db.add_log(uid, "reset_voucher", code)
        user_state.pop(uid, None)
        await update.message.reply_text(
            f"✅ Penggunaan voucher `{code}` direset.",
            reply_markup=back_kb("adm_vouchers"), parse_mode="Markdown"
        )
        return True

    # ============ BROADCAST ============
    if action == "adm_broadcast_all":
        users = db.get_all_users()
        user_state.pop(uid, None)
        success, failed = 0, 0
        for u in users.values():
            try:
                await context.bot.send_message(int(u["id"]), text, parse_mode="Markdown")
                success += 1
            except Exception:
                failed += 1
        db.add_log(uid, "broadcast_all", f"success:{success} failed:{failed}")
        await update.message.reply_text(
            f"✅ Broadcast selesai.\n\nBerhasil: *{success}*\nGagal: *{failed}*",
            reply_markup=back_kb("adm_main"), parse_mode="Markdown"
        )
        return True

    if action == "adm_broadcast_user":
        step = state.get("step")
        if step == "uid":
            state["target"] = text
            state["step"] = "message"
            await update.message.reply_text("📝 Kirim pesan:")
            return True
        if step == "message":
            target = state["target"]
            try:
                await context.bot.send_message(int(target), text, parse_mode="Markdown")
                await update.message.reply_text("✅ Pesan terkirim.", reply_markup=back_kb("adm_main"))
            except Exception as e:
                await update.message.reply_text(f"❌ Gagal: {e}")
            user_state.pop(uid, None)
            return True

    # ============ SETTINGS ============
    if action == "adm_set_field":
        key = state["key"]
        value = text
        if key == "min_topup":
            try:
                value = int(text.replace(".", "").replace(",", ""))
            except ValueError:
                await update.message.reply_text("❌ Harus angka:")
                return True
        db.update_setting(key, value)
        db.add_log(uid, "setting_update", f"{key}={value}")
        user_state.pop(uid, None)
        await update.message.reply_text(
            f"✅ Pengaturan *{key}* diperbarui.",
            reply_markup=back_kb("adm_settings"), parse_mode="Markdown"
        )
        return True

    if action == "adm_set_payment":
        key = state["key"]
        step = state["step"]
        s = db.get_settings()
        if step == "number":
            s["payments"][key]["number"] = text
            state["step"] = "holder"
            await update.message.reply_text("Masukkan nama pemilik rekening:")
            return True
        if step == "holder":
            s["payments"][key]["holder"] = text
            db.save_settings(s)
            db.add_log(uid, "update_payment", key)
            user_state.pop(uid, None)
            await update.message.reply_text(
                f"✅ Rekening *{s['payments'][key]['name']}* diperbarui.",
                reply_markup=back_kb("adm_settings"), parse_mode="Markdown"
            )
            return True

    # ============ KELOLA ADMIN ============
    if action == "adm_admin_add":
        if db.add_admin(text):
            db.add_log(uid, "add_admin", text)
            await update.message.reply_text(
                f"✅ User `{text}` sekarang menjadi admin.",
                reply_markup=back_kb("adm_admins"), parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❌ User sudah menjadi admin.", reply_markup=back_kb("adm_admins")
            )
        user_state.pop(uid, None)
        return True

    if action == "adm_admin_remove":
        if db.remove_admin(text):
            db.add_log(uid, "remove_admin", text)
            await update.message.reply_text(
                f"✅ Admin `{text}` dihapus.",
                reply_markup=back_kb("adm_admins"), parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❌ Bukan admin tambahan (mungkin admin config).",
                reply_markup=back_kb("adm_admins")
            )
        user_state.pop(uid, None)
        return True

    # ============ CHAT USER ============
    if action == "adm_chat_user":
        target = state["target"]
        try:
            await context.bot.send_message(
                int(target),
                f"💬 *Pesan dari Admin:*\n\n{text}",
                parse_mode="Markdown"
            )
            db.add_log(uid, "chat_user", target)
            await update.message.reply_text("✅ Pesan terkirim.", reply_markup=back_kb("adm_main"))
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal: {e}")
        user_state.pop(uid, None)
        return True

    return False