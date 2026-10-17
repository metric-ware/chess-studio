import json, subprocess
from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100
ASR = 22050
HOP = 512
ROOT = Path(__file__).resolve().parent.parent
MUSIC = ROOT / "assets" / "music"
SFX = ROOT / "assets" / "sfx"


def load(path, sr=SR, channels=2):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", str(channels), "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32).copy()
    return a.reshape(-1, channels) if channels > 1 else a


YT_ARGS = ["--js-runtimes", "node", "--extractor-args", "youtube:player_client=web_embedded,mweb;player_skip=webpage"]


def fetch(query, slug, artist=""):
    """Find the official upload of a song on YouTube (prefers '- Topic' / artist channels over edits) and save it as mp3."""
    import re
    res = subprocess.run(["yt-dlp", "--flat-playlist", "-J", f"ytsearch10:{query}"], capture_output=True, text=True, check=True)
    entries = [e for e in json.loads(res.stdout)["entries"] if e and e.get("duration")]
    words = lambda s: set(re.findall(r"\w+", s.lower()))
    q = words(query)

    def score(e):
        title, ch = e["title"].lower(), (e.get("channel") or "").lower()
        s = 4 * len(q & words(title)) / len(q) + 5 * ch.endswith(" - topic") + 2 * bool(artist and words(artist.split(",")[0]) & words(ch))
        for w in ("edit", "loop", "hour", "1h", "tiktok", "amv", "compilation", "mix"):
            s -= 3 * (w in title and w not in query.lower())
        for w in ("slowed", "sped", "remix", "reverb", "ultra", "super"):
            s -= 2 * ((w in title) != (w in query.lower()))
        s -= 6 * (not 60 <= e["duration"] <= 420)
        return s + 0.1 * np.log10((e.get("view_count") or 1) + 1)

    best = max(entries, key=score)
    MUSIC.mkdir(parents=True, exist_ok=True)
    subprocess.run(["yt-dlp", "-q", "--no-progress", *YT_ARGS, "-f", "ba/b", "-x", "--audio-format", "mp3", "--audio-quality", "0",
                    "-o", str(MUSIC / f"{slug}.%(ext)s"), "--", best["id"]], check=True)
    meta = {"title": best["title"], "query": query, "artist": artist, "source": f"https://www.youtube.com/watch?v={best['id']}",
            "channel": best.get("channel"), "duration": best["duration"], "views_at_download": best.get("view_count")}
    (MUSIC / f"{slug}.json").write_text(json.dumps(meta, indent=1))
    return meta


# ---------- analysis ----------

def _mel_fb(n_fft, n=64, fmin=30, fmax=11000):
    freqs = np.fft.rfftfreq(n_fft, 1 / ASR)
    mel, imel = (lambda f: 2595 * np.log10(1 + f / 700)), (lambda m: 700 * (10 ** (m / 2595) - 1))
    pts = imel(np.linspace(mel(fmin), mel(fmax), n + 2))
    fb = np.array([np.clip(np.minimum((freqs - l) / (c - l), (r - freqs) / (r - c)), 0, None) for l, c, r in zip(pts, pts[1:], pts[2:])])
    return fb, pts[1:-1]


def _smooth(x, n):
    n = max(1, int(n))
    return np.convolve(x, np.ones(n) / n, mode="same")


def _tempo(env, fr, bpm_range=(60, 200)):
    e = env - env.mean()
    ac = np.fft.irfft(np.abs(np.fft.rfft(e, 2 * len(e))) ** 2)[: len(e)]
    bpms = np.arange(bpm_range[0], bpm_range[1], 0.25)
    lags = 60 * fr / bpms
    score = np.interp(lags, np.arange(len(ac)), ac)
    # log-gaussian prior like librosa, centered on slowed-funk/phonk tempos to resolve half/double ambiguity
    score *= np.exp(-0.5 * (np.log2(bpms / 110) / 0.8) ** 2)
    return float(bpms[np.argmax(score)])


