"""Gera a foto de perfil (800x800) e o banner (2560x1440) do canal Por Que Será?"""
import math, random, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = sys.argv[1]
BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
SEMI = "/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf"
NAVY_TOP, NAVY_BOT = (10, 25, 60), (8, 70, 110)
YELLOW, WHITE = (255, 214, 0), (255, 255, 255)

def gradient(w, h, a, b, radial=False):
    img = Image.new("RGB", (w, h))
    px = img.load()
    cx, cy, rmax = w / 2, h / 2, math.hypot(w / 2, h / 2)
    for y in range(h):
        for x in range(0, w):
            t = math.hypot(x - cx, y - cy) / rmax if radial else y / (h - 1)
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return img

def fast_gradient(w, h, a, b):
    col = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / (h - 1)
        col.putpixel((0, y), tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)))
    return col.resize((w, h))

def glow_text(base, xy, text, font, fill, anchor="mm", glow=(255, 214, 0), radius=18, alpha=110):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(xy, text, font=font, fill=glow + (alpha,), anchor=anchor)
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius)))
    d = ImageDraw.Draw(base)
    d.text((xy[0] + 6, xy[1] + 8), text, font=font, fill=(0, 0, 0, 120), anchor=anchor)
    d.text(xy, text, font=font, fill=fill, anchor=anchor)

def faint_marks(base, n, size_range, seed):
    rnd = random.Random(seed)
    w, h = base.size
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    for _ in range(n):
        s = rnd.randint(*size_range)
        f = ImageFont.truetype(BLACK, s)
        mark = Image.new("RGBA", (s * 2, s * 2), (0, 0, 0, 0))
        ImageDraw.Draw(mark).text((s, s), "?", font=f, fill=(255, 255, 255, rnd.randint(14, 34)), anchor="mm")
        mark = mark.rotate(rnd.randint(-30, 30), resample=Image.BICUBIC)
        layer.alpha_composite(mark, (rnd.randint(-s, w - s), rnd.randint(-s, h - s)))
    base.alpha_composite(layer)

# ---------- Foto de perfil 800x800 ----------
p = gradient(800, 800, (14, 90, 140), (6, 18, 48), radial=True).convert("RGBA")
faint_marks(p, 10, (90, 170), seed=3)
glow_text(p, (400, 385), "?", ImageFont.truetype(BLACK, 560), YELLOW, radius=30, alpha=140)
p.convert("RGB").save(f"{OUT}/foto_perfil.png")

# ---------- Banner 2560x1440 (área segura central 1546x423) ----------
b = fast_gradient(2560, 1440, NAVY_TOP, NAVY_BOT).convert("RGBA")
faint_marks(b, 45, (120, 320), seed=7)
cx, cy = 1280, 720
glow_text(b, (cx, cy - 40), "POR QUE SERÁ?", ImageFont.truetype(BLACK, 170), WHITE, glow=YELLOW, radius=26, alpha=90)
d = ImageDraw.Draw(b)
# troca o "?" final por amarelo: redesenha por cima
f = ImageFont.truetype(BLACK, 170)
full_w = d.textlength("POR QUE SERÁ?", font=f)
q_w = d.textlength("?", font=f)
qx = cx + full_w / 2 - q_w
d.text((qx, cy - 40), "?", font=f, fill=YELLOW, anchor="lm")
sub = "Curiosidades em 1 minuto  •  Vídeo novo todo dia"
d.text((cx, cy + 105), sub, font=ImageFont.truetype(SEMI, 58), fill=(220, 235, 255), anchor="mm")
b.convert("RGB").save(f"{OUT}/banner.png")
print("ok")
