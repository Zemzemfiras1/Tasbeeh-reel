#!/usr/bin/env python3
"""
Render an animated Arabic-English Tasbeeh counter Reel.

Features:
- Custom Arabic and English Dhikr
- Adjustable target count and repetition interval
- Automatic video duration calculation
- Royal ("queenly") colour palettes: purple, burgundy, blue, violet, amethyst, with gold
- A simple, randomly chosen illustrated background on every run:
  mosque skyline, lantern, Quran with prayer beads, or geometric star
- Optional custom background image
- MP3 soundtrack support
- H.264 MP4 output

Examples:
    python render.py --target 100 --count-interval 1.5
    python render.py --palette royal-purple --scene mosque
    python render.py --seed 4242            # repeat a previous random look
    python render.py --preview look.png     # save one still frame and exit
"""

from __future__ import annotations

import argparse
import array
import math
import random
import shutil
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


# ---------------------------------------------------------
# ROYAL PALETTES
# ---------------------------------------------------------

GOLD = (226, 188, 98)
GOLD_BRIGHT = (247, 216, 130)
IVORY = (250, 241, 222)


def mix(a, b, t):
    return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(3))


@dataclass(frozen=True)
class Palette:
    name: str
    top: tuple      # sky colour at the top of the frame
    bottom: tuple   # deeper colour at the bottom
    glow: tuple     # soft light behind the counter
    accent: tuple   # gold used for lines, text and ornaments
    active: tuple   # lit bead colour
    pale: tuple     # main text colour
    muted: tuple    # secondary text colour
    panel: tuple    # RGBA fill of the centre counter disc
    idle: tuple     # RGBA fill of beads not yet counted
    shadow: tuple   # silhouette colour (skyline, Quran)


def build_palette(name, top, bottom, glow):
    return Palette(
        name=name,
        top=top,
        bottom=bottom,
        glow=glow,
        accent=GOLD,
        active=GOLD_BRIGHT,
        pale=IVORY,
        muted=mix(IVORY, glow, 0.25),
        panel=(*mix(bottom, (0, 0, 0), 0.30), 228),
        idle=(*mix(glow, IVORY, 0.35), 205),
        shadow=mix(bottom, (0, 0, 0), 0.55),
    )


PALETTE_SPECS = {
    "royal-purple": ((58, 22, 100), (24, 8, 50), (138, 70, 190)),
    "burgundy": ((104, 18, 50), (44, 6, 26), (184, 58, 92)),
    "royal-blue": ((20, 42, 118), (7, 15, 56), (60, 108, 208)),
    "midnight-violet": ((38, 18, 84), (13, 7, 38), (104, 76, 196)),
    "amethyst": ((92, 34, 120), (38, 12, 58), (176, 98, 196)),
}

PALETTES = {name: build_palette(name, *spec) for name, spec in PALETTE_SPECS.items()}

# Words in --background that pick a palette or a scene.
PALETTE_WORDS = {
    "royal-purple": ("purple", "lavender"),
    "burgundy": ("burgundy", "crimson", "ruby", "wine", "red"),
    "royal-blue": ("blue", "sapphire", "navy"),
    "midnight-violet": ("violet", "midnight"),
    "amethyst": ("amethyst", "plum", "magenta"),
}

SCENES = ("mosque", "lantern", "quran", "star")

# Opt-in animated scenes: never picked at random, only by --scene or keywords.
ANIMATED_SCENES = ("rain-flower",)

SCENE_WORDS = {
    "mosque": ("mosque", "masjid", "minaret", "dome", "skyline", "moon", "crescent"),
    "lantern": ("lantern", "fanous", "ramadan"),
    "quran": ("quran", "koran", "book", "rehal", "beads"),
    "star": ("star", "geometric", "pattern", "ornament"),
    "rain-flower": ("rain", "flower", "bloom", "raindrop", "garden"),
}


def choose_style(description, palette_arg, scene_arg, rng):
    """Pick palette and scene. Explicit flags win, then keywords, then random."""
    text = (description or "").lower()

    palette = palette_arg if palette_arg and palette_arg != "random" else None
    if palette is None:
        for name, words in PALETTE_WORDS.items():
            if any(word in text for word in words):
                palette = name
                break
    if palette is None:
        palette = rng.choice(list(PALETTES))

    scene = scene_arg if scene_arg and scene_arg != "random" else None
    if scene is None:
        for name, words in SCENE_WORDS.items():
            if any(word in text for word in words):
                scene = name
                break
    if scene is None:
        scene = rng.choice(SCENES)

    return PALETTES[palette], scene



# ---------------------------------------------------------
# DHIKR LIBRARY (the seven recommended adhkar, wording supplied by the user)
# ---------------------------------------------------------

ADHKAR = {
    1: ("سُبْحَانَ اللَّهِ", "SubhanAllah", "Glory be to Allah.", ("subhanallah", "subhan")),
    2: ("الْحَمْدُ لِلَّهِ", "Alhamdulillah", "All praise and thanks belong to Allah.", ("alhamdulillah", "hamd")),
    3: ("اللَّهُ أَكْبَرُ", "Allahu Akbar", "Allah is the Greatest.", ("akbar",)),
    4: ("لَا إِلَٰهَ إِلَّا اللَّهُ", "La ilaha illa Allah", "There is no god worthy of worship except Allah.", ("tahlil", "ilaha")),
    5: ("أَسْتَغْفِرُ اللَّهَ", "Astaghfirullah", "I seek forgiveness from Allah.", ("astaghfirullah", "istighfar", "forgiveness")),
    6: ("سُبْحَانَ اللَّهِ وَبِحَمْدِهِ", "SubhanAllahi wa bihamdihi", "Glory be to Allah and praise be to Him.", ("bihamdihi",)),
    7: ("لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ", "La hawla wa la quwwata illa billah", "There is no power and no strength except through Allah.", ("hawla", "quwwata", "hawqala")),
}


def find_dhikr(key):
    """Return (arabic, transliteration, meaning) for a number 1-7 or a name, else None."""
    text = str(key).strip().lower().replace("-", "").replace(" ", "")
    if text.isdigit() and int(text) in ADHKAR:
        a, t, m, _ = ADHKAR[int(text)]
        return a, t, m
    # longest keyword first so "bihamdihi" beats "subhan"
    hits = sorted(
        ((len(w), n) for n, v in ADHKAR.items() for w in v[3] if w in text or text in w.replace(" ", "")),
        reverse=True,
    )
    if hits:
        a, t, m, _ = ADHKAR[hits[0][1]]
        return a, t, m
    return None