def _track(env, fr, bpm, tightness=100):
    period = 60 * fr / bpm
    local = np.convolve(env, signal.windows.gaussian(int(period), period / 16), mode="same")
    n = len(local)
    cum, back = np.zeros(n), -np.ones(n, int)
    lo_off, hi_off = int(round(2 * period)), int(round(period / 2))
    for i in range(n):
        hi = i - hi_off
        if hi < 0:
            cum[i] = local[i]
            continue
        prev = np.arange(max(0, i - lo_off), hi + 1)
        cand = cum[prev] - tightness * np.log((i - prev) / period) ** 2
        k = np.argmax(cand)
        cum[i], back[i] = local[i] + cand[k], prev[k]
    tail = np.arange(max(0, n - int(period)), n)
    i = tail[np.argmax(cum[tail])]
    beats = []
    while i >= 0:
        beats.append(i)
        i = back[i]
    beats = np.array(beats[::-1])
    strong = local[beats] > 0.3 * np.median(local[beats])
    return beats[np.argmax(strong): len(beats) - np.argmax(strong[::-1])]


def analyze(path, bpm=None):
    """Tempo, beats, downbeats, drops and a 10Hz energy curve of a song. Cached next to the file as .json."""
    path = Path(path)
    meta_path = path.with_suffix(".json")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    if "analysis" in meta and (bpm is None or meta["analysis"]["bpm"] == bpm):
        return meta["analysis"]
    y = load(path, ASR, 1)
    _, _, Z = signal.stft(y, ASR, nperseg=2048, noverlap=2048 - HOP, boundary=None, padded=False)
    S = np.abs(Z)
    fr = ASR / HOP
    fb, centers = _mel_fb(2048)
    M = np.log1p(100 * (fb @ S))
    flux = np.maximum(0, np.diff(M, axis=1, prepend=M[:, :1]))
    env = flux.mean(0)
    env = np.maximum(0, env - _smooth(env, fr))
    env /= env.std() + 1e-9
    low_flux = flux[centers < 150].mean(0)
    bpm = bpm or _tempo(env, fr)
    bframes = _track(env, fr, bpm)
    beats = bframes / fr + 1024 / ASR
    # downbeat phase: kicks tend to land on bar starts
    phase = int(np.argmax([low_flux[bframes[k::4]].mean() if len(bframes[k::4]) else 0 for k in range(4)]))
    freqs = np.fft.rfftfreq(2048, 1 / ASR)
    db = lambda p: 10 * np.log10(_smooth(p, fr * 0.25) + 1e-10)
    low_db, full_db = db((S[freqs < 150] ** 2).sum(0)), db((S ** 2).sum(0))
    times = np.arange(S.shape[1]) / fr + 1024 / ASR

    def win(x, a, b):
        m = (times >= a) & (times < b)
        return x[m].mean() if m.any() else x.mean()

    top = np.percentile(full_db, 95)
    cands = []
    for b in beats[beats > 3]:
        # short post window pins the exact impact beat (a 2-beat dip before a drop must not win over the drop itself)
        rise = 0.6 * (win(low_db, b, b + 1.5) - win(low_db, b - 2.5, b - 0.15)) + 0.4 * (win(full_db, b, b + 1.5) - win(full_db, b - 2.5, b - 0.15))
        loud = win(full_db, b, b + 3) - top
        cands.append((float(rise + 0.5 * min(loud, 0)), float(b)))
    drops = []
    for s, b in sorted(cands, reverse=True):
        if s < 3 or len(drops) >= 6:
            break
        if all(abs(b - d["t"]) > 6 for d in drops):
            drops.append({"t": round(b, 3), "score": round(s, 2)})
    drops.sort(key=lambda d: d["t"])
    analysis = {
        "bpm": round(bpm, 2),
        "duration": round(len(y) / ASR, 3),
        "beats": [round(float(b), 3) for b in beats],
        "downbeats": [round(float(b), 3) for b in beats[phase::4]],
        "drops": drops,
        "main_drop": max(drops, key=lambda d: d["score"])["t"] if drops else None,
        "energy": [round(float(v), 1) for v in np.interp(np.arange(0, times[-1], 0.1), times, full_db)],
    }
    meta["analysis"] = analysis
    meta_path.write_text(json.dumps(meta, indent=1))
    return analysis


