import argparse, json, sys
import numpy as np
from . import audio
from .edit import BUILD, load_edit as load


def times(args):
    """Seconds, with start:end:step ranges expanded (12:13:0.1 is a filmstrip of 10 frames)."""
    out = []
    for a in args:
        if ":" in a:
            t0, t1, step = map(float, a.split(":"))
            out += [round(t, 4) for t in np.arange(t0, t1 - 1e-9, step)]
        else:
            out.append(float(a))
    return out


def main():
    ap = argparse.ArgumentParser(prog="python -m studio")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render", help="render an edit script to exports/<slug>.mp4")
    r.add_argument("script", nargs="?", help="edit slug or script path (default: latest edit)")
    r.add_argument("--workers", type=int)
    r.add_argument("--draft", action="store_true", help="one sample per frame, fast encode, to build/<slug>_draft.mp4")
    p = sub.add_parser("preview", help="contact sheet of the frames at the given times -> build/previews/")
    p.add_argument("times", nargs="*", help="seconds, or start:end:step ranges (default: eight frames)")
    p.add_argument("--edit", help="edit slug or script path (default: latest edit)")
    p.add_argument("--name", default="preview")
    p.add_argument("--cols", type=int, default=4)
    p.add_argument("--scale", type=float, default=0.34)
    s = sub.add_parser("still", help="one full-res frame as png")
    s.add_argument("time", type=float)
    s.add_argument("out")
    s.add_argument("--edit", help="edit slug or script path (default: latest edit)")
    sub.add_parser("songs", help="music library with bpm and drops")
    a = sub.add_parser("analyze", help="beat/drop analysis + plot for a song slug")
    a.add_argument("slug")
    a.add_argument("--bpm", type=float)
    f = sub.add_parser("fetch", help="download a song's official upload from YouTube as mp3")
    f.add_argument("query")
    f.add_argument("slug")
    f.add_argument("--artist", default="")
    x = ap.parse_args()

    if x.cmd == "render":
        load(x.script).render(x.workers, x.draft)
    elif x.cmd == "preview":
        edit = load(x.edit)
        ts = times(x.times) if x.times else np.linspace(0, edit.duration - 1 / edit.fps, 8).tolist()
        print(edit.preview(ts, x.name, x.cols, x.scale))
    elif x.cmd == "still":
        print(load(x.edit).still(x.time, x.out))
    elif x.cmd == "songs":
        for mp3 in sorted(audio.MUSIC.glob("*.mp3")):
            an = audio.analyze(mp3)
            meta = json.loads(mp3.with_suffix(".json").read_text())
            drops = " ".join(f'{d["t"]:.1f}({d["score"]:.0f})' for d in an["drops"])
            print(f'{mp3.stem:34} {an["bpm"]:6.1f}bpm {an["duration"]:6.1f}s  main={an["main_drop"]}  drops: {drops}  | {meta["title"][:50]}')
    elif x.cmd == "analyze":
        path = audio.MUSIC / f"{x.slug}.mp3"
        an = audio.analyze(path, x.bpm)
        out = BUILD / "previews" / f"song_{x.slug}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        audio.plot(path, out)
        print(json.dumps({k: an[k] for k in ("bpm", "duration", "main_drop", "drops")}, indent=1))
        print("downbeats:", " ".join(f"{b:.2f}" for b in an["downbeats"]))
        print("plot:", out)
    elif x.cmd == "fetch":
        print(json.dumps(audio.fetch(x.query, x.slug, x.artist), indent=1))
        audio.analyze(audio.MUSIC / f"{x.slug}.mp3")


if __name__ == "__main__":
    sys.exit(main())
