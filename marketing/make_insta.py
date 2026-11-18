"""Instagram templates for Fidel English: 4:5 posts (1080x1350) and stories (1080x1920).

Usage (from the marketing folder):  python make_insta.py
Writes PNG files to marketing/instagram/. Change the texts below and run again to make new posts.
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instagram")
BOLD, REG, EMO = "C:/Windows/Fonts/ebrimabd.ttf", "C:/Windows/Fonts/ebrima.ttf", "C:/Windows/Fonts/seguiemj.ttf"
WHITE, GOLD, INK, MUTED, CARD, TG = (255, 255, 255), (255, 196, 61), (12, 38, 28), (190, 214, 200), (24, 70, 52), (42, 171, 238)
BG1, BG2 = (14, 58, 40), (6, 30, 20)

def font(size, bold=True): return ImageFont.truetype(BOLD if bold else REG, size)

def canvas(w, h):
    """Dark green gradient with soft gold dots."""
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        k = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(BG1[i] * (1 - k) + BG2[i] * k) for i in range(3)))
    im = im.convert("RGBA")
    dots = Image.new("RGBA", (w, h), (0, 0, 0, 0)); dd = ImageDraw.Draw(dots)
    for x, y, r in [(90, 140, 70), (w - 120, 260, 45), (w - 70, h - 200, 90), (60, h - 330, 40), (w // 2, h - 60, 30)]:
        dd.ellipse([x - r, y - r, x + r, y + r], fill=GOLD + (28,))
    im.alpha_composite(dots)
    return im

def emoji(ch, size):
    """Colour emoji drawn at 109px (the font's size) and scaled."""
    e = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(e).text((80, 80), ch, font=ImageFont.truetype(EMO, 109), embedded_color=True, anchor="mm", fill="#000")
    e = e.crop(e.getbbox() or (0, 0, 1, 1))
    k = size / max(e.size)
    return e.resize((max(1, int(e.width * k)), max(1, int(e.height * k))), Image.LANCZOS)

def ctext(im, y, text, f, fill, w=None):
    d = ImageDraw.Draw(im); w = w or im.width
    d.text((w // 2, y), text, font=f, fill=fill, anchor="ma")
    return y + f.size + 14

def wrap(text, f, maxw):
    words, lines, cur = text.split(" "), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = wd
    if cur: lines.append(cur)
    return lines

def card(w, h, fill=CARD, outline=(70, 130, 100), width=4, r=48):
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(c).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=fill + (255,), outline=outline + (255,), width=width)
    return c

def logo_row(im, y):
    """🦁 Fidel English, centred."""
    f = font(54); tw = int(ImageDraw.Draw(im).textlength("Fidel English", font=f))
    box = card(96, 96, GOLD, GOLD, 1, 26); l = emoji("🦁", 70); box.alpha_composite(l, ((96 - l.width) // 2, (96 - l.height) // 2))
    x = (im.width - (96 + 22 + tw)) // 2
    im.alpha_composite(box, (x, y)); ImageDraw.Draw(im).text((x + 118, y + 48), "Fidel English", font=f, fill=WHITE, anchor="lm")

def bot_button(im, y, w=820):
    b = card(w, 140, TG, TG, 1, 70)
    ImageDraw.Draw(b).text((w // 2, 70), "@FidelEnglishBot", font=font(66), fill=WHITE, anchor="mm")
    im.alpha_composite(b, ((im.width - w) // 2, y))

def save(im, name):
    os.makedirs(OUT, exist_ok=True)
    im.convert("RGB").save(os.path.join(OUT, name), quality=95); print("made", name)

# ---------- 1. price post ----------
def post_price():
    im = canvas(1080, 1350); logo_row(im, 70)
    y = ctext(im, 230, "ሙሉ የ4 ወር", font(84), WHITE)
    y = ctext(im, y, "የእንግሊዝኛ ኮርስ", font(84), WHITE)
    c = card(860, 400, (60, 48, 10), GOLD, 7)
    ctext(c, 40, "አንድ ጊዜ ብቻ ይክፈሉ", font(52, False), GOLD)
    ctext(c, 120, "300 ብር", font(170), WHITE)
    im.alpha_composite(c, (110, y + 30))
    f = emoji("🔥", 110); im.alpha_composite(f, (850, y - 10))
    y += 470
    y = ctext(im, y, "101 ትምህርቶች · 19 ጨዋታዎች", font(46, False), MUTED)
    y = ctext(im, y, "የቤት እንስሳ · በአማርኛ ማብራሪያ", font(46, False), MUTED)
    t = card(560, 96, GOLD, GOLD, 1, 48); ImageDraw.Draw(t).text((280, 48), "3 ቀን በነፃ ይሞክሩ!", font=font(50), fill=INK, anchor="mm")
    im.alpha_composite(t, (260, y + 18))
    bot_button(im, 1170)
    save(im, "post-1-price.png")

# ---------- 2. hook post ----------
def post_hook():
    im = canvas(1080, 1350); logo_row(im, 70)
    e = emoji("😰", 230); im.alpha_composite(e, ((1080 - e.width) // 2, 220))
    y = ctext(im, 490, "እንግሊዝኛ", font(110), GOLD)
    y = ctext(im, y, "መናገር ይጨንቅዎታል?", font(86), WHITE)
    y += 40
    for line in ["በቀን 10 ደቂቃ ብቻ ይለማመዱ።", "ያዳምጡ፣ ይድገሙ፣ ይናገሩ።", "ስህተትዎን ወዲያውኑ ይወቁ።"]:
        y = ctext(im, y, line, font(52, False), MUTED)
    t = card(560, 96, GOLD, GOLD, 1, 48); ImageDraw.Draw(t).text((280, 48), "3 ቀን በነፃ ይሞክሩ!", font=font(50), fill=INK, anchor="mm")
    im.alpha_composite(t, (260, y + 30))
    bot_button(im, 1170)
    save(im, "post-2-hook.png")

# ---------- 3. games and pet post ----------
def post_games():
    im = canvas(1080, 1350); logo_row(im, 70)
    y = ctext(im, 220, "በጨዋታ ይማሩ!", font(110), GOLD)
    icons = ["🏰", "🏃", "💣", "🧟", "👽", "🐉", "🔎", "🏆"]
    for i, ch in enumerate(icons):
        tile = card(200, 200, CARD, (70, 130, 100), 4, 40); e = emoji(ch, 120)
        tile.alpha_composite(e, ((200 - e.width) // 2, (200 - e.height) // 2))
        im.alpha_composite(tile, (70 + (i % 4) * 240, y + 30 + (i // 4) * 240))
    y += 530
    y = ctext(im, y, "19 አዝናኝ ጨዋታዎች", font(80), WHITE)
    y = ctext(im, y, "+ በተማሩ ቁጥር የሚያድግ የቤት እንስሳ", font(46, False), MUTED)
    bot_button(im, 1170)
    save(im, "post-3-games.png")

# ---------- 4. idiom of the day (change IDIOMS to make new posts) ----------
IDIOMS = [
    ("I'm saving for a rainy day.", "ለክፉ ቀን እያጠራቀምኩ ነው።", "ስለ ገንዘብ ሲያወሩ"),
    ("It's a piece of cake.", "በጣም ቀላል ነው።", "ቀላል ነገርን ሲገልጹ"),
    ("We're living from hand to mouth.", "ከእጅ ወደ አፍ እየኖርን ነው።", "እንደ አማርኛው ፈሊጥ!"),
]
def post_idiom(n, en, am, note):
    im = canvas(1080, 1350); logo_row(im, 70)
    tag = card(560, 90, GOLD, GOLD, 1, 45); ImageDraw.Draw(tag).text((280, 45), "የዕለቱ ፈሊጥ 💬".replace(" 💬", ""), font=font(48), fill=INK, anchor="mm")
    im.alpha_composite(tag, (260, 220))
    c = card(940, 640, CARD, (70, 130, 100), 4)
    f = font(84); lines = wrap(en, f, 840); yy = 70
    for ln in lines: yy = ctext(c, yy, ln, f, WHITE)
    ImageDraw.Draw(c).line([(220, yy + 20), (720, yy + 20)], fill=GOLD + (255,), width=4)
    fa = font(62); yy += 60
    for ln in wrap(am, fa, 840): yy = ctext(c, yy, ln, fa, GOLD)
    yy += 20; ctext(c, yy, note, font(44, False), MUTED)
    im.alpha_composite(c, (70, 360))
    ctext(im, 1040, "ሌሎች 400+ ፈሊጦችን በኮርሱ ይማሩ", font(48, False), MUTED)
    bot_button(im, 1170)
    save(im, "post-4-idiom-%d.png" % n)

# ---------- 5. story (1080x1920) ----------
def story():
    im = canvas(1080, 1920); logo_row(im, 140)
    e = emoji("🦁", 260); im.alpha_composite(e, ((1080 - e.width) // 2, 330))
    y = ctext(im, 660, "እንግሊዝኛ በአማርኛ", font(96), WHITE)
    y = ctext(im, y + 10, "በ4 ወር ይናገሩ!", font(110), GOLD)
    c = card(880, 420, (60, 48, 10), GOLD, 7)
    ctext(c, 40, "ሙሉ ኮርስ · 4 ወር", font(60), GOLD)
    ctext(c, 130, "300 ብር", font(160), WHITE)
    ctext(c, 330, "አንድ ጊዜ ብቻ", font(46, False), GOLD)
    im.alpha_composite(c, (100, y + 50))
    y += 520
    t = card(600, 110, GOLD, GOLD, 1, 55); ImageDraw.Draw(t).text((300, 55), "3 ቀን በነፃ ይሞክሩ!", font=font(56), fill=INK, anchor="mm")
    im.alpha_composite(t, (240, y + 20))
    ctext(im, 1630, "ቴሌግራም ላይ ይፈልጉን", font(60), WHITE)
    bot_button(im, 1730, 900)
    save(im, "story-1-price.png")

if __name__ == "__main__":
    post_price(); post_hook(); post_games()
    for i, (en, am, note) in enumerate(IDIOMS, 1): post_idiom(i, en, am, note)
    story()