def plot(path, out_png, start=0, end=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    a = analyze(path)
    end = end or a["duration"]
    e = np.array(a["energy"])
    t = np.arange(len(e)) / 10
    fig, ax = plt.subplots(figsize=(18, 4))
    m = (t >= start) & (t <= end)
    ax.plot(t[m], e[m], lw=0.8, color="k")
    for b in a["beats"]:
        if start <= b <= end:
            ax.axvline(b, color="0.8", lw=0.5)
    for b in a["downbeats"]:
        if start <= b <= end:
            ax.axvline(b, color="tab:blue", lw=0.8)
    for d in a["drops"]:
        if start <= d["t"] <= end:
            ax.axvline(d["t"], color="red", lw=2)
            ax.text(d["t"], e[m].max(), f'{d["t"]:.2f}s ({d["score"]})', color="red")
    ax.set_title(f'{Path(path).stem}  {a["bpm"]} bpm')
    ax.set_xlim(start, end)
    fig.tight_layout()
    fig.savefig(out_png, dpi=90)
    plt.close(fig)


# ---------- sound effects (synthesized, deterministic) ----------

def _t(dur):
    return np.arange(int(dur * SR)) / SR


def _st(x, pan=0.0):
    x = np.asarray(x, np.float32)
    if x.ndim == 2:
        return x
    return np.stack([x * np.sqrt((1 - pan) / 2), x * np.sqrt((1 + pan) / 2)], 1) * np.sqrt(2)


def _shaped_noise(dur, center, width, seed):
    """Noise whose spectrum is a moving gaussian bump; center/width are arrays over time (Hz)."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    f, tt, Z = signal.stft(rng.standard_normal(n + 4096), SR, nperseg=1024)
    tt = np.clip(tt / dur, 0, 1)
    c = np.interp(tt, np.linspace(0, 1, len(center)), center)
    w = np.interp(tt, np.linspace(0, 1, len(width)), width)
    Z *= np.exp(-0.5 * ((f[:, None] - c[None]) / w[None]) ** 2)
    return signal.istft(Z, SR, nperseg=1024)[1][:n]


def _reverb(x, length=1.2, mix=0.3, seed=3):
    rng = np.random.default_rng(seed)
    ir = rng.standard_normal(int(length * SR)) * np.exp(-_t(length) * 6 / length)
    ir = signal.lfilter(*signal.butter(2, 6000 / (SR / 2)), ir)
    wet = signal.fftconvolve(x, ir)[: len(x) + len(ir)]
    wet /= np.abs(wet).max() + 1e-9
    out = np.zeros(len(wet))
    out[: len(x)] += x * (1 - mix)
    return out + wet * mix * np.abs(x).max()


def _norm(x, peak=0.9):
    return x / (np.abs(x).max() + 1e-9) * peak


@lru_cache(None)
def sfx(name, dur=None, seed=0):
    """Stereo float32 array for a named effect. chess.com sounds use their file names (move-self, capture, ...)."""
    if (SFX / f"cc_{name}.mp3").exists():
        return load(SFX / f"cc_{name}.mp3")
    if name == "whoosh":
        d = dur or 0.45
        env = np.sin(np.pi * np.clip(_t(d) / d, 0, 1) ** 0.7) ** 2
        x = _shaped_noise(d, np.geomspace(400, 3500, 16), np.geomspace(250, 2000, 16), seed) * env
        pan = np.linspace(-0.7, 0.7, len(x))
        return _st(np.stack([x * np.sqrt((1 - pan) / 2), x * np.sqrt((1 + pan) / 2)], 1) * 1.4 / (np.abs(x).max() + 1e-9) * 0.8)
    if name == "whoosh_down":
        d = dur or 0.6
        env = np.sin(np.pi * np.clip(_t(d) / d, 0, 1) ** 1.3) ** 2
        return _st(_norm(_shaped_noise(d, np.geomspace(3000, 250, 16), np.geomspace(1500, 200, 16), seed) * env, 0.8))
    if name == "impact":
        d = dur or 2.2
        t = _t(d)
        freq = 30 + 110 * np.exp(-t * 9)
        body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 2.2)
        rng = np.random.default_rng(seed)
        crack = signal.lfilter(*signal.butter(2, 4000 / (SR / 2)), rng.standard_normal(len(t))) * np.exp(-t * 35)
        x = np.tanh(2.5 * body + 0.8 * crack)
        return _st(_norm(_reverb(x, 1.6, 0.25)))
    if name == "boom":  # short punchy hit for text pops / beat cuts
        d = dur or 0.5
        t = _t(d)
        x = np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-t * 25)) / SR) * np.exp(-t * 7)
        return _st(_norm(np.tanh(3 * x), 0.85))
    if name == "subdrop":
        d = dur or 1.6
        t = _t(d)
        return _st(_norm(np.sin(2 * np.pi * np.cumsum(28 + 70 * np.exp(-t * 3)) / SR) * np.exp(-t * 1.8) * np.minimum(1, t * 200)))
    if name == "riser":
        d = dur or 2.0
        t = _t(d)
        env = (t / d) ** 2
        noise = _shaped_noise(d, np.geomspace(300, 7000, 32), np.geomspace(150, 3000, 32), seed)
        tone = signal.sawtooth(2 * np.pi * np.cumsum(np.geomspace(110, 880, len(t))) / SR) * 0.25
        tone = signal.lfilter(*signal.butter(2, 3000 / (SR / 2)), tone)
        return _st(_norm((_norm(noise) + tone) * env, 0.75))
    if name == "ding":  # bell
        d = dur or 1.6
        t = _t(d)
        x = sum(a * np.sin(2 * np.pi * 1320 * r * t) * np.exp(-t * k) for r, a, k in [(1, 1, 3), (2.0, 0.5, 5), (2.76, 0.35, 7), (5.4, 0.2, 11), (8.93, 0.1, 16)])
        return _st(_norm(_reverb(x * np.minimum(1, t * 800), 1.0, 0.25), 0.55))
    if name == "heartbeat":
        t = _t(0.9)
        thump = lambda s: np.where(t >= s, np.sin(2 * np.pi * 55 * (t - s)) * np.exp(-(t - s) * 14), 0)
        return _st(_norm(np.tanh(2 * (thump(0) + 0.8 * thump(0.28))), 0.9))
    raise KeyError(name)


# ---------- mixing ----------

class Mix:
    def __init__(self, duration):
        self.buf = np.zeros((int(duration * SR) + SR, 2), np.float32)
        self.duration = duration

    def add(self, x, at, gain_db=0.0):
        x = sfx(x) if isinstance(x, str) else _st(x)
        i = int(round(at * SR))
        if i < 0:
            x, i = x[-i:], 0
        n = min(len(x), len(self.buf) - i)
        if n > 0:
            self.buf[i: i + n] += x[:n] * 10 ** (gain_db / 20)

    def music(self, path, song_start, at=0.0, dur=None, gain_db=0.0, fade_in=0.0, fade_out=0.6, mutes=()):
        """Place a song excerpt at edit time `at`; mutes [(t0, t1)] in edit time silence it (a short ramp before)."""
        song = _song(str(path))
        dur = dur or self.duration - at
        x = song[int(song_start * SR): int((song_start + dur) * SR)].copy()
        n = len(x)
        env = np.ones(n, np.float32)
        if fade_in:
            env *= np.clip(np.arange(n) / (fade_in * SR), 0, 1)
        if fade_out:
            env *= np.clip((n - np.arange(n)) / (fade_out * SR), 0, 1)
        for t0, t1 in mutes:
            a, b = (int(np.clip((u - at) * SR, 0, n)) for u in (t0, t1))
            if b > a:
                env[a:b] = 0
                env[max(0, a - 256):a] *= np.linspace(1, 0, a - max(0, a - 256))
        self.add(x * env[:, None], at, gain_db)

    def write(self, path, lufs=-14.0):
        out = self.buf[: int(self.duration * SR)]
        tmp = Path(path).with_suffix(".raw.wav")
        wavfile.write(tmp, SR, out)
        pass1 = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(tmp), "-af", f"loudnorm=I={lufs}:TP=-1:LRA=11:print_format=json", "-f", "null", "-"],
                               capture_output=True, text=True).stderr
        m = json.loads(pass1[pass1.rindex("{"): pass1.rindex("}") + 1])
        af = (f"loudnorm=I={lufs}:TP=-1:LRA=11:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
              f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']},aresample={SR}")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-af", af, "-c:a", "pcm_s16le", str(path)], check=True)
        tmp.unlink()


@lru_cache(8)
def _song(path):
    return load(path)