# ---------------------------------------------------------
# FONTS
# ---------------------------------------------------------

def find_font(bold: bool = False) -> str | None:
    if bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]

    for candidate in candidates:
        if Path(candidate).exists():
            return candidate

    return None


def font(size: int, bold: bool = False):
    path = find_font(bold)

    if path:
        return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def arabic_font(size: int):
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)

    return font(size)


# ---------------------------------------------------------
# TEXT HELPERS
# ---------------------------------------------------------

def centered(draw, text, y, selected_font, fill, width, **kw):
    box = draw.textbbox((0, 0), text, font=selected_font, **kw)
    text_width = box[2] - box[0]

    draw.text(
        ((width - text_width) / 2, y),
        text,
        font=selected_font,
        fill=fill,
        **kw,
    )


# ---------------------------------------------------------
# DRAWING TOOLKIT FOR BACKGROUND MOTIFS
#
# Motifs are drawn as white-on-black masks at 2x size (smooth edges),
# then painted onto the background in one flat colour. Local motif
# coordinates use y-up, with (0, 0) at the motif's anchor point.
# ---------------------------------------------------------

SS = 2  # supersampling factor


def new_mask(width, height):
    return Image.new("L", (width * SS, height * SS), 0)


class Pen:
    def __init__(self, mask, cx, cy, scale, flip=1):
        self.d = ImageDraw.Draw(mask)
        self.cx, self.cy, self.s, self.flip = cx, cy, scale, flip

    def T(self, x, y):
        return (
            (self.cx + self.flip * x * self.s) * SS,
            (self.cy - y * self.s) * SS,
        )

    def poly(self, pts, fill=255):
        self.d.polygon([self.T(*p) for p in pts], fill=fill)

    def rect(self, x0, y0, x1, y1, fill=255):
        ax, ay = self.T(x0, y1)
        bx, by = self.T(x1, y0)
        self.d.rectangle(
            [min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)], fill=fill
        )

    def circle(self, x, y, r, fill=255):
        ax, ay = self.T(x - r, y + r)
        bx, by = self.T(x + r, y - r)
        self.d.ellipse(
            [min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)], fill=fill
        )

    def line(self, p, q, width, fill=255):
        self.d.line(
            [self.T(*p), self.T(*q)],
            fill=fill,
            width=max(1, round(width * self.s * SS)),
        )


def dome_pts(radius, height, tip=0.22, n=40):
    """Half-outline of an onion-style dome with a slight point."""
    pts = []
    for i in range(n + 1):
        a = math.pi * i / n
        sa = math.sin(a)
        pts.append((radius * math.cos(a), height * sa + tip * height * sa ** 12))
    return pts


def shifted(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


def paint(img, mask, color, opacity, halo=0):
    """Paint a motif mask onto the image in a flat colour."""
    small = mask.resize(img.size, Image.Resampling.LANCZOS)

    if halo:
        soft = small.filter(ImageFilter.GaussianBlur(halo))
        soft = soft.point(lambda v: int(v * opacity * 0.45))
        img.paste(color, mask=soft)

    img.paste(color, mask=small.point(lambda v: int(v * opacity)))


def add_glow(img, color, center, radius, strength):
    width, height = img.size
    size = max(2, int(radius * 2))

    # PIL's radial gradient only reaches 181/255 at the edge of its square,
    # so rescale it to fade to exactly zero (no visible hard edge).
    rad = ImageOps.invert(Image.radial_gradient("L"))
    rad = rad.resize((size, size), Image.Resampling.BICUBIC)
    rad = rad.point(lambda v: int(max(0, v - 74) * 255 / 181 * strength))

    mask = Image.new("L", (width, height), 0)
    mask.paste(rad, (int(center[0] - radius), int(center[1] - radius)))
    img.paste(color, mask=mask)


# ---------------------------------------------------------
# MOTIFS (simple, original shapes inspired by classic Islamic art)
# ---------------------------------------------------------

def draw_mosque(p):
    """Mosque skyline: central dome, side domes, two minarets, arched door."""
    p.rect(-900, -400, 900, 62)           # low wall that spans the frame
    p.rect(-270, 0, 270, 170)             # main hall
    p.rect(-125, 170, 125, 238)           # drum
    p.poly(shifted(dome_pts(138, 168), 0, 238))

    top = 238 + 168 + 0.22 * 168
    p.line((0, top - 8), (0, top + 50), 7)
    p.circle(0, top + 78, 26)             # finial crescent
    p.circle(11, top + 84, 21, 0)

    for sx in (-205, 205):                # side domes
        p.rect(sx - 48, 170, sx + 48, 214)
        p.poly(shifted(dome_pts(56, 52), sx, 214))
        p.line((sx, 276), (sx, 312), 5)
        p.circle(sx, 318, 7)

    for sx in (-560, 560):                # far small domes
        p.rect(sx - 46, 62, sx + 46, 98)
        p.poly(shifted(dome_pts(52, 46), sx, 98))

    for mx in (-375, 375):                # minarets
        p.rect(mx - 23, 0, mx + 23, 300)
        p.rect(mx - 40, 300, mx + 40, 322)
        p.rect(mx - 17, 322, mx + 17, 405)
        p.rect(mx - 27, 405, mx + 27, 418)
        p.poly([(mx - 24, 418), (mx + 24, 418), (mx, 500)])
        p.line((mx, 495), (mx, 535), 4)
        p.circle(mx, 542, 8)
        p.rect(mx - 5, 170, mx + 5, 255, 0)

    p.rect(-38, 0, 38, 84, 0)             # door
    p.circle(0, 84, 38, 0)
    for wx in (-215, -150, 150, 215):     # windows
        p.rect(wx - 13, 70, wx + 13, 128, 0)
        p.circle(wx, 128, 13, 0)


def draw_lantern(p, chain):
    """Hanging Ramadan lantern. Anchor is the ring; chain reaches upward."""
    p.rect(-2.5, 28, 2.5, 28 + chain)
    p.circle(0, 26, 11)
    p.circle(0, 26, 5.5, 0)
    p.poly(shifted(dome_pts(60, 40, 0.2), 0, -30))
    p.rect(-68, -42, 68, -30)
    p.poly([(-62, -42), (62, -42), (74, -212), (-74, -212)])
    p.poly([(-74, -212), (74, -212), (42, -244), (-42, -244)])
    p.circle(0, -254, 10)
    p.line((0, -254), (0, -288), 5)
    p.circle(0, -294, 7)

    for wx in (-38, 0, 38):               # arched windows
        p.rect(wx - 12, -190, wx + 12, -100, 0)
        p.circle(wx, -100, 12, 0)
    p.rect(-52, -148, 52, -143, 255)      # lattice bar


def draw_quran(p):
    """Open Quran on a folding stand, with a string of prayer beads."""
    p.line((-135, 48), (115, -125), 22)
    p.line((135, 48), (-115, -125), 22)
    p.rect(-165, -140, 165, -122)

    left = [(-232, 46), (-8, -6), (-8, 176), (-232, 226)]
    p.poly(left)
    p.poly([(-x, y) for x, y in left])
    p.line((0, -8), (0, 178), 5, 0)

    for sign in (-1, 1):                  # lines of text
        for f in (0.12, 0.24, 0.36, 0.48, 0.60, 0.72, 0.84):
            pts = []
            for xx in (205, 32):
                u = (232 - xx) / 224
                bottom = 46 + (-6 - 46) * u
                top = 226 + (176 - 226) * u
                pts.append((sign * xx, bottom + (top - bottom) * f))
            p.line(pts[0], pts[1], 4, 0)

    p0, c, p1 = (236, 70), (310, 10), (262, -112)   # prayer beads
    n = 10
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]
        p.circle(x, y, 8.5)
    p.line(p1, (262, -140), 4)
    p.poly([(248, -140), (276, -140), (284, -196), (240, -196)])


