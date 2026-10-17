import math, re
import cairo, chess, cv2
import numpy as np
from .gfx import clamp, col, ease, image, lerp, prog

SPRITE_FOOT = 0.097  # transparent margin below every neo piece, as a fraction of the sprite height
Z = np.array([0.0, 0.0, 1.0])


def piece_path(symbol):
    return f"pieces/neo/{'w' if symbol.isupper() else 'b'}{symbol.lower()}.png"


def sq_xy(sq):
    """Board coordinates of a square's centre: one unit per square, a1's corner at (0, 0), z up."""
    return chess.square_file(sq) + 0.5, chess.square_rank(sq) + 0.5


class Cam:
    """Look at (x, y), framing `span` vertical board units through a fixed 20-degree lens.
    Yaw/pitch are degrees (yaw 0 = White's side, pitch 90 = overhead); roll is radians; ox/oy are pixel offsets."""
    FIELDS = ("x", "y", "span", "yaw", "pitch", "roll", "ox", "oy")

    def __init__(self, x=4.0, y=4.0, span=12.0, yaw=0.0, pitch=70.0, roll=0.0, ox=0.0, oy=0.0):
        self.x, self.y, self.span, self.yaw, self.pitch, self.roll, self.ox, self.oy = x, y, span, yaw, pitch, roll, ox, oy

    def vals(self):
        return [getattr(self, k) for k in self.FIELDS]

    def lerp(self, other, k):
        vals = dict(zip(self.FIELDS, [lerp(a, b, k) for a, b in zip(self.vals(), other.vals())]))
        vals["yaw"] = self.yaw + ((other.yaw - self.yaw + 180) % 360 - 180) * k
        vals["roll"] = self.roll + ((other.roll - self.roll + math.pi) % math.tau - math.pi) * k
        return Cam(**vals)


def keyframes(t, keys):
    """[(start, duration, Cam or fn(t))], blending from the starting pose and velocity of each transition."""
    first = keys[0][2]
    cam = first(t) if callable(first) else first
    for i, (start, dur, c) in enumerate(keys[1:], 1):
        if t < start:
            break
        c = c(t) if callable(c) else c
        p = ease(prog(t, start, dur))
        if p >= 1:
            cam = c
        else:
            source = keyframes(start, keys[:i])
            ahead = keyframes(start + 1 / 120, keys[:i])
            cam = source.lerp(ahead, (t - start) * 120).lerp(c, p)
    return cam


