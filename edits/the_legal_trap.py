from studio import *

WHITE, VIOLET, TEAL, RED, GRAY = "#f2f2f2", "#b07aff", "#26c2a3", "#ed3e40", "#c9ccd1"
BOOK, BEST = "#a88865", "#81b64c"
SONG = "montagem_uranium_slowed"
MOVES = "e4 e5 Nf3 Nc6 Bc4 d6 Nc3 Bg4 h3 Bh5 Nxe5 Bxd1 Bxf7+ Ke7 Nd5#"
# the intro up to its second downbeat, then the drop; groove bar 2 plays twice so the break lands on Bxd1
edit = Edit("the_legal_trap", 18.5, song=SONG, segments=[(0.0, 5.248), (14.559, 21.525), (16.881, 19.203), (21.525, 30.0)],
            drop=14.559, fade_out=0.3, vignette=0.12, shade=430)

b = lambda t, k: edit.beat(t, k)
DROP = edit.drop
# cold open: the song's four ticks are the bishop's four hops, its first boom the queen being smashed
TICKS = [0.020, 0.166, 0.311, 0.457]
SMASH = 0.603
LAND_N, LAND_B, NET = (b(SMASH, k) for k in (3, 4, 5))
# board, from the drop: one ply per beat, the queen taken as the music breaks, mate on the slam
B = lambda k: DROP + k * (b(DROP, 1) - DROP)
OPENING = [b(DROP, k) for k in range(1, 8)]
BG4, H3, BH5, NXE5, BXD1 = (b(DROP, k) for k in (8, 10, 11, 13, 16))
BXF7, KE7 = B(17.5), B(18.5)
MATE = edit.to_edit(23.87)
END = edit.duration

game = Game(MOVES)
game.schedule(OPENING + [BG4, H3, BH5, NXE5, BXD1, BXF7, KE7, MATE],
              dur=[0.4] * 7 + [0.45, 0.35, 0.42, 0.6, 0.9, 0.5, 0.4, 0.8])
assert game.plies[-1]["mate"]

LOOK = Look(ambient=0.62)
HALL = Look(board=False, stand=True, floor="#ececec", floor2="#8f9297", tile=1.0, fog_density=0.06, fog_start=10, ambient=0.4)


# ---------- cold open ----------

def jolt(t, t0, amount):
    """A damped rock after an impact at t0."""
    s = t - t0
    return amount * math.exp(-s * 9) * math.sin(s * 28) if s >= 0 else 0.0


QUEEN_SQ = (0.5, 0.5)
HOPS = [(-4.5 + k, 5.5 - k) for k in range(6)]  # the bishop's diagonal, ending on the queen
HOP_T = [TICKS[0] - 0.146] + TICKS + [SMASH]
KING_SQ = (-2.5, -0.5)
# the trap springs: a knight lands to the king's right, a bishop to his left, then his escape squares light up
POUNCES = [("N", (-0.4, 4.4), (-1.55, -0.2), LAND_N, 1.55, -1),
           ("B", (-5.6, 3.8), (-3.45, -0.8), LAND_B, 1.2, 1)]
ESCAPES = [(-3.5, -1.5), (-2.5, -1.5), (-1.5, -1.5), (-1.5, 0.5), (-2.5, 0.5), (-3.5, 0.5)]
GLOW = "#8c5cff"  # the violet accent as light: the caption violet reads pink once it multiplies the white floor


def bishop_hall(t):
    if t >= SMASH:
        k = ease(prog(t, SMASH, 0.25))
        return dict(sym="b", x=QUEEN_SQ[0] + 0.22 * k, y=QUEEN_SQ[1] - 0.22 * k, rot=jolt(t, SMASH, 0.14))
    i = max(0, next(i for i in range(1, len(HOP_T)) if t < HOP_T[i]) - 1)
    p = prog(t, HOP_T[i], HOP_T[i + 1] - HOP_T[i])
    (ax, ay), (bx, by) = HOPS[i], HOPS[i + 1]
    return dict(sym="b", x=lerp(ax, bx, p), y=lerp(ay, by, p), z=0.22 * 4 * p * (1 - p),
                rot=0.12 * math.sin(math.pi * p))


