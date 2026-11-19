"""Silent games ad (1080x1920, ~40 s): real game play recorded by record_games.mjs, with Amharic captions.
No sound at all, so it works when Facebook/Instagram/TikTok play videos muted.

Usage:  python make_games_ad.py <recordings dir> <ffmpeg> <out.mp4>
"""
import os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

REC, FF, OUT = sys.argv[1:4]
W, H, FPS = 1080, 1920, 30
BOLD, REG, EMO = "C:/Windows/Fonts/ebrimabd.ttf", "C:/Windows/Fonts/ebrima.ttf", "C:/Windows/Fonts/seguiemj.ttf"
WHITE, GOLD, INK, MUTED, CARD, TG = (255, 255, 255), (255, 196, 61), (12, 38, 28), (190, 214, 200), (24, 70, 52), (42, 171, 238)
BG1, BG2 = (14, 58, 40), (6, 30, 20)
VW, VH, VX, VY = 800, 1422, 140, 400          # where the game video sits

# (clip, start s, length s, emoji, Amharic line, English line)
SCENES = [
    ("village", 6.0, 8.0, "🐺", "መንደሩን ከጅቦች ያድኑ!", "Pick the right English word"),
    ("boss",    0.3, 5.5, "🐉", "ዘንዶውን በእንግሊዝኛ ያሸንፉ!", "Grammar Boss Battle"),
    ("zombie",  1.0, 5.0, "🧟", "ከዞምቢዎች ያምልጡ!", "Spell and fix the sentence"),
    ("bomb",    1.0, 4.5, "💣", "ቦምቡን ያክሽፉ!", "Answer before time runs out"),
    ("alien",   1.0, 4.5, "👽", "መጻተኞችን እንግሊዝኛ ያስተምሩ!", "Idioms and everyday English"),
    ("pet",     0.0, 4.5, "🐶", "በተማሩ ቁጥር የሚያድግ የቤት እንስሳ", "Your pet grows when you learn"),
]

def font(size, bold=True): return ImageFont.truetype(BOLD if bold else REG, size)
def bg():
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):
        k = y / H; d.line([(0, y), (W, y)], fill=tuple(int(BG1[i] * (1 - k) + BG2[i] * k) for i in range(3)))
    im = im.convert("RGBA"); dots = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(dots)
    for x, y, r in [(90, 150, 80), (W - 110, 300, 50), (W - 60, H - 220, 100), (50, H - 400, 45)]:
        dd.ellipse([x - r, y - r, x + r, y + r], fill=GOLD + (30,))
    im.alpha_composite(dots); return im
def emoji(ch, size):
    e = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(e).text((80, 80), ch, font=ImageFont.truetype(EMO, 109), embedded_color=True, anchor="mm", fill="#000")
    e = e.crop(e.getbbox() or (0, 0, 1, 1)); k = size / max(e.size)
    return e.resize((max(1, int(e.width * k)), max(1, int(e.height * k))), Image.LANCZOS)
