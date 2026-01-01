from flask import Flask, request, send_file
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests

app = Flask(__name__)

AVATAR_SIZE = (125, 125)
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
SECRET_KEY = "BNGX"

# تحميل الخطوط
def load_fonts(sizes):
    fonts = {"primary": {}, "fallbacks": []}
    for size in sizes:
        try:
            fonts["primary"][size] = ImageFont.truetype(FONT_PRIMARY, size)
        except:
            fonts["primary"][size] = ImageFont.load_default()
    for font_path in FONT_FALLBACKS:
        fallback_fonts = {}
        for size in sizes:
            try:
                fallback_fonts[size] = ImageFont.truetype(font_path, size)
            except:
                fallback_fonts[size] = None
        fonts["fallbacks"].append(fallback_fonts)
    return fonts

fonts = load_fonts([30, 35, 40, 50])

def char_in_font(char, font):
    try:
        glyph = font.getmask(char)
        return glyph.getbbox() is not None
    except:
        return False

def smart_draw_text(draw, position, text, font_dict, size, fill):
    x, y = position
    primary_font = font_dict["primary"][size]
    fallbacks = font_dict["fallbacks"]

    for char in text:
        font_to_use = None
        if char_in_font(char, primary_font):
            font_to_use = primary_font
        else:
            for fb_fonts in fallbacks:
                fb_font = fb_fonts[size]
                if fb_font and char_in_font(char, fb_font):
                    font_to_use = fb_font
                    break
        if not font_to_use:
            font_to_use = primary_font

        draw.text((x, y), char, font=font_to_use, fill=fill)
        char_width = font_to_use.getbbox(char)[2] - font_to_use.getbbox(char)[0]
        x += char_width

def fetch_image(url, size=None):
    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        img = Image.open(BytesIO(res.content)).convert("RGBA")
        if size:
            img = img.resize(size, Image.LANCZOS)
        return img
    except Exception as e:
        print(f"Error fetching image: {e}")
        return None

def fetch_avatar_image(avatar_id, head_pic, banner_id):
    """محاولة جلب الصورة من مصادر مختلفة"""
    # قائمة IDs المحتملة للصورة الشخصية
    potential_ids = []
    
    # إضافة جميع IDs الممكنة
    if avatar_id:
        potential_ids.append(avatar_id)
    if head_pic:
        potential_ids.append(head_pic)
    if banner_id:
        potential_ids.append(banner_id)
    
    print(f"Trying avatar IDs: {potential_ids}")
    
    # محاولة كل ID
    for img_id in potential_ids:
        try:
            url = f"https://pika-ffitmes-api.vercel.app/?item_id={img_id}&watermark=TaitanApi&key=PikaApis"
            print(f"Trying URL: {url}")
            res = requests.get(url, timeout=5)
            res.raise_for_status()
            
            # التحقق مما إذا كان المحتوى صورة
            content = res.content
            if content and len(content) > 100:  # صورة حقيقية عادةً تكون أكبر من 100 بايت
                img = Image.open(BytesIO(content)).convert("RGBA")
                img.verify()  # التحقق من صحة الصورة
                img = Image.open(BytesIO(content)).convert("RGBA")  # إعادة فتح بعد التحقق
                print(f"Successfully loaded image ID: {img_id}")
                return img
        except Exception as e:
            print(f"Failed to load image ID {img_id}: {e}")
            continue
    
    # إذا فشلت جميع المحاولات، استخدم صورة افتراضية
    print("All avatar IDs failed, using default image")
    return None


@app.route('/bnr')
def generate_avatar_only():
    uid = request.args.get("uid")
    key = request.args.get("key")

    if key != SECRET_KEY:
        return " KEY ", 403
    if not uid:
        return "INVALID UID", 400

    try:
        # ✅ API الجديد
        api_url = f"https://info-eight-rho.vercel.app/accinfo?uid={uid}&region=IND"
        res = requests.get(api_url, timeout=40)
        res.raise_for_status()
        data = res.json()

        # ✅ استخراج من basicInfo و profileInfo
        basic_info = data.get("basicInfo", {})
        profile_info = data.get("profileInfo", {})

        nickname = basic_info.get("nickname", "Unknown")
        likes = basic_info.get("liked", 0)
        level = basic_info.get("level", 0)
        
        # استخراج جميع IDs المحتملة للصورة الشخصية
        avatar_id = profile_info.get("avatarId")
        head_pic = basic_info.get("headPic")
        banner_id = basic_info.get("bannerId")
        
        print(f"Extracted IDs - avatarId: {avatar_id}, headPic: {head_pic}, bannerId: {banner_id}")

    except Exception as e:
        return f" API INFO ERROR : {e}", 500

    # الخلفية
    bg_img = fetch_image("https://i.postimg.cc/L4PQBgmx/IMG-20250807-042134-670.jpg")
    if not bg_img:
        return " IMAGE ERROR ", 500

    img = bg_img.copy()
    draw = ImageDraw.Draw(img)

    # الصورة الشخصية - محاولة جميع IDs الممكنة
    avatar_img = fetch_avatar_image(avatar_id, head_pic, banner_id)
    
    avatar_x, avatar_y = 90, 82
    if avatar_img:
        avatar_img = avatar_img.resize(AVATAR_SIZE, Image.LANCZOS)
        img.paste(avatar_img, (avatar_x, avatar_y), avatar_img)
    else:
        # إذا لم تنجح أي صورة، استخدم صورة افتراضية
        print("Using default avatar")
        default_avatar = Image.new('RGBA', AVATAR_SIZE, (100, 100, 150, 200))
        img.paste(default_avatar, (avatar_x, avatar_y), default_avatar)

    # المستوى
    level_text = f"Lv. {level}"
    level_x = avatar_x - 40
    level_y = avatar_y + 160
    smart_draw_text(draw, (level_x, level_y), level_text, fonts, 50, "black")

    # الاسم
    nickname_x = avatar_x + AVATAR_SIZE[0] + 80
    nickname_y = avatar_y - 3
    smart_draw_text(draw, (nickname_x, nickname_y), nickname, fonts, 50, "black")

    # UID
    bbox_uid = fonts["primary"][35].getbbox(uid)
    text_w = bbox_uid[2] - bbox_uid[0]
    text_h = bbox_uid[3] - bbox_uid[1]
    img_w, img_h = img.size
    text_x = img_w - text_w - 110
    text_y = img_h - text_h - 17
    smart_draw_text(draw, (text_x, text_y), uid, fonts, 35, "white")

    # عدد اللايكات
    likes_text = f"{likes}"
    bbox_likes = fonts["primary"][40].getbbox(likes_text)
    likes_w = bbox_likes[2] - bbox_likes[0]
    likes_y = text_y - (bbox_likes[3] - bbox_likes[1]) - 25
    likes_x = img_w - likes_w - 60
    smart_draw_text(draw, (likes_x, likes_y), likes_text, fonts, 40, "black")

    # تذييل المطور
    dev_text = "DEV BY : BNGX"
    bbox_dev = fonts["primary"][30].getbbox(dev_text)
    dev_w = bbox_dev[2] - bbox_dev[0]
    padding = 30
    dev_x = img_w - dev_w - padding
    dev_y = padding
    smart_draw_text(draw, (dev_x, dev_y), dev_text, fonts, 30, "white")

    # إخراج الصورة
    output = BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    return send_file(output, mimetype='image/png')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