def queen_hall(t):
    """Knocked over by the bishop: tumbles to its right and comes to rest on its side beside him."""
    if t < SMASH:
        return dict(sym="Q", x=QUEEN_SQ[0], y=QUEEN_SQ[1])
    s = t - SMASH
    d = 1.0 * (1 - math.exp(-s * 4.5))
    return dict(sym="Q", x=QUEEN_SQ[0] + d * 0.95, y=QUEEN_SQ[1] - d * 0.3, z=max(0.0, 1.5 * s - 3.8 * s * s),
                rot=1.5 * ease(prog(s, 0, 0.4)) + jolt(t, SMASH + 0.4, 0.12))


def pounce(t, sym, a, b_, land, height, facing):
    """A white piece leaping out of the dark to land beside the king."""
    t0 = land - 0.64
    if t < t0:
        return None
    p = prog(t, t0, 0.64)
    travel = p * p * (3 - 2 * p)
    return dict(sym=sym, x=lerp(a[0], b_[0], travel), y=lerp(a[1], b_[1], travel), z=4 * height * p * (1 - p),
                sx=facing, rot=facing * (-0.18 * math.sin(math.tau * p) + jolt(t, land, 0.13)))


def escape_lit(t, k):
    """The k-th escape square lighting up: the front row on one beat, the back row on the next."""
    return ease(prog(t, b(NET, k // 3) + 0.07 * (k % 3), 0.14))


def king_hall(t):
    return dict(sym="k", x=KING_SQ[0], y=KING_SQ[1],
                rot=-jolt(t, LAND_N, 0.1) + jolt(t, LAND_B, 0.12) - jolt(t, NET, 0.05) + jolt(t, b(NET, 1), 0.07))


def truck_at(t):
    return ease(prog(t, 1.25, 1.0))


def hall_cam(t):
    linger = ease(prog(t, SMASH, 0.7))
    push = ease(prog(t, LAND_N - 0.2, NET - LAND_N + 0.2))
    net = ease(prog(t, NET - 0.1, DROP - NET - 0.2))
    rise = ease(prog(t, DROP - 0.32, 0.32))
    start = Cam(-0.3, 1.3, span=3.9 - 0.45 * ease(prog(t, 0, SMASH)), yaw=-25, pitch=12, oy=190)
    start = start.lerp(Cam(0.9, 0.5, span=3.5, yaw=-20, pitch=14, oy=210), linger)
    king = Cam(KING_SQ[0] + 0.3, KING_SQ[1] + 0.35, span=4.1, yaw=-25, pitch=13, oy=200)
    close = Cam(KING_SQ[0] + 0.05, KING_SQ[1] + 0.25, span=3.9, yaw=-17, pitch=16, oy=215)
    above = Cam(KING_SQ[0], KING_SQ[1] + 0.1, span=4.3, yaw=-8, pitch=27, oy=170)
    cam = start.lerp(king, truck_at(t)).lerp(close, push).lerp(above, net)
    return cam.lerp(Cam(cam.x, cam.y + 1.2, span=cam.span * 1.5, yaw=cam.yaw + 25, pitch=48, roll=0.06, oy=cam.oy), rise)


def hall(t):
    f = Frame(edit.w, edit.h)
    cam = hall_cam(t)
    bishop = bishop_hall(t)
    trio = [pounce(t, *p) for p in POUNCES]
    pieces = [p for p in [king_hall(t), bishop, queen_hall(t)] + trio if p]
    lights = [(cam.x, cam.y, 3.2, 0.2, "#ffffff"),
              (QUEEN_SQ[0] + 0.3, QUEEN_SQ[1], 2.3, 1.05, "#ffffff"),
              (bishop["x"], bishop["y"], 1.2, 1.2 * (1 - ease(prog(t, SMASH, 0.6))), RED),
              (KING_SQ[0], KING_SQ[1] + 0.2, 1.8, 0.95, RED)]
    # the white pieces drag a violet pool of light in from the dark, so they read before they land
    for p, (_, _, _, land, _, _) in zip(trio, POUNCES):
        if p:
            lights.append((p["x"], p["y"], 0.75, 1.7 * ease(prog(t, land - 0.64, 0.2)), GLOW))

    def under(c, v):
        for k, (x, y) in enumerate(ESCAPES):
            a = escape_lit(t, k)
            if a > 0:
                v.poly(c, [(x - 0.5, y - 0.5), (x + 0.5, y - 0.5), (x + 0.5, y + 0.5), (x - 0.5, y + 0.5)])
                c.set_source_rgba(*col(RED, 0.7 * a))
                c.fill()

    focus = lerp(QUEEN_SQ, KING_SQ, truck_at(t))
    draw_board(f, View(cam, f.w, f.h), HALL, lights, pieces, under, focus=focus, dof=0.4, k=2)
    return f


# ---------- board ----------

def ply_color(i):
    san = game.plies[i]["san"]
    if i < 10:
        return BOOK
    return {"Nxe5": TEAL, "Bxd1": RED, "Bxf7+": BEST, "Ke7": RED, "Nd5#": BEST}[san]


def pinner(t):
    """The black bishop pinning the f3 knight (g4, then h5), wherever it is at t."""
    return next((p["x"], p["y"]) for p in game.pieces(t) if p["sym"] == "b" and p.get("sq") in (chess.G4, chess.H5))


def drift(t0, t1, a, b_):
    """A shot that keeps gliding from Cam a to Cam b over [t0, t1]."""
    return lambda t: a.lerp(b_, prog(t, t0, t1 - t0))


CAMS = [
    (DROP, 0, Cam(3.6, 2.6, span=9.6, yaw=-58, pitch=46, roll=-0.12, oy=40)),
    (DROP, 0.7, drift(DROP, OPENING[-1], Cam(4.0, 4.0, span=11.8, yaw=-22, pitch=67, oy=110), Cam(4.6, 3.4, span=9.8, yaw=-3, pitch=66, oy=120))),
    (OPENING[-1] - 0.2, 0.8, drift(OPENING[-1], NXE5 - 0.6, Cam(5.0, 2.9, span=8.6, yaw=-4, pitch=66, oy=125), Cam(5.2, 2.7, span=7.8, yaw=3, pitch=64, oy=125))),
    (NXE5 - 0.6, 0.6, drift(NXE5 - 0.6, BXD1, Cam(5.1, 2.6, span=7.4, yaw=2, pitch=64, oy=130), Cam(4.6, 2.0, span=6.6, yaw=9, pitch=66, oy=130))),
    (BXF7 - 0.5, 0.5, drift(BXF7, MATE - 0.6, Cam(4.8, 5.8, span=7.2, yaw=-2, pitch=66, oy=135), Cam(4.6, 5.8, span=6.8, yaw=-7, pitch=67, oy=135))),
    (MATE - 0.6, 0.6, Cam(4.4, 5.7, span=6.5, yaw=-9, pitch=69, oy=135)),
    (MATE + 0.05, END - MATE - 0.05, Cam(4.4, 5.55, span=7.6, yaw=-13, pitch=72, oy=135)),
]


def board(t):
    f = Frame(edit.w, edit.h)
    i, _ = game.current(t)
    pos = game.position(t)
    checked = pos.king(pos.turn) if pos.is_check() else None
    cam = keyframes(t, CAMS)
    lights = [(cam.x, cam.y, 4.6, 0.45, "#ffffff")]
    if i >= 0:
        ply = game.plies[i]
        glow = 0.35 * ease(prog(t, ply["t0"], 0.2))
        if ply["san"] in ("Nxe5", "Bxd1", "Nd5#") and t >= game.t1(i):
            glow += 0.65 * math.exp(-(t - game.t1(i)) * 2.5)
        lights.append((*sq_xy(ply["move"].to_square), 1.25, glow, ply_color(i)))
    if checked is not None:
        lights.append((*sq_xy(checked), 1.2, 0.45, RED))
    pieces = game.pieces(t)
    if t > MATE:
        for p in pieces:
            if p["sym"] == "k":
                p["rot"] = -1.45 * ease(prog(t, MATE + 0.45, 0.4))

    def under(c, v):
        if i >= 0:
            mv, color = game.plies[i]["move"], ply_color(i)
            fade = ease(prog(t, game.plies[i]["t0"], 0.12))
            v.square(c, mv.from_square, color, 0.5 * fade)
            v.square(c, mv.to_square, color, 0.8 * fade)
        if checked is not None:
            v.glow(c, checked, RED)
        if t > MATE:
            for k, sq in enumerate((chess.D7, chess.E6, chess.E8, chess.F6)):
                v.square(c, sq, RED, 0.55 * ease(prog(t, MATE + 0.08 + 0.06 * k, 0.12)))

    def over(c, v):
        # the pin: g4/h5 bishop -> f3 knight -> d1 queen, until the knight jumps; then the bishop's open road to the queen
        if BG4 <= t < BXD1 + 0.3:
            grab = game.plies[11]  # ...Bxd1
            bx, by = pinner(t) if t < grab["t0"] else (7.5, 4.5)
            grow = ease(prog(t, BG4, 0.2))
            fade = 1 - ease(prog(t, grab["t0"], grab["dur"]))
            if t < NXE5 - 0.25:
                v.line(c, [(bx, by), (3.5, 0.5)], RED, 0.09, 0.75 * fade, progress=grow)
            else:
                v.arrow(c, [(bx, by), (3.5, 0.5)], RED, alpha=0.85 * fade, progress=ease(prog(t, NXE5 - 0.25, 0.25)), short=0.3)
        for path, j, age, fade in game.arrows(t):
            v.arrow(c, path, ply_color(j), alpha=0.9 * fade, progress=ease(prog(age, 0, 0.14)), short=0.3)

    draw_board(f, View(cam, f.w, f.h), LOOK, lights, pieces, under, over)
    return f


edit.scene(lambda t: hall(t) if t < DROP else board(t), cuts=[DROP])

# ---------- captions and sound ----------

edit.style.update(face="display", fill=WHITE, accent=VIOLET, shadow=3, upper=True, max_width=940)


def C(t0, t1, s, y=174, size=70, **kw):
    edit.caption(t0, t1, s, y, size, **kw)


def L(t0, t1, s, y=285, **kw):
    edit.caption(t0, t1, s, y, 29, **dict(dict(face="label", fill=GRAY, tracking=0.025, upper=False, anim="reveal"), **kw))


C(-0.7, DROP, "Lose your [queen].", y=150, size=72)
C(LAND_N, DROP, "Win in 8 moves.", y=232, size=72, anim="pop")
C(DROP, BG4, "The [Légal] trap")
# the opening's notation grows under the title, its left edge fixed so earlier moves don't shift
line = [f"{k // 2 + 1}.{p['san']}" if k % 2 == 0 else p["san"] for k, p in enumerate(game.plies[:7])]
width = lambda s: text_layout(s, 29, "label", 940, 1.12, False, 0.025, 12)[1]
left = edit.w / 2 - width(" ".join(line)) / 2
for k, t0 in enumerate(OPENING):
    s = " ".join(line[:k + 1])
    L(t0, OPENING[k + 1] if k + 1 < len(OPENING) else BG4, s, x=left + width(s) / 2, anim="reveal" if k == 0 else "none", out="cut")
C(BG4, H3, "They [pin] your knight")
L(BG4, H3, "4...Bg4")
C(H3, BH5, "Kick it")
L(H3, BH5, "5.h3")
C(BH5, NXE5 - 0.58, "Still [pinned]")
L(BH5, NXE5 - 0.58, "5...Bh5")
C(NXE5 - 0.58, NXE5, "Ignore it")
C(NXE5, B(14.5), "Nxe5!!", 190, 116, anim="pop", upper=False, fill=TEAL)
L(NXE5, B(14.5), "BRILLIANT", y=290)
C(B(14.5), BXD1, "[Free] queen?")
C(BXD1, BXF7, "They take it")
L(BXD1, BXF7, "6...Bxd1??", y=270)
C(BXF7, KE7, "[Check]", 190, 96, anim="pop")
L(BXF7, KE7, "7.Bxf7+", y=270)
C(KE7, MATE, "Only move")
L(KE7, MATE, "7...Ke7")
C(MATE, END, "[Checkmate]", 190, 112, anim="pop", out="cut")
L(MATE + 0.15, END, "8.Nd5# · NO QUEEN NEEDED", y=290, out="cut")

edit.game_sounds(game, gain=-8)
for t, name, gain in [(SMASH, "capture", -6), (SMASH, "impact", -16), (LAND_N - 0.5, "whoosh", -14), (LAND_N, "boom", -10),
                      (LAND_B - 0.45, "whoosh", -16), (LAND_B, "boom", -11), (NET, "boom", -14), (b(NET, 1), "boom", -12),
                      (DROP - 0.35, "whoosh", -9), (DROP, "impact", -10), (NXE5, "ding", -15),
                      (BXD1, "subdrop", -10), (KE7 + 0.05, "heartbeat", -10), (MATE - 0.6, "whoosh", -13),
                      (MATE, "impact", -5), (MATE, "subdrop", -9)]:
    edit.sfx(name, t, gain)
edit.mute(DROP - 0.06, DROP)
edit.mute(MATE - 0.09, MATE)