def paint_star(img, pal, opacity, cx, cy, radius, line_px=5):
    """Eight-pointed geometric star (two layers) with dots on the tips."""
    width, height = img.size
    mask = new_mask(width, height)
    d = ImageDraw.Draw(mask)

    for k in (1.0, 0.82):
        pts = []
        for i in range(16):
            ang = 2 * math.pi * i / 16 - math.pi / 2
            rad = radius * k * (1.0 if i % 2 == 0 else 0.7654)
            pts.append(((cx + rad * math.cos(ang)) * SS, (cy + rad * math.sin(ang)) * SS))
        d.line(pts + [pts[0]], fill=255, width=line_px * SS, joint="curve")

    dot = max(4, line_px * 2)
    for i in range(8):
        ang = 2 * math.pi * i / 8 - math.pi / 2
        x = (cx + radius * math.cos(ang)) * SS
        y = (cy + radius * math.sin(ang)) * SS
        d.ellipse((x - dot * SS, y - dot * SS, x + dot * SS, y + dot * SS), fill=255)

    paint(img, mask, pal.accent, opacity)


def paint_crescent(img, pal, cx, cy, radius, side):
    width, height = img.size
    mask = new_mask(width, height)
    d = ImageDraw.Draw(mask)

    d.ellipse(
        ((cx - radius) * SS, (cy - radius) * SS, (cx + radius) * SS, (cy + radius) * SS),
        fill=255,
    )
    ox, oy, r2 = cx + side * 0.38 * radius, cy - 0.10 * radius, radius * 0.84
    d.ellipse(
        ((ox - r2) * SS, (oy - r2) * SS, (ox + r2) * SS, (oy + r2) * SS),
        fill=0,
    )
    paint(img, mask, pal.accent, 0.85, halo=22)


# ---------------------------------------------------------
# BACKGROUND SCENES
# ---------------------------------------------------------

def vertical_gradient(width, height, top, bottom):
    mask = Image.linear_gradient("L").resize((width, height), Image.Resampling.BILINEAR)
    return Image.composite(
        Image.new("RGB", (width, height), bottom),
        Image.new("RGB", (width, height), top),
        mask,
    )


def sprinkle(img, pal, rng):
    """Tiny stars and a few four-point sparkles."""
    width, height = img.size
    d = ImageDraw.Draw(img, "RGBA")

    for _ in range(80):
        x, y = rng.randrange(width), rng.randrange(height)
        r = rng.choice((1, 1, 2, 2, 3))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(*pal.pale, rng.randint(40, 140)))

    placed = 0
    while placed < 5:
        x, y = rng.randrange(60, width - 60), rng.randrange(60, height - 60)
        # keep sparkles off the counter, the Dhikr text and the progress bar
        if 0.12 * height < y < 0.78 * height and abs(x - width / 2) < width * 0.34:
            continue
        if 0.66 * height < y < 0.84 * height and abs(x - width / 2) < width * 0.40:
            continue
        placed += 1
        r = rng.randint(10, 18)
        q = r * 0.22
        d.polygon(
            [(x, y - r), (x + q, y - q), (x + r, y), (x + q, y + q),
             (x, y + r), (x - q, y + q), (x - r, y), (x - q, y - q)],
            fill=(*pal.active, 150),
        )


def add_frame(img, pal):
    """Thin double gold border: quiet and regal."""
    width, height = img.size
    d = ImageDraw.Draw(img, "RGBA")
    m = int(width * 0.035)

    d.rounded_rectangle(
        (m, m, width - m, height - m),
        radius=int(width * 0.04),
        outline=(*pal.accent, 110),
        width=3,
    )
    d.rounded_rectangle(
        (m + 14, m + 14, width - m - 14, height - m - 14),
        radius=int(width * 0.03),
        outline=(*pal.accent, 55),
        width=1,
    )


def scene_mosque(img, pal, rng):
    width, height = img.size
    unit = width / 1080
    side = rng.choice((-1, 1))

    paint_star(img, pal, 0.14, width / 2, height * 0.42, width * 0.47)
    paint_crescent(img, pal, width * (0.5 + side * 0.34), height * 0.14, width * 0.065, side)

    # Kept low so the skyline sits below the progress bar.
    add_glow(img, pal.glow, (width / 2, height * 0.94), width * 0.70, 0.60)
    mask = new_mask(width, height)
    draw_mosque(Pen(mask, width / 2, height, 0.60 * unit))
    paint(img, mask, pal.shadow, 0.94)


def scene_lantern(img, pal, rng):
    width, height = img.size
    unit = width / 1080
    flip = rng.choice((-1, 1))

    paint_star(img, pal, 0.14, width / 2, height * 0.42, width * 0.47)

    for fx, fy, sc in ((0.13, 0.20, 0.78), (0.87, 0.09, 0.58)):
        s = sc * unit
        cx = width * (0.5 + flip * (fx - 0.5))
        cy = height * fy
        mask = new_mask(width, height)
        draw_lantern(Pen(mask, cx, cy, s), chain=cy / s + 40)
        paint(img, mask, pal.accent, 0.78, halo=16)