class View:
    """Perspective projection of a Cam into a w*h frame."""

    def __init__(self, cam, w, h):
        th, ps = math.radians(cam.pitch), math.radians(cam.yaw)
        self.cam, self.w, self.h = cam, w, h
        self.fwd = np.array([math.sin(ps) * math.cos(th), math.cos(ps) * math.cos(th), -math.sin(th)])
        self.right = np.array([math.cos(ps), -math.sin(ps), 0.0])
        self.up = np.cross(self.right, self.fwd)
        lens = 2 * math.tan(math.radians(20) / 2)
        self.pos = np.array([cam.x, cam.y, 0.0]) - (cam.span / lens) * self.fwd
        self.f = h / lens
        self.cx, self.cy = w / 2 + cam.ox, h / 2 + cam.oy
        self.cr, self.sr = math.cos(cam.roll), math.sin(cam.roll)
        self._rays = {}

    def project(self, pts):
        """(..., 3) board points -> (..., 2) screen points and (...,) depths."""
        d = np.asarray(pts, float) - self.pos
        zc = np.maximum(d @ self.fwd, 1e-3)
        u, v = self.f * (d @ self.right) / zc, -self.f * (d @ self.up) / zc
        return np.stack([self.cx + u * self.cr - v * self.sr, self.cy + u * self.sr + v * self.cr], -1), zc

    def p(self, x, y, z=0.0):
        s, _ = self.project([x, y, z])
        return float(s[0]), float(s[1])

    def depth(self, x, y, z=0.0):
        return float((np.array([x, y, z]) - self.pos) @ self.fwd)

    def plane(self, k, z=0.0):
        """(x, y, depth) where each ray of a 1/k-resolution grid meets height z; NaN above the horizon."""
        if k not in self._rays:
            gy, gx = np.mgrid[0:self.h // k, 0:self.w // k].astype(np.float32)
            dx, dy = gx * k + k / 2 - self.cx, gy * k + k / 2 - self.cy
            u, v = dx * self.cr + dy * self.sr, -dx * self.sr + dy * self.cr
            d = self.fwd[None, None] + self.right[None, None] * (u / self.f)[..., None] - self.up[None, None] * (v / self.f)[..., None]
            self._rays[k] = d
        d = self._rays[k]
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.where(d[..., 2] < -1e-4, (z - self.pos[2]) / d[..., 2], np.nan)
        return self.pos[0] + t * d[..., 0], self.pos[1] + t * d[..., 1], t

    def poly(self, ctx, pts, z=0.0):
        s, _ = self.project([(x, y, z) for x, y in pts])
        ctx.move_to(*s[0])
        for q in s[1:]:
            ctx.line_to(*q)
        ctx.close_path()

    def square(self, ctx, sq, color, alpha=1.0):
        x, y = chess.square_file(sq), chess.square_rank(sq)
        self.poly(ctx, [(x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)])
        ctx.set_source_rgba(*col(color, alpha))
        ctx.fill()

    def glow(self, ctx, sq, color):
        """chess.com's check marker: a radial gradient filling the square."""
        ctx.save()
        ctx.set_matrix(self.local(*sq_xy(sq)))
        g = cairo.RadialGradient(0, 0, 0, 0, 0, 0.72)
        g.add_color_stop_rgba(0, *col(color, 1.0))
        g.add_color_stop_rgba(0.45, *col(color, 0.85))
        g.add_color_stop_rgba(1, *col(color, 0))
        ctx.set_source(g)
        ctx.rectangle(-0.5, -0.5, 1, 1)
        ctx.fill()
        ctx.restore()

    def line(self, ctx, pts, color, width=0.12, alpha=1.0, progress=1.0):
        """A flat round-capped stroke lying on the board through board points, drawn up to `progress` of its length."""
        path = _trim(pts, progress)
        if path is None or alpha <= 0:
            return
        ctx.push_group()
        ctx.set_source_rgba(*col(color))
        for a, b in zip(path, path[1:]):
            n = _normal(a, b) * width / 2
            self.poly(ctx, [a + n, b + n, b - n, a - n])
            ctx.fill()
        for q in path:
            self.disc(ctx, q[0], q[1], width / 2)
            ctx.fill()
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(alpha)

    def arrow(self, ctx, pts, color, width=0.2, head=0.48, alpha=0.85, progress=1.0, short=0.0):
        """A chess.com-style arrow lying on the board: square-cornered shaft through board points (a straight line or a
        knight's L) and a triangular head ending `short` before the last point, grown to `progress` of its length."""
        pts = [np.array(q, float) for q in pts]
        if short:
            d = pts[-1] - pts[-2]
            pts[-1] = pts[-1] - d / np.linalg.norm(d) * short
        path = _trim(pts, progress)
        if path is None or alpha <= 0:
            return
        total = sum(float(np.linalg.norm(b - a)) for a, b in zip(path, path[1:]))
        tip = path[-1]
        shaft = _trim(path, 1 - min(head * 0.9, total * 0.9) / total)
        if shaft is None or len(shaft) < 2:
            shaft = [path[0], path[0] + (tip - path[0]) * 0.01]
        end = shaft[-1]
        left, right = [], []
        for j, q in enumerate(shaft):
            n0 = _normal(shaft[max(j - 1, 0)], shaft[max(j, 1)])
            n1 = _normal(shaft[min(j, len(shaft) - 2)], shaft[min(j + 1, len(shaft) - 1)])
            m = n0 + n1
            m = m / np.linalg.norm(m) * (width / 2) / max(0.3, float(m @ n1) / np.linalg.norm(m))
            left.append(q + m)
            right.append(q - m)
        n = _normal(end, tip)
        ctx.push_group()
        self.poly(ctx, left + [end + n * head / 2, tip, end - n * head / 2] + right[::-1])
        ctx.set_source_rgba(*col(color))
        ctx.fill()
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(alpha)

    def disc(self, ctx, x, y, r, n=24):
        self.poly(ctx, [(x + r * math.cos(a), y + r * math.sin(a)) for a in np.linspace(0, math.tau, n, endpoint=False)])

    def local(self, x, y, z=0.0):
        """cairo matrix approximating the projection of the board plane (lifted by z) around (x, y), fitted by central
        differences so it stays accurate across a whole square (sprites lying flat, shadows, check glows)."""
        o, (ax, ay), (bx, by), (cx, cy), (dx, dy) = (self.p(x, y, z), self.p(x + 0.5, y, z), self.p(x - 0.5, y, z),
                                                     self.p(x, y + 0.5, z), self.p(x, y - 0.5, z))
        return cairo.Matrix(ax - bx, ay - by, cx - dx, cy - dy, o[0], o[1])

    def flat_matrix(self, x, y, z, size, w, h, sx=1.0, sy=1.0, rot=0.0):
        """cairo matrix laying a w*h sprite flat on the board at height z, centred on (x, y) with its top toward +y,
        turned by rot (radians, counterclockwise seen from above). sx, sy scale it."""
        m = cairo.Matrix(size * sx / w, 0, 0, -size * sy / h, -size * sx / 2, size * sy / 2)
        m = m.multiply(cairo.Matrix(math.cos(rot), math.sin(rot), -math.sin(rot), math.cos(rot), 0, 0))
        return m.multiply(self.local(x, y, z))

    def stand_matrix(self, x, y, z, size, w, h, sx=1.0, sy=1.0, rot=0.0):
        """cairo matrix standing a w*h sprite upright on (x, y), lifted by z and facing the camera. sx, sy stretch it
        (negative sx mirrors it), rot leans it about its base (radians, positive = to screen right)."""
        base = np.array([x, y, z]) - Z * size * SPRITE_FOOT
        u = Z * math.cos(rot) + self.right * math.sin(rot)
        r = self.right * math.cos(rot) - Z * math.sin(rot)
        up, half = u * size * sy, r * size * sx / 2
        (tl, tr, bl), _ = self.project([base + up - half, base + up + half, base - half])
        return cairo.Matrix((tr[0] - tl[0]) / w, (tr[1] - tl[1]) / w, (bl[0] - tl[0]) / h, (bl[1] - tl[1]) / h, tl[0], tl[1])


def _normal(a, b):
    d = b - a
    return np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-9)