def text(im, y, s, f, fill): ImageDraw.Draw(im).text((W // 2, y), s, font=f, fill=fill, anchor="ma")
def fit(s, size, maxw=1000, bold=True):
    while ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(s, font=font(size, bold)) > maxw: size -= 4
    return font(size, bold)
def card(w, h, fill, outline, width=4, r=48):
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(c).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=fill + (255,), outline=outline + (255,), width=width); return c
def logo(im, y, size=50):
    f = font(size); tw = int(ImageDraw.Draw(im).textlength("Fidel English", font=f)); b = int(size * 1.7)
    box = card(b, b, GOLD, GOLD, 1, b // 4); l = emoji("🦁", int(b * .72)); box.alpha_composite(l, ((b - l.width) // 2, (b - l.height) // 2))
    x = (W - (b + 20 + tw)) // 2; im.alpha_composite(box, (x, y)); ImageDraw.Draw(im).text((x + b + 20, y + b // 2), "Fidel English", font=f, fill=WHITE, anchor="lm")

def scene_overlay(ic, am, en):
    """Background with a rounded hole for the game video, the caption on top and the bot name below."""
    im = bg()
    e = emoji(ic, 120); im.alpha_composite(e, ((W - e.width) // 2, 40))
    text(im, 178, am, fit(am, 76), GOLD); text(im, 290, en, fit(en, 46, bold=False), MUTED)
    hole = Image.new("L", (W, H), 255); ImageDraw.Draw(hole).rounded_rectangle([VX, VY, VX + VW, VY + VH], 44, fill=0)
    im.putalpha(Image.composite(im.getchannel("A"), Image.new("L", (W, H), 0), hole))
    ImageDraw.Draw(im).rounded_rectangle([VX - 4, VY - 4, VX + VW + 4, VY + VH + 4], 48, outline=GOLD + (255,), width=6)
    pill = card(560, 70, TG, TG, 1, 35); ImageDraw.Draw(pill).text((280, 35), "@FidelEnglishBot", font=font(40), fill=WHITE, anchor="mm")
    im.alpha_composite(pill, ((W - 560) // 2, VY + VH + 24)); return im

def intro():
    im = bg(); logo(im, 160, 58)
    e = emoji("🎮", 300); im.alpha_composite(e, ((W - e.width) // 2, 470))
    text(im, 860, "እንግሊዝኛ", font(150), GOLD); text(im, 1040, "በጨዋታ ይማሩ!", font(120), WHITE)
    text(im, 1240, "Learn English by playing", font(54, False), MUTED)
    for i, ch in enumerate(["🐺", "🐉", "🧟", "💣", "👽", "🐶"]):
        t = card(130, 130, CARD, (70, 130, 100), 4, 30); g = emoji(ch, 84); t.alpha_composite(g, ((130 - g.width) // 2, (130 - g.height) // 2))
        im.alpha_composite(t, (75 + i * 160, 1430))
    return im
def outro():
    im = bg(); logo(im, 110, 58)
    text(im, 330, "19 ጨዋታዎች · 101 ትምህርቶች", fit("19 ጨዋታዎች · 101 ትምህርቶች", 70), WHITE)
    text(im, 430, "ሁሉም ማብራሪያ በአማርኛ", font(56, False), MUTED)
    t = card(640, 120, GOLD, GOLD, 1, 60); ImageDraw.Draw(t).text((320, 60), "3 ቀን በነፃ ይሞክሩ!", font=font(62), fill=INK, anchor="mm")
    im.alpha_composite(t, ((W - 640) // 2, 560))
    c = card(900, 440, (60, 48, 10), GOLD, 7); cd = ImageDraw.Draw(c)
    cd.text((450, 40), "ሙሉ ኮርስ · 4 ወር", font=font(64), fill=GOLD, anchor="ma"); cd.text((450, 130), "300 ብር", font=font(160), fill=WHITE, anchor="ma")
    cd.text((450, 340), "አንድ ጊዜ ብቻ ይክፈሉ", font=font(52, False), fill=GOLD, anchor="ma")
    im.alpha_composite(c, ((W - 900) // 2, 760))
    text(im, 1290, "ቴሌግራም ላይ ይፈልጉን", font(66), WHITE)
    b = card(920, 160, TG, TG, 1, 80); ImageDraw.Draw(b).text((460, 80), "@FidelEnglishBot", font=font(78), fill=WHITE, anchor="mm")
    im.alpha_composite(b, ((W - 920) // 2, 1400))
    text(im, 1600, "t.me/FidelEnglishBot", font(58), GOLD)
    p = emoji("👆", 130); im.alpha_composite(p, ((W - p.width) // 2, 1700))
    return im

tmp = tempfile.mkdtemp(); parts = []
def ff(*a): subprocess.run([FF, "-loglevel", "error", "-y", *a], check=True)
def still(im, secs, name):
    png = os.path.join(tmp, name + ".png"); im.convert("RGB").save(png); out = os.path.join(tmp, name + ".mp4")
    ff("-loop", "1", "-t", str(secs), "-i", png, "-vf", f"fps={FPS},format=yuv420p,fade=t=in:st=0:d=0.25", "-c:v", "libx264", "-preset", "medium", "-crf", "20", out)
    parts.append(out)

still(intro(), 2.5, "intro")
for clip, st, ln, ic, am, en in SCENES:
    png = os.path.join(tmp, clip + "_ov.png"); scene_overlay(ic, am, en).save(png); out = os.path.join(tmp, clip + ".mp4")
    fc = (f"[0:v]fps={FPS},trim=start={st}:duration={ln},setpts=PTS-STARTPTS,scale={VW}:{VH}[g];"
          f"color=c=0x0e3a28:s={W}x{H}:r={FPS}:d={ln}[b];[b][g]overlay={VX}:{VY}[v];[v][1:v]overlay=0:0,format=yuv420p,fade=t=in:st=0:d=0.2[o]")
    ff("-f", "concat", "-safe", "0", "-i", os.path.join(REC, clip, "list.txt"), "-loop", "1", "-t", str(ln), "-i", png,
       "-filter_complex", fc, "-map", "[o]", "-t", str(ln), "-c:v", "libx264", "-preset", "medium", "-crf", "20", out)
    parts.append(out); print("scene", clip, flush=True)
still(outro(), 5.0, "outro")
lst = os.path.join(tmp, "parts.txt"); open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
# silent audio track so every app accepts the file
ff("-f", "concat", "-safe", "0", "-i", lst, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
   "-c:v", "copy", "-c:a", "aac", "-b:a", "32k", "-movflags", "+faststart", OUT)
print("done", OUT)