def scene_quran(img, pal, rng):
    width, height = img.size
    unit = width / 1080
    flip = rng.choice((-1, 1))

    paint_star(img, pal, 0.13, width / 2, height * 0.42, width * 0.47)

    s = 0.58 * unit
    cx = width * (0.5 - flip * 0.40)
    cy = height * 0.12
    mask = new_mask(width, height)
    draw_lantern(Pen(mask, cx, cy, s), chain=cy / s + 40)
    paint(img, mask, pal.accent, 0.78, halo=14)

    by = height * 0.92
    add_glow(img, pal.glow, (width / 2, by - 40), width * 0.60, 0.55)
    mask = new_mask(width, height)
    draw_quran(Pen(mask, width / 2, by, 0.78 * unit, flip))
    paint(img, mask, pal.shadow, 0.94)


def scene_star(img, pal, rng):
    width, height = img.size
    side = rng.choice((-1, 1))

    paint_star(img, pal, 0.24, width / 2, height * 0.42, width * 0.47, line_px=6)
    for fx in (0.25, 0.5, 0.75):          # row of small stars along the bottom
        paint_star(img, pal, 0.34, width * fx, height * 0.935, width * 0.055, line_px=3)
    paint_crescent(img, pal, width * (0.5 + side * 0.34), height * 0.14, width * 0.065, side)



def scene_rain_flower(img, pal, rng):
    """Static part of the rain-flower scene: soft clouds and a small mound of earth."""
    width, height = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cloud = (*mix(pal.glow, IVORY, 0.30), 78)
    for cx, cy, rx, ry in [
        (0.30, 0.150, 0.20, 0.030), (0.52, 0.135, 0.24, 0.040), (0.72, 0.155, 0.20, 0.030),
        (0.42, 0.165, 0.22, 0.028), (0.62, 0.170, 0.20, 0.025),
    ]:
        d.ellipse((width * (cx - rx), height * (cy - ry), width * (cx + rx), height * (cy + ry)), fill=cloud)
    layer = layer.filter(ImageFilter.GaussianBlur(18))
    img.paste(layer, (0, 0), layer)

    # earth mound under the flower
    d = ImageDraw.Draw(img, "RGBA")
    gy = int(height * 0.625)
    d.ellipse((width * 0.22, gy - 26, width * 0.78, gy + 70), fill=(*mix(pal.shadow, pal.glow, 0.22), 235))
    d.arc((width * 0.22, gy - 26, width * 0.78, gy + 70), 200, 340, fill=(*pal.accent, 150), width=3)


def smooth(x, a=0.0, b=1.0):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


RAIN_RNG = random.Random(7)
RAIN_DROPS = [
    (RAIN_RNG.uniform(0.06, 0.94), RAIN_RNG.uniform(850, 1250), RAIN_RNG.uniform(0, 1), RAIN_RNG.uniform(26, 56))
    for _ in range(64)
]
PETAL_PINK = (236, 142, 172)
PETAL_LIGHT = (250, 200, 216)
LEAF_GREEN = (82, 168, 116)
STEM_GREEN = (64, 140, 98)


def lens(p0, ang, length, half_w, steps=14):
    """Pointed leaf/petal shape starting at p0 and pointing along ang (radians)."""
    ca, sa = math.cos(ang), math.sin(ang)
    left, right = [], []
    for i in range(steps + 1):
        t = i / steps
        w = half_w * math.sin(math.pi * t) ** 0.85
        x, y = t * length, w
        left.append((p0[0] + x * ca - y * sa, p0[1] + x * sa + y * ca))
        right.append((p0[0] + x * ca + y * sa, p0[1] + x * sa - y * ca))
    return left + right[::-1]


