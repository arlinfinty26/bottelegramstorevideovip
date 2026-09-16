# ================== KONFIGURASI ARL INFINITY ==================
BOT_TOKEN = "8273332683:AAHBUnnqSQa-XDlylzCxnnwWjD8Taq6qVB0"
ADMIN_IDS = [1227792372]

STORE_NAME = "ARL INFINITY"
STORE_TAGLINE = "Toko Digital Terpercaya"
STORE_DESCRIPTION = (
    "ARL INFINITY adalah toko online terpercaya yang menyediakan "
    "berbagai produk digital berkualitas dengan harga bersaing."
)

ADMIN_USERNAME = "ARLINFINITY"
CHANNEL_USERNAME = "ARLINFINITYYY"

PAYMENTS = {
    "bca": {"name": "BCA", "number": "1234567890", "holder": "ARL INFINITY"},
    "dana": {"name": "DANA", "number": "081234567890", "holder": "ARL INFINITY"},
    "gopay": {"name": "GoPay", "number": "081234567890", "holder": "ARL INFINITY"},
    "qris": {"name": "QRIS", "number": "Scan QR di channel", "holder": "ARL INFINITY"},
}

MIN_TOPUP = 10000

# ================== GAMBAR WELCOME ==================
# Isi dengan link gambar, atau kosongkan "" kalau tidak mau pakai gambar
WELCOME_IMAGE = "https://i.ibb.co/p6Npzyhr/logo-start-bot.png"

# ================== CHANNEL TESTIMONI ==================
# Isi dengan username channel (pakai @) atau ID channel (pakai -100xxxx)
# Bot HARUS jadi admin di channel ini agar bisa posting
TESTIMONI_CHANNEL = "@channelinfo12"

# ================== LINK BOT ==================
# Link bot Telegram Anda (dipakai untuk tombol "Order Via Bot" di channel)
BOT_LINK = "https://t.me/ARLINFINITYY_bot"