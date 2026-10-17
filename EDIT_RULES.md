# Editing guide

A request to edit a video means **deliver a finished, upload-ready Short in the same run**: research the idea, build the animation, review what you made, fix its real weaknesses, and render the final MP4. Don't stop at a draft or a plan, and don't wait for the user to say "keep going". Ask only when missing information genuinely blocks the work.

## Priorities

1. **The hook.** The first second decides whether people keep watching. Open on something moving, specific, and intriguing, with the hook text already readable on frame 1.
2. **Watch time.** Keep people watching until the end. Cut at a fast pace and keep something happening on screen and in the audio at every moment. No empty or silent stretches, no recap, replay, hero outro, or slow hold at the end. End as soon as the payoff reads.

**Never prolong a video artificially.** A requested or planned duration is an estimate, not a target. If the user says 30 seconds and the story is done at 20, deliver 20. A faster cut beats extra footage that adds no value.

## What works with this audience

- **Animated cutscenes as hooks.** Chess viewers like short cinematic animations: a knight leaping, a queen sliding in, a king being chased. These are animated scenes, not a game playing on a board. Build them in Python, in 2D or 2.5D (the `draw_board` renderer with `Look(board=False, stand=True)` gives a lit, foggy floor with standing pieces). Pieces stay chess pieces: no faces, eyes, or cartoon squash and stretch. Cutscenes can also work mid-video. There is no 3D pipeline; Blender and other 3D tools are not used.
- **Good typography.** Short lines in heavy sans caps (`display` = Inter Tight ExtraBold, `label` = Inter Tight Medium), white with one accent color for the key word, words that land with the action.
- **Purposeful, smooth camera.** Track the action with lead and frame the relevant pieces together. The 2.5D camera (`Cam`/`View`) uses a fixed 20-degree lens; `span` controls framing in board units. It supports yaw, pitch, roll, and depth of field. Keep the piece that matters in frame.
- **No cheap effects.** No targeting circles around pieces, stacked flashes and shakes, or generic hero shots. Every graphic should explain something, like a check line, a route, or the square that matters.
- Viral chess edit channels such as ZaveeCHESS and Strategy Chess are good references, and their theme is the house style: a gray and white board with flat neo pieces floating in a black void, tilted and rotated in 3D, chess.com highlight colors, one accent color per video glowing on the action, punchy title cards. `research/` has sampled frames. Looking at current Shorts from those channels for inspiration is fine.

## Format and deliverable

- Shorts are **4:5, 1080×1350, 60fps** (the `Edit` default).
- The deliverable is **only the MP4** in `exports/<slug>.mp4`. Don't make thumbnails, covers, titles, or descriptions for Shorts.
- Exported files carry no identifying metadata (no tool, encoder, or source tags). `export_clean` handles this; don't add tags.

## Tests and quality checks are forbidden

Don't write tests, and don't add or run automated video quality checks: no test files, no lint or scoring scripts, no caption-bounds, reading-speed, smoothness, loudness, frame-count, or sync-plot passes over a render. They measure the wrong things and push edits toward arbitrary metrics. Review an edit by looking at it: preview stills while building, and frames pulled from the exported MP4 at the moments that matter.

## Keep the latest three edits

The project keeps only the three most recent edits. Each kept edit has:
- `edits/<slug>.py`, the complete build;
- `exports/<slug>.mp4`, the final video;
- `projectNotes/<slug>_final_build.md`, a record of the agreed final version: story beats, chess line and sources, music splice, camera and caption decisions, and what the user asked to change.

That record lets a later "fix this" or "polish that" request start from the agreed version instead of reinventing it. Keep it accurate whenever the edit changes. When a fourth edit is finished, delete the oldest edit's script, export, and final-build note. `build/` holds disposable previews and render scratch and can be deleted at any time.

## Building an edit

1. Pick a topic that isn't in `projectNotes/past_videos_and_topics.md`. Choose the hook, the payoff, and the shortest understandable path between them.
2. Verify the chess. `Game` validates SAN; assert `is_checkmate()` for claimed mates. Verify historical games against a reliable source, and mark hypothetical lines on screen.
3. Choose music that fits the story, and splice it to fit the edit (`segments`). Don't stretch the edit to fill the music. Drops and beats from the analysis are suggestions, so look at the waveform plot from `analyze` before trusting one.
4. Build, preview stills at the key moments, render, and look at frames from the export: the opening, each transition, the important moves, and the ending. Fix whatever is weakest (a slow hook, an unclear move, a piece out of frame, a dead moment, a cheap-looking graphic) and render again.

```sh
python -m studio songs                       # music library with bpm and drops
python -m studio analyze <song_slug>          # beats/drops + waveform plot
python -m studio fetch "<title> <artist>" <slug> --artist "<artist>"
python -m studio preview 0 1.5 3.2 --name review   # latest edit; --edit <slug> selects another
python -m studio preview 9:11:0.1 --cols 10 --scale 0.18   # filmstrip of a range
python -m studio render --draft   # fast one-sample render -> build/<slug>_draft.mp4
python -m studio still 12.3 build/frame.png
python -m studio render <slug>       # -> exports/<slug>.mp4; slug defaults to the latest edit
```