def draw_rain_flower(frame, draw, elapsed, count, target, interval, palette, width, height, side_seed):
    """Animated layer: falling rain, a drop that lands on the flower at every count,
    ripples, and a flower that grows and opens as the count rises."""
    cx = width // 2
    gy = int(height * 0.625)                       # ground line
    cp = min(1.0, elapsed / (target * interval))   # smooth progress 0..1

    # ---- background rain (loops forever, stops at the ground) ----
    top, span = int(height * 0.19), gy - int(height * 0.19)
    for fx, speed, phase, ln in RAIN_DROPS:
        y = top + (phase * span + elapsed * speed) % span
        x = fx * width - (y - top) * 0.05
        draw.line((x, y, x - 5, y + ln), fill=(*palette.pale, 70), width=3)

    # ---- flower geometry ----
    stem_full = 420
    stem_h = stem_full * (0.40 + 0.60 * smooth(cp, 0.0, 0.40))
    bloom = smooth(cp, 0.22, 0.95)
    sway = 12 * math.sin(elapsed * 0.9)
    head = (cx + sway, gy - stem_h)

    since = elapsed - (count - 1) * interval       # time since this count began
    pulse = max(0.0, 1.0 - since / 0.9) ** 2 if since >= 0 else 0.0

    # glow behind the head, brightest right after a drop lands
    glow_r = 120 + 90 * bloom
    gl = Image.new("RGBA", (int(glow_r * 2), int(glow_r * 2)), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gl)
    for i in range(6, 0, -1):
        r = glow_r * i / 6
        gd.ellipse((glow_r - r, glow_r - r, glow_r + r, glow_r + r), fill=(*palette.accent, int((18 + 70 * pulse) * (1 - i / 7))))
    gl = gl.filter(ImageFilter.GaussianBlur(10))
    frame.paste(gl, (int(head[0] - glow_r), int(head[1] - glow_r)), gl)

    # ---- the flower itself, drawn 2x then reduced for smooth edges ----
    bx, by, bw, bh = cx - 300, gy - 620, 600, 640
    k = 2
    layer = Image.new("RGBA", (bw * k, bh * k), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)

    def P(x, y):
        return ((x - bx) * k, (y - by) * k)

    # stem
    pts = []
    for i in range(21):
        t = i / 20
        pts.append(P(cx + sway * t * t, gy - stem_h * t))
    ld.line(pts, fill=STEM_GREEN, width=15 * k, joint="curve")
    for pt in (pts[0], pts[-1]):
        ld.ellipse((pt[0] - 7 * k, pt[1] - 7 * k, pt[0] + 7 * k, pt[1] + 7 * k), fill=STEM_GREEN)

    # leaves
    leaf_scale = smooth(cp, 0.05, 0.45)
    for t, direction in ((0.30, -1), (0.52, 1)):
        sx = cx + sway * t * t
        sy = gy - stem_h * t
        ang = math.radians(-90 + direction * 52) + 0.05 * math.sin(elapsed * 1.1 + t * 6)
        if leaf_scale < 0.06:
            continue
        poly = lens((sx, sy), ang, (60 + 90 * leaf_scale) * leaf_scale ** 0.6, 26 * (0.3 + 0.7 * leaf_scale))
        ld.polygon([P(*q) for q in poly], fill=LEAF_GREEN, outline=(*mix(LEAF_GREEN, IVORY, 0.4), 200))

    # petals: a closed bud that fans out into a full bloom
    big = 62 + 98 * bloom
    spread = 38 + 322 * bloom
    for layer_i, (n, length, color, rot) in enumerate((
        (9, big, PETAL_PINK, 0.0),
        (9, big * 0.72, PETAL_LIGHT, 0.5),
        (7, big * 0.42, mix(PETAL_LIGHT, IVORY, 0.5), 0.25),
    )):
        for i in range(n):
            frac = (i + rot) / n - 0.5 + 0.5 / n
            a = math.radians(-90 + spread * frac) + 0.03 * math.sin(elapsed * 1.3 + i)
            poly = lens(head, a, length, length * 0.30)
            ld.polygon([P(*q) for q in poly], fill=(*color, 245), outline=(*mix(color, IVORY, 0.5), 220))
    cr = 14 + 12 * bloom
    c = P(*head)
    ld.ellipse((c[0] - cr * k, c[1] - cr * k, c[0] + cr * k, c[1] + cr * k), fill=GOLD_BRIGHT, outline=GOLD, width=2 * k)

    layer = layer.resize((bw, bh), Image.Resampling.BOX)
    frame.paste(layer, (bx, by), layer)

    # ---- the drop for the next count ----
    if count < target:
        t_next = count * interval
        fall = 0.75
        u = (elapsed - (t_next - fall)) / fall
        if 0 <= u < 1:
            sgn = 1 if (count + side_seed) % 2 else -1
            x0, y0 = cx + sgn * 300, height * 0.185
            x = x0 + (head[0] - x0) * u
            y = y0 + (head[1] - 20 - y0) * u * u
            r = 14
            draw.polygon([(x, y - 44), (x - r * 0.9, y - 8), (x + r * 0.9, y - 8)], fill=(190, 224, 255, 235))
            draw.ellipse((x - r, y - r - 6, x + r, y + r - 6), fill=(190, 224, 255, 235))
            draw.ellipse((x - 5, y - r - 2, x + 1, y - 7), fill=(255, 255, 255, 230))

    # ---- ripples where the last drop landed ----
    if 0 <= since < 0.9:
        for j in range(2):
            tt = since - j * 0.18
            if tt <= 0:
                continue
            rr = 36 + tt * 230
            a = int(200 * max(0, 1 - tt / 0.9))
            draw.ellipse(
                (head[0] - rr, head[1] - rr * 0.55, head[0] + rr, head[1] + rr * 0.55),
                outline=(*palette.pale, a), width=3,
            )


def draw_ring_counter(frame, draw, count, target, palette, width, height):
    cx, cy, r = width // 2, int(height * 0.255), 96
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=palette.panel)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(*palette.pale, 70), width=8)
    prog = min(1.0, count / target)
    if prog > 0:
        draw.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * prog, fill=palette.accent, width=8)
    centered(draw, str(count), cy - 52, font(76, True), palette.pale, width)
    centered(draw, f"OF {target}", cy + 34, font(18, True), palette.accent, width)

SCENE_PAINTERS = {
    "mosque": scene_mosque,
    "lantern": scene_lantern,
    "quran": scene_quran,
    "star": scene_star,
    "rain-flower": scene_rain_flower,
}


def make_background(width, height, palette, scene, rng):
    img = vertical_gradient(width, height, palette.top, palette.bottom)
    add_glow(img, palette.glow, (width * 0.5, height * 0.40), width * 1.05, 0.50)
    add_frame(img, palette)
    sprinkle(img, palette, rng)
    SCENE_PAINTERS[scene](img, palette, rng)
    return img


# ---------------------------------------------------------
# BACKGROUND IMAGE
# ---------------------------------------------------------

def load_background(width, height, image_path):
    image = Image.open(image_path).convert("RGB")

    image_ratio = image.width / image.height
    target_ratio = width / height

    if image_ratio > target_ratio:
        new_height = height
        new_width = int(height * image_ratio)
    else:
        new_width = width
        new_height = int(width / image_ratio)

    image = image.resize(
        (new_width, new_height),
        Image.Resampling.LANCZOS,
    )

    left = (new_width - width) // 2
    top = (new_height - height) // 2

    image = image.crop(
        (left, top, left + width, top + height)
    )

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 95))
    image = Image.alpha_composite(image.convert("RGBA"), overlay)

    return image.convert("RGB")


# ---------------------------------------------------------
# TASBEEH FRAME
# ---------------------------------------------------------

