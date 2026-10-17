# chessStudio

Python tooling that lets AI agents edit viral short-form chess videos (4:5, 1080×1350, 60fps) from code. An agent writes one small script describing the game, timing, captions and music, and the studio renders a finished MP4.

Example: [The Légal Trap on YouTube Shorts](https://www.youtube.com/shorts/qenlkRRqwK4) ([source MP4](exports/the_legal_trap.mp4)), the queen sacrifice produced entirely by this tooling.

## What it does

- **2.5D board renderer:** a tilted, rotating board with flat neo pieces floating in a black void, or standing pieces for cutscenes, with a scriptable camera.
- **Legal-move animation:** feed it a move list and `python-chess` keeps every move legal and timed.
- **Music sync:** analyses a song's beats and drop, splices segments, and lands moves, captures and mate on the beat.
- **Sound effects:** chess.com move sounds plus synthesized whooshes, impacts, booms and risers.
- **Typography and post effects:** eased captions with accent words, adaptive motion blur, vignette and fades.
- **Fast export:** parallel rendering to MP4 with stripped metadata, plus stills, filmstrips and draft renders for quick iteration.

## Layout

- `studio/`: renderer (`board.py`), graphics and effects (`gfx.py`), audio (`audio.py`), timeline and export (`edit.py`), CLI (`__main__.py`).
- `edits/`: one script per video defining `edit = Edit(...)`.
- `exports/`: final MP4s.
- `assets/`: piece sprites, move sounds, the Inter Tight font (OFL), and an empty `music/` folder for your own tracks.
- `AGENTS.md`, `EDIT_RULES.md`, `projectNotes/`: instructions and project memory for AI agents working in the repo.
- `research/`: notes on what makes chess Shorts go viral.

## Quick use

Requires Python 3.14, pycairo, python-chess, OpenCV, NumPy, SciPy, Pillow, matplotlib, yt-dlp and FFmpeg.

```sh
python -m studio preview                  # stills of the latest edit
python -m studio still 12.3 build/frame.png
python -m studio render --draft           # fast draft
python -m studio render                   # final MP4 in exports/
```

Full workflow and rules for agents: [EDIT_RULES.md](EDIT_RULES.md).

## Music

`assets/music/` is empty. Drop in your own tracks (`<name>.mp3`) and reference the name from an edit script, e.g. `SONG = "my_track"`. The example edit `edits/the_legal_trap.py` uses a song that is not included, so point `SONG` at your own track and adjust the `segments` and `drop` timings to its beats before rendering. Make sure you have the rights to any music you use.