def _trim(pts, progress):
    """The polyline through pts cut at `progress` of its length (None if nothing is left)."""
    pts = [np.array(p, float) for p in pts]
    segs = [(a, b, float(np.linalg.norm(b - a))) for a, b in zip(pts, pts[1:])]
    total = sum(s[2] for s in segs) * clamp(progress)
    if total < 1e-3:
        return None
    path, run = [pts[0]], 0.0
    for a, b, l in segs:
        if run + l >= total:
            path.append(a + (b - a) * (total - run) / l)
            break
        path.append(b)
        run += l
    return path


class Look:
    """A board slab against a solid background; optional checker floor for standing-piece cutscenes. Fog thickens with
    depth beyond fog_start, so a subject in front of it keeps its full brightness while the floor fades out behind."""

    def __init__(self, light="#f0f0f0", dark="#999ca0", background="#000000", floor=None, floor2=None, tile=2.0, slab=0.12,
                 edge="#34363a", fog_density=0.0, fog_start=0.0, ambient=0.7, ambient_color="#ffffff",
                 board=True, stand=False):
        self.light, self.dark, self.floor, self.floor2, self.tile, self.slab, self.edge = light, dark, floor, floor2, tile, slab, edge
        self.background, self.fog_density, self.fog_start = background, fog_density, fog_start
        self.ambient, self.ambient_color = ambient, ambient_color
        self.board, self.stand = board, stand


def light_at(look, lights, x, y):
    """RGB light multiplier at board points (arrays). lights: [(x, y, radius, strength, color)] on the board plane."""
    out = np.ones(np.shape(x) + (3,), np.float32) * (np.array(col(look.ambient_color)[:3]) * look.ambient)
    for lx, ly, r, s, c in lights:
        out += np.exp(-((x - lx) ** 2 + (y - ly) ** 2) / (r * r))[..., None] * (np.array(col(c)[:3]) * s)
    return out


def _bgr(c):
    return np.array(col(c)[2::-1], np.float32)


