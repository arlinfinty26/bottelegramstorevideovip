from datetime import datetime, timezone, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

WIB = timezone(timedelta(hours=7))


def mask_uid(uid):
    """Mask user ID: 214***09"""
    s = str(uid)
    if len(s) <= 5:
        return s[0] + "*" * (len(s) - 1)
    return s[:3] + "*" * (len(s) - 5) + s[-2:]


def fmt_rp(n):
    return f"Rp {int(n):,}".replace(",", ".")


async def post_notif_order(bot, channel, order, user_id, store_name="ARL INFINITY"):
    """Kirim notifikasi pesanan baru ke channel testimoni (format teks + tombol)."""
    try:
        from database import get_product
        import config

        products = order.get("items", {})
        names = []
        for pid, qty in products.items():
            p = get_product(pid)
            pname = p.get("name") if p else f"Produk #{pid}"
            if qty > 1:
                names.append(f"{pname} x{qty}")
            else:
                names.append(pname)

        produk_str = ", ".join(names) if names else "-"
        total_qty = sum(products.values()) if products else 0

        now = datetime.now(WIB)
        waktu = now.strftime("%Y-%m-%d %H:%M:%S")

        text = (
            f"🛍️ <b>NOTIFIKASI PESANAN BARU</b> 🛍️\n\n"
            f"👤 Buyer: <code>{mask_uid(user_id)}</code>\n"
            f"🧩 Produk: {produk_str}\n"
            f"🚀 Jumlah: {total_qty} Pcs\n"
            f"💰 Total Bayar: <b>{fmt_rp(order['total'])}</b>\n"
            f"🔔 Waktu: {waktu}"
        )

        # Tombol "Order Via Bot" dengan link bot
        bot_link = getattr(config, "BOT_LINK", "")
        if bot_link:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ Order Via Bot", url=bot_link)]
            ])
        else:
            kb = None

        await bot.send_message(
            chat_id=channel,
            text=text,
            parse_mode="HTML",
            reply_markup=kb
        )
        return True
    except Exception as e:
        print(f"⚠️ Gagal kirim notif order: {e}")
        return False