import multiprocessing, os, runpy, shutil, subprocess, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import cairo, cv2
import numpy as np
from PIL import Image, ImageDraw
from . import audio
from .gfx import H, ROOT, W, Frame, font, text_anim, vignette

BUILD = ROOT / "build"
EXPORTS = ROOT / "exports"
GAME_SOUNDS = {"move": "move-self", "capture": "capture", "castle": "castle", "check": "move-check", "mate": "move-check",
               "promote": "promote"}


def load_edit(script=None):
    """The `edit` defined by an edit script (each load runs the script again, so it returns a fresh Edit)."""
    if script is None:
        script = max((ROOT / "edits").glob("*.py"), key=lambda p: p.stat().st_mtime)
    else:
        script = Path(script)
        if not script.is_file():
            script = ROOT / "edits" / f"{script.stem}.py"
    return runpy.run_path(str(script))["edit"]


class Edit:
    """One video: a motion-blurred scene, timed draw layers, captions and an audio mix, rendered to exports/<slug>.mp4.

    Music: `segments=[(song_t0, song_t1), ...]` of `song` are spliced back to back (cut on downbeats to keep the
    groove); default is the song from its start. `drop` is a song time (default: the detected main drop); edit.drop,
    edit.beats and edit.to_edit(song_time) are in edit time.
    Frame = bg, scene, layers in registration order, caption shade, vignette, captions."""

    def __init__(self, slug, duration, song=None, segments=None, drop=None, fps=60, size=(W, H), music_gain=0.0,
                 lufs=-14.0, bg="#000000", vignette=0.15, shade=0, fade_out=0.35):
        self.slug, self.duration, self.fps, self.fade_out = slug, duration, fps, fade_out
        self.w, self.h = size
        self.music_gain, self.lufs = music_gain, lufs
        self.bg, self.vignette, self.shade = bg, vignette, shade
        self.layers, self.sounds, self.captions, self.mutes = [], [], [], []
        self.style = {}
        self.shot, self.cuts, self.draft = None, [], False
        self.song, self.segments, self.beats, self.drop = song, [], [], None
        if not song:
            return
        self.segments = list(segments or [(0.0, duration)])
        an = audio.analyze(audio.MUSIC / f"{song}.mp3")
        offs = np.cumsum([0] + [b - a for a, b in self.segments])

        def all_edit(x):
            """Every edit time at which song time x plays (a song part can be used more than once)."""
            return [round(float(o + x - s0), 4) for (s0, s1), o in zip(self.segments, offs) if s0 <= x < s1 and 0 <= o + x - s0 <= duration]

        beats = []
        for x in sorted(e for b in an["beats"] for e in all_edit(b)):
            # a segment's last beat (cut ms after it starts) and the next segment's first beat land on almost the same
            # edit time; only the later one is heard
            if beats and x - beats[-1] < 0.1:
                beats[-1] = x
            else:
                beats.append(x)
        self.beats = beats
        self.to_edit = lambda x: next(iter(all_edit(x)), None)
        self.drop = self.to_edit(an["main_drop"] if drop is None else drop)

    # --- timing helpers ---
    def beat(self, t, k=0):
        """The k-th beat at or after t (k may be negative: beats before t)."""
        i = next((i for i, b in enumerate(self.beats) if b >= t - 1e-3), len(self.beats))
        return self.beats[min(max(i + k, 0), len(self.beats) - 1)]

    # --- authoring ---
    def scene(self, shot, cuts=()):
        """The moving picture under every layer: shot(t) -> Frame, motion-blurred (see _expose). Shutter samples never
        straddle a time in `cuts`, so hard cuts stay hard."""
        self.shot, self.cuts = shot, sorted(cuts)
        return shot

    def at(self, t0=0.0, t1=None):
        """Decorator: register fn(f, t, lt) drawn while t0 <= t < t1 (lt = t - t0). Draw order = registration order."""
        def deco(fn):
            self.layers.append((t0, self.duration if t1 is None else t1, fn))
            return fn
        return deco

    def caption(self, t0, t1, s, y=180, size=84, anim="reveal", x=None, out="fade", **style):
        """Caption above every layer while t0 <= t < t1 (x defaults to the frame centre). "[word]" = accent color,
        "\n" = line break. Style defaults come from self.style (see gfx.text_sprite)."""
        self.captions.append(dict(t0=t0, t1=t1, s=s, x=self.w / 2 if x is None else x, y=y, size=size, anim=anim, out=out,
                                  style=dict(self.style, **style)))

    def sfx(self, name, t, gain=0.0):
        if 0 <= t < self.duration:
            self.sounds.append((t, name, gain))

    def game_sounds(self, game, gain=-3.0):
        for t, kind in game.events():
            self.sfx(GAME_SOUNDS[kind], t, gain)

    def mute(self, t0, t1):
        """Silence the music between two edit times (a gap right before a slam)."""
        self.mutes.append((t0, t1))

    # --- rendering ---
    def _expose(self, t):
        """The scene over a 180-degree shutter. Samples start at the shutter's two ends and double (2, 3, 5, ... 33)
        while neighbouring samples still differ visibly somewhere (the biggest 8x8-block mean difference), so a still
        frame costs two renders and a whip gets enough samples to smear instead of showing separate copies."""
        if self.draft:
            return self.shot(t).np().copy()
        lo, hi = t - 0.25 / self.fps, t + 0.25 / self.fps
        for c in self.cuts:
            if t >= c:
                lo = max(lo, c)
            else:
                hi = min(hi, c - 1e-4)
        lo, hi = max(lo, 0.0), min(hi, self.duration - 1e-4)
        ts = [lo, hi]
        shots = [self.shot(x).np().copy() for x in ts]
        while len(ts) < 33:
            moved = max(cv2.resize(cv2.absdiff(a, b), (self.w // 8, self.h // 8), interpolation=cv2.INTER_AREA).max()
                        for a, b in zip(shots, shots[1:]))
            if moved < 40:
                break
            mids = [(a + b) / 2 for a, b in zip(ts, ts[1:])]
            new = [self.shot(x).np().copy() for x in mids]
            ts = [x for pair in zip(ts, mids + [None]) for x in pair if x is not None]
            shots = [s for pair in zip(shots, new + [None]) for s in pair if s is not None]
        return (np.sum(shots, axis=0, dtype=np.float32) / len(shots)).astype(np.uint8)

    def frame(self, t):
        f = Frame(self.w, self.h, self.bg)
        if self.shot:
            f.np()[:] = self._expose(t)
            f.dirty()
        for t0, t1, fn in self.layers:
            if t0 <= t < t1:
                fn(f, t, t - t0)
        if self.shade:
            g = cairo.LinearGradient(0, 0, 0, self.shade)
            g.add_color_stop_rgba(0, 0, 0, 0, 0.85)
            g.add_color_stop_rgba(0.6, 0, 0, 0, 0.55)
            g.add_color_stop_rgba(1, 0, 0, 0, 0)
            f.ctx.set_source(g)
            f.ctx.rectangle(0, 0, self.w, self.shade)
            f.ctx.fill()
        if self.vignette:
            vignette(f, self.vignette)
        for c in self.captions:
            text_anim(f, t, c["s"], c["t0"], c["t1"], c["x"], c["y"], c["size"], c["anim"], c["out"], **c["style"])
        a = f.np()
        a[..., 3] = 255
        return f

    def still(self, t, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(self.frame(t).np()[..., [2, 1, 0]]).save(path)
        return path

    def preview(self, times, name="preview", cols=4, scale=0.34):
        """Labeled contact sheet of the frames at `times` in build/previews/ (stills only: motion needs the render)."""
        global _ED
        _ED = self
        with ProcessPoolExecutor(max_workers=min(len(times), os.process_cpu_count() or 1),
                                 mp_context=multiprocessing.get_context("fork")) as pool:
            frames = list(pool.map(_render_small, [(t, scale) for t in times]))
        tw, th = frames[0].size
        rows = (len(frames) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (tw + 8) + 8, rows * (th + 40) + 8), "#202020")
        d = ImageDraw.Draw(sheet)
        for k, (t, im) in enumerate(zip(times, frames)):
            x, y = 8 + (k % cols) * (tw + 8), 8 + (k // cols) * (th + 40)
            sheet.paste(im, (x, y + 32))
            d.text((x, y), f"t={t:.2f}s", fill="#ffffff", font=font("label", 26))
        out = BUILD / "previews" / f"{self.slug}_{name}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(out)
        return out

    def render(self, workers=None, draft=False):
        """exports/<slug>.mp4; draft=True renders one sample per frame with a fast encode to build/<slug>_draft.mp4
        for checking motion and timing quickly."""
        global _ED
        _ED, self.draft = self, draft
        t_start = time.time()
        work = BUILD / self.slug / "render"
        work.mkdir(parents=True, exist_ok=True)
        n = int(round(self.duration * self.fps))
        workers = workers or max(1, (os.process_cpu_count() or 1) - 2)
        bounds = np.linspace(0, n, workers + 1).astype(int)
        jobs = [(int(a), int(b), str(work / f"seg{k:02d}.mp4")) for k, (a, b) in enumerate(zip(bounds, bounds[1:])) if b > a]
        print(f"Rendering {self.slug}: {len(jobs)} workers, {'draft' if draft else 'final'}", flush=True)
        with ProcessPoolExecutor(max_workers=len(jobs), mp_context=multiprocessing.get_context("fork")) as pool:
            futures = {pool.submit(_render_range, job): i for i, job in enumerate(jobs)}
            segs = [None] * len(jobs)
            for done, future in enumerate(as_completed(futures), 1):
                segs[futures[future]] = future.result()
                print(f"Rendered segment {done}/{len(jobs)}", flush=True)
        (work / "segs.txt").write_text("".join(f"file '{s}'\n" for s in segs))
        video, wav = work / "video.mp4", work / "mix.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(work / "segs.txt"), "-c", "copy", str(video)], check=True)
        self.mix().write(wav, self.lufs)
        out = BUILD / f"{self.slug}_draft.mp4" if draft else EXPORTS / f"{self.slug}.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)
        export_clean(video, wav, work / "export.mp4", self.duration)
        (work / "export.mp4").replace(out)
        shutil.rmtree(work)
        print(f"rendered {out} ({n} frames, {time.time() - t_start:.1f}s)")
        return out

    def mix(self):
        m = audio.Mix(self.duration)
        at = 0.0
        for i, (s0, s1) in enumerate(self.segments):
            d = min(s1 - s0, self.duration - at)
            if d <= 0:
                break
            last = i == len(self.segments) - 1 or at + d >= self.duration
            m.music(audio.MUSIC / f"{self.song}.mp3", s0, at, d, self.music_gain, fade_in=0.012 if i else 0.0,
                    fade_out=self.fade_out if last else 0.012, mutes=self.mutes)
            at += d
        for t, name, gain in self.sounds:
            m.add(name, t, gain)
        return m


_ED = None


def _render_range(job):
    i0, i1, path = job
    ed = _ED
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{ed.w}x{ed.h}", "-r", str(ed.fps), "-i", "-",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv:flags=bicubic+accurate_rnd+full_chroma_int,format=yuv420p,"
                  "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv",
           "-c:v", "libx264", "-preset", "veryfast" if ed.draft else "medium", "-crf", "23" if ed.draft else "15", "-threads", "2",
           "-g", str(ed.fps), path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(i0, i1):
        p.stdin.write(ed.frame(i / ed.fps).np().data)
    p.stdin.close()
    if p.wait():
        raise RuntimeError(f"ffmpeg failed on {path}")
    return path


def _render_small(job):
    t, scale = job
    a = _ED.frame(t).np()
    return Image.fromarray(a[..., [2, 1, 0]]).resize((int(_ED.w * scale), int(_ED.h * scale)), Image.LANCZOS)


def export_clean(video, wav, out, duration):
    """Final mux with all identifying metadata removed: container tags, creation times, encoder strings, track
    handler names and the x264 settings SEI (NAL type 6) inside the bitstream."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0", "-t", f"{duration}",
                    "-c:v", "copy", "-bsf:v", "filter_units=remove_types=6", "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
                    "-map_metadata", "-1", "-map_chapters", "-1", "-metadata:s:v:0", "handler_name=", "-metadata:s:a:0", "handler_name=",
                    "-metadata:s:v:0", "language=und", "-metadata:s:a:0", "language=und",
                    "-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact", "-movflags", "+faststart", str(out)], check=True)
    data = bytearray(Path(out).read_bytes())
    i = 0
    while (i := data.find(b"hdlr", i + 1)) != -1:
        # FFmpeg names the tracks VideoHandler/SoundHandler; the name runs from 28 bytes after the box type to the box
        # end, so zeroing it in place empties it without changing any box size
        end = i - 4 + int.from_bytes(data[i - 4:i], "big")
        if i + 28 < end < i + 256 and data[i + 28:end].rstrip(b"\0") in (b"VideoHandler", b"SoundHandler"):
            data[i + 28:end] = bytes(end - i - 28)
    Path(out).write_bytes(data)
    return out
