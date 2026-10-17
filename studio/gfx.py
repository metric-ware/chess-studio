import math, re
from functools import lru_cache
from pathlib import Path
import cairo, cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
W, H = 1080, 1350


# ---------- color / math / easing ----------

def col(c, a=None):
    """'#rrggbb', (r,g,b) or (r,g,b,a) in 0-255 -> (r,g,b,a) floats for cairo."""
    if isinstance(c, str):
        c = c.lstrip("#")
        c = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + ((int(c[6:8], 16),) if len(c) == 8 else ())
    r, g, b = (v / 255 for v in c[:3])
    return r, g, b, (a if a is not None else (c[3] / 255 if len(c) > 3 else 1.0))


def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def lerp(a, b, x):
    if isinstance(a, (tuple, list)):
        return tuple(lerp(u, v, x) for u, v in zip(a, b))
    return a + (b - a) * x


def prog(t, t0, dur):
    return clamp((t - t0) / dur) if dur > 0 else float(t >= t0)


def ease(p):
    """Quintic smoothstep: zero velocity and acceleration at both ends."""
    p = clamp(p)
    return p * p * p * (p * (p * 6 - 15) + 10)


def smooth(fn, t0, t1, sigma, rate=120):
    """fn(t) -> tuple of floats, Gaussian-smoothed in time and tabulated over [t0, t1]; returns a function of t that
    interpolates the table. The kernel is centred, so a camera following it starts moving before the action does and
    settles after it, and a target that jumps (a new move starting) turns into a smooth glide."""
    pad = int(3 * sigma * rate)
    ts = t0 + (np.arange(int((t1 - t0) * rate) + 1 + 2 * pad) - pad) / rate
    vals = np.array([fn(t) for t in ts], float)
    k = np.exp(-0.5 * (np.arange(-pad, pad + 1) / (sigma * rate)) ** 2)
    k /= k.sum()
    sm = np.stack([np.convolve(np.pad(v, pad, mode="edge"), k, mode="valid") for v in vals.T], 1)
    return lambda t: tuple(float(np.interp(t, ts, s)) for s in sm.T)


# ---------- frame ----------

class Frame:
    """Cairo surface backed by a numpy BGRA (premultiplied) array."""

    def __init__(self, w=W, h=H, bg=None):
        self.w, self.h = w, h
        self.arr = np.zeros((h, w, 4), np.uint8)
        self.surf = cairo.ImageSurface.create_for_data(memoryview(self.arr), cairo.FORMAT_ARGB32, w, h, w * 4)
        self.ctx = cairo.Context(self.surf)
        if bg is not None:
            self.ctx.set_source_rgba(*col(bg))
            self.ctx.paint()

    def np(self):
        self.surf.flush()
        return self.arr

    def dirty(self):
        self.surf.mark_dirty()