def draw_board(f, view, look, lights, pieces, under=None, over=None, focus=None, dof=0.0, k=4):
    """Render the scene into frame f. pieces: dicts with sym, x, y and optional z (lift), alpha, size, sx, sy, rot,
    stand (overrides look.stand). under(ctx, view) draws lit decals on the board (highlights), over(ctx, view) unlit
    ones above it and below the pieces (arrows, trails). focus=(x, y) with dof > 0 blurs by distance from that
    point's depth."""
    slab = look.slab if look.board else 0.0
    fx, fy, depth = view.plane(k, -slab)
    if look.board:
        tx, ty, td = view.plane(k, 0.0)
        top = np.isfinite(td) & (tx >= 0) & (tx <= 8) & (ty >= 0) & (ty <= 8)
        fx, fy, depth = np.where(top, tx, fx), np.where(top, ty, fy), np.where(top, td, depth)
    hit = np.isfinite(depth) if look.floor else top if look.board else np.zeros_like(depth, dtype=bool)
    fx, fy, d0 = np.nan_to_num(fx), np.nan_to_num(fy), np.nan_to_num(depth)
    c = f.ctx
    c.set_source_rgba(*col(look.background))
    c.paint()
    if look.floor:
        odd = ((np.floor(fx / look.tile) + np.floor(fy / look.tile)) % 2)[..., None]
        ground = _bgr(look.floor) + (_bgr(look.floor2 or look.floor) - _bgr(look.floor)) * odd
        a = f.np()
        a[..., :3] = cv2.resize((np.where(hit[..., None], ground, _bgr(look.background)) * 255).astype(np.uint8),
                               (f.w, f.h), interpolation=cv2.INTER_LINEAR)
        f.dirty()
    lit = light_at(look, lights, fx, fy)
    if look.board:
        # the slab's visible sides, its top, then the squares (each square needs its own move_to: without it Cairo
        # joins consecutive squares into one subpath and fills triangular wedges between them)
        for (x0, y0), (x1, y1), facing in (((0, 0), (8, 0), view.pos[1] < 0), ((8, 0), (8, 8), view.pos[0] > 8),
                                           ((8, 8), (0, 8), view.pos[1] > 8), ((0, 8), (0, 0), view.pos[0] < 0)):
            if facing:
                (p0, p1, p2, p3), _ = view.project([(x0, y0, 0), (x1, y1, 0), (x1, y1, -slab), (x0, y0, -slab)])
                c.move_to(*p0)
                for q in (p1, p2, p3):
                    c.line_to(*q)
                c.close_path()
        c.set_source_rgba(*col(look.edge))
        c.fill()
        view.poly(c, [(0, 0), (8, 0), (8, 8), (0, 8)])
        c.set_source_rgba(*col(look.light))
        c.fill()
        grid, _ = view.project([(i, j, 0.0) for j in range(9) for i in range(9)])
        grid = grid.reshape(9, 9, 2)
        for j in range(8):
            for i in range(j % 2, 8, 2):
                c.move_to(*grid[j, i])
                for q in (grid[j, i + 1], grid[j + 1, i + 1], grid[j + 1, i]):
                    c.line_to(*q)
                c.close_path()
        c.set_source_rgba(*col(look.dark))
        c.fill()
    if under:
        under(c, view)
    # light and fog as one multiply and one add, at 1/k resolution scaled up: uint8 math (mul is stored x128) keeps
    # this pass a few milliseconds
    fog = (1 - np.exp(-np.maximum(d0 - look.fog_start, 0) * look.fog_density))[..., None]
    mul = np.where(hit[..., None], lit[..., ::-1] * (1 - fog), 1.0)
    add = np.where(hit[..., None], fog * _bgr(look.background) * 255, 0.0)
    gh, gw = mul.shape[:2]
    mul4 = np.concatenate([np.clip(mul * 128, 0, 255), np.full((gh, gw, 1), 128.0)], 2).astype(np.uint8)
    add4 = np.concatenate([np.clip(add, 0, 255), np.zeros((gh, gw, 1))], 2).astype(np.uint8)
    a = f.np()
    cv2.multiply(a, cv2.resize(mul4, (f.w, f.h), interpolation=cv2.INTER_LINEAR), dst=a, scale=1 / 128)
    cv2.add(a, cv2.resize(add4, (f.w, f.h), interpolation=cv2.INTER_LINEAR), dst=a)
    f.dirty()
    if over:
        over(c, view)
    fd = view.depth(*focus) if focus else None
    defocus = lambda d: 0.0
    if fd and dof > 0:
        # the surface blurs per pixel by its depth; pieces are drawn afterwards, each blurred by its own depth, so a
        # standing piece in focus stays sharp in front of a blurred background
        defocus = lambda d: clamp(abs(d - fd) / (fd * 0.55)) * dof
        blur = (np.clip(np.abs(np.nan_to_num(depth, nan=fd + 40) - fd) / (fd * 0.55), 0, 1) * dof).astype(np.float32)
        a = f.np()
        soft = cv2.resize(cv2.GaussianBlur(cv2.resize(a, (f.w // 3, f.h // 3), interpolation=cv2.INTER_AREA), (0, 0), 3.2),
                          (f.w, f.h), interpolation=cv2.INTER_LINEAR)
        m = cv2.resize(blur, (f.w, f.h), interpolation=cv2.INTER_LINEAR)
        a[:] = cv2.blendLinear(a, soft, 1 - m, m)
        f.dirty()
    pieces = [dict(p, stand=p.get("stand", look.stand)) for p in pieces if view.depth(p["x"], p["y"]) > 0.8]
    flat = sorted((p for p in pieces if not p["stand"]), key=lambda p: p.get("z", 0.0))  # stable: equal z keeps list order
    stand = sorted((p for p in pieces if p["stand"]), key=lambda p: -view.depth(p["x"], p["y"]))
    for p in flat + stand:
        mid = p.get("z", 0.0) + (0.4 * p.get("size", 1.0) if p["stand"] else 0.0)
        _shadow(c, view, p)
        _sprite(c, view, look, lights, p, 9.6 * defocus(view.depth(p["x"], p["y"], mid)))


def _geo(p):
    return dict(sx=p.get("sx", 1.0), sy=p.get("sy", 1.0), rot=p.get("rot", 0.0))


def _shadow(c, view, p):
    """A soft contact shadow under a standing piece; a lifted flat piece casts a blurred silhouette on the board."""
    z, al, size = p.get("z", 0.0), p.get("alpha", 1.0), p.get("size", 1.0)
    c.save()
    if p["stand"]:
        r = 0.5 * abs(p.get("sx", 1)) * size
        c.set_matrix(view.local(p["x"] + 0.05, p["y"] - 0.05))
        g = cairo.RadialGradient(0, 0, 0, 0, 0, r)
        g.add_color_stop_rgba(0, 0, 0, 0, 0.6 * al / (1 + 2.5 * z))
        g.add_color_stop_rgba(1, 0, 0, 0, 0)
        c.set_source(g)
        c.arc(0, 0, r, 0, math.tau)
        c.fill()
    elif z > 0.005:
        surf = image(piece_path(p["sym"]), 24)
        c.set_matrix(view.flat_matrix(p["x"] + 0.12 * z, p["y"] - 0.2 * z, 0.0, size * (1 + 0.3 * z), surf.get_width(),
                                      surf.get_height(), **_geo(p)))
        c.set_source_rgba(0, 0, 0, 0.45 * al / (1 + 1.5 * z))
        c.mask_surface(surf, 0, 0)
    c.restore()


def _sprite(c, view, look, lights, p, blur=0.0):
    """A piece sprite lit by the light at its base, fogged by its depth and blurred by `blur` screen pixels."""
    z, al, size = p.get("z", 0.0), p.get("alpha", 1.0), p.get("size", 1.0)
    place = view.stand_matrix if p["stand"] else view.flat_matrix
    m0 = place(p["x"], p["y"], z, size, 1, 1, **_geo(p))
    px = max(math.hypot(m0.xx, m0.yx), math.hypot(m0.xy, m0.yy))
    res = min(1024, max(16, int(math.ceil(px / 16) * 16)))
    surf = image(piece_path(p["sym"]), res, round(blur * res / px * 2) / 2 if blur > 0.6 else 0.0)
    w, h = surf.get_width(), surf.get_height()
    light = light_at(look, lights, np.array(p["x"]), np.array(p["y"]))
    fogp = 1 - math.exp(-max(view.depth(p["x"], p["y"]) - look.fog_start, 0) * look.fog_density)
    c.save()
    c.set_matrix(place(p["x"], p["y"], z, size, w, h, **_geo(p)))
    c.set_source_surface(surf, 0, 0)
    c.get_source().set_filter(cairo.FILTER_GOOD)
    c.paint_with_alpha(al)
    c.set_operator(cairo.OPERATOR_MULTIPLY)
    c.set_source_rgb(*(1 - (1 - np.clip(light, 0, 1)) * al).tolist())
    c.mask_surface(surf, 0, 0)
    if light.max() > 1:
        c.set_operator(cairo.OPERATOR_ADD)
        c.set_source_rgba(*(np.clip(light - 1, 0, 1) * 0.35 * al).tolist(), al)
        c.mask_surface(surf, 0, 0)
    c.set_operator(cairo.OPERATOR_OVER)
    c.set_source_rgba(*col(look.background, fogp * al))
    c.mask_surface(surf, 0, 0)
    c.restore()


def parse_moves(moves):
    if isinstance(moves, str):
        moves = [m for m in re.sub(r"\d+\.(\.\.)?", " ", moves).split() if m not in ("1-0", "0-1", "1/2-1/2", "*")]
    return moves


class Game:
    """A move sequence with per-move timing; everything is a pure function of time. schedule() times are landings."""

    def __init__(self, moves, fen=chess.STARTING_FEN, dur=0.4):
        self.fen = fen
        pos = chess.Board(fen)
        self.plies = []
        for san in parse_moves(moves):
            mv = pos.parse_san(san)
            cap_sq = None
            if pos.is_capture(mv):
                cap_sq = mv.to_square if not pos.is_en_passant(mv) else chess.square(chess.square_file(mv.to_square),
                                                                                    chess.square_rank(mv.from_square))
            rook = None
            if pos.is_castling(mv):
                kside = chess.square_file(mv.to_square) > chess.square_file(mv.from_square)
                r = chess.square_rank(mv.from_square)
                rook = (chess.square(7 if kside else 0, r), chess.square(5 if kside else 3, r))
            before = pos.copy()
            captured = pos.piece_at(cap_sq).symbol() if cap_sq is not None else None
            pos.push(mv)
            self.plies.append(dict(san=before.san(mv), move=mv, piece=before.piece_at(mv.from_square).symbol(), before=before,
                                   after=pos.copy(), cap_sq=cap_sq, captured=captured, rook=rook, check=pos.is_check(),
                                   mate=pos.is_checkmate(), t0=None, dur=dur))

    def schedule(self, times, dur=None, first=0):
        for k, t in enumerate(times):
            p = self.plies[first + k]
            if dur is not None:
                p["dur"] = dur[k] if isinstance(dur, (list, tuple)) else dur
            p["t0"] = t - p["dur"]
        return self

    def t1(self, i):
        return self.plies[i]["t0"] + self.plies[i]["dur"]

    def current(self, t):
        """(index of the last ply that has started, its progress 0..1), or (-1, 1)."""
        idx = -1
        for i, p in enumerate(self.plies):
            if p["t0"] is not None and p["t0"] <= t:
                idx = i
        return (idx, prog(t, self.plies[idx]["t0"], self.plies[idx]["dur"])) if idx >= 0 else (-1, 1.0)

    def position(self, t):
        i, pr = self.current(t)
        if i < 0:
            return chess.Board(self.fen)
        return self.plies[i]["after"] if pr >= 1 else self.plies[i]["before"]

    def pose(self, i, pr):
        """Anticipation, travel and lift of a moving piece; knights follow a curved L-shaped leap."""
        p = self.plies[i]
        (ax, ay), (bx, by) = sq_xy(p["move"].from_square), sq_xy(p["move"].to_square)
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        u = prog(pr, 0.07, 0.93)
        e = ease(u)
        knight = p["piece"].lower() == "n"
        if knight:
            cx, cy = (ax, by) if abs(dy) > abs(dx) else (bx, ay)
            x = (1 - e) ** 2 * ax + 2 * e * (1 - e) * cx + e * e * bx
            y = (1 - e) ** 2 * ay + 2 * e * (1 - e) * cy + e * e * by
        else:
            x, y = lerp(ax, bx, e), lerp(ay, by, e)
        prep = math.sin(math.pi * prog(pr, 0, 0.07)) if pr < 0.07 else 0.0
        height = 0.95 if knight else 0.2 if p["piece"].lower() == "k" else 0.28
        lift = height * 4 * u * (1 - u)
        turn = 1 if dx + 0.5 * dy >= 0 else -1
        return dict(x=x - 0.06 * dx / length * prep, y=y - 0.06 * dy / length * prep, z=lift,
                    rot=turn * (0.1 * prep + (0.2 if knight else 0.09) * math.sin(math.tau * u) * math.sin(math.pi * u)))

    def pieces(self, t, fade=0.18):
        """Piece poses, with a brief landing settle and captured pieces displaced under the capturer."""
        i, pr = self.current(t)
        board = self.position(t)
        skip, out = set(), []
        if i >= 0 and pr < 1:
            p = self.plies[i]
            skip.add(p["move"].from_square)
            out.append(dict(sym=p["piece"], sq=p["move"].to_square, moving=True, **self.pose(i, pr)))
            if p["rook"]:
                skip.add(p["rook"][0])
                (ax, ay), (bx, by) = sq_xy(p["rook"][0]), sq_xy(p["rook"][1])
                out.append(dict(sym="R" if p["piece"].isupper() else "r", x=lerp(ax, bx, ease(pr)), y=lerp(ay, by, ease(pr)),
                                sq=p["rook"][1], moving=True))
        for sq, pc in board.piece_map().items():
            if sq not in skip:
                x, y = sq_xy(sq)
                out.append(dict(sym=pc.symbol(), x=x, y=y, sq=sq))
        if i >= 0 and pr >= 1:
            q = self.plies[i]
            age = t - self.t1(i)
            if age < 0.2:
                landed = next(p for p in out if p.get("sq") == q["move"].to_square)
                landed["rot"] = 0.11 * math.exp(-age * 18) * math.sin(age * 34)
            if q["captured"] and age < fade:
                (ax, ay), (x, y) = sq_xy(q["move"].from_square), sq_xy(q["cap_sq"])
                dx, dy = x - ax, y - ay
                length, k = math.hypot(dx, dy), age / fade
                out.insert(0, dict(sym=q["captured"], x=x + dx / length * 0.18 * ease(k),
                                   y=y + dy / length * 0.18 * ease(k), rot=0.22 * ease(k), alpha=1 - ease(k)))
        return out

    def arrows(self, t):
        """Check arrows on screen at t: [(board points, ply index, age, fade)] from each check's landing until the reply
        lands, fading while the reply moves (a mate's arrow stays). A knight's arrow takes its L, long leg first."""
        out = []
        for i, p in enumerate(self.plies):
            if not p["check"] or p["t0"] is None or t < self.t1(i):
                continue
            fade_from, end = self.t1(i) + 0.75, self.t1(i) + 0.9
            if i + 1 < len(self.plies) and self.plies[i + 1]["t0"] is not None:
                fade_from, end = self.plies[i + 1]["t0"], self.t1(i + 1)
            if p["mate"]:
                fade_from = end = math.inf
            if t >= end:
                continue
            fade = 1 - ease(prog(t, fade_from, end - fade_from)) if end < math.inf else 1.0
            kx, ky = sq_xy(p["after"].king(p["after"].turn))
            for a in p["after"].checkers():
                ax, ay = sq_xy(a)
                path = [(ax, ay), (kx, ky)]
                if p["after"].piece_type_at(a) == chess.KNIGHT:
                    path.insert(1, (ax, ky) if abs(ky - ay) > abs(kx - ax) else (kx, ay))
                out.append((path, i, t - self.t1(i), fade))
        return out

    def trail(self, t, sym):
        """The route walked so far by the piece with symbol sym (a king, say): its from-squares, then where it is now."""
        pts = [sq_xy(p["move"].from_square) for p in self.plies if p["piece"] == sym and p["t0"] is not None and p["t0"] <= t]
        now = next(((p["x"], p["y"]) for p in self.pieces(t) if p["sym"] == sym), None)
        return pts + [now] if now else pts

    def events(self):
        """[(landing time, kind)]: mate, check, promote, castle, capture or move."""
        out = []
        for p in self.plies:
            if p["t0"] is not None:
                kind = ("mate" if p["mate"] else "check" if p["check"] else "promote" if p["move"].promotion else "castle" if p["rook"]
                        else "capture" if p["captured"] else "move")
                out.append((p["t0"] + p["dur"], kind))
        return out
