import io
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

MONTHS_ID = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
             "Juli", "Agustus", "September", "Oktober", "November", "Desember"]


def format_tanggal_id(iso_str):
    """Format ISO date ke format Indonesia: 14 September 2026"""
    if not iso_str:
        return "-"
    try:
        dt = datetime.fromisoformat(iso_str)
    except Exception:
        return "-"
    return f"{dt.day:02d} {MONTHS_ID[dt.month]} {dt.year}"


def _font(size, bold=False):
    """Cari font yang tersedia di sistem."""
    candidates = []
    if os.name == "nt":  # Windows
        base = "C:/Windows/Fonts/"
        candidates = [
            base + ("arialbd.ttf" if bold else "arial.ttf"),
            base + ("segoeuib.ttf" if bold else "segoeui.ttf"),
            base + ("calibrib.ttf" if bold else "calibri.ttf"),
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/system/fonts/Roboto-Bold.ttf" if bold else "/system/fonts/Roboto-Regular.ttf",
            "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf" if bold
            else "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]
    candidates += ["arialbd.ttf" if bold else "arial.ttf", "arial.ttf"]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _initials(name):
    parts = [p for p in (name or "?").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def _circle_avatar(name, size=200, bg=(37, 99, 235), fg=(255, 255, 255), photo_bytes=None):
    """Bikin avatar bulat. Pakai foto user kalau ada, kalau tidak pakai inisial."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    if photo_bytes:
        try:
            p = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
            w, h = p.size
            s = min(w, h)
            p = p.crop(((w - s) // 2, (h - s) // 2,
                        (w - s) // 2 + s, (h - s) // 2 + s)).resize((size, size))
            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, size, size], fill=255)
            img.paste(p, (0, 0), mask)
            return img
        except Exception:
            pass

    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, size, size], fill=bg)
    txt = _initials(name)
    f = _font(int(size * 0.45), bold=True)
    bbox = draw.textbbox((0, 0), txt, font=f)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]),
              txt, font=f, fill=fg)
    return img


def generate_profile_card(user, tg_user, store_name="ARL INFINITY", photo_bytes=None):
    """
    Bikin kartu anggota (KTP digital) untuk user.
    Return: io.BytesIO berisi file PNG.
    """
    W, H = 1000, 620
    bg_page = (241, 245, 249)
    card_bg = (255, 255, 255)
    primary = (37, 99, 235)
    primary_dark = (29, 78, 216)
    dark = (17, 24, 39)
    gray = (100, 116, 139)
    border = (226, 232, 240)
    green = (22, 163, 74)
    red = (220, 38, 38)

    img = Image.new("RGB", (W, H), bg_page)
    draw = ImageDraw.Draw(img)

    # Kartu utama dengan sudut tumpul
    draw.rounded_rectangle([20, 20, W - 20, H - 20], radius=28,
                            fill=card_bg, outline=border, width=2)

    # Header biru
    draw.rounded_rectangle([20, 20, W - 20, 130], radius=28, fill=primary)
    draw.rectangle([20, 100, W - 20, 130], fill=primary)
    # Aksen dekoratif
    draw.ellipse([W - 180, -60, W + 40, 160], fill=primary_dark)
    draw.ellipse([W - 120, -20, W + 60, 160], fill=(59, 130, 246))

    # Judul header
    f_header = _font(32, bold=True)
    f_sub = _font(17)
    draw.text((52, 42), "KARTU TANDA ANGGOTA", font=f_header, fill=(255, 255, 255))
    draw.text((52, 88), f"{store_name}  •  Member Card Digital", font=f_sub, fill=(219, 234, 254))

    # Avatar (foto atau inisial)
    avatar = _circle_avatar(
        tg_user.first_name or "User",
        size=210,
        photo_bytes=photo_bytes,
    )
    img.paste(avatar, (60, 180), avatar)
    # Border avatar
    draw.ellipse([58, 178, 272, 392], outline=primary, width=5)

    # Badge "MEMBER" di bawah avatar
    badge_w, badge_h = 214, 40
    draw.rounded_rectangle([58, 400, 58 + badge_w, 400 + badge_h],
                            radius=20, fill=(219, 234, 254))
    f_badge = _font(18, bold=True)
    badge_text = "✦ MEMBER AKTIF"
    bbox = draw.textbbox((0, 0), badge_text, font=f_badge)
    tw = bbox[2] - bbox[0]
    draw.text((58 + (badge_w - tw) / 2 - bbox[0], 410), badge_text,
              font=f_badge, fill=primary)

    # Data fields
    x_label = 320
    x_value = 480
    y = 190
    gap = 54

    def field(label, value, color=dark):
        nonlocal y
        draw.text((x_label, y + 4), label, font=_font(17), fill=gray)
        draw.text((x_value, y), ": " + str(value),
                  font=_font(21, bold=True), fill=color)
        y += gap

    field("ID Telegram", tg_user.id)
    field("Nama Akun", tg_user.first_name or "-")
    if tg_user.last_name:
        field("Nama Belakang", tg_user.last_name)
    field("Username", ("@" + tg_user.username) if tg_user.username else "Tidak ada")
    field("Terdaftar Sejak", format_tanggal_id(user.get("joined", "")))

    # Bottom info cards
    y2 = 445
    box_h = 120

    # Saldo card
    draw.rounded_rectangle([50, y2, 480, y2 + box_h], radius=18,
                            fill=(240, 253, 244), outline=(187, 247, 208), width=2)
    draw.text((80, y2 + 18), "SALDO AKUN", font=_font(15, bold=True), fill=green)
    saldo_text = f"Rp{int(user.get('balance', 0)):,}".replace(",", ".")
    draw.text((80, y2 + 48), saldo_text, font=_font(30, bold=True), fill=(21, 128, 61))

    # Total belanja card
    draw.rounded_rectangle([520, y2, 950, y2 + box_h], radius=18,
                            fill=(254, 242, 242), outline=(254, 202, 202), width=2)
    draw.text((550, y2 + 18), "TOTAL BELANJA", font=_font(15, bold=True), fill=red)
    spent_text = f"Rp{int(user.get('total_spent', 0)):,}".replace(",", ".")
    draw.text((550, y2 + 48), spent_text, font=_font(30, bold=True), fill=(153, 27, 27))

    # Footer
    f_foot = _font(13)
    draw.text((50, H - 38),
              f"© {store_name}  •  Kartu ini dibuat otomatis oleh sistem & bersifat digital.",
              font=f_foot, fill=gray)

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    out.seek(0)
    return out