def to_surface(rgba):
    """RGBA uint8 array -> cairo ImageSurface (premultiplied, owns its memory)."""
    h, w = rgba.shape[:2]
    a = rgba[..., 3:4].astype(np.uint16)
    pm = (rgba[..., :3].astype(np.uint16) * a // 255).astype(np.uint8)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    buf = np.ndarray((h, surf.get_stride() // 4, 4), np.uint8, surf.get_data())
    buf[:, :w, 0], buf[:, :w, 1], buf[:, :w, 2], buf[:, :w, 3] = pm[..., 2], pm[..., 1], pm[..., 0], rgba[..., 3]
    surf.mark_dirty()
    return surf


@lru_cache(768)
def image(path, size=None, blur=0.0):
    """Load an image file (any mode) as a cairo surface, optionally resized so its longer side is `size` (Lanczos) and
    Gaussian-blurred by `blur` pixels."""
    im = Image.open(ASSETS / path if not Path(path).is_absolute() else path).convert("RGBA")
    if size:
        s = size / max(im.size)
        im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    if blur:
        im = im.convert("RGBa").filter(ImageFilter.GaussianBlur(blur)).convert("RGBA")
    return to_surface(np.asarray(im))


def blit(ctx, surf, x, y, scale=1.0, alpha=1.0):
    """Paint surf centred at (x, y)."""
    if alpha <= 0 or scale < 1e-4:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(scale, scale)
    ctx.set_source_surface(surf, -surf.get_width() / 2, -surf.get_height() / 2)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


# ---------- text ----------

FONTS = {"display": ("fonts/InterTight.ttf", [800]), "label": ("fonts/InterTight.ttf", [550])}


@lru_cache(None)
def font(name, size):
    path, axes = FONTS[name]
    f = ImageFont.truetype(str(ASSETS / path), size)
    if axes:
        f.set_variation_by_axes(axes)
    return f


def _width(fnt, s, track):
    return fnt.getlength(s) + track * max(0, len(s) - 1)


def _offset(fnt, s, i, track):
    return fnt.getlength(s[:i + 1]) - fnt.getlength(s[i]) + track * i


@lru_cache(512)
def text_layout(text, size=84, face="display", max_width=940, spacing=1.12, upper=False, tracking=0.0, pad=0):
    """Centred, word-wrapped layout: ([(x, y, run, accent, word_index)], width, height, word count).
    [bracketed words] are accent runs; a word is a list of runs so "[mate]?" keeps the "?" glued to the accent.
    tracking adds letter spacing as a fraction of the size."""
    if upper:
        text = text.upper()
    fnt, track = font(face, size), tracking * size
    words = [[]]
    for part, acc in [(m[0] or m[1], bool(m[0])) for m in re.findall(r"\[([^\]]*)\]|([^\[\]]+)", text)]:
        for i, line in enumerate(part.split("\n")):
            if i:
                words += ["\n", []]
            for j, chunk in enumerate(line.split(" ")):
                if j:
                    words.append([])
                if chunk:
                    words[-1].append((chunk, acc))
    words = [w for w in words if w]
    space = fnt.getlength(" ") + 2 * track
    lines, cur, cw = [], [], 0.0
    for w in words:
        if w == "\n":
            lines.append(cur)
            cur, cw = [], 0.0
            continue
        wl = _width(fnt, "".join(r for r, _ in w), track)
        if cur and cw + space + wl > max_width:
            lines.append(cur)
            cur, cw = [], 0.0
        cur.append((w, wl))
        cw += (space if len(cur) > 1 else 0) + wl
    lines.append(cur)
    lh = round(size * spacing)
    widths = [sum(x[1] for x in ln) + space * max(0, len(ln) - 1) for ln in lines]
    runs, n = [], 0
    for li, ln in enumerate(lines):
        x, y = pad + (max(widths) - widths[li]) / 2, pad + li * lh
        for w, wl in ln:
            whole, offset = "".join(r for r, _ in w), 0
            for run, acc in w:
                runs.append((x + _offset(fnt, whole, offset, track), y, run, acc, n))
                offset += len(run)
            x += wl + space
            n += 1
    top = min((y + fnt.getbbox(run, anchor="ls")[1] for _, y, run, _, _ in runs), default=0)
    bottom = max((y + fnt.getbbox(run, anchor="ls")[3] for _, y, run, _, _ in runs), default=size)
    runs = [(x, y - top + pad, run, acc, wi) for x, y, run, acc, wi in runs]
    return runs, math.ceil(max(widths + [1]) + 2 * pad), math.ceil(bottom - top + 2 * pad), n


@lru_cache(512)
def text_sprite(text, size=84, face="display", fill="#ffffff", accent="#ed3e40", max_width=940, spacing=1.12, shadow=0,
                upper=False, tracking=0.0, words=None):
    """Text rendered to a cairo surface; [bracketed words] use the accent color, shadow=N adds a soft dark drop shadow.
    words=(a, b) draws only words a..b-1 on the full layout's canvas, so partial sprites line up with the whole."""
    pad = shadow * 2 + 6
    runs, iw, ih, _ = text_layout(text, size, face, max_width, spacing, upper, tracking, pad)
    fnt, track = font(face, size), tracking * size
    im = Image.new("RGBA", (iw, ih))
    d = ImageDraw.Draw(im)
    for x, y, run, acc, wi in runs:
        if words is None or words[0] <= wi < words[1]:
            if track:
                for j, ch in enumerate(run):
                    d.text((x + _offset(fnt, run, j, track), y), ch, font=fnt, fill=accent if acc else fill, anchor="ls")
            else:
                d.text((x, y), run, font=fnt, fill=accent if acc else fill, anchor="ls")
    if shadow:
        sh = Image.new("RGBA", (iw, ih))
        sh.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(shadow)).point(lambda v: int(v * 0.85)))
        out = Image.new("RGBA", (iw, ih))
        out.alpha_composite(sh, (0, max(1, shadow // 2)))
        out.alpha_composite(im)
        im = out
    return to_surface(np.asarray(im))


def text(f, s, x, y, size=84, alpha=1.0, scale=1.0, **style):
    blit(f.ctx, text_sprite(s, size, **style), x, y, scale, alpha)


def text_anim(f, t, s, t0, t1, x, y, size=84, anim="reveal", out="fade", step=0.035, **style):
    """Caption visible in [t0, t1). anim: stagger (words rise and fade in one after another) | reveal (the whole line
    rises in) | pop (a quick scale-in for single-word punches) | none. out: fade | cut."""
    if not t0 <= t < t1:
        return
    lt, rem = t - t0, t1 - t
    fade = min(0.1, (t1 - t0) * 0.15)
    a = 1.0 if out == "cut" else ease(rem / fade)
    if anim == "stagger":
        n = text_layout(s, size, style.get("face", "display"), style.get("max_width", 940), style.get("spacing", 1.12),
                        style.get("upper", False), style.get("tracking", 0.0))[3]
        for j in range(n):
            p = ease(prog(lt, j * step, 0.18))
            if p > 0:
                blit(f.ctx, text_sprite(s, size, words=(j, j + 1), **style), x, y + (1 - p) * 12, 1.0, a * p)
        return
    sc, dy = 1.0, 0.0
    if anim == "reveal":
        p = ease(prog(lt, 0, min(0.18, (t1 - t0) * 0.3)))
        dy, a = (1 - p) * 12, a * p
    elif anim == "pop":
        p = ease(prog(lt, 0, min(0.16, (t1 - t0) * 0.3)))
        sc, a = 0.96 + 0.04 * p, a * p
    text(f, s, x, y + dy, size, a, sc, **style)


# ---------- post effects (operate on the whole frame) ----------

@lru_cache(8)
def _vignette_mask(w, h, amount, roundness):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = ((x - w / 2) / (w / 2)) ** 2, ((y - h / 2) / (h / 2)) ** 2
    d = np.sqrt(dx * roundness + dy if w <= h else dx + dy * roundness)  # roundness acts on the short axis
    m = np.clip(1 - amount * np.clip(d - 0.35, 0, None) ** 1.6, 0, 1)
    return np.repeat((m * 255).astype(np.uint8)[..., None], 4, 2)


def vignette(f, amount=0.9, roundness=1.6):
    a = f.np()
    cv2.multiply(a, _vignette_mask(f.w, f.h, round(amount, 2), roundness), dst=a, scale=1 / 255)
    f.dirty()