def make_frame(
    elapsed,
    target,
    count_interval,
    arabic,
    translation,
    width,
    height,
    background,
    palette,
    verse=None,
    verse_source=None,
    animated=None,
    transliteration=None,
):
    frame = background.copy()
    draw = ImageDraw.Draw(frame, "RGBA")

    # Counter timing
    count = min(
        target,
        int(elapsed / count_interval) + 1,
    )

    count = max(0, count)

    completed = count >= target
    progress = min(1.0, count / target)

    # Header
    centered(
        draw,
        "TASBEEH",
        int(height * 0.075),
        font(34, True),
        palette.accent,
        width,
    )

    centered(
        draw,
        "A MOMENT OF REMEMBRANCE",
        int(height * 0.115),
        font(17),
        palette.muted,
        width,
    )

    # Beads
    cx = width // 2
    cy = int(height * 0.42)

    if animated == "rain-flower":
        draw_rain_flower(frame, draw, elapsed, count, target, count_interval,
                         palette, width, height, 0)
        draw = ImageDraw.Draw(frame, "RGBA")
        draw_ring_counter(frame, draw, count, target, palette, width, height)
        bead_count = 0

    radius = int(width * 0.31)
    if animated != "rain-flower":
        bead_count = 33
    else:
        bead_count = 0

    for i in range(bead_count):
        angle = (2 * math.pi * i / bead_count) - math.pi / 2

        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)

        active_index = int(progress * bead_count)

        is_active = i < active_index

        bead_radius = 11

        color = palette.active if is_active else palette.idle

        draw.ellipse(
            (
                x - bead_radius,
                y - bead_radius,
                x + bead_radius,
                y + bead_radius,
            ),
            fill=color,
            outline=(*palette.pale, 170),
            width=2,
        )

    if animated != "rain-flower":
        # Center counter circle
        circle_radius = int(width * 0.23)

        draw.ellipse(
            (
                cx - circle_radius,
                cy - circle_radius,
                cx + circle_radius,
                cy + circle_radius,
            ),
            fill=palette.panel,
            outline=palette.accent,
            width=3,
        )

        # Count
        centered(
            draw,
            str(count),
            cy - 65,
            font(100, True),
            palette.pale,
            width,
        )

        centered(
            draw,
            f"OF {target}",
            cy + 55,
            font(20, True),
            palette.accent,
            width,
        )

    # Dhikr
    centered(
        draw,
        arabic,
        int(height * 0.68),
        arabic_font(49),
        palette.pale,
        width,
    )

    if transliteration:
        centered(
            draw,
            transliteration,
            int(height * 0.72),
            font(29, True),
            palette.accent,
            width,
        )

    centered(
        draw,
        translation,
        int(height * (0.76 if transliteration else 0.735)),
        font(25),
        palette.muted,
        width,
    )

    # Progress bar
    bar_width = int(width * 0.72)
    bar_height = 9

    bar_x = (width - bar_width) // 2
    bar_y = int(height * 0.795)

    draw.rounded_rectangle(
        (
            bar_x,
            bar_y,
            bar_x + bar_width,
            bar_y + bar_height,
        ),
        radius=5,
        fill=(*palette.pale, 70),
    )

    draw.rounded_rectangle(
        (
            bar_x,
            bar_y,
            bar_x + int(bar_width * progress),
            bar_y + bar_height,
        ),
        radius=5,
        fill=palette.accent,
    )

    centered(
        draw,
        f"{int(progress * 100)}% COMPLETED",
        bar_y + 28,
        font(17),
        palette.muted,
        width,
    )

    # Optional verse at the bottom (text and source come from the user)
    if verse:
        verse_size = 44
        max_w = int(width * 0.86)
        while verse_size > 24:
            vf = arabic_font(verse_size)
            box = draw.textbbox((0, 0), verse, font=vf, direction="rtl")
            if box[2] - box[0] <= max_w:
                break
            verse_size -= 2
        vf = arabic_font(verse_size)
        draw.line(
            (int(width * 0.38), int(height * 0.826), int(width * 0.62), int(height * 0.826)),
            fill=(*palette.accent, 150),
            width=2,
        )
        centered(draw, verse, int(height * 0.834), vf, palette.accent, width, direction="rtl")
        if verse_source:
            centered(
                draw,
                verse_source,
                int(height * 0.874),
                arabic_font(30),
                palette.muted,
                width,
                direction="rtl",
            )

    # Completion message
    if completed:
        centered(
            draw,
            "ALHAMDULILLAH",
            int(height * (0.94 if verse else 0.91)),
            font(27, True),
            palette.accent,
            width,
        )

    return frame


# ---------------------------------------------------------
# AUDIO: one bead click on every count
#
# The supplied MP3 is a quiet rumble with a bead click about every
# 0.85 s. Playing it as a loop drifts away from the counter, so instead
# the clicks are cut out of the file (high-pass filtering removes the
# rumble) and one is placed on the exact frame where each count changes.
# Standard library only; FFmpeg does the decoding.
# ---------------------------------------------------------

AUDIO_SR = 48000
CLICK_PRE = 0.015       # seconds kept before the click peak
CLICK_LEN = 0.22        # seconds per click slice (clicks decay in ~0.1 s)
CLICK_FADE = 0.07       # fade-out at the end of a slice
ONE_SHOT_MAX = 1.5      # files this short are used whole as the click


