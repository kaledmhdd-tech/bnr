from flask import Flask, request, send_file
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests

app = Flask(__name__)

# ================== الإعدادات ==================
AVATAR_SIZE = (125, 125)
SECRET_KEY = "BNGX"

FONT_PRIMARY = "Tajawal-Bold.ttf"
FONT_FALLBACKS = [
    "DejaVuSans.ttf",
    "NotoSans-Regular.ttf",
    "ARIAL.TTF",
    "NotoSansArabic-Regular.ttf",
    "NotoSansSymbols2-Regular.ttf",
    "NotoSansCJKjp-Regular.otf",
    "unifont-15.0.01.ttf"
]

# ================== تحميل الخطوط ==================
def load_fonts(sizes):
    fonts = {"primary": {}, "fallbacks": []}

    for size in sizes:
        try:
            fonts["primary"][size] = ImageFont.truetype(FONT_PRIMARY, size)
        except:
            fonts["primary"][size] = ImageFont.load_default()

    for path in FONT_FALLBACKS:
        fb = {}
        for size in sizes:
            try:
                fb[size] = ImageFont.truetype(path, size)
            except:
                fb[size] = None
        fonts["fallbacks"].append(fb)

    return fonts


fonts = load_fonts([30, 35, 40, 50])

# ================== أدوات النص ==================
def char_in_font(char, font):
    try:
        return font.getmask(char).getbbox() is not None
    except:
        return False


def smart_draw_text(draw, pos, text, font_dict, size, color):
    x, y = pos
    primary = font_dict["primary"][size]

    for ch in text:
        font = primary
        if not char_in_font(ch, primary):
            for fb in font_dict["fallbacks"]:
                if fb[size] and char_in_font(ch, fb[size]):
                    font = fb[size]
                    break

        draw.text((x, y), ch, font=font, fill=color)
        box = font.getbbox(ch)
        x += box[2] - box[0]


# ================== جلب الصور ==================
def fetch_image(url, size=None):
    try:
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGBA")
        if size:
            img = img.resize(size, Image.LANCZOS)
        return img
    except Exception as e:
        print("IMG ERROR:", e)
        return None


# ================== API البنر ==================
@app.route("/bnr")
def banner_api():
    uid = request.args.get("uid")
    key = request.args.get("key")

    if key != SECRET_KEY:
        return "🚫 KEY غير صحيح", 403

    if not uid:
        return "❌ UID مطلوب", 400

    # ---------- جلب بيانات اللاعب ----------
    try:
        api_url = f"https://info-eight-rho.vercel.app/accinfo?uid={uid}&region=ME"
        res = requests.get(api_url, timeout=6)
        res.raise_for_status()
        data = res.json()

        basic = data.get("basicInfo", {})
        profile = data.get("profileInfo", {})

        uid = basic.get("accountId", uid)
        nickname = basic.get("nickname", "UNKNOWN")
        level = basic.get("level", 0)
        likes = basic.get("liked", 0)
        avatar_id = profile.get("avatarId")
        banner_id = basic.get("bannerId")

    except Exception as e:
        return f"❌ API ERROR: {e}", 500

    # ---------- تحميل البنر ----------
    bg_img = fetch_image(
        f"https://pika-ffitmes-api.vercel.app/?item_id={banner_id}&key=PikaApis"
    )

    if not bg_img:
        return "❌ فشل تحميل البنر", 500

    img = bg_img.copy()
    draw = ImageDraw.Draw(img)

    # ---------- الأفاتار ----------
    avatar_img = fetch_image(
        f"https://pika-ffitmes-api.vercel.app/?item_id={avatar_id}&key=PikaApis",
        AVATAR_SIZE
    )

    avatar_x, avatar_y = 90, 80
    if avatar_img:
        img.paste(avatar_img, (avatar_x, avatar_y), avatar_img)

    # ---------- المستوى ----------
    smart_draw_text(
        draw,
        (avatar_x - 40, avatar_y + 160),
        f"Lv. {level}",
        fonts,
        50,
        "black"
    )

    # ---------- الاسم ----------
    smart_draw_text(
        draw,
        (avatar_x + AVATAR_SIZE[0] + 80, avatar_y - 5),
        nickname,
        fonts,
        50,
        "black"
    )

    # ---------- UID ----------
    uid_font = fonts["primary"][35]
    w = uid_font.getbbox(uid)[2]
    img_w, img_h = img.size

    smart_draw_text(
        draw,
        (img_w - w - 110, img_h - 55),
        uid,
        fonts,
        35,
        "white"
    )

    # ---------- الإعجابات ----------
    likes_txt = str(likes)
    w2 = fonts["primary"][40].getbbox(likes_txt)[2]

    smart_draw_text(
        draw,
        (img_w - w2 - 60, img_h - 105),
        likes_txt,
        fonts,
        40,
        "black"
    )

    # ---------- توقيع ----------
    smart_draw_text(
        draw,
        (img_w - 300, 25),
        "DEV BY : BNGX",
        fonts,
        30,
        "white"
    )

    # ---------- إخراج ----------
    out = BytesIO()
    img.save(out, "PNG")
    out.seek(0)

    return send_file(out, mimetype="image/png")


# ================== تشغيل ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
