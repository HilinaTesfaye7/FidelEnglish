"""Fidel English TikTok ad v5 (vertical 1080x1920, ~47 s): 19 games, English Pet Academy and idioms. 3-day free trial; opening line "ወይኔ ጉዴ!".
One payment of 300 Birr opens the full 4-month course. Based on make_ad4.py. Funny commercial with Amharic voice, music and sound effects.

Usage:  python make_ad2.py <voice_dir> <ffmpeg> <out.mp4> [stills <out_dir> <t1,t2,...>]
The voice_dir holds the voice clips (n1..n9, s1, s2, en_*.mp3). Music and effects are generated here (original).
"""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

VO, FF = sys.argv[1], sys.argv[2]
W, H, FPS, SR = 1080, 1920, 30, 44100
BOLD, REG, EMO = "C:/Windows/Fonts/ebrimabd.ttf", "C:/Windows/Fonts/ebrima.ttf", "C:/Windows/Fonts/seguiemj.ttf"
WHITE, GOLD, GREEN, RED, INK = (255, 255, 255), (255, 196, 61), (46, 204, 113), (235, 87, 87), (12, 38, 28)
MUTED, CARD, TG = (190, 214, 200), (24, 70, 52), (42, 171, 238)

# ======================= audio clips + timeline =======================
def load(name):
    raw = subprocess.run([FF, "-loglevel", "error", "-i", os.path.join(VO, name + ".mp3"), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    loud = np.where(np.abs(a) > 0.012)[0]                      # trim silence at both ends
    if len(loud): a = a[max(0, loud[0] - 800): loud[-1] + 2400]
    return a
CLIPS = {n: load(n) for n in ["en_howareyou", "n1", "n2", "en_thankyou_teacher", "s1", "n3", "s2", "n4",
                               "en_thankyou_student", "n5", "n6c", "ngames", "npet", "n8", "n8b", "n9"]}
LEN = {k: len(v) / SR for k, v in CLIPS.items()}

VOICE, SFX, T = [], [], {}      # (time, clip), (time, effect), named times
t = 0.4
T["s1"] = 0.0
VOICE.append((t, "en_howareyou")); T["how"] = t; t += LEN["en_howareyou"] + 0.35
VOICE.append((t, "n1")); T["panic"] = t; t += LEN["n1"] + 0.3
T["s2"] = t; SFX.append((t, "whoosh")); t += 0.35
VOICE.append((t, "n2")); T["rescue"] = t; t += LEN["n2"] + 0.5
T["s3"] = t; SFX.append((t, "whoosh")); t += 0.5
SFX.append((t - 0.05, "click")); VOICE.append((t, "en_thankyou_teacher")); T["teach"] = t; t += LEN["en_thankyou_teacher"] + 0.5
SFX.append((t - 0.05, "click")); VOICE.append((t, "s1")); T["try1"] = t; t += LEN["s1"] + 0.15
SFX.append((t, "buzz")); T["fail1"] = t; t += 0.35
VOICE.append((t, "n3")); t += LEN["n3"] + 0.5
SFX.append((t - 0.05, "click")); VOICE.append((t, "s2")); T["try2"] = t; t += LEN["s2"] + 0.15
SFX.append((t, "buzz")); T["fail2"] = t; t += 0.35
VOICE.append((t, "n4")); t += LEN["n4"] + 0.5
SFX.append((t - 0.05, "click")); VOICE.append((t, "en_thankyou_student")); T["try3"] = t; t += LEN["en_thankyou_student"] + 0.15
SFX.append((t, "ding")); T["pass"] = t; t += 0.3
VOICE.append((t, "n5")); t += LEN["n5"] + 0.6
T["s4"] = t; SFX.append((t, "whoosh")); t += 0.3
VOICE.append((t, "n6c")); T["feat"] = t; t += LEN["n6c"] + 0.6
T["sg"] = t; SFX.append((t, "whoosh")); t += 0.3
VOICE.append((t, "ngames")); T["games"] = t; t += max(LEN["ngames"] + 0.7, 2.6)
T["sp"] = t; SFX.append((t, "whoosh")); t += 0.3
VOICE.append((t, "npet")); T["pet"] = t; t += LEN["npet"] + 0.9
T["s5"] = T["cheer"] = T["ulul"] = t
T["s6"] = t; SFX.append((t, "whoosh")); t += 0.3
VOICE.append((t, "n8")); T["price"] = t; t += LEN["n8"] + 0.4
SFX.append((t, "ding")); VOICE.append((t, "n8b")); T["full"] = t; t += LEN["n8b"] + 0.9
T["s7"] = t; SFX.append((t, "whoosh")); t += 0.3
VOICE.append((t, "n9")); T["cta"] = t; t += LEN["n9"] + 2.2
T["end"] = TOTAL = t

# ======================= music + effects =======================
rng = np.random.default_rng(3)
def env(n, a=0.004, r=0.2):
    tt = np.arange(n) / SR
    return np.minimum(1, tt / a) * np.exp(-tt / r)
def tone(f, dur, vol, shape="sine", r=0.2):
    n = int(dur * SR); tt = np.arange(n) / SR
    w = np.sin(2 * np.pi * f * tt)
    if shape == "pluck": w = w + 0.35 * np.sin(4 * np.pi * f * tt) + 0.12 * np.sin(6 * np.pi * f * tt)
    if shape == "square": w = np.sign(w) * 0.6
    return vol * w * env(n, 0.004, r)
def kick():
    n = int(0.28 * SR); tt = np.arange(n) / SR
    return 0.8 * np.sin(2 * np.pi * np.cumsum(55 + 100 * np.exp(-tt * 28)) / SR) * np.exp(-tt * 10)
def noise(dur, vol, decay):
    n = int(dur * SR); return vol * rng.uniform(-1, 1, n) * np.exp(-np.arange(n) / SR * decay)

N = int(TOTAL * SR) + SR
music, fx, voice = np.zeros(N, np.float32), np.zeros(N, np.float32), np.zeros(N, np.float32)
def put(buf, sig, at):
    i = int(at * SR); j = min(len(buf), i + len(sig))
    if 0 <= i < len(buf): buf[i:j] += sig[: j - i]

hz = lambda m: 440 * 2 ** ((m - 69) / 12)
BPM = 118; beat = 60 / BPM; bar = 4 * beat
chords = [[60, 64, 67], [57, 60, 64], [65, 69, 72], [67, 71, 74]]       # C Am F G — happy and bouncy
bass = [36, 33, 41, 43]
melody = [72, 74, 76, 79, 76, 74, 72, 74, 76, 76, 74, 72, 69, 72, 74, 72]  # playful pentatonic hook
for b in range(int(TOTAL / bar) + 1):
    t0 = b * bar; c = chords[b % 4]
    for k in range(4):
        tb = t0 + k * beat
        put(music, kick(), tb)
        if k % 2 == 1: put(music, noise(0.12, 0.22, 30), tb)                      # clap
        put(music, noise(0.04, 0.07, 90), tb + beat / 2)                          # hat
        put(music, tone(hz(bass[b % 4]), beat * 0.45, 0.28, "sine", 0.18), tb)
        put(music, tone(hz(bass[b % 4] + 12), beat * 0.3, 0.12, "sine", 0.1), tb + beat / 2)
    for k in range(8):                                                             # bouncy chord stabs
        if k in (1, 3, 5, 7):
            for m in c: put(music, tone(hz(m), 0.18, 0.045, "pluck", 0.08), t0 + k * beat / 2)
    if b % 2 == 1:
        for k, m in enumerate(melody[(b // 2 % 2) * 8:(b // 2 % 2) * 8 + 8]):
            put(music, tone(hz(m), beat / 2, 0.05, "pluck", 0.15), t0 + k * beat / 2)
music = music[:N]

def sfx(kind):
    if kind == "buzz":                                     # wrong: "wah-wah"
        n = int(0.55 * SR); tt = np.arange(n) / SR
        f = 210 - 90 * tt / 0.55
        return 0.32 * np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.minimum(1, (0.55 - tt) * 8) * (0.6 + 0.4 * np.sin(2 * np.pi * 7 * tt))
    if kind == "ding":                                     # right
        return tone(1046, 0.9, 0.28, "sine", 0.35) + tone(1568, 0.9, 0.18, "sine", 0.25)
    if kind == "click":
        return noise(0.03, 0.25, 160)
    if kind == "whoosh":
        n = int(0.4 * SR); w = rng.uniform(-1, 1, n); tt = np.arange(n) / SR
        w = np.convolve(w, np.ones(12) / 12, "same")
        return 0.25 * w * np.sin(np.pi * tt / 0.4)
    if kind == "ulul":                                     # "lililili" ululation
        n = int(1.6 * SR); tt = np.arange(n) / SR
        f = 1150 + 60 * np.sin(2 * np.pi * 5 * tt)
        am = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 11 * tt))
        am = np.convolve(am, np.ones(300) / 300, "same")
        e = np.minimum(1, tt / 0.05) * np.minimum(1, (1.6 - tt) / 0.25)
        return 0.22 * np.sin(2 * np.pi * np.cumsum(f) / SR) * am * e
    if kind == "pop":
        n = int(0.12 * SR); tt = np.arange(n) / SR
        return 0.25 * np.sin(2 * np.pi * np.cumsum(300 + 900 * tt / 0.12) / SR) * np.exp(-tt * 25)
# ======================= drawing helpers =======================
_fc = {}
def font(size, bold=True, emoji=False):
    k = (size, bold, emoji)
    if k not in _fc: _fc[k] = ImageFont.truetype(EMO if emoji else (BOLD if bold else REG), size)
    return _fc[k]
def text_sprite(t, size, color, bold=True, sh=True):
    f = font(size, bold); bb = f.getbbox(t)
    img = Image.new("RGBA", (bb[2] - bb[0] + 40, bb[3] - bb[1] + 40), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((20 - bb[0], 20 - bb[1]), t, font=f, fill=color)
    return shadow(img) if sh else img
def emoji_sprite(e, size):
    f = font(109, emoji=True); bb = f.getbbox(e)
    img = Image.new("RGBA", (bb[2] - bb[0] + 20, bb[3] - bb[1] + 20), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((10 - bb[0], 10 - bb[1]), e, font=f, embedded_color=True)
    k = size / 109
    return img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))), Image.LANCZOS)
def shadow(img, r=12, a=130):
    pad = r * 2; base = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    blk = Image.new("RGBA", img.size, (0, 0, 0, 255)); blk.putalpha(img.split()[3].point(lambda v: v * a // 255))
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0)); sh.paste(blk, (pad, pad + 8), blk)
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(r))); base.alpha_composite(img, (pad, pad)); return base
def rrect(w, h, r, fill, outline=None, width=0):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ImageDraw.Draw(img).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=fill, outline=outline, width=width); return img
def ctext(d, y, t, f, col, w):
    bb = f.getbbox(t); d.text(((w - (bb[2] - bb[0])) // 2 - bb[0], y), t, font=f, fill=col)
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_back(x): x = clamp(x); c1 = 1.70158; return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2

bg = Image.new("RGB", (W, H)); bd = ImageDraw.Draw(bg)
for y in range(H):
    k = y / H; bd.line([(0, y), (W, y)], fill=(int(10 + 14 * k), int(46 + 30 * k), int(34 + 20 * k)))
bg = bg.convert("RGBA")
def glow(size, color, a):
    g = Image.new("RGBA", (size, size), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([size * .2, size * .2, size * .8, size * .8], fill=color + (a,))
    return g.filter(ImageFilter.GaussianBlur(size // 8))
GLOW1, GLOW2 = glow(700, GOLD, 60), glow(800, (90, 220, 160), 50)

EL = []
def add(sprite, cx, cy, t_in, t_out, anim="rise", dur=0.4):
    EL.append(dict(s=sprite, cx=cx, cy=cy, t_in=t_in, t_out=t_out, anim=anim, dur=dur))

# ======================= scenes =======================
# 1. "How are you?" ... panic
add(emoji_sprite("🧑", 230), 300, 620, T["how"] - 0.2, T["s2"], "pop")
bub = rrect(560, 170, 60, (255, 255, 255, 255)); ImageDraw.Draw(bub).polygon([(60, 150), (40, 215), (130, 150)], fill=WHITE)
bub2 = Image.new("RGBA", (560, 220), (0, 0, 0, 0)); bub2.alpha_composite(bub); ImageDraw.Draw(bub2).polygon([(70, 165), (40, 220), (140, 165)], fill=WHITE)
ctext(ImageDraw.Draw(bub2), 45, "How are you?", font(76), INK, 560)
add(shadow(bub2), 700, 460, T["how"], T["s2"], "pop")
add(emoji_sprite("😅", 300), 540, 1080, T["panic"], T["s2"], "shake")
add(text_sprite("እ... እ...", 110, WHITE), 540, 1380, T["panic"] + 0.1, T["s2"], "rise")
add(text_sprite("ወይኔ ጉዴ!", 150, GOLD), 540, 1560, T["panic"] + 2.05, T["s2"], "pop")

# 2. rescue
logo = rrect(300, 300, 70, GOLD + (255,)); _l = emoji_sprite("🦁", 210); logo.alpha_composite(_l, ((300 - _l.width) // 2, (300 - _l.height) // 2))
add(shadow(logo, 18), 540, 700, T["rescue"], T["s3"], "pop", 0.55)
add(text_sprite("አይዞዎት!", 150, GOLD), 540, 1010, T["rescue"] + 0.2, T["s3"], "pop")
add(text_sprite("Fidel English", 110, WHITE), 540, 1190, T["rescue"] + 0.9, T["s3"], "rise")
add(text_sprite("መጥቷል!", 100, WHITE), 540, 1330, T["rescue"] + 1.3, T["s3"], "rise")

# 3. phone demo
PH_W, PH_H, PCX, PCY = 760, 1240, 540, 1010
phone = rrect(PH_W, PH_H, 80, (240, 245, 241, 255), (20, 24, 22, 255), 18); pd = ImageDraw.Draw(phone)
pd.rounded_rectangle([PH_W // 2 - 80, 34, PH_W // 2 + 80, 62], 14, fill=(20, 24, 22))
ctext(pd, 120, "SPEAKING · መናገር", font(34, False), (90, 110, 100), PH_W)
pd.rounded_rectangle([50, 190, PH_W - 50, 520], 40, fill=WHITE, outline=(210, 220, 214), width=4)
ctext(pd, 250, "Thank you", font(96), INK, PH_W)
ctext(pd, 400, "አመሰግናለሁ", font(58), (31, 107, 79), PH_W)
pd.rounded_rectangle([50, 560, PH_W - 50, 680], 30, fill=WHITE, outline=(210, 220, 214), width=4)
ctext(pd, 592, "🔊  Listen · ያዳምጡ".replace("🔊  ", ""), font(48), INK, PH_W)
pd.ellipse([PH_W // 2 - 85, 730, PH_W // 2 + 85, 900], fill=(31, 107, 79))
mic = emoji_sprite("🎤", 110); phone.alpha_composite(mic, (PH_W // 2 - mic.width // 2, 815 - mic.height // 2))
ctext(pd, 920, "Record · ይቅረጹ", font(40, False), (90, 110, 100), PH_W)
ptop = PCY - PH_H // 2
add(shadow(phone, 26, 150), PCX, PCY, T["s3"] + 0.1, T["s4"], "rise", 0.5)
pulse = Image.new("RGBA", (PH_W - 100, 120), (0, 0, 0, 0)); ImageDraw.Draw(pulse).rounded_rectangle([0, 0, PH_W - 101, 119], 30, outline=(46, 204, 113, 255), width=10)
add(pulse, PCX, ptop + 620, T["teach"], T["teach"] + LEN["en_thankyou_teacher"] + 0.2, "blink", 0.1)
ring = Image.new("RGBA", (220, 220), (0, 0, 0, 0)); ImageDraw.Draw(ring).ellipse([5, 5, 215, 215], outline=(235, 87, 87, 255), width=12)
for k in ("try1", "try2", "try3"):
    add(ring, PCX, ptop + 815, T[k] - 0.1, T[k] + LEN[{"try1": "s1", "try2": "s2", "try3": "en_thankyou_student"}[k]] + 0.1, "blink", 0.1)
def student(t, at, until):
    b = rrect(520, 150, 60, (255, 240, 200, 255)); ctext(ImageDraw.Draw(b), 34, t, font(72), INK, 520)
    g = Image.new("RGBA", (640, 170), (0, 0, 0, 0)); g.alpha_composite(emoji_sprite("🧑", 120), (0, 15)); g.alpha_composite(b, (120, 10))
    add(shadow(g), 540, 300, at, until, "pop", 0.3)
student("ታንክ ዩ 😬".replace(" 😬", ""), T["try1"], T["try2"] - 0.1)
student("ሳንክ ዩ", T["try2"], T["try3"] - 0.1)
student("Thank you!", T["try3"], T["s4"])
def verdict(ok, words, at, until):
    c = rrect(PH_W - 100, 210, 36, ((226, 247, 234, 255) if ok else (252, 228, 226, 255)))
    f = font(78); bb = f.getbbox(words); ic = emoji_sprite("✅" if ok else "❌", 96)
    x0 = (PH_W - 100 - (bb[2] - bb[0]) - ic.width - 20) // 2
    c.alpha_composite(ic, (x0, (210 - ic.height) // 2))
    ImageDraw.Draw(c).text((x0 + ic.width + 20 - bb[0], 52), words, font=f, fill=(30, 140, 80) if ok else (200, 60, 50))
    add(c, PCX, ptop + 1080, at, until, "pop", 0.3)
verdict(False, "እስቲ እንደገና!", T["fail1"], T["try2"] - 0.1)
verdict(False, "እረ ወይኔ!", T["fail2"], T["try3"] - 0.1)
verdict(True, "ጀግና! አልፈዋል", T["pass"], T["s4"])
CONFETTI = [(T["pass"], 2.4), (T["pet"] + LEN["npet"] * 0.62, 2.2)]

# 4. features
add(text_sprite("ፊደል ኢንግሊሽ ውስጥ…", 74, GOLD), 540, 380, T["feat"], T["sg"], "rise")
feats = [("🔊", "ያዳምጡ", "ትክክለኛ የእንግሊዝኛ ድምፅ"), ("🎤", "ይናገሩ", "ስልኩ ትክክል መሆንዎን ይነግርዎታል"),
         ("💬", "ፈሊጦች", "It's a piece of cake!"), ("📥", "ያውርዱ", "ያለ ኢንተርኔት ይማሩ")]
step = LEN["n6c"] / 4
for i, (e, a, b) in enumerate(feats):
    c = rrect(920, 230, 44, CARD + (255,), (70, 130, 100, 255), 3); cd = ImageDraw.Draw(c)
    c.alpha_composite(emoji_sprite(e, 130), (40, 45))
    cd.text((210, 40), a, font=font(70), fill=WHITE); cd.text((210, 135), b, font=font(44, False), fill=MUTED)
    add(shadow(c, 14, 110), 540, 640 + i * 265, T["feat"] + 0.2 + i * step, T["sg"], "slide")

# 4b. 19 games
add(text_sprite("19 ጨዋታዎች!", 150, GOLD), 540, 330, T["games"], T["sp"], "pop")
add(text_sprite("ይጫወቱና ይማሩ", 78, WHITE), 540, 480, T["games"] + 0.4, T["sp"], "rise")
GICONS = ["🐺", "🦁", "🧟", "💣", "👽", "🐉", "🎤", "🎈", "🧩", "🧠", "🏃", "🥊"]
for i, e in enumerate(GICONS):
    tile = rrect(220, 220, 50, CARD + (255,), (70, 130, 100, 255), 4); ic = emoji_sprite(e, 140)
    tile.alpha_composite(ic, ((220 - ic.width) // 2, (220 - ic.height) // 2))
    add(shadow(tile, 12, 110), 225 + (i % 4) * 210, 720 + (i // 4) * 240, T["games"] + 0.3 + i * 0.12, T["sp"], "pop", 0.3)
SFX.extend([(T["games"] + 0.3 + i * 0.12, "pop") for i in range(12)])

# 4c. English Pet Academy: the pet grows as you learn
add(text_sprite("የራስዎ የቤት እንስሳ!", 104, GOLD), 540, 330, T["pet"], T["s5"], "pop")
room = rrect(900, 900, 70, (217, 245, 229, 255)); rd = ImageDraw.Draw(room)
rd.rounded_rectangle([0, 600, 899, 899], 70, fill=(200, 155, 109)); rd.rectangle([0, 600, 899, 700], fill=(200, 155, 109))
plant = emoji_sprite("🪴", 150); room.alpha_composite(plant, (700, 470)); ball = emoji_sprite("⚽", 100); room.alpha_composite(ball, (90, 560))
add(shadow(room, 20, 120), 540, 1020, T["pet"] + 0.1, T["s5"], "rise", 0.4)
PL = LEN["npet"]
def pet_at(size, extra, t0, t1, anim="pop"):
    g = Image.new("RGBA", (520, 520), (0, 0, 0, 0)); p = emoji_sprite("🐶", size); g.alpha_composite(p, ((520 - p.width) // 2, 520 - p.height - 20))
    for e, sz, dy in extra:
        x = emoji_sprite(e, sz); g.alpha_composite(x, ((520 - x.width) // 2, 520 - p.height - 20 + dy))
    add(g, 540, 1080, t0, t1, anim, 0.35)
t1, t2 = T["pet"] + PL * 0.33, T["pet"] + PL * 0.62
pet_at(170, [], T["pet"] + 0.3, t1)
pet_at(260, [("🕶️", 150, 75)], t1, t2)
pet_at(340, [("🕶️", 190, 100), ("👑", 160, -120)], t2, T["s5"], "pop")
for k, (lv, frac) in enumerate([(1, .2), (5, .6), (12, 1.0)]):
    bar = rrect(760, 110, 55, (255, 255, 255, 235)); bdw = ImageDraw.Draw(bar)
    bdw.rounded_rectangle([170, 38, 170 + int(540 * frac), 72], 17, fill=(252, 120, 60)); bdw.rounded_rectangle([170, 38, 710, 72], 17, outline=(220, 200, 190), width=3)
    bdw.text((28, 24), "Lv " + str(lv), font=font(50), fill=INK)
    ts = [T["pet"] + 0.3, t1, t2][k]; te = [t1, t2, T["s5"]][k]
    add(bar, 540, 1530, ts, te, "rise" if k == 0 else "pop", 0.3)
add(text_sprite("Level up! እሰይ!", 84, GOLD), 540, 1680, t1 + 0.1, T["s5"], "pop")
add(emoji_sprite("💖", 110), 820, 760, t2, T["s5"], "bounce")
add(text_sprite("በተማሩ ቁጥር ያድጋል!", 74, WHITE), 540, 460, T["pet"] + 0.8, T["s5"], "rise")
SFX.extend([(t1, "ding"), (t2, "ding")])

# 6. price
add(text_sprite("3 ቀን በነፃ", 160, GOLD), 540, 520, T["price"] + 0.1, T["s7"], "pop")
add(text_sprite("ይሞክሩ!", 120, WHITE), 540, 690, T["price"] + 0.4, T["s7"], "rise")
full = rrect(900, 440, 60, (60, 48, 10, 255), GOLD + (255,), 7); fd = ImageDraw.Draw(full)
ctext(fd, 34, "ሙሉ ኮርስ · 4 ወር", font(64), GOLD, 900); ctext(fd, 130, "300 ብር", font(150), WHITE, 900)
ctext(fd, 312, "አንድ ጊዜ ብቻ ይክፈሉ", font(52, False), GOLD, 900)
add(shadow(full, 18), 540, 1150, T["full"] + 0.1, T["s7"], "pop", 0.45)
add(emoji_sprite("🔥", 120), 910, 940, T["full"] + 0.5, T["s7"], "bounce")

# 7. call to action
add(text_sprite("ቴሌግራም ላይ ይፈልጉን", 76, WHITE), 540, 520, T["cta"], T["end"] + 1, "rise")
btn = rrect(900, 190, 95, TG + (255,)); bdr = ImageDraw.Draw(btn)
ctext(bdr, 48, "@FidelEnglishBot", font(84), WHITE, 900)
add(shadow(btn, 18), 540, 720, T["cta"] + 0.3, T["end"] + 1, "pop", 0.5)
add(emoji_sprite("👆", 150), 540, 900, T["cta"] + 0.8, T["end"] + 1, "bounce")
add(text_sprite("ዛሬውኑ ይጀምሩ!", 130, GOLD), 540, 1130, T["cta"] + 2.0, T["end"] + 1, "pop")
foot = Image.new("RGBA", (620, 150), (0, 0, 0, 0)); sl = rrect(130, 130, 32, GOLD + (255,)); _s = emoji_sprite("🦁", 92); sl.alpha_composite(_s, ((130 - _s.width) // 2, (130 - _s.height) // 2))
foot.alpha_composite(sl, (0, 10)); ImageDraw.Draw(foot).text((160, 38), "Fidel English", font=font(72), fill=WHITE)
add(foot, 540, 1400, T["cta"] + 2.4, T["end"] + 1, "rise")

for at, kind in SFX: put(fx, sfx(kind).astype(np.float32), at)
for at, name in VOICE: put(voice, CLIPS[name] * 1.1, at)

level = np.convolve(np.abs(voice), np.ones(int(0.25 * SR)) / (0.25 * SR), "same")
duck = np.convolve(np.where(level > 0.01, 0.3, 1.0), np.ones(int(0.2 * SR)) / (0.2 * SR), "same").astype(np.float32)
mix = music * duck * 0.8 + fx + voice
fo = int(1.5 * SR); mix[int(TOTAL * SR) - fo:int(TOTAL * SR)] *= np.linspace(1, 0, fo)
mix = mix[:int(TOTAL * SR)]; mix /= max(1.0, np.abs(mix).max() / 0.95)


CONF_BITS = [emoji_sprite(e, 70) for e in ["🎉", "⭐", "🦁", "🎊", "👏", "🌟"]]
conf_seed = np.random.default_rng(9)
CONF = [[(conf_seed.uniform(0, W), conf_seed.uniform(-0.6, 0), conf_seed.integers(len(CONF_BITS)), conf_seed.uniform(0.7, 1.3), conf_seed.uniform(-180, 180)) for _ in range(34)] for _ in CONFETTI]

def frame(t):
    img = bg.copy()
    img.alpha_composite(GLOW1, (int(-160 + 120 * math.sin(t * .5)), int(140 + 90 * math.cos(t * .4))))
    img.alpha_composite(GLOW2, (int(480 + 100 * math.cos(t * .35)), int(1150 + 120 * math.sin(t * .45))))
    for e in EL:
        if t < e["t_in"] or t > e["t_out"]: continue
        p = (t - e["t_in"]) / e["dur"]; out = clamp((e["t_out"] - t) / 0.25)
        s, cx, cy, a = e["s"], e["cx"], e["cy"], clamp(p) * out
        an = e["anim"]
        if an == "rise": cy += (1 - ease_out(p)) * 60
        elif an == "slide": cx += (1 - ease_out(p)) * 700
        elif an == "pop":
            k = 0.5 + 0.5 * ease_back(p)
            if abs(k - 1) > .005: s = s.resize((max(1, int(s.width * k)), max(1, int(s.height * k))), Image.BILINEAR)
        elif an == "shake": cx += 14 * math.sin(t * 40); cy += 6 * math.sin(t * 31)
        elif an == "bounce": cy += 24 * math.sin((t - e["t_in"]) * 7)
        elif an == "blink": a *= 0.55 + 0.45 * math.sin(t * 14)
        if a <= .01: continue
        if a < .99: s = s.copy(); s.putalpha(s.split()[3].point(lambda v, q=a: int(v * q)))
        img.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2)))
    for (start, dur), pieces in zip(CONFETTI, CONF):
        if start <= t <= start + dur:
            u = (t - start) / dur
            for x, y0, bi, sp, rot in pieces:
                y = (y0 + u * 1.5 * sp) * H
                if -100 < y < H + 100:
                    piece = CONF_BITS[bi].rotate(rot * u * 3, expand=True)
                    img.alpha_composite(piece, (int(x + 40 * math.sin(u * 9 + x)) - piece.width // 2, int(y)))
    if t < 0.2: img = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), img, t / 0.2)
    return img.convert("RGB")

if __name__ == "__main__":
    if len(sys.argv) > 4 and sys.argv[4] == "stills":
        for tt in [float(x) for x in sys.argv[6].split(",")]: frame(tt).resize((540, 960)).save(os.path.join(sys.argv[5], "f%05.1f.png" % tt))
        print("TIMES", {k: round(v, 2) for k, v in T.items()}); sys.exit()
    out = sys.argv[3]; wav = out + ".wav"
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(wav, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-",
                          "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    n = int(TOTAL * FPS)
    for i in range(n):
        p.stdin.write(frame(i / FPS).tobytes())
        if i % 300 == 0: print("frame %d/%d" % (i, n), flush=True)
    p.stdin.close(); p.wait(); os.remove(wav)
    print("done", round(TOTAL, 1), "seconds")