def decode_audio(ffmpeg, path, highpass=None):
    cmd = [ffmpeg, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(AUDIO_SR)]
    if highpass:
        # volume leaves headroom for filter overshoot
        cmd += ["-af", f"highpass=f={highpass},volume=0.5"]
    cmd += ["-f", "f32le", "-"]

    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    samples = array.array("f")
    samples.frombytes(raw[: len(raw) // 4 * 4])
    if sys.byteorder == "big":
        samples.byteswap()
    return samples


def find_clicks(samples):
    """Return (peak_sample_index, strength) for strong, well-separated clicks."""
    win = int(AUDIO_SR * 0.002)
    count = len(samples) // win
    if count < 3:
        return []

    env = [max(map(abs, samples[i * win:(i + 1) * win])) for i in range(count)]
    top = max(env)
    if top <= 0:
        return []

    threshold = 0.25 * top
    min_gap = int(0.3 / 0.002)
    peaks = []

    for i in range(1, count - 1):
        if env[i] > threshold and env[i] >= env[i - 1] and env[i] > env[i + 1]:
            if peaks and i - peaks[-1] < min_gap:
                if env[i] > env[peaks[-1]]:
                    peaks[-1] = i
            else:
                peaks.append(i)

    clicks = []
    for p in peaks:
        lo, hi = p * win, (p + 1) * win
        exact = max(range(lo, hi), key=lambda j: abs(samples[j]))
        clicks.append((exact, env[p]))

    return clicks


def make_click_slice(samples, peak_index, length, fade_out):
    """Cut a click, normalise it and fade its edges. Returns (chunk, peak_offset)."""
    pre = int(CLICK_PRE * AUDIO_SR)
    start = max(0, peak_index - pre)
    chunk = list(samples[start:start + length])
    if not chunk:
        return None

    peak = max(abs(v) for v in chunk) or 1.0
    gain = 0.9 / peak
    fade_in = max(1, int(0.002 * AUDIO_SR))
    fade_out = max(1, min(fade_out, len(chunk)))
    last = len(chunk) - 1

    for i in range(len(chunk)):
        g = gain
        if i < fade_in:
            g *= i / fade_in
        remaining = last - i
        if remaining < fade_out:
            g *= remaining / fade_out
        chunk[i] *= g

    return chunk, peak_index - start


def synth_tick():
    """Soft wooden bead tick, used only when the sound file has no clicks."""
    n = int(0.14 * AUDIO_SR)
    chunk = []
    for i in range(n):
        t = i / AUDIO_SR
        chunk.append(
            math.sin(2 * math.pi * 1900 * t) * math.exp(-t * 55)
            + 0.5 * math.sin(2 * math.pi * 3300 * t) * math.exp(-t * 80)
        )
    peak = max(abs(v) for v in chunk)
    chunk = [0.9 * v / peak for v in chunk]
    attack = int(0.001 * AUDIO_SR)
    for i in range(attack):
        chunk[i] *= i / attack
    return [(chunk, 0)]


def load_click_pool(ffmpeg, sound_path):
    """Return a list of (samples, peak_offset) click sounds taken from the file."""
    full = decode_audio(ffmpeg, sound_path)
    seconds = len(full) / AUDIO_SR

    # A short file is a ready-made sound effect: use it whole.
    if 0 < seconds <= ONE_SHOT_MAX:
        peak_index = max(range(len(full)), key=lambda j: abs(full[j]))
        piece = make_click_slice(full, peak_index, len(full), int(0.1 * AUDIO_SR))
        if piece:
            print(f"Audio: using {sound_path.name} as a one-shot click")
            return [piece]

    # A long file: high-pass away the rumble and cut out each click.
    filtered = decode_audio(ffmpeg, sound_path, highpass=700)
    clicks = find_clicks(filtered)

    if clicks:
        strengths = sorted(c[1] for c in clicks)
        median = strengths[len(strengths) // 2]
        length = int(CLICK_LEN * AUDIO_SR)
        usable = []

        for i, (index, strength) in enumerate(clicks):
            next_gap = (clicks[i + 1][0] - index) if i + 1 < len(clicks) else length
            if strength >= 0.5 * median and next_gap >= length:
                piece = make_click_slice(filtered, index, length, int(CLICK_FADE * AUDIO_SR))
                if piece:
                    usable.append(piece)
            if len(usable) >= 24:
                break

        if len(usable) >= 3:
            print(f"Audio: cut {len(usable)} bead clicks from {sound_path.name}")
            return usable

    print(f"Audio: no clear clicks in {sound_path.name}; using a built-in bead tick")
    return synth_tick()


def count_time(k, interval, fps):
    """Time the picture first shows count k, matching make_frame exactly."""
    f = max(0, math.ceil((k - 1) * interval * fps - 1e-9))
    while int((f / fps) / interval) + 1 < k:
        f += 1
    while f > 0 and int(((f - 1) / fps) / interval) + 1 >= k:
        f -= 1
    return f / fps


def build_click_track(ffmpeg, sound_path, target, interval, fps, volume, wav_path):
    pool = load_click_pool(ffmpeg, sound_path)
    total = int(round(target * interval * AUDIO_SR))
    buf = array.array("h", bytes(2 * total))
    scale = volume * 32767

    for k in range(1, target + 1):
        chunk, offset = pool[(k - 1) % len(pool)]
        pos = int(round(count_time(k, interval, fps) * AUDIO_SR)) - offset

        for i, v in enumerate(chunk):
            j = pos + i
            if 0 <= j < total:
                s = buf[j] + int(v * scale)
                buf[j] = -32768 if s < -32768 else 32767 if s > 32767 else s

    if sys.byteorder == "big":
        buf.byteswap()

    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(AUDIO_SR)
        wf.writeframes(buf.tobytes())

    print(f"Audio: {target} clicks synchronised to the counter")


# ---------------------------------------------------------
# VIDEO RENDERING
# ---------------------------------------------------------

def render_video(args, background, palette, output):
    ffmpeg = shutil.which("ffmpeg")

    if not ffmpeg:
        raise RuntimeError(
            "FFmpeg was not found. Install FFmpeg before rendering."
        )

    total_duration = args.target * args.count_interval
    total_frames = math.ceil(total_duration * args.fps)

    print(f"Target: {args.target}")
    print(f"Interval: {args.count_interval} seconds")
    print(f"Duration: {total_duration:.2f} seconds")
    print(f"Frames: {total_frames}")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        frame_dir = temp_dir / "frames"
        frame_dir.mkdir()

        for frame_number in range(total_frames):
            elapsed = frame_number / args.fps

            frame = make_frame(
                elapsed=elapsed,
                target=args.target,
                count_interval=args.count_interval,
                arabic=args.arabic,
                translation=args.translation,
                width=args.width,
                height=args.height,
                background=background,
                palette=palette,
                verse=args.verse,
                verse_source=args.verse_source,
                animated=args.scene_name,
                transliteration=args.transliteration,
            )

            frame.save(
                frame_dir / f"frame_{frame_number:06d}.png"
            )

            if frame_number % args.fps == 0:
                print(
                    f"\rRendering: {frame_number / total_frames * 100:.1f}%",
                    end="",
                    flush=True,
                )

        print("\nEncoding MP4...")

        # Inputs first, then output options. Putting encoder options before the
        # audio input makes ffmpeg treat them as input options and fail.
        command = [
            ffmpeg,
            "-y",
            "-framerate", str(args.fps),
            "-i", str(frame_dir / "frame_%06d.png"),
        ]

        has_audio = False
        audio_filter = []   # volume is already applied when clicks are synced

        if not args.no_audio:
            if args.sound:
                sound_path = Path(args.sound).expanduser()

                if not sound_path.is_absolute():
                    candidates = [
                        Path.cwd() / sound_path,
                        Path(__file__).resolve().parent / sound_path,
                        Path(__file__).resolve().parent.parent / sound_path,
                    ]

                    sound_path = next(
                        (p for p in candidates if p.is_file()),
                        candidates[0],
                    )

                if not sound_path.is_file():
                    raise FileNotFoundError(
                        f"Sound file not found: {args.sound}"
                    )

                if args.sound_mode == "sync":
                    # One click per count, placed on the frame where it changes.
                    wav_path = temp_dir / "clicks.wav"
                    build_click_track(
                        ffmpeg,
                        sound_path,
                        args.target,
                        args.count_interval,
                        args.fps,
                        args.volume,
                        wav_path,
                    )
                    command += ["-i", str(wav_path)]
                else:
                    # Old behaviour: the whole file plays as a looping soundtrack.
                    command += [
                        "-stream_loop", "-1",
                        "-i", str(sound_path),
                    ]
                    audio_filter = ["-af", f"volume={args.volume}"]
                has_audio = True

            else:
                print("No sound file supplied; creating silent video.")

        command += [
            "-map", "0:v:0",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", str(args.crf),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
        ]

        if has_audio:
            command += [
                "-map", "1:a:0",
                *audio_filter,
                "-ac", "2",
                "-c:a", "aac",
                "-b:a", "192k",
            ]

        command += [
            "-t", f"{total_duration:.3f}",
            str(output),
        ]

        subprocess.run(command, check=True)

    print(f"\nVideo created: {output}")


# ---------------------------------------------------------
# COMMAND LINE
# ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Create an animated Arabic-English Tasbeeh Reel."
    )

    parser.add_argument(
        "--output",
        default="tasbeeh-reel.mp4",
    )

    parser.add_argument(
        "--target",
        type=int,
        default=33,
        help="Number of Tasbeeh repetitions.",
    )

    parser.add_argument(
        "--count-interval",
        type=float,
        default=1.0,
        help="Seconds between repetitions. Default: 1.0.",
    )

    parser.add_argument(
        "--fps",
        type=int,
        default=30,
    )

    parser.add_argument(
        "--width",
        type=int,
        default=1080,
    )

    parser.add_argument(
        "--height",
        type=int,
        default=1920,
    )

    parser.add_argument(
        "--dhikr",
        default=None,
        help="Pick a dhikr from the library by number 1-7 or name (e.g. 5, istighfar, hawqala). "
             "Sets the Arabic, transliteration and meaning. --arabic/--translation override it.",
    )

    parser.add_argument(
        "--arabic",
        default=None,
    )

    parser.add_argument(
        "--translation",
        default=None,
    )

    parser.add_argument(
        "--transliteration",
        default=None,
        help="Optional transliteration line between the Arabic and the meaning.",
    )

    parser.add_argument(
        "--verse",
        default=None,
        help="Optional Arabic verse or text shown at the bottom of every frame. Use exact text supplied by the user.",
    )

    parser.add_argument(
        "--verse-source",
        default=None,
        help="Optional source line under the verse, e.g. the surah and verse number.",
    )

    parser.add_argument(
        "--background",
        default="random",
        help=(
            "'random' (default) picks a royal palette and an illustrated scene "
            "each run. Keywords steer the choice, e.g. 'purple mosque', "
            "'blue lantern', 'burgundy quran'."
        ),
    )

    parser.add_argument(
        "--palette",
        default="random",
        choices=["random", *PALETTES],
        help="Royal colour palette. Default: random each run.",
    )

    parser.add_argument(
        "--scene",
        default="random",
        choices=["random", *SCENES, *ANIMATED_SCENES],
        help="Illustrated background scene. Default: random each run.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Repeat a previous random look. Printed on every run.",
    )

    parser.add_argument(
        "--preview",
        default=None,
        metavar="PNG",
        help="Save one still frame to this PNG and exit without rendering video.",
    )

    parser.add_argument(
        "--background-image",
        default=None,
        help="Optional background image (takes priority over the scenes).",
    )

    parser.add_argument(
        "--sound",
        default="sounds/reference-click.mp3",
        help="Audio file. Default: the click sound taken from the reference reels. In sync mode its clicks are placed on every count.",
    )

    parser.add_argument(
        "--sound-mode",
        default="sync",
        choices=["sync", "loop"],
        help=(
            "'sync' (default) plays one click exactly when each count changes. "
            "'loop' plays the whole MP3 continuously, not tied to the counter."
        ),
    )

    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Render without audio.",
    )

    parser.add_argument(
        "--volume",
        type=float,
        default=0.65,
        help="Audio volume from 0.0 to 1.0.",
    )

    parser.add_argument(
        "--crf",
        type=int,
        default=20,
        help="Video quality. Lower values mean higher quality.",
    )

    args = parser.parse_args()

    if args.dhikr is not None:
        found = find_dhikr(args.dhikr)
        if not found:
            parser.error("--dhikr: use a number 1-7 or a name such as subhanallah, alhamdulillah, akbar, tahlil, istighfar, bihamdihi, hawqala")
        d_ar, d_tr, d_mean = found
        args.arabic = args.arabic or d_ar
        args.translation = args.translation or d_mean
        if args.transliteration is None:
            args.transliteration = d_tr
    elif args.arabic is None and args.translation is None:
        args.arabic, args.transliteration, args.translation = ADHKAR[1][0], ADHKAR[1][1], ADHKAR[1][2]
    args.arabic = args.arabic or ADHKAR[1][0]
    args.translation = args.translation or ""

    if args.target < 1:
        parser.error("--target must be at least 1")

    if args.count_interval <= 0:
        parser.error("--count-interval must be greater than zero")

    if args.fps < 1:
        parser.error("--fps must be at least 1")

    if args.width < 1 or args.height < 1:
        parser.error("--width and --height must be positive")

    if not 0 <= args.volume <= 1:
        parser.error("--volume must be between 0 and 1")

    if not 0 <= args.crf <= 51:
        parser.error("--crf must be between 0 and 51")

    output = Path(args.output).expanduser()

    if not output.suffix:
        output = output.with_suffix(".mp4")

    output.parent.mkdir(parents=True, exist_ok=True)

    total_duration = args.target * args.count_interval

    print("\nATHEEL TASBEEH REEL RENDERER")
    print("---------------------------")
    print(f"Repetitions: {args.target}")
    print(f"Time per repetition: {args.count_interval}s")
    print(f"Total duration: {total_duration:.2f}s")

    # A fresh random look on every run unless --seed is given.
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(1, 10**9)
    rng = random.Random(seed)

    palette, scene = choose_style(args.background, args.palette, args.scene, rng)
    args.scene_name = scene

    if args.background_image:
        background = load_background(
            args.width,
            args.height,
            args.background_image,
        )
        print(f"Background: image {args.background_image} (palette for text: {palette.name})")
    else:
        background = make_background(
            args.width,
            args.height,
            palette,
            scene,
            rng,
        )
        print(f"Background: palette={palette.name}, scene={scene}, seed={seed}")

    if args.preview:
        preview = Path(args.preview).expanduser()
        preview.parent.mkdir(parents=True, exist_ok=True)
        make_frame(
            elapsed=total_duration * 0.4,
            target=args.target,
            count_interval=args.count_interval,
            arabic=args.arabic,
            translation=args.translation,
            width=args.width,
            height=args.height,
            background=background,
            palette=palette,
            verse=args.verse,
            verse_source=args.verse_source,
            animated=scene,
            transliteration=args.transliteration,
        ).save(preview)
        print(f"Preview saved: {preview}")
        return

    try:
        render_video(args, background, palette, output)
    except (subprocess.CalledProcessError, OSError, RuntimeError) as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